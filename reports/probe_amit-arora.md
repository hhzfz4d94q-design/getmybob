# ATS resolution report — `amit-arora`

Target companies in profile: **25**

| Company | AI hint | AI atsUrl | Verified source | Token | Jobs | Match? | Notes |
|---|---|---|---|---|---:|:---:|---|
| JPMorgan Chase | workday | `https://jpmc.wd1.myworkdayjobs.com/jpmc` | unknown | — | 0 | -- |  |
| Citigroup | workday | `https://citi.wd5.myworkdayjobs.com/2` | workday | citi/2 | 2000 | OK |  |
| Bank of America | workday | `https://bofa.wd1.myworkdayjobs.com/en-US…` | workday | ghr/Lateral-US | 1494 | OK | seed |
| Goldman Sachs | workday | `https://goldmansachs.wd1.myworkdayjobs.c…` | unknown | — | 0 | -- |  |
| Wells Fargo | workday | `https://wellsfargo.wd5.myworkdayjobs.com…` | workday | wf/WellsFargoJobs | 1800 | OK | seed |
| Morgan Stanley | workday | `https://ms.wd5.myworkdayjobs.com/msexter…` | workday | ms/External | 1488 | OK | seed |
| US Bancorp | workday | `https://usbank.wd5.myworkdayjobs.com/en-…` | workday | usbank/US_Bank_Careers | 1215 | OK | seed |
| TD Bank | workday | `https://td.wd3.myworkdayjobs.com/TD_Bank…` | workday | td/TD_Bank_Careers | 1470 | OK |  |
| Regions Financial | workday | `https://regions.wd5.myworkdayjobs.com/Re…` | workday | regions/Regions_Careers | 478 | OK |  |
| Signature Bank / New York Community Bancorp | unknown | `—` | unknown | — | 0 | OK |  |
| MUFG Americas | workday | `https://mufgamericas.wd5.myworkdayjobs.c…` | workday | mufgub/MUFG-Careers | 569 | OK | seed |
| Mizuho Americas | unknown | `—` | workday | mizuho/mizuhoamericas | 86 | NEW | seed |
| Valley National Bank | unknown | `—` | unknown | — | 0 | OK |  |
| Signature Financial / Flagstar Bank | unknown | `—` | workday | flagstar/flagstar | 230 | NEW | seed |
| Moody's Analytics | workday | `https://moodys.wd5.myworkdayjobs.com/Car…` | unknown | — | 0 | -- |  |
| S&P Global | workday | `https://spglobal.wd1.myworkdayjobs.com/C…` | workday | spgi/SPGI_Careers | 504 | OK | seed |
| Protiviti | workday | `https://protiviti.wd5.myworkdayjobs.com/…` | workday | roberthalf/ProtivitiNA | 84 | OK | seed |
| Deloitte | workday | `https://deloitte.wd1.myworkdayjobs.com/d…` | unknown | — | 0 | -- |  |
| KPMG | workday | `https://kpmgus.wd5.myworkdayjobs.com/KPM…` | unknown | — | 0 | -- |  |
| Ernst & Young (EY) | workday | `https://ey.wd5.myworkdayjobs.com/EY_Exte…` | unknown | — | 0 | -- |  |
| FIS Global | workday | `https://fisglobal.wd5.myworkdayjobs.com/…` | workday | fis/SearchJobs | 595 | OK | seed |
| Fiserv | workday | `https://fiserv.wd5.myworkdayjobs.com/Ext…` | workday | fiserv/EXT | 442 | OK | seed |
| OneTrust | greenhouse | `—` | greenhouse | onetrust | 87 | OK |  |
| ServiceNow | workday | `https://servicenow.wd5.myworkdayjobs.com…` | smartrecruiters | servicenow | 492 | NEW |  |
| Archer (RSA) | unknown | `—` | greenhouse | archer | 1 | NEW |  |

**Resolved: 17 / 25 (68%)**
_Seed map provided atsUrl for **11** companies the AI left blank._

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

- **workday**: 14
- **greenhouse**: 2
- **smartrecruiters**: 1

## AI-vs-verified disagreements

- **ServiceNow**: AI guessed `workday`, actually `smartrecruiters`
