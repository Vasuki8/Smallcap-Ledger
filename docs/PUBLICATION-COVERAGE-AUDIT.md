# AMC communication coverage audit

Prepared: 2026-09-26T22:44:05+00:00

**Read-only:** AMC-origin communications only; third-party news is excluded. Factsheets and portfolio files do not count as communications.

## Summary

- Funds with at least one retained AMC communication: **32 / 36**.
- Funds with no retained AMC communication: **4**.
- Retained communication documents: **230**; archived originals: **213**.
- Market/newsletter/CIO/product-view documents: **214**; letters to unitholders: **16**.
- Communication documents with an explicit published date: **52**.
- Funds with a registered communication-oriented source page: **29**.

## Repair priorities

| Priority | Repair | Actionable | Affected funds | Reason |
| ---: | --- | --- | ---: | --- |
| 1 | review_registered_communication_sources | yes | 3 | A registered first-party communication/news source exists, but no AMC communication document has been retained for the fund. |
| 2 | documented_communication_source_limitation | no | 1 | The AMC communication is currently identifiable only inside a source class intentionally excluded from communication coverage; retain the gap until a standalone first-party communication source appears. |
| 3 | documented_communication_archive_limitation | no | 3 | The original AMC communication asset is intentionally retained as link-only because robots policy disallows automatic retrieval; keep the metadata/source link and do not treat this as a repairable fetch failure. |
| 3 | repair_unarchived_communication_documents | yes | 1 | AMC communication metadata is retained but one or more original document versions are not archived. |

### Affected funds

- **review_registered_communication_sources:** The Wealth Company Small Cap Fund, UTI Small Cap Fund, Union Small Cap Fund
- **documented_communication_source_limitation:** Trustmf Small Cap Fund
- **documented_communication_archive_limitation:** Franklin India Small Cap Fund, Kotak Small Cap Fund, Samco Small Cap Fund
- **repair_unarchived_communication_documents:** LIC Mf Small Cap Fund

## Per-fund audit

