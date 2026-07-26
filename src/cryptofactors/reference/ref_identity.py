"""ARCH-003 catalog-backed reference identity resolution.

Reference identities remain catalog TEXT keys. Integer IDs are resolved only
through ``ref_*_surrogate`` compatibility tables; no catalog key is cast.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from cryptofactors.reference.errors import ReferenceNotFoundError
from cryptofactors.reference.models import dt_to_iso, ensure_utc


@dataclass(frozen=True, slots=True)
class ListingIdentity:
    """One active listing resolved under valid and knowledge time."""

    listing_event_id: str
    instrument_id: str
    canonical_instrument_id: int
    venue: str
    venue_symbol: str


class ReferenceIdentityResolver:
    """Explicit catalog resolver; callers own the database dependency."""

    def __init__(self, database: Path | str) -> None:
        self._database = Path(database)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._database)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _time(value: datetime, label: str) -> str:
        try:
            return dt_to_iso(ensure_utc(value))
        except (AttributeError, ValueError) as exc:
            raise ValueError(f"{label} must be timezone-aware") from exc

    def listing_identities_at(
        self,
        venue: str,
        valid_at: datetime,
        known_at: datetime,
        venue_symbol: str | None = None,
    ) -> tuple[ListingIdentity, ...]:
        """Resolve active listing lifecycle state under both time dimensions."""
        valid = self._time(valid_at, "valid_at")
        known = self._time(known_at, "known_at")
        symbol_clause = " AND upper(v.venue_symbol) = upper(?)" if venue_symbol else ""
        params: list[str] = [venue, valid, valid, known, known]
        if venue_symbol:
            params.append(venue_symbol)
        conn = self._connect()
        try:
            rows = conn.execute(
                "WITH active_events AS ("
                " SELECT l.listing_event_id, l.instrument_id, v.venue_symbol, l.event_type, "
                " row_number() OVER (PARTITION BY l.listing_id "
                " ORDER BY l.valid_from DESC, l.known_from DESC, l.listing_event_id DESC) AS rn "
                " FROM ref_listing_event l JOIN ref_venue_listing v ON v.listing_id = l.listing_id "
                " JOIN ref_venue venue ON venue.venue_id = v.venue_id "
                " WHERE upper(venue.venue_code) = upper(?) "
                " AND l.valid_from <= ? AND (l.valid_to IS NULL OR l.valid_to > ?) "
                " AND l.known_from <= ? AND (l.known_to IS NULL OR l.known_to > ?)"
                + symbol_clause
                + ") "
                "SELECT e.listing_event_id, e.instrument_id, s.canonical_instrument_id, "
                "e.venue_symbol FROM active_events e "
                "JOIN ref_instrument_surrogate s ON s.instrument_id = e.instrument_id "
                "WHERE e.rn = 1 AND e.event_type IN ('LIST', 'RESUME') "
                "ORDER BY e.venue_symbol",
                params,
            ).fetchall()
        finally:
            conn.close()
        return tuple(
            ListingIdentity(
                listing_event_id=str(row["listing_event_id"]),
                instrument_id=str(row["instrument_id"]),
                canonical_instrument_id=int(row["canonical_instrument_id"]),
                venue=venue.upper(),
                venue_symbol=str(row["venue_symbol"]),
            )
            for row in rows
        )

    def listing_events_known_at(self, venue: str, known_at: datetime) -> tuple[dict[str, object], ...]:
        """Return listing lifecycle events available by the immutable snapshot cutoff."""
        known = self._time(known_at, "known_at")
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT l.listing_event_id, l.event_type, v.venue_symbol, l.valid_from, l.valid_to, "
                "l.known_from, l.known_to, s.canonical_instrument_id FROM ref_listing_event l "
                "JOIN ref_venue_listing v ON v.listing_id = l.listing_id "
                "JOIN ref_venue venue_row ON venue_row.venue_id = v.venue_id "
                "JOIN ref_instrument_surrogate s ON s.instrument_id = l.instrument_id "
                "WHERE upper(venue_row.venue_code) = upper(?) AND l.known_from <= ? "
                "AND (l.known_to IS NULL OR l.known_to > ?) "
                "ORDER BY l.venue_symbol, l.valid_from, l.known_from, l.listing_event_id",
                (venue, known, known),
            ).fetchall()
        finally:
            conn.close()
        return tuple({key: row[key] for key in row} for row in rows)

    def resolve_instrument_id(
        self,
        venue: str,
        venue_symbol: str,
        as_of: datetime,
        known_at: datetime,
    ) -> int:
        identities = self.listing_identities_at(venue, as_of, known_at, venue_symbol)
        if len(identities) != 1:
            raise ReferenceNotFoundError(
                "active venue listing not found",
                context={"venue": venue, "venue_symbol": venue_symbol},
            )
        return identities[0].canonical_instrument_id

    def resolve_contract_id(self, chain: str, address: str) -> int:
        """Resolve an exact chain/address token-contract identity."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT s.canonical_instrument_id FROM ref_instrument i "
                "JOIN ref_instrument_surrogate s ON s.instrument_id = i.instrument_id "
                "WHERE i.identity_kind = 'token_contract' AND i.chain = ? AND i.address = ?",
                (chain, address),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            raise ReferenceNotFoundError(
                "token contract not found", context={"chain": chain, "address": address}
            )
        return int(row["canonical_instrument_id"])

    def asset_id_for_instrument(self, instrument_id: int) -> int:
        """Resolve a canonical instrument surrogate to an asset surrogate."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT a.canonical_asset_id FROM ref_instrument_surrogate i "
                "JOIN ref_instrument r ON r.instrument_id = i.instrument_id "
                "JOIN ref_asset_surrogate a ON a.asset_id = r.asset_id "
                "WHERE i.canonical_instrument_id = ?",
                (instrument_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            raise ReferenceNotFoundError(
                "instrument surrogate not found", context={"instrument_id": instrument_id}
            )
        return int(row["canonical_asset_id"])


def resolve_instrument_id(
    venue: str,
    venue_symbol: str,
    as_of: datetime,
    *,
    known_at: datetime,
    resolver: ReferenceIdentityResolver,
) -> int:
    """Resolve through an explicit catalog resolver."""
    return resolver.resolve_instrument_id(venue, venue_symbol, as_of, known_at)


def resolve_contract_id(
    chain: str, address: str, *, resolver: ReferenceIdentityResolver
) -> int:
    """Resolve a token contract through an explicit catalog resolver."""
    return resolver.resolve_contract_id(chain, address)


def asset_id_for_instrument(
    instrument_id: int, *, resolver: ReferenceIdentityResolver
) -> int:
    """Resolve an asset through an explicit catalog resolver."""
    return resolver.asset_id_for_instrument(instrument_id)
