# Binance (source note - corrected)

**Capture:**
- URL: https://api.binance.com/api/v3/exchangeInfo?symbol=USDTUSDC
- Result: {"code":-1121,"msg":"Invalid symbol."}
- Proof: no such direct pair.
- To confirm no direct USD anchor: Binance uses USDT as quote for most, no primary stable-to-USD fiat pair for anchor.
- Evidence from exchangeInfo (or cite accepted bar audit).

**Gates:**
- direct_usd_anchor: no
- recommend: SECONDARY ONLY

**Stable pairs are cross, not independent USD.**