| Fund | Communications | Market views | Unitholder letters | Archived | Published-date docs | Latest published | Registered communication sources | Issues |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- |
| Abakkus Small Cap Fund | 11 | 11 | 0 | 11 | 10 | 2026-08-11 | 3 | publication_date_missing |
| Aditya Birla Sun Life Small Cap Fund | 1 | 1 | 0 | 1 | 0 | Gap | 1 | publication_date_missing |
| Axis Small Cap Fund | 3 | 3 | 0 | 3 | 2 | 2026-03-15 | 2 | publication_date_missing |
| Bajaj Finserv Small Cap Fund | 1 | 1 | 0 | 1 | 1 | 2026-05-21 | 1 | none |
| Bandhan Small Cap Fund | 3 | 3 | 0 | 3 | 3 | 2026-09-11 | 3 | none |
| Bank Of India Small Cap Fund | 3 | 3 | 0 | 3 | 0 | Gap | 1 | publication_date_missing |
| Baroda Bnp Paribas Small Cap Fund | 1 | 0 | 1 | 1 | 0 | Gap | 0 | publication_date_missing |
| Canara Robeco Small Cap Fund | 1 | 1 | 0 | 1 | 0 | Gap | 2 | publication_date_missing |
| DSP Small Cap Fund | 13 | 0 | 13 | 13 | 0 | Gap | 0 | publication_date_missing |
| Edelweiss Small Cap Fund | 1 | 1 | 0 | 1 | 0 | Gap | 2 | publication_date_missing |
| Franklin India Small Cap Fund | 10 | 10 | 0 | 0 | 10 | 2026-09-18 | 1 | communication_document_not_archived, communication_archive_limitation |
| Groww Small Cap Fund | 3 | 3 | 0 | 3 | 3 | 2026-09-21 | 1 | none |
| HDFC Small Cap Fund | 1 | 0 | 1 | 1 | 0 | Gap | 2 | publication_date_missing |
| HSBC Small Cap Fund | 20 | 20 | 0 | 20 | 20 | 2026-08-11 | 1 | none |
| Helios Small Cap Fund | 2 | 2 | 0 | 2 | 0 | Gap | 0 | publication_date_missing |
| ICICI Prudential Small Cap Fund | 3 | 3 | 0 | 3 | 1 | 2026-08-11 | 1 | publication_date_missing |
| Invesco India Small Cap Fund | 1 | 1 | 0 | 1 | 0 | Gap | 1 | publication_date_missing |
| Iti Small Cap Fund | 3 | 3 | 0 | 3 | 0 | Gap | 3 | publication_date_missing |
| Jm Small Cap Fund | 1 | 1 | 0 | 1 | 0 | Gap | 0 | publication_date_missing |
| Kotak Small Cap Fund | 1 | 1 | 0 | 0 | 1 | 2026-09-09 | 1 | communication_document_not_archived, communication_archive_limitation |
| LIC Mf Small Cap Fund | 19 | 19 | 0 | 14 | 0 | Gap | 1 | communication_document_not_archived, publication_date_missing |
| Mahindra Manulife Small Cap Fund | 1 | 1 | 0 | 1 | 0 | Gap | 1 | publication_date_missing |
| Mirae Asset Small Cap Fund | 1 | 1 | 0 | 1 | 0 | Gap | 1 | publication_date_missing |
| Motilal Oswal Small Cap Fund | 1 | 1 | 0 | 1 | 0 | Gap | 2 | publication_date_missing |
| Nippon India Small Cap Fund | 103 | 103 | 0 | 103 | 0 | Gap | 1 | publication_date_missing |
| Pgim India Small Cap Fund | 5 | 5 | 0 | 5 | 0 | Gap | 1 | publication_date_missing |
| Quant Small Cap Fund | 7 | 7 | 0 | 7 | 0 | Gap | 1 | publication_date_missing |
| Quantum Small Cap Fund | 1 | 0 | 1 | 1 | 0 | Gap | 0 | publication_date_missing |
| SBI Small Cap Fund | 1 | 1 | 0 | 1 | 1 | 2026-01-08 | 1 | none |
| Samco Small Cap Fund | 1 | 1 | 0 | 0 | 0 | Gap | 0 | communication_document_not_archived, communication_archive_limitation, publication_date_missing |
| Sundaram Small Cap Fund | 6 | 6 | 0 | 6 | 0 | Gap | 1 | publication_date_missing |
| Tata Small Cap Fund | 1 | 1 | 0 | 1 | 0 | Gap | 1 | publication_date_missing |
| The Wealth Company Small Cap Fund | 0 | 0 | 0 | 0 | 0 | Gap | 1 | no_amc_communications_collected |
| Trustmf Small Cap Fund | 0 | 0 | 0 | 0 | 0 | Gap | 0 | no_amc_communications_collected, communication_source_limitation |
| UTI Small Cap Fund | 0 | 0 | 0 | 0 | 0 | Gap | 1 | no_amc_communications_collected |
| Union Small Cap Fund | 0 | 0 | 0 | 0 | 0 | Gap | 1 | no_amc_communications_collected |

## Notes

- This audit counts only AMC-origin documents classified as market view or unitholder letter.
- Newsletters, CIO/investment/market outlooks and product presentations are normalized to market view by the existing document classifier.
- Factsheets, scheme documents, portfolios and generic disclosures remain available on fund pages but do not satisfy communication coverage.
- A missing published_at value is reported as missing metadata; first_seen is never substituted as the publication date.
- Documented source limitations remain visible as zero communication coverage and are not silently promoted from excluded source classes.
- Robots-blocked originals remain visible as link-only archive limitations and are not queued as ordinary repairable download failures.
- The audit is read-only and performs no source fetch, document mutation or UI change.
