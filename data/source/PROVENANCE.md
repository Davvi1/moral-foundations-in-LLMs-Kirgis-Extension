# Source data provenance

Raw inputs, copied unmodified. Nothing in this directory is edited by hand or by script —
derived files live in `data/`, built by `scripts/build_items.py`.

## kirgis_vignettes_short.csv — the 116 administered items

- **From:** `github.com/peterkirgis/llm-moral-foundations`, path `data/survey/vignettes_short.csv`
- **Repo HEAD at copy:** `fc39db0e3290ae6f7e23d05f79947e53b6afcb6f` (2025-05-16)
- **Last commit touching this file:** `1e83f46b1412370be396cf1d22d196c7a3a9dcbf` (2025-04-17, "full analysis")
- **SHA256:** `B748403C8EA2FDBC5B7D1B44AD46531DD9CF571B37429046B0A1DEE7F3DFE3B8`
- **Copied:** 2026-08-07
- 116 rows. Columns: `Scenario, Foundation, Care, Fairness, Loyalty, Authority, Sanctity,
  Liberty, Not Wrong, Wrong`.

## kirgis_vignettes_full132.csv — Clifford's full set, kept for reference

- **From:** same repo, path `data/survey/vignettes.csv`
- **SHA256:** `476B2BE2E12B64F819E34857CC8AA9DF1021FEC6F4D67A58AC18B4B81B15277D`
- 132 rows. Identical schema, except `Foundation` retains Clifford's finer Care labels:
  `Care (e)`, `Care (p, a)`, `Care (p, h)`.
- Not administered. Kept because it documents **which 116 of the 132 Kirgis used**: he drops
  all 16 physical-harm Care items (9 `Care (p, a)` animal-harm, 7 `Care (p, h)` human-harm)
  and keeps the 16 `Care (e)` emotional-harm items. 132 − 16 = 116.
  **Consequence: the Care foundation in this study is emotional harm only.**

## Upstream source of truth

Both files are transcriptions of **Clifford, Iyengar, Cabeza & Sinnott-Armstrong (2015),
"Moral foundations vignettes," *Behavior Research Methods* 47(4):1178–1198, Table 1
("Respondent ratings of moral scenarios"), pp. 1183–1186** — in the main article, not
supplementary material.

Verified 2026-08-07 by reading the published PDF and matching 9 rows spanning Care (e),
Care (p, a), Sanctity and Social Norms. All columns matched exactly, e.g.:

| Scenario | Foundation | Care | Not Wrong | Wrong |
|---|---|---|---|---|
| You see a teenage boy chuckling at an amputee he passes by while on the subway. | Care (e) | 83 % | 0 % | 3.4 |
| You see someone using an old rotary phone and refusing to go buy a new one. | Social Norms | 0 % | 100 % | 0.0 |

This is a transcription of a published table, **not a reconstruction**. That distinction is
carried into `data/mfv_116_meta.csv` in the `source` column.

## Two caveats on the human baseline — carry these into the write-up

1. **It is not nationally representative.** Clifford Study 1 recruited n = 330, 192, 94 from
   "a national online panel by Qualtrics," "limited to the age range of 18–40 (M = 35, 32,
   33)," and "balanced on ideology." Kirgis's Discussion describes it as "a nationally
   representative sample of US adults." It is an ideology-quota online panel of 18–40s.
2. **n ≈ 30 per vignette** — "each vignette was rated by approximately 30 individuals." The
   standard error of each item mean is therefore ≈ 0.2 on a 0–4 scale. Treating these means
   as an error-free reference understates uncertainty.

## Response scale

Clifford's Measures section: respondents rated "how morally wrong the behavior is on a
5-point scale labeled *not at all wrong, not too wrong, somewhat wrong, very wrong,
extremely wrong*." The `Wrong` column is the mean on that scale coded 0–4 (verified range
across the 116 items: min 0.0, max 3.8, mean 2.203). These are the same five labels reused
in `config/prompt.yaml`.
