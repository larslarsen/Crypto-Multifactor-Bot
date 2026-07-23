#!/usr/bin/env python3
"""Fetch the CoinMarketCap survivorship graveyard (inactive/dead coins) + birth/death dates.

READ-ONLY, one-shot, rate-limited. No API key, no R, no external deps (stdlib only).

PROVENANCE — how these endpoints were derived (so the next model isn't reverse-engineering
from scratch):
  The user was pointed at the `crypto2` R package (CRAN, GPL) which scrapes CoinMarketCap
  without an API key. crypto2's `construct_url()` hard-codes its base URLs BASE64-OBSCURED
  (not for secrecy — to dodge breakage detection). The decoded bases (from
  R/extras.R) are:
      aHR0cHM6Ly9hcGkuY29pbm1hcmtldGNhcC5jb20vZGF0YS1hcGkvdjEv        -> .../data-api/v1/
      aHR0cHM6Ly9hcGkuY29pbm1hcmtldGNhcC5jb20vZGF0YS1hcGkvdjMv        -> .../data-api/v3/
      aHR0cHM6Ly9hcGkuY29pbm1hcmtldGNhcC5jb20vZGF0YS1hcGkvdjMuMS8=    -> .../data-api/v3.1/
      aHR0cHM6Ly9hcGkuY29pbm1hcmtldGNhcC5jb20vYWdnci92My8=            -> .../aggr/v3/
  crypto2's `crypto_list(only_active=FALSE)` calls:
      R/crypto_list.R  -> path = "cryptocurrency/map?listing_status=inactive"
  NOTE: crypto2's documented `crypto_history`/scrape routines hit the v3/v3.1 detail
  endpoints; the INACTIVE MAP itself resolves on the OLDER `data-api/v1/map`, while the
  per-coin DETAIL (with dates) resolves on `data-api/v3/cryptocurrency/detail`. The
  `aggr/v3` base 404s for these paths now — don't assume the last base64 entry is live;
  test each. We confirmed live (2026-07-22):
      GET https://api.coinmarketcap.com/data-api/v1/cryptocurrency/map?listing_status=inactive
          -> 1,756 dead coins, fields {id,name,symbol,slug,is_active=0}
      GET https://api.coinmarketcap.com/data-api/v3/cryptocurrency/detail?id=<id>
          -> {dateLaunched, dateAdded, latestUpdateTime, status, ...}

THIS IS CMC'S UNDOCUMENTED WEBSITE BACK-END, NOT THE OFFICIAL PAID API. It works today
without a key but is NOT contractually stable and has no SLA. Treat output as a CANDIDATE
survivorship universe pending source-authority review (UNIVERSE-003), not an accepted
authority. Suitable for a ONE-SHOT backfill; NOT a recurring live dependency.

Two-step:
  1. map?listing_status=inactive  -> full dead-coin identity list (1 cheap call)
  2. detail?id=<id>               -> per-coin dates (1 call per coin; one-shot backfill)

Date fields (per dead coin) — semantics matter, read carefully:
  - dateLaunched / dateAdded : birth  (first_historical_data proxy; adequate for
                                   point-in-time membership START)
  - latestUpdateTime         : last CMC activity = death-date PROXY. This is NOT an
                                   authoritative exchange delisting/halt time and carries NO
                                   final tradable price and NO failure cause. Do not launder
                                   this into an "authoritative delisting date" field.
  See UNIVERSE-003 for the DF-08 implication (G08 likely satisfied; G06 final-price/
  failure-cause NOT satisfied by this source alone).

IMPORTANT for downstream consumers: label every row with provenance
(death_date_is_proxy=true, source=cmc_data_api_unofficial, retrieved_at=...) so proxy
dates are never silently treated as authoritative.

Usage:
  python3 fetch_cmc_dead_universe.py --limit 25            # sample (detail for 25)
  python3 fetch_cmc_dead_universe.py                       # full (~1.7k detail calls)
  python3 fetch_cmc_dead_universe.py --out dead.csv --sleep 0.4
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.request
from typing import Any

MAP_URL = (
    "https://api.coinmarketcap.com/data-api/v1/cryptocurrency/map"
    "?listing_status=inactive"
)
DETAIL_URL = "https://api.coinmarketcap.com/data-api/v3/cryptocurrency/detail?id={id}"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
FIELDS = [
    "id", "name", "symbol", "slug", "is_active",
    "dateLaunched", "dateAdded", "latestUpdateTime",
    "birth_date", "death_proxy_date", "status",
    "death_date_is_proxy", "source", "retrieved_at",
]
RETRIEVED_AT = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _get(url: str, timeout: int = 40) -> dict[str, Any]:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())  # type: ignore[no-any-return]


def fetch_inactive_map() -> list[dict[str, Any]]:
    d = _get(MAP_URL, timeout=60)
    if (d.get("status") or {}).get("error_message", "SUCCESS") != "SUCCESS":
        raise RuntimeError(f"map error: {d.get('status')}")
    return d.get("data") or []


def fetch_detail(coin_id: int, retries: int = 3, sleep: float = 0.4) -> dict[str, Any]:
    for attempt in range(retries):
        try:
            d = _get(DETAIL_URL.format(id=coin_id))
            return d.get("data") or {}
        except Exception:  # noqa: BLE001 - one-shot scratch tool, retry then skip
            if attempt == retries - 1:
                return {}
            time.sleep(sleep * (attempt + 2))
    return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="detail calls (0=all dead coins)")
    ap.add_argument("--sleep", type=float, default=0.4, help="seconds between detail calls")
    ap.add_argument("--out", default="cmc_dead_universe.csv")
    args = ap.parse_args()

    coins = fetch_inactive_map()
    print(f"inactive (dead) coins in map: {len(coins)}", file=sys.stderr)
    targets = coins[: args.limit] if args.limit else coins
    print(f"fetching detail for {len(targets)} coins (sleep={args.sleep}s)...", file=sys.stderr)

    rows = []
    for i, c in enumerate(targets, 1):
        det = fetch_detail(c["id"], sleep=args.sleep)
        birth_date = det.get("dateAdded") or det.get("dateLaunched") or c.get("dateAdded") or c.get("dateLaunched")
        death_proxy = det.get("latestUpdateTime") or c.get("latestUpdateTime")
        rows.append({
            "id": c.get("id"),
            "name": c.get("name"),
            "symbol": c.get("symbol"),
            "slug": c.get("slug"),
            "is_active": c.get("is_active"),
            "dateLaunched": det.get("dateLaunched"),
            "dateAdded": det.get("dateAdded"),
            "latestUpdateTime": det.get("latestUpdateTime"),
            "birth_date": birth_date,
            "death_proxy_date": death_proxy,
            "status": det.get("status"),
            # provenance labels — these are CMC-observed proxy dates from an UNDOCUMENTED
            # endpoint, not authoritative exchange delisting records. Never launder.
            "death_date_is_proxy": "true",
            "source": "cmc_data_api_unofficial",
            "retrieved_at": RETRIEVED_AT,
        })
        if i % 25 == 0 or i == len(targets):
            print(f"  [{i}/{len(targets)}] {c.get('symbol')}", file=sys.stderr)
        time.sleep(args.sleep)

    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {args.out}", file=sys.stderr)

    dated = sum(1 for r in rows if r["latestUpdateTime"])
    print(f"rows with death-proxy date (latestUpdateTime): {dated}/{len(rows)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
