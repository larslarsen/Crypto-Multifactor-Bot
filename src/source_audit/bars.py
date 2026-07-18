"""Deterministic trade-to-OHLCV reconstruction and provider-candle comparison.

Timestamp units are never inferred inside this module. Callers must supply
timezone-aware UTC datetimes on every trade.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from .errors import BarReconstructionError, InvalidNumericError
from .models import (
    BarComparisonResult,
    BarFieldMismatch,
    BarReconstructionResult,
    DuplicateTradeReport,
    IntervalClosure,
    OHLCVBar,
    Trade,
)


def _require_utc(ts: datetime, *, field_name: str) -> datetime:
    if not isinstance(ts, datetime):
        raise BarReconstructionError(
            f"{field_name} must be a datetime",
            context={"type": type(ts).__name__},
        )
    if ts.tzinfo is None:
        raise BarReconstructionError(
            f"{field_name} must be timezone-aware UTC",
            context={"value": str(ts)},
        )
    return ts.astimezone(timezone.utc)


def _to_decimal(value: Any, *, field_name: str) -> Decimal:
    if isinstance(value, bool):
        raise InvalidNumericError(f"{field_name}: boolean is not a valid financial value")
    if isinstance(value, Decimal):
        dec = value
    elif isinstance(value, int):
        dec = Decimal(value)
    elif isinstance(value, str):
        try:
            dec = Decimal(value)
        except (InvalidOperation, ValueError) as exc:
            raise InvalidNumericError(
                f"{field_name}: invalid Decimal string {value!r}"
            ) from exc
    elif isinstance(value, float):
        raise InvalidNumericError(
            f"{field_name}: float is rejected; use Decimal or string"
        )
    else:
        raise InvalidNumericError(
            f"{field_name}: unsupported type {type(value).__name__}"
        )
    if not dec.is_finite():
        raise InvalidNumericError(f"{field_name}: non-finite value {dec}")
    if dec < 0:
        raise InvalidNumericError(f"{field_name}: negative value {dec}")
    return dec


def normalize_trade(
    raw: Mapping[str, Any],
    *,
    timestamp_key: str = "timestamp_utc",
    price_key: str = "price",
    quantity_key: str = "quantity",
    trade_id_key: str = "trade_id",
    quote_quantity_key: str | None = "quote_quantity",
    derive_trade_id: bool = False,
) -> Trade:
    """Normalize a raw mapping into a :class:`Trade`.

    If ``derive_trade_id`` is True and ``trade_id_key`` is absent, a stable identity
    is derived from ``(timestamp_utc.isoformat(), price, quantity, sequential hash)``
    is **not** used — callers must supply ``trade_id`` or set ``derive_trade_id`` with
    a deterministic formula based on fields present.
    """
    if timestamp_key not in raw:
        raise BarReconstructionError(
            f"Missing timestamp key {timestamp_key!r}",
            context={"keys": sorted(raw.keys())},
        )
    ts = _require_utc(raw[timestamp_key], field_name=timestamp_key)
    price = _to_decimal(raw[price_key], field_name=price_key)
    qty = _to_decimal(raw[quantity_key], field_name=quantity_key)
    if price <= 0:
        raise InvalidNumericError(f"{price_key}: price must be > 0 (non-positive rejected)")
    if qty <= 0:
        raise InvalidNumericError(
            f"{quantity_key}: quantity must be > 0 (non-positive/invalid rejected)"
        )

    quote: Decimal | None = None
    if quote_quantity_key is not None and quote_quantity_key in raw and raw[quote_quantity_key] is not None:
        quote = _to_decimal(raw[quote_quantity_key], field_name=quote_quantity_key)

    if trade_id_key in raw and raw[trade_id_key] is not None:
        trade_id = str(raw[trade_id_key])
    elif derive_trade_id:
        # Deterministic derived identity from timestamp, price, quantity.
        trade_id = f"{ts.isoformat()}|{price}|{qty}"
    else:
        raise BarReconstructionError(
            "trade_id is required unless derive_trade_id=True",
            context={"keys": sorted(raw.keys())},
        )

    return Trade(
        timestamp_utc=ts,
        price=price,
        quantity=qty,
        trade_id=trade_id,
        quote_quantity=quote,
    )


def _align_interval_start(
    ts: datetime,
    *,
    interval: timedelta,
    origin: datetime,
) -> datetime:
    """Return the left edge of the interval containing ``ts``.

    Alignment: ``origin + n * interval`` where ``n = floor((ts - origin) / interval)``.
    """
    origin_utc = _require_utc(origin, field_name="alignment_origin_utc")
    ts_utc = _require_utc(ts, field_name="timestamp_utc")
    delta = ts_utc - origin_utc
    # Integer floor division on whole microseconds to avoid float drift.
    delta_us = (
        delta.days * 86_400_000_000
        + delta.seconds * 1_000_000
        + delta.microseconds
    )
    step_us = (
        interval.days * 86_400_000_000
        + interval.seconds * 1_000_000
        + interval.microseconds
    )
    if step_us <= 0:
        raise BarReconstructionError("interval_duration must be positive")
    n = delta_us // step_us
    return origin_utc + timedelta(microseconds=n * step_us)


def _in_interval(
    ts: datetime,
    start: datetime,
    end: datetime,
    closure: IntervalClosure,
) -> bool:
    if closure is IntervalClosure.LEFT_CLOSED_RIGHT_OPEN:
        return start <= ts < end
    if closure is IntervalClosure.LEFT_OPEN_RIGHT_CLOSED:
        return start < ts <= end
    raise BarReconstructionError(f"Unknown closure: {closure}")


def reconstruct_bars(
    trades: Sequence[Trade | Mapping[str, Any]],
    *,
    interval_duration: timedelta,
    alignment_origin_utc: datetime,
    closure: IntervalClosure = IntervalClosure.LEFT_CLOSED_RIGHT_OPEN,
    normalize_kwargs: Mapping[str, Any] | None = None,
) -> BarReconstructionResult:
    """Reconstruct OHLCV bars from trades.

    Rules
    -----
    - No implicit zero-filled bars for absent intervals.
    - Sort key: ``(timestamp_utc, trade_id)`` — deterministic under reordering.
    - Identical timestamps are ordered by ``trade_id`` (stable tie-break).
    - Duplicate ``trade_id`` values are reported; the first occurrence in sorted
      order is kept for aggregation, subsequent ones are excluded from OHLCV
      but counted in ``duplicate_trades``.
    - Prices and quantities are ``Decimal``.
    """
    if interval_duration.total_seconds() <= 0:
        raise BarReconstructionError("interval_duration must be positive")
    origin = _require_utc(alignment_origin_utc, field_name="alignment_origin_utc")

    norm_kw = dict(normalize_kwargs or {})
    normalized: list[Trade] = []
    for item in trades:
        if isinstance(item, Trade):
            # Validate direct Trade objects identically to mapping inputs.
            ts = _require_utc(item.timestamp_utc, field_name="timestamp_utc")
            price = _to_decimal(item.price, field_name="price")
            qty = _to_decimal(item.quantity, field_name="quantity")
            if price <= 0:
                raise InvalidNumericError(
                    "price: price must be > 0 (non-positive rejected)"
                )
            if qty <= 0:
                raise InvalidNumericError(
                    "quantity: quantity must be > 0 (non-positive/invalid rejected)"
                )
            if not str(item.trade_id):
                raise BarReconstructionError("trade_id must be a non-empty string")
            quote: Decimal | None = None
            if item.quote_quantity is not None:
                quote = _to_decimal(item.quote_quantity, field_name="quote_quantity")
            normalized.append(
                Trade(
                    timestamp_utc=ts,
                    price=price,
                    quantity=qty,
                    trade_id=str(item.trade_id),
                    quote_quantity=quote,
                )
            )
        else:
            normalized.append(normalize_trade(item, **norm_kw))

    input_count = len(normalized)
    id_counts = Counter(t.trade_id for t in normalized)
    duplicates = tuple(
        DuplicateTradeReport(trade_id=tid, occurrences=cnt)
        for tid, cnt in sorted(id_counts.items())
        if cnt > 1
    )

    # Sort deterministically; keep first of each trade_id.
    sorted_trades = sorted(normalized, key=lambda t: (t.timestamp_utc, t.trade_id))
    seen_ids: set[str] = set()
    unique: list[Trade] = []
    for t in sorted_trades:
        if t.trade_id in seen_ids:
            continue
        seen_ids.add(t.trade_id)
        unique.append(t)

    # Bucket by aligned interval start.
    buckets: dict[datetime, list[Trade]] = defaultdict(list)
    for t in unique:
        start = _align_interval_start(
            t.timestamp_utc, interval=interval_duration, origin=origin
        )
        end = start + interval_duration
        # Verify membership under closure; for left-closed/right-open, alignment
        # guarantees membership. For left-open/right-closed, a trade exactly on
        # start belongs to the previous interval — re-check.
        if not _in_interval(t.timestamp_utc, start, end, closure):
            if closure is IntervalClosure.LEFT_OPEN_RIGHT_CLOSED:
                start = start - interval_duration
                end = start + interval_duration
                if not _in_interval(t.timestamp_utc, start, end, closure):
                    raise BarReconstructionError(
                        "Trade does not fall into any interval under closure",
                        context={
                            "trade_id": t.trade_id,
                            "timestamp": t.timestamp_utc.isoformat(),
                        },
                    )
            else:
                raise BarReconstructionError(
                    "Trade does not fall into aligned interval",
                    context={
                        "trade_id": t.trade_id,
                        "timestamp": t.timestamp_utc.isoformat(),
                    },
                )
        buckets[start].append(t)

    bars: list[OHLCVBar] = []
    for start in sorted(buckets.keys()):
        bucket = buckets[start]
        # Already sorted globally; preserve order within bucket.
        bucket_sorted = sorted(bucket, key=lambda t: (t.timestamp_utc, t.trade_id))
        prices = [t.price for t in bucket_sorted]
        base_vol = sum((t.quantity for t in bucket_sorted), Decimal("0"))
        quote_vol = Decimal("0")
        for t in bucket_sorted:
            if t.quote_quantity is not None:
                quote_vol += t.quote_quantity
            else:
                quote_vol += t.price * t.quantity
        bars.append(
            OHLCVBar(
                interval_start_utc=start,
                interval_end_utc=start + interval_duration,
                open=prices[0],
                high=max(prices),
                low=min(prices),
                close=prices[-1],
                volume_base=base_vol,
                volume_quote=quote_vol,
                trade_count=len(bucket_sorted),
            )
        )

    return BarReconstructionResult(
        bars=tuple(bars),
        input_trade_count=input_count,
        unique_trade_count=len(unique),
        duplicate_trades=duplicates,
        interval_duration_s=int(interval_duration.total_seconds()),
        alignment_origin_utc=origin,
        closure=closure,
    )


def _dec_str(value: Decimal | int | str) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def _provider_bar_from_mapping(
    raw: Mapping[str, Any],
    *,
    timestamp_key: str,
    open_key: str,
    high_key: str,
    low_key: str,
    close_key: str,
    base_volume_key: str,
    quote_volume_key: str | None,
    trade_count_key: str | None,
    interval_duration: timedelta,
) -> OHLCVBar:
    ts = raw[timestamp_key]
    if not isinstance(ts, datetime):
        raise BarReconstructionError(
            "Provider bar timestamp must be datetime (units already resolved)"
        )
    ts_utc = _require_utc(ts, field_name=timestamp_key)
    o = _to_decimal(raw[open_key], field_name=open_key)
    h = _to_decimal(raw[high_key], field_name=high_key)
    low = _to_decimal(raw[low_key], field_name=low_key)
    c = _to_decimal(raw[close_key], field_name=close_key)
    base = _to_decimal(raw[base_volume_key], field_name=base_volume_key)
    if quote_volume_key is None or quote_volume_key not in raw:
        raise BarReconstructionError(
            "Provider bar missing quote volume field",
            context={"quote_volume_key": quote_volume_key},
        )
    quote = _to_decimal(raw[quote_volume_key], field_name=quote_volume_key)
    if trade_count_key is None or trade_count_key not in raw:
        raise BarReconstructionError(
            "Provider bar missing trade_count field",
            context={"trade_count_key": trade_count_key},
        )
    tc_raw = raw[trade_count_key]
    if isinstance(tc_raw, bool) or not isinstance(tc_raw, int):
        raise InvalidNumericError("trade_count must be an int")
    return OHLCVBar(
        interval_start_utc=ts_utc,
        interval_end_utc=ts_utc + interval_duration,
        open=o,
        high=h,
        low=low,
        close=c,
        volume_base=base,
        volume_quote=quote,
        trade_count=tc_raw,
    )


def compare_bars(
    reconstructed: Sequence[OHLCVBar],
    provider: Sequence[OHLCVBar | Mapping[str, Any]],
    *,
    price_tolerance: Decimal,
    volume_tolerance: Decimal,
    trade_count_tolerance: int = 0,
    interval_duration: timedelta | None = None,
    provider_field_map: Mapping[str, str] | None = None,
) -> BarComparisonResult:
    """Compare reconstructed bars to provider candles with explicit Decimal tolerances.

    Does not silently coerce units or ignore missing fields.
    """
    if not isinstance(price_tolerance, Decimal) or price_tolerance < 0:
        raise InvalidNumericError("price_tolerance must be a non-negative Decimal")
    if not isinstance(volume_tolerance, Decimal) or volume_tolerance < 0:
        raise InvalidNumericError("volume_tolerance must be a non-negative Decimal")
    if trade_count_tolerance < 0:
        raise InvalidNumericError("trade_count_tolerance must be >= 0")

    fmap = {
        "timestamp_key": "interval_start_utc",
        "open_key": "open",
        "high_key": "high",
        "low_key": "low",
        "close_key": "close",
        "base_volume_key": "volume_base",
        "quote_volume_key": "volume_quote",
        "trade_count_key": "trade_count",
    }
    if provider_field_map:
        fmap.update(dict(provider_field_map))

    provider_bars: list[OHLCVBar] = []
    for item in provider:
        if isinstance(item, OHLCVBar):
            provider_bars.append(item)
        else:
            if interval_duration is None:
                raise BarReconstructionError(
                    "interval_duration is required when provider bars are mappings"
                )
            provider_bars.append(
                _provider_bar_from_mapping(
                    item,
                    timestamp_key=fmap["timestamp_key"],
                    open_key=fmap["open_key"],
                    high_key=fmap["high_key"],
                    low_key=fmap["low_key"],
                    close_key=fmap["close_key"],
                    base_volume_key=fmap["base_volume_key"],
                    quote_volume_key=fmap["quote_volume_key"],
                    trade_count_key=fmap["trade_count_key"],
                    interval_duration=interval_duration,
                )
            )

    recon_by_start: dict[datetime, list[OHLCVBar]] = defaultdict(list)
    for bar in reconstructed:
        recon_by_start[bar.interval_start_utc].append(bar)

    prov_by_start: dict[datetime, list[OHLCVBar]] = defaultdict(list)
    for bar in provider_bars:
        prov_by_start[bar.interval_start_utc].append(bar)

    duplicate_provider = tuple(
        sorted(ts for ts, bars_list in prov_by_start.items() if len(bars_list) > 1)
    )
    duplicate_reconstructed = tuple(
        sorted(ts for ts, bars_list in recon_by_start.items() if len(bars_list) > 1)
    )

    missing_from_provider: list[datetime] = []
    missing_from_reconstructed: list[datetime] = []
    ohlc: list[BarFieldMismatch] = []
    base_m: list[BarFieldMismatch] = []
    quote_m: list[BarFieldMismatch] = []
    tc_m: list[BarFieldMismatch] = []
    align_m: list[BarFieldMismatch] = []

    recon_keys = set(recon_by_start)
    prov_keys = set(prov_by_start)

    for ts in sorted(recon_keys - prov_keys):
        missing_from_provider.append(ts)
    for ts in sorted(prov_keys - recon_keys):
        missing_from_reconstructed.append(ts)

    def _mismatch(
        ts: datetime,
        field_name: str,
        expected: Decimal | int,
        observed: Decimal | int,
        abs_delta: Decimal | int | None,
        signed: Decimal | int | None,
    ) -> BarFieldMismatch:
        return BarFieldMismatch(
            interval_start_utc=ts,
            field_name=field_name,
            expected=_dec_str(expected),
            observed=_dec_str(observed),
            absolute_delta=None if abs_delta is None else _dec_str(abs_delta),
            signed_delta=None if signed is None else _dec_str(signed),
        )

    for ts in sorted(recon_keys & prov_keys):
        # Never overwrite duplicates: use first observation for field compare;
        # duplicates are reported separately.
        r = recon_by_start[ts][0]
        p = prov_by_start[ts][0]

        if r.interval_end_utc != p.interval_end_utc:
            align_m.append(
                BarFieldMismatch(
                    interval_start_utc=ts,
                    field_name="interval_end_utc",
                    expected=r.interval_end_utc.isoformat(),
                    observed=p.interval_end_utc.isoformat(),
                    absolute_delta=None,
                    signed_delta=None,
                )
            )

        for field_name, rv, pv in (
            ("open", r.open, p.open),
            ("high", r.high, p.high),
            ("low", r.low, p.low),
            ("close", r.close, p.close),
        ):
            delta = rv - pv
            if abs(delta) > price_tolerance:
                ohlc.append(
                    _mismatch(ts, field_name, pv, rv, abs(delta), delta)
                )

        bdelta = r.volume_base - p.volume_base
        if abs(bdelta) > volume_tolerance:
            base_m.append(
                _mismatch(ts, "volume_base", p.volume_base, r.volume_base, abs(bdelta), bdelta)
            )

        qdelta = r.volume_quote - p.volume_quote
        if abs(qdelta) > volume_tolerance:
            quote_m.append(
                _mismatch(
                    ts, "volume_quote", p.volume_quote, r.volume_quote, abs(qdelta), qdelta
                )
            )

        tdelta = r.trade_count - p.trade_count
        if abs(tdelta) > trade_count_tolerance:
            tc_m.append(
                _mismatch(ts, "trade_count", p.trade_count, r.trade_count, abs(tdelta), tdelta)
            )

    return BarComparisonResult(
        missing_from_provider=tuple(missing_from_provider),
        missing_from_reconstructed=tuple(missing_from_reconstructed),
        ohlc_mismatches=tuple(ohlc),
        base_volume_mismatches=tuple(base_m),
        quote_volume_mismatches=tuple(quote_m),
        trade_count_mismatches=tuple(tc_m),
        timestamp_alignment_mismatches=tuple(align_m),
        duplicate_provider_intervals=duplicate_provider,
        duplicate_reconstructed_intervals=duplicate_reconstructed,
        price_tolerance=price_tolerance,
        volume_tolerance=volume_tolerance,
        trade_count_tolerance=trade_count_tolerance,
    )
