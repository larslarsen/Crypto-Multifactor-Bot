# Kraken - USDTZUSD

**Candidate:** Kraken spot USDT/USD (pair USDTZUSD)

**Fetch method:** Public REST /0/public/OHLC

**Sample captured:**
- 30d daily: sha=8dfd26f... size=2744
- Depeg period (2022): sha=5d0b72... size=62214 , showed rates ~0.9987

**Timestamps:**
- OHLC returns [timestamp, open, high, low, close, vwap, volume, count]
- Timestamp is unix seconds.
- No explicit "publication time" separate; assumed close time is observation.
- Retrieval time captured.

**Availability/Revision:**
- Historical data available via API for past periods.
- Data appears immutable for past bars (no revision observed in sample).
- For PIT: can query with since, but full historical requires multiple pages or downloadable.

**Direct USD anchor:** Yes, USDTZUSD is direct.

**Depeg coverage:** Sample from 2022 period captured rates below 0.999.

**Direction:** Close price is USDT per USD? Wait, in Kraken, USDTZUSD is USDT quoted in ZUSD, so price is USD per USDT? Need to confirm.

From sample: 0.9987 means 1 USDT ~ 0.9987 USD.

Direction: USD received per USDT = the price.

**Licensing:** Public market data, free to use with attribution per Kraken terms.

**Conclusion for PIT:** Viable for historical if full archive fetched. Has depeg evidence. Good candidate.

