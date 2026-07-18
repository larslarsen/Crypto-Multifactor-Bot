## Universe and portfolio test

Not specified until data pass audit. Candidate design: weekly cross-sectional sort on the
FDV premium and/or trailing dilution rate; top-minus-bottom or long-low-dilution portfolios;
equal-weight primary with liquidity-capped secondary; net of conservative trading costs.
Must exclude blue-chip/mature coins if the effect proves concentrated in the first trading
year (LIT-030).

## Controls and neutralization

Control for market, size, momentum, liquidity, and network-value characteristics before
attributing premia to dilution. Latent/hidden-factor controls required (LIT-029, LIT-031).

## Costs/capacity concerns

Unlock-driven flows and thin float make capacity and impact sensitive; costs must use
point-in-time spreads/depth (DF-09). Small/illiquid legs may not survive realistic costs.

## Primary metrics

Net long-short return, information coefficient, quintile monotonicity, subperiod and
venue stability, turnover, crash behavior, and dilution-attribution of returns.

## Robustness tests

- persistence outside the first trading year;
- blue-chip vs new-asset split;
- FDV-premium vs realized-supply-growth decomposition;
- cost sensitivity;
- hidden-factor and accepted-crypto-factor neutrality.

## Rejection criteria

- effect exists only with look-ahead from later supply corrections;
- no point-in-time supply/unlock series exists;
- vanishes after conservative costs or accepted-factor controls;
- concentrated in one era or a few assets without a prespecified explanation.

## Experiment IDs

None yet (deferred).

## Result history

None. Literature basis: Guo (2026), LIT-030 (SSRN 6636258); Mohammad et al. (2026),
LIT-036 (Front. Blockchain 9:1817622). Both report a negative relation between dilution/
unlocks and subsequent value, but are working-paper / single-chain and unrefereed or narrow.
Not validated by this project.
