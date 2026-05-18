# ATS resolution report — `amit-arora`

Target companies in profile: **25**

| Company | AI hint | Verified source | Token | Jobs | Match? | Notes |
|---|---|---|---|---:|:---:|---|
| JPMorgan Chase | workday | unknown | — | 0 | -- |  |
| Citigroup | workday | workday | citi/2 | 2000 | OK |  |
| Bank of America | workday | unknown | — | 0 | -- |  |
| Goldman Sachs | workday | unknown | — | 0 | -- |  |
| Wells Fargo | workday | unknown | — | 0 | -- |  |
| Morgan Stanley | workday | unknown | — | 0 | -- |  |
| US Bancorp | workday | unknown | — | 0 | -- |  |
| TD Bank | workday | workday | td/TD_Bank_Careers | 1469 | OK |  |
| Regions Financial | workday | workday | regions/Regions_Careers | 478 | OK |  |
| Signature Bank / New York Community Bancorp | unknown | unknown | — | 0 | OK |  |
| MUFG Americas | workday | unknown | — | 0 | -- |  |
| Mizuho Americas | unknown | workday | mizuho/mizuhoamericas | 86 | NEW | seed |
| Valley National Bank | unknown | unknown | — | 0 | OK |  |
| Signature Financial / Flagstar Bank | unknown | workday | flagstar/flagstar | 230 | NEW | seed |
| Moody's Analytics | workday | unknown | — | 0 | -- |  |
| S&P Global | workday | unknown | — | 0 | -- |  |
| Protiviti | workday | unknown | — | 0 | -- |  |
| Deloitte | workday | unknown | — | 0 | -- |  |
| KPMG | workday | unknown | — | 0 | -- |  |
| Ernst & Young (EY) | workday | unknown | — | 0 | -- |  |
| FIS Global | workday | unknown | — | 0 | -- |  |
| Fiserv | workday | unknown | — | 0 | -- |  |
| OneTrust | greenhouse | greenhouse | onetrust | 87 | OK |  |
| ServiceNow | workday | smartrecruiters | servicenow | 492 | NEW |  |
| Archer (RSA) | unknown | greenhouse | archer | 1 | NEW |  |

**Resolved: 8 / 25 (32%)**
_Seed map provided atsUrl for **2** companies the AI left blank._

## Companies the seed map flags as not on a supported ATS

These use Avature / Oracle HCM / Phenom / iCIMS / proprietary — separate adapter work needed to scrape them:

- **JPMorgan Chase** — Oracle Cloud HCM (careers.jpmorgan.com)
- **Goldman Sachs** — Proprietary higher.gs.com / goldmansachs.tal.net
- **Signature Bank / New York Community Bancorp** — Acquired by Flagstar — use Flagstar tenant
- **Valley National Bank** — iCIMS (valley.com/about/careers)
- **Moody's Analytics** — Phenom/Eightfold (careers.moodys.com)
- **Deloitte** — Avature (apply.deloitte.com) — regional Workday tenants exist but no single US one
- **KPMG** — Phenom/iCIMS (kpmguscareers.com) US; Oracle HCM globally
- **Ernst & Young (EY)** — Avature/SuccessFactors (careers.ey.com)
- **ServiceNow** — SmartRecruiters (careers.smartrecruiters.com/servicenow) — existing SR match is correct
- **Archer (RSA)** — Proprietary (archerirm.com/careers)

## Breakdown by source

- **workday**: 5
- **greenhouse**: 2
- **smartrecruiters**: 1

## AI-vs-verified disagreements

- **ServiceNow**: AI guessed `workday`, actually `smartrecruiters`
