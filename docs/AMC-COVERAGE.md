# Official AMC coverage update

Validated on 7 September 2026 against the bundled historical archive and downloaded official AMC documents. This report records extraction coverage, not a guarantee that every value is the newest publication. The deployed site regenerates `data/coverage.json` after every build.

| Fund | Latest available AUM (₹ crore) | AUM reporting date | Expense coverage | Holdings coverage |
|---|---:|---|---|---|
| Abakkus Small Cap Fund | Gap | — | TER + BER | Gap |
| Aditya Birla Sun Life Small Cap Fund | [5,865.30](https://mutualfund.adityabirlacapital.com/-/media/bsl/files/resources/factsheets/2026/absl-factsheet_aug-2026.pdf) | 2026-07-31 | TER + BER | Gap |
| Axis Small Cap Fund | [31,448.32](https://www.axismf.com/mutual-funds/equity-funds/axis-small-cap-fund/sc-dg/direct) | 2026-08-31 | Gap | Gap |
| Bajaj Finserv Small Cap Fund | [2,366.08](https://media.bajajamc.com/wp-content/uploads/2026/02/Bajaj-Finserv-Small-Cap-Fund_August-2026.pdf) | 2026-07-31 | TER + BER | Gap |
| Bandhan Small Cap Fund | Gap | — | TER + BER | Gap |
| Bank Of India Small Cap Fund | Gap | — | TER + BER | Gap |
| Baroda Bnp Paribas Small Cap Fund | Gap | — | TER + BER | Gap |
| Canara Robeco Small Cap Fund | [14,230.88](https://digitalassets.canararobeco.com/digital-factsheet/2026/july/Scheme/Factsheet.pdf) | 2026-07-31 | BER only | 86 positions; partial; 2026-07-31 |
| DSP Small Cap Fund | [21,658.64](https://www.dspim.com/invest/mutual-fund-schemes/equity-funds/small-cap-fund/dspmc-direct-growth) | 2026-08-31 | TER + BER | 80 positions; partial; 2026-06-30 |
| Edelweiss Small Cap Fund | [6,825.00](https://www.edelweissmf.com/Files/MF/Downloads/FACTSHEETS/FACTSHEETS/Edelweiss_Factsheet_August__2026_10082026160011.pdf) | 2026-07-31 | TER + BER | Gap |
| Franklin India Small Cap Fund | Gap | — | TER + BER | Gap |
| Groww Small Cap Fund | Gap | — | Gap | Gap |
| HDFC Small Cap Fund | [41,890.86](https://www.hdfcfund.com/explore/mutual-funds/hdfc-small-cap-fund/regular) | 2026-08-31 | TER + BER | 84 positions; partial; 2026-07-31 |
| HSBC Small Cap Fund | [17,783.74](https://www.assetmanagement.hsbc.co.in/-/media/Files/attachments/india/mutual-funds/factsheet/the-asset-july-2026.pdf) | 2026-07-31 | BER only | Gap |
| Helios Small Cap Fund | [1,455.13](https://www.heliosmf.in/wp-content/uploads/2026/08/helios-mutual-fund-factsheet-jul26.pdf) | 2026-07-31 | TER + BER | 90 positions; partial; 2026-07-31 |
| ICICI Prudential Small Cap Fund | Gap | — | Gap | Gap |
| Invesco India Small Cap Fund | [14,474.79](https://www.invescomutualfund.com/docs/default-source/factsheet/invesco-mf-factsheet-july-2026.pdf) | 2026-07-31 | BER only | 65 positions; partial; 2026-07-31 |
| Iti Small Cap Fund | [3,454.00](https://www.itiamc.com/digitalfactsheet/July2026/innerpages/Small-Cap.html) | 2026-07-31 | TER + BER | Gap |
| Jm Small Cap Fund | Gap | — | Gap | Gap |
| Kotak Small Cap Fund | [19,678.00](https://www.kotakmf.com/mutual-funds/equity-funds/kotak-smallcap-fund/dir-g) | 2026-08-31 | TER + BER | Gap |
| LIC Mf Small Cap Fund | Gap | — | TER + BER | Gap |
| Mahindra Manulife Small Cap Fund | [5,086.57](https://www.mahindramanulife.com/digital-factsheet/july-2026/Equity-funds/Small-Cap-Fund.html) | 2026-07-31 | Gap | Gap |
| Mirae Asset Small Cap Fund | Gap | — | Gap | Gap |
| Motilal Oswal Small Cap Fund | Gap | — | TER + BER | Gap |
| Nippon India Small Cap Fund | [78,956.77](https://mf.nipponindiaim.com/InvestorServices/FundwiseFactsheet/NipponIndia-Small-Cap-Fund-MF-Factsheet-2026.pdf) | 2026-07-31 | TER + BER | 251 positions; partial; 2026-07-31 |
| Pgim India Small Cap Fund | Gap | — | TER + BER | Gap |
| Quant Small Cap Fund | [35,557.21](https://quantmutual.com/Admin/Factsheet/quant_Factsheet_-_September_2026.pdf) | 2026-08-31 | TER + BER | Gap |
| Quantum Small Cap Fund | [254.14](https://www.quantumamc.com/FileCDN/FactSheet/6d1f7559-717e-4b8e-8e98-31f7ccdb4a82.pdf) | 2026-07-31 | TER + BER | 59 positions; partial; 2026-07-31 |
| SBI Small Cap Fund | Gap | — | TER + BER | Gap |
| Samco Small Cap Fund | [196.45](https://www.samcomf.com/amc-document-download/Factsheet-August2026_1788525518.pdf) | 2026-08-31 | TER + BER | Gap |
| Sundaram Small Cap Fund | Gap | — | TER + BER | Gap |
| Tata Small Cap Fund | [13,187.58](https://www.tatamutualfund.com/mutual-funds/tata-small-cap-fund-direct-growth) | 2026-09-03 | TER + BER | Gap |
| The Wealth Company Small Cap Fund | Gap | — | TER + BER | Gap |
| Trustmf Small Cap Fund | Gap | — | TER + BER | Gap |
| UTI Small Cap Fund | Gap | — | Gap | Gap |
| Union Small Cap Fund | Gap | — | TER + BER | Gap |

## What changed

- Added official monthly report sources and download directories; Canara Robeco and Invesco monthly locations roll forward with a three-month lookback.
- Broader PDF extraction covers AUM and separately labelled expense components. Invesco, Canara Robeco, Quantum, Samco, Edelweiss, Helios, Bajaj Finserv, HSBC and quant reports were exercised against original downloaded files.
- Expanded Excel support handles native date cells, period-ended dates, and `% to AUM` headers. Quantum and Helios July disclosures yielded 59 and 90 ISIN positions.
- Previously archived reports are reprocessed once per parser version. Original records and source documents remain in the cumulative history.
- Every parsed or unrecognized document gets an extraction status and content hash. SID/KIM documents stay archived; stated fee limits are not treated as actual TER.
- Quantum factsheet expense figures that exclude transaction costs are kept under a distinct metric. AMFI remains the existing source for more frequent total expense observations.

## Remaining gaps

This update does not complete coverage of all 36 funds. Blocked requests, JavaScript-only pages, unsupported PDF layouts, image-only tables and large documents still need additional source-specific work. The registry includes source pages for all fund houses, but a registered source does not imply successful extraction. Older AUM and portfolio history is limited to reports actually obtained; no intervening values are fabricated.

Fund communications remain AMC-only. A reported benchmark name does not supply missing BSE TRI history, and this update does not invent IDCW distribution histories.

## Deployment

Merging this update triggers a bounded official-report upgrade on the existing GitHub Actions runner. It restores and augments the existing release archive, then builds and publishes the site. The existing midnight IST schedule continues discovering new documents. The previous website stays available if deployment fails.

Validation: 34 isolated automated tests, original-report visual spot checks, generated-site validation, and cumulative-history superset checks.
