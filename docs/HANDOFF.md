# Smallcap Ledger backend handoff

Updated: 2026-09-26, after Groww/HSBC first-party communication recovery and successful production deployment.

## Latest completed batch: recover Groww and HSBC AMC communications

**Groww Small Cap Fund and HSBC Small Cap Fund are no longer in the missing-communication-source queue.** Both now have dedicated first-party communication collectors that retain explicit source dates and originals without treating monthly fund factsheets as news.

### Groww evidence and collector

Read-only diagnostic PR **#198** merged as commit `2434f72026f1c07c0016e0491fc3eee25b4b06cf` and established that Groww's distributor portal exposes a real, server-readable market-intelligence route:

- `https://www.growwmf.in/distributor/knowledge-hub/publications`
- page identity: **Reports & newsletters**
- description: disciplined market commentary, archived date-wise
- the page embeds a structured Next.js payload binding each report's:
  - heading
  - report type
  - explicit report date
  - exact PDF URL
  - PDF MIME type

The live payload contained three current reports:

- **Daily Market Pulse** — **2026-09-21**
- **Weekly Market Pulse** — **2026-09-19**
- **Fixed Income Weekly Wrap Up** — **2026-09-18**

The exact Daily Market Pulse source retained by the release gate is:

`https://cms-resources.growwmf.in/uploads/daily_report_4_c7907e5e42.pdf`

The collector accepts Groww publication binaries only from the observed first-party publication asset host `cms-resources.growwmf.in` and requires HTTPS, `/uploads/`, PDF MIME identity and a `.pdf` path. It does not infer market-view coverage from the ordinary monthly factsheet even though Groww factsheets also contain CIO Desk / Market Outlook sections.

### HSBC evidence and collector

The production probe confirmed a dedicated, server-readable first-party **Local Market Commentary** index:

`https://www.assetmanagement.hsbc.co.in/en/mutual-funds/news-and-insights?categories=%5B%27local-market-commentary%27%5D`

The page exposed current and historical commentary links including RBI policy reviews, Macro Sphere notes, valuation commentary and budget/fixed-income perspectives.

The collector:

- follows only same-domain HSBC `/en/mutual-funds/news-and-insights/<article>` children from the Local Market Commentary source;
- fetches each candidate without archiving it first;
- retains it only when the article itself contains the explicit **Local Market Commentary** category;
- binds the publication date to the text immediately following the article's in-page `H1`, preventing older dates cited inside the commentary body from being mistaken for publication dates;
- archives only validated article HTML as the communication original.

Current release-gating article:

- **RBI Monetary Policy Review - August 2026**
- `https://www.assetmanagement.hsbc.co.in/en/mutual-funds/news-and-insights/rbi-monetary-policy-review-august-2026`
- explicit page publication date: **2026-08-11**
- origin: **HSBC Asset Management / HSBC Mutual Fund**
- kind: `market view`
- original HTML: **archived**

### Implementation

PR **#199** merged as commit `117fa704625f9ebe5bc0219910f7d40bdbaf22e0`.

It added:

- `tracker/groww_communications.py`
- `tracker/hsbc_communications.py`
- `scripts/refresh_groww_hsbc_communications.py`
- dedicated routing from `tracker/disclosures.py`
- the Groww publication asset-host boundary
- communication-audit recognition for `Local Market Commentary`
- regression coverage for structured Groww payload identity, exact PDF ownership, HSBC category/date validation, source routing, audit registration and idempotent production recovery
- replacement/removal of the temporary Groww/HSBC diagnostic step.

No third-party news, factsheet-as-news substitution, guessed URLs, inferred dates, portfolio changes or financial-data changes were introduced.

### Production verification

Final production workflow **36244239818** completed successfully at **2026-09-26T13:12:49Z**.

Live recovery evidence:

- **Groww communications:** **3**
- Groww Daily Market Pulse:
  - `published_at=2026-09-21`
  - **1 archived original**
- Groww source result: **3 market-intelligence PDFs retained / 0 download-parser gaps**
- **HSBC communications:** **20**
- HSBC RBI Monetary Policy Review - August 2026:
  - `published_at=2026-08-11`
  - **1 archived original**
- HSBC source result: **20 Local Market Commentary articles retained / 0 download-parser gaps**

Full validation:

- build: **success**
- full regression suite: **414 tests passed**
- generated-site/download validation: **success**
- cumulative-history publication: **success**
- communication/coverage audit publication: **success**
- GitHub Pages deployment: **success**

Pages artifact **10907230385** is **233,713,762 bytes** with digest `sha256:fec46c38d2300382a66a10ed5813e42d3c2584aa4d225b6ce3f179f324b3678c`.

### Communication coverage after this batch

Final audit generated at **2026-09-26T13:12:19Z**:

- funds with at least one retained AMC communication: **23 / 36** (was 21)
- funds with no retained AMC communication: **13**
- retained communication documents: **210**
- archived communication originals: **162**
- market/newsletter/CIO/product-view documents: **188**
- letters to unitholders: **22**
- communication documents with an explicit `published_at`: **49**
- funds with a registered communication-oriented source: **17**

**Groww final state:** **3 market views / 3 archived originals / 3 explicit dates**, latest **2026-09-21**, with no communication-audit issue.

**HSBC final state:** **20 market views / 20 archived originals / 20 explicit dates**, latest **2026-08-11**, with no communication-audit issue.

### Next backend/data-retrieval task

Continue bounded first-party communication-source discovery for the remaining **13** funds:

1. **ICICI Prudential Small Cap Fund**
2. **Invesco India Small Cap Fund**
3. Kotak Small Cap Fund
4. Mirae Asset Small Cap Fund
5. PGIM India Small Cap Fund
6. Quant Small Cap Fund
7. SBI Small Cap Fund
8. Sundaram Small Cap Fund
9. Tata Small Cap Fund
10. The Wealth Company Small Cap Fund
11. TRUSTMF Small Cap Fund
12. UTI Small Cap Fund
13. Union Small Cap Fund

Start with **ICICI Prudential**, then **Invesco India**.

Promising first-party candidates have already been identified for the next run but are **not yet production-retained communication sources** and must be validated before registration:

- ICICI Prudential: the first-party Prudent Fact Sheet / market-review surface and the AMC's SEBI-repository Monthly Market Outlook mailers.
- Invesco India: first-party Market Outlook presentation PDFs under `invescomutualfund.com/docs/default-source/presentations-pdf/`.

For both funds, establish either a durable dynamic catalog or a narrowly justified exact-current anchor; retain explicit source dates only and add a production recovery gate before marking coverage complete.

The `repair_unarchived_communication_documents` queue remains **Franklin India, LIC MF, Nippon India and Samco**. Franklin remains a known policy-limited case: metadata is first-party and dated, while Widen originals stay link-only under robots restrictions.

The portfolio recovery queue remains independently blocked at **6 items / 0 actionable now**. Do not estimate censored holdings or re-probe blocked portfolio transports without a retained source-change signal.

## Previous completed batch: recover Edelweiss and Franklin AMC communications

**Edelweiss Small Cap Fund and Franklin India Small Cap Fund are no longer in the missing-communication-source queue.** The two AMCs require different evidence models, and the backend now preserves that distinction instead of weakening access controls.

### Edelweiss evidence

The production runner initially recovered Edelweiss Fund & Market Insights successfully, but repeated later pushes showed the HTML insight routes returning **403 Forbidden**. The release gate was therefore narrowed to an exact first-party publication rather than bypassing the blocked pages.

Release-gating source:

- **Factor Investing Outlook 2026**
- `https://www.edelweissmf.com/Files/Insigths/viewpoint/EMF_Factor_Investing_Outlook_2026_01012026_060107_PM.pdf`
- origin: **Edelweiss Mutual Fund**
- kind: `market view`
- original binary: **archived**
- explicit publication date: **not established**; `published_at` remains null

The dynamic Edelweiss Fund & Market Insights / Curve / Factor Outlook HTML routes remain registered for normal future retries, but their transient 403 does not block publication when the exact first-party PDF evidence is available.

### Franklin evidence and robots boundary

Franklin's public Latest Commentaries page is a JavaScript shell in the production runner, and the Widen asset tenant disallows automatic retrieval under its robots policy. The tracker does **not** bypass that policy.

Frontend diagnostics established that Franklin's own public site populates Latest Commentaries through the same-domain endpoint:

- `https://www.franklintempletonindia.com/api/articleApi`
- request type: `application/x-www-form-urlencoded`
- `pageType=latest-commentaries`
- production environment: `env=prod`

The collector now uses that same first-party API contract. It:

- archives the exact Franklin API JSON response as source evidence;
- accepts only Franklin `latest-commentaries` article records with recognized market-commentary titles;
- retains explicit `referenceDate` / `publishDate` dates supplied by Franklin;
- stores first-party Franklin article URLs as the communication URLs;
- preserves the Widen asset URL inside the archived API evidence;
- does **not** fetch or claim the Widen original binary is archived when robots disallow automatic access.

The former Widen viewer is removed from scheduled source seeding and any historical source-page row for it is disabled as superseded evidence, not deleted.

### Implementation and release history

PR **#196** merged as commit `f42549ded6795db9492d067da1a735197da3cac7` and introduced:

- safe form-encoded POST support in the public fetch helper;
- `tracker/franklin_communications.py`;
- Franklin first-party article API ingestion;
- Franklin API-source provenance with link-only Widen originals;
- the v2 Edelweiss/Franklin recovery gate;
- removal of completed Franklin diagnostics and generic Widen crawl-host permission.

Its first production run correctly stopped before publication because Edelweiss's HTML insight routes had begun returning 403, even though Franklin already recovered **10** communication records successfully.

PR **#197** merged as commit `54d8d571eafa57e520dd01e3d82012afc4d7dcfe` and changed the Edelweiss release gate to the exact first-party Factor Investing Outlook PDF while leaving the dynamic HTML sources registered for future retries.

### Production verification

Final production workflow **36241290583** completed successfully at **2026-09-26T12:16:59Z**.

Live recovery evidence:

- **Edelweiss:** **1** retained market-view record; exact Factor Investing Outlook PDF archived; **0 download/parser gaps**.
- **Franklin:** **10** market-commentary records retained from the first-party article API.
- Franklin API snapshot: **archived** as source evidence.
- Franklin Monthly Equity Outlook:
  - first-party article URL: `https://www.franklintempletonindia.com/knowledge-centre/quick-learn/latest-commentaries/article/monthly-equity-outlook`
  - explicit publication date: **2026-08-06**
  - original Widen binary: **link-only / not archived**.
- Franklin link-only originals: **10**, matching all 10 retained Franklin communication records.

Full validation:

- build: **success**
- full regression suite: **406 tests passed**
- generated-site/download validation: **success**
- cumulative-history publication: **success**
- communication/coverage audit publication: **success**
- GitHub Pages deployment: **success**

Pages artifact **10906510322** is **233,533,677 bytes** with digest `sha256:9835bdf415d94eff21fd27079aa4d3bb10ba071ff41d45599ef0cbde8a311d01`.

### Communication coverage after this batch

Final audit generated at **2026-09-26T12:16:29Z**:

- funds with at least one retained AMC communication: **21 / 36** (was 19)
- funds with no retained AMC communication: **15**
- retained communication documents: **187**
- archived communication originals: **139**
- market/newsletter/CIO/product-view documents: **165**
- letters to unitholders: **22**
- communication documents with an explicit `published_at`: **26**
- funds with a registered communication-oriented source: **15**

**Edelweiss final state:** **1 market view / 1 archived original**. Its publication date remains an evidence gap.

**Franklin final state:** **10 market views / 0 archived individual originals / 10 explicit dates**. Latest retained communication date is **2026-09-18**. The archived Franklin API snapshot is the retained provenance for those metadata records. The audit intentionally flags `communication_document_not_archived` for Franklin rather than pretending the robots-blocked Widen binaries were saved.

### Intervening completed batch: Bajaj Finserv and Bandhan communications

The repository advanced between handoff updates. PR **#187** merged as commit `c270486696bc3edba5d6d5d009bc9c2784f555b8` and successfully recovered:

- **Bajaj Finserv:** dedicated first-party Outlook catalog; exact current `EQUITY OUTLOOK MAY` viewer retained with explicit date **2026-05-21**.
- **Bandhan:** official Market Outlook landing route plus current equity/debt September 2026 CMS posts; both current posts retained with explicit date **2026-09-11**.

Production workflow **36223408547** completed successfully. This batch moved communication coverage from **17 / 36 to 19 / 36** before the Edelweiss/Franklin work above.

### Next backend/data-retrieval task

Continue bounded first-party communication-source discovery for the remaining **15** funds with no retained AMC communication:

1. **Groww Small Cap Fund**
2. **HSBC Small Cap Fund**
3. ICICI Prudential Small Cap Fund
4. Invesco India Small Cap Fund
5. Kotak Small Cap Fund
6. Mirae Asset Small Cap Fund
7. PGIM India Small Cap Fund
8. Quant Small Cap Fund
9. SBI Small Cap Fund
10. Sundaram Small Cap Fund
11. Tata Small Cap Fund
12. The Wealth Company Small Cap Fund
13. TRUSTMF Small Cap Fund
14. UTI Small Cap Fund
15. Union Small Cap Fund

Start with **Groww communication discovery**, then **HSBC**. Prefer existing registered AMC/fund pages and first-party insight/market-view directories before adding new routes. Preserve explicit source dates only; never substitute `first_seen`.

The `repair_unarchived_communication_documents` queue now contains **Franklin India, LIC MF, Nippon India and Samco**. Franklin is a known policy-limited case: its first-party metadata is retained, while original Widen binaries remain link-only until automated access is permitted or owner-supplied originals are imported.

The portfolio recovery queue remains independently blocked at **6 items / 0 actionable now**. Do not estimate censored holdings or re-probe blocked portfolio transports without a retained source-change signal.

## Previous completed batch: add Abakkus and Axis AMC communication sources

**Abakkus Small Cap Fund and Axis Small Cap Fund are no longer in the missing-communication queue.** Both now have retained first-party market-view evidence plus dedicated source routes that can be revisited by the normal documents collector.

### First-party sources added

**Abakkus**

- dynamic market-outlook catalog: `https://insights.abakkusinvest.com/tag/market-outlook/`
- exact current recovery anchor: `https://insights.abakkusinvest.com/market-outlook-august-2026/`
- source label: `Market Outlook` / `Market Outlook - August 2026`
- the dynamic catalog is first-party Abakkus Insights and exposes monthly Market Outlook entries.

**Axis**

- dynamic Market-Outlook category: `https://www.axismf.com/mutual-fund-knowledge-centre/articles?tag=Market-Outlook`
- exact recovery anchor: `https://www.axismf.com/cms/sites/default/files/pdf-factsheets/Axis%20MF_%20Annual%20Equity%20Outlook%202026.pdf`
- source labels: `Market Outlook` / `Annual Equity Outlook 2026`
- the dynamic article category is treated as communication context only for child article URLs under the same Axis knowledge-centre path; unrelated Axis pages are not promoted.

PR **#183** merged as commit `f52bf42e1428c717f518df82d56162a1b4d4cfe7`.

### Collector changes

The communication collector now:

- allows explicit first-party Market-Outlook category context to classify narrowly scoped child articles as `market view`;
- keeps ordinary article/fund pages outside that context unless their own title/URL independently establishes a communication;
- recognizes dated Abakkus `/market-outlook-<month>-<year>/` pages as communication artifacts while leaving the generic tag archive as a source page;
- treats direct `market view` / `unitholder letter` files as communications rather than false financial-parser gaps;
- extracts an explicit HTML publication date only from source-provided metadata or markers:
  - `article:published_time`
  - HTML `time[datetime]`
  - JSON-LD `datePublished`
  - literal `Last updated on <date>`
- never substitutes `first_seen`, observation time, directory month or a market-data date for publication date.

### Production recovery evidence

Final production workflow **36222040546** completed successfully at **2026-09-26T05:54:43Z**.

The live one-time recovery gate observed:

- **Abakkus dynamic catalog:** **10 relevant links / 10 documents archived / 0 download-parser gaps**
- **Abakkus exact August outlook:** retained as `market view`, explicit `published_at=2026-08-11`, one archived version
- **Axis dynamic Market-Outlook category:** **2 relevant links / 2 documents archived / 0 download-parser gaps**
- **Axis Annual Equity Outlook 2026:** retained as `market view`, one archived version, **0 false parser gaps**
- dynamic-catalog verification succeeded for both AMCs.

Full production validation:

- build: **success**
- full regression suite: **392 tests passed**
- generated-site/download validation: **success**
- cumulative-history publication: **success**
- communication/coverage audit publication: **success**
- GitHub Pages deployment: **success**

Pages artifact **10899359504** is **233,796,655 bytes** with digest `sha256:4963e146a2852f9ef064a374e01a353e2a36ad034757170da3e5320259db9765`.

### Communication coverage after this batch

Final audit generated at **2026-09-26T05:54:09Z**:

- funds with at least one retained AMC communication: **17 / 36** (was 15)
- funds with no retained AMC communication: **19** (was 21)
- retained communication documents: **172** (was 158)
- archived communication originals: **134** (was 120)
- market/newsletter/CIO/product-view documents: **150** (was 136)
- letters to unitholders: **22**
- communication documents with an explicit `published_at`: **12** (was 0)
- funds with a registered communication-oriented source: **11** (was 9)

**Abakkus final state:** **11 market-view documents / 11 archived originals / 10 explicit publication dates**. Latest explicit publication date is **2026-08-11**. The dynamic Market Outlook catalog is `Checked`.

**Axis final state:** **3 market-view documents / 3 archived originals / 2 explicit publication dates**. Latest explicit publication date is **2026-03-15**. The dynamic Market-Outlook category and annual outlook PDF are both `Checked`.

Both funds still report `publication_date_missing` because at least one retained communication lacks an unambiguous publication date. Preserve that gap; do not infer one.

### Next backend/data-retrieval task

Continue bounded first-party communication-source discovery for the remaining **19** funds with no retained AMC communication and no dedicated communication source.

Current audit order:

1. **Bajaj Finserv Small Cap Fund**
2. **Bandhan Small Cap Fund**
3. Edelweiss Small Cap Fund
4. Franklin India Small Cap Fund
5. Groww Small Cap Fund
6. HSBC Small Cap Fund
7. ICICI Prudential Small Cap Fund
8. Invesco India Small Cap Fund
9. Kotak Small Cap Fund
10. Mirae Asset Small Cap Fund
11. PGIM India Small Cap Fund
12. Quant Small Cap Fund
13. SBI Small Cap Fund
14. Sundaram Small Cap Fund
15. Tata Small Cap Fund
16. The Wealth Company Small Cap Fund
17. TRUSTMF Small Cap Fund
18. UTI Small Cap Fund
19. Union Small Cap Fund

Start with **Bajaj Finserv communication discovery**, then **Bandhan**. This is separate from Bajaj's blocked **portfolio** recovery: do not treat the portfolio transport blocker as evidence that AMC communication sources are unavailable. Use first-party communication/insight pages only and keep third-party news excluded.

The separate `repair_unarchived_communication_documents` queue remains for **LIC MF, Nippon India and Samco** after the missing-source discovery priority.

The portfolio recovery queue remains independently blocked at **6 items / 0 actionable now**; do not estimate censored holdings or re-probe blocked portfolio routes without a retained source-change signal.

## Previous completed batch: recover retained ITI and Mahindra AMC communications

**The first actionable communication-retrieval queue item is complete.** ITI Small Cap Fund and Mahindra Manulife Small Cap Fund now expose their already-retained first-party monthly outlook/update pages as AMC communications instead of leaving them misclassified as factsheets/source pages.

### Retained evidence reviewed

Read-only diagnostic PR **#180** merged as commit `23dc472e20c8926cc316e980a224e8b5e110e9e8` and inspected the restored production database before any classification change.

It established the exact retained rows:

- **ITI · Equity Market Update** — `https://www.itiamc.com/digitalfactsheet/July2026/equity-update.html` — one archived HTML version; previously `factsheet`.
- **ITI · Debt Market Update** — `https://www.itiamc.com/digitalfactsheet/July2026/debt-update.html` — one archived HTML version; previously `factsheet`.
- **ITI · Market Outlook** — `https://www.itiamc.com/digitalfactsheet/July2026/CEO.html` — one archived HTML version; previously `source page`.
- **Mahindra Manulife · Market Outlook** — `https://www.mahindramanulife.com/digital-factsheet/july-2026/Outlook.html` — one archived HTML version; previously `source page`.

The ITI update pages were misclassified because the generic word `digitalfactsheet` in the URL took precedence over their explicit **Equity Market Update / Debt Market Update** titles.

### Implementation

PR **#181** merged as commit `eab7f7a1b68ba9a950f8919a7ab0852d73981551`.

The backend now:

- gives explicit communication titles precedence over generic `factsheet` path text;
- treats only **dated monthly digital-factsheet pages** with explicit communication titles as communication artifacts; generic market-update directories remain source pages;
- promotes the four exact already-versioned rows above to `market view`;
- leaves all four `published_at` fields **null** because no exact publication date is retained; collection time is not substituted;
- uses a canonical AMC/source-key resolver for document ingestion so a **Mahindra** source cannot attach to **Kotak Mahindra Mutual Fund**;
- keeps third-party news excluded;
- adds an idempotent push-time retained-evidence recovery gate;
- removes the completed diagnostic step/script.

The first implementation run correctly stopped at regression before publication because a general prefix rule made an intentionally ambiguous synthetic AMC name resolve when it should not.

PR **#182** merged as commit `b6e538d6b75defd0cae04a3e45d79a49dd52b0c9` and narrowed that resolver to two reviewed real-world aliases only:

- `Kotak Mahindra Mutual Fund -> Kotak`
- `Mahindra Manulife Mutual Fund -> Mahindra`

All other ambiguous multi-brand names continue to resolve to **none** rather than guessing.

### Production verification

Final production workflow **36219730560** completed successfully at **2026-09-26T05:07:44Z**:

- retained communication recovery: **4 promoted**
- ITI exact market-view rows: **3**
- Mahindra Manulife exact market-view rows: **1**
- Kotak/Mahindra communication cross-associations: **0**
- full regression suite: **385 tests passed**
- generated-site/download validation: **success**
- cumulative-history publication: **success**
- communication/coverage audit publication: **success**
- GitHub Pages deployment: **success**

Pages artifact **10898318429** is **236,554,212 bytes** with digest `sha256:a762bef0ac87ab6159285762ef7ecd7f9dd5e6872be4d620638776a3b6ea4431`.

### Communication coverage after this batch

Final audit generated at **2026-09-26T05:07:08Z**:

- funds with at least one retained AMC communication: **15 / 36** (was 13)
- funds with no retained AMC communication: **21** (was 23)
- retained communication documents: **158** (was 154)
- archived communication originals: **120** (was 116)
- market/newsletter/CIO/product-view documents: **136** (was 132)
- letters to unitholders: **22**
- documents with an explicit `published_at`: **0**
- correctly matched registered communication-oriented source coverage: **9 fund houses**

ITI now has **3 / 3 archived market-view pages**. Mahindra Manulife now has **1 / 1 archived market-view page**. Their only remaining communication-audit issue is `publication_date_missing`; do not infer a date from `first_seen` or from the monthly directory name.

The former `review_registered_communication_sources` repair priority is now gone.

### Next backend/data-retrieval task

**Begin bounded first-party communication-source discovery for the remaining 21 funds with no retained AMC communication and no dedicated communication source registered.**

Current affected funds, in audit order:

**Abakkus, Axis, Bajaj Finserv, Bandhan, Edelweiss, Franklin India, Groww, HSBC, ICICI Prudential, Invesco India, Kotak, Mirae Asset, PGIM India, Quant, SBI, Sundaram, Tata, The Wealth Company, TRUSTMF, UTI and Union Small Cap funds.**

Start with **Abakkus Small Cap Fund**, then **Axis Small Cap Fund**, using existing registered AMC/fund pages first. For each fund:

- identify only first-party newsletters, market/CIO/investment views, product views/presentations, or letters to unitholders;
- register a dedicated communication source only when the page identity is unambiguous;
- retain the original URL/hash and explicit publication date when the source supplies one;
- never use `first_seen` as a publication date;
- never ingest third-party news or generic press/news coverage merely because it mentions the fund;
- add source-specific regression evidence before marking the fund covered.

The separate `repair_unarchived_communication_documents` queue remains for **LIC MF, Nippon India and Samco** after the missing-source discovery priority.

The portfolio recovery queue remains independently blocked at **6 items / 0 actionable now**; do not re-probe Union, Bajaj or Edelweiss portfolio routes until their retained source-change watch changes, and do not estimate Bandhan/Sundaram/UTI censored portfolio weights.

## Previous completed batch: audit AMC-origin communication/news coverage

**The backend now has a dedicated read-only audit for the tracker’s AMC-publication requirement.** It measures newsletters/market/CIO/investment views and letters to unitholders separately from factsheets, portfolios and generic disclosures, and it explicitly excludes third-party news.

### What changed

PR **#178** merged as commit `b202e08bc722a5f225bf931675d6c1b4fd43ba05` and added:

- `tracker/publication_coverage.py` — a read-only per-fund communication coverage audit;
- `docs/PUBLICATION-COVERAGE-AUDIT.json` — machine-readable coverage and repair priorities;
- `docs/PUBLICATION-COVERAGE-AUDIT.md` — operator-readable summary;
- regression coverage proving AMC-origin filtering, third-party exclusion, published-date gap handling, repair-priority grouping and read-only behavior;
- normal successful-build publication through `scripts/record_build.py`.

The first production audit exposed a fund-house matching collision: **Kotak Mahindra Mutual Fund** incorrectly inherited a **Mahindra Manulife** communication source because substring matching saw “Mahindra” in both names. PR **#179** merged as commit `a3d7116386df7e55a066b93cee26b82ef2a49f87` and corrected the audit to resolve one registered AMC source key by normalized prefix. A dedicated regression now prevents that Kotak/Mahindra collision.

No source fetch, financial-data mutation, UI change, paid data, third-party news ingestion, source deletion or retention-policy change was introduced by this audit batch.

### Production verification

Final production workflow **36218671256** completed successfully:

- build: **success**
- full regression suite: **381 tests passed**
- generated-site/download validation: **success**
- cumulative-history publication: **success**
- collection-status/audit publication: **success**
- GitHub Pages deployment: **success**

Pages artifact **10898346614** is **236,555,178 bytes** with digest `sha256:2bedaebf73caafae81891fd69dc03de37d2b470fda56410d4203b6855c3fc916`.

Final communication audit generated at **2026-09-26T04:45:39Z**:

- funds: **36**
- funds with at least one retained AMC communication: **13**
- funds with no retained AMC communication: **23**
- retained communication documents: **154**
- archived communication originals: **116**
- market/newsletter/CIO/product-view documents: **132**
- letters to unitholders: **22**
- communication documents with an explicit `published_at`: **0**
- funds with a correctly matched registered communication-oriented source: **9**

The zero `published_at` count is an evidence gap, not permission to backdate records from collection time. `first_seen` must not be substituted for the publication date.

### Actionable communication-retrieval queue

Priority **1 — review already registered first-party communication sources**:

1. **Iti Small Cap Fund**
   - `https://www.itiamc.com/digitalfactsheet/July2026/CEO.html` — Market Outlook — Checked
   - `https://www.itiamc.com/digitalfactsheet/July2026/equity-update.html` — Equity Market Update — Checked
   - `https://www.itiamc.com/digitalfactsheet/July2026/debt-update.html` — Debt Market Update — Checked
   - These pages already yielded archived related documents, but none are currently classified/retained as an AMC communication for the fund.

2. **Mahindra Manulife Small Cap Fund**
   - `https://www.mahindramanulife.com/digital-factsheet/july-2026/Outlook.html` — Market Outlook — Partial
   - The retained source check found two relevant linked documents, but neither currently satisfies the communication audit.

Priority **2 — discover a dedicated first-party communication source** for **21 funds**:
Abakkus, Axis, Bajaj Finserv, Bandhan, Edelweiss, Franklin India, Groww, HSBC, ICICI Prudential, Invesco India, Kotak, Mirae Asset, PGIM India, Quant, SBI, Sundaram, Tata, The Wealth Company, TRUSTMF, UTI and Union Small Cap funds.

Priority **3 — repair retained communication originals** for **LIC MF, Nippon India and Samco**. These funds already have communication metadata, but some corresponding original versions are not archived.

### Next backend/data-retrieval task

**Start with ITI, then Mahindra Manulife, using retained evidence before any new broad discovery.**

For ITI:
- inspect the exact documents/links already retained from the three registered market-update/outlook pages;
- determine why they are currently classified outside `market view` / `unitholder letter`;
- promote only documents whose first-party title/source unambiguously identifies an AMC communication;
- retain an explicit publication date only when the source itself provides one; never substitute `first_seen`.

Then apply the same evidence-first review to Mahindra Manulife’s registered Outlook page. If the existing archived links are genuine AMC outlook/communication documents, fix the narrow classifier/association and add regression coverage. If they are not communications, preserve the gap and move that fund to first-party communication-source discovery.

The portfolio recovery queue remains separately blocked at **6 items / 0 actionable now**; do not re-probe Union, Bajaj or Edelweiss until their retained source-change watch changes. Bandhan, Sundaram and UTI remain precision-limited and must not be completed by estimating censored weights.

## Previous completed batch: recover ICICI Prudential complete monthly portfolios

**ICICI Prudential Small Cap Fund is no longer in the incomplete-portfolio recovery queue.** The tracker now retains two consecutive, first-party, complete month-end portfolio snapshots from ICICI Prudential's public downloads service, with exact source URLs, source hashes, reporting dates and constituent weights.

### What changed

The AMC's canonical `/downloads/...` ZIP URL still redirects to the retired/unreachable `archive.icicipruamc.com` host. Investigation found that the same exact public monthly ZIPs are served by ICICI Prudential through the working first-party `/blob/downloads/...` delivery route.

The collector now:

- resolves the exact `Other Scheme Disclosures -> Monthly Portfolio Disclosures` records from ICICI Prudential's public downloads API rather than guessing filenames;
- selects the newest two closed month-end ZIPs;
- preserves the exact first-party ZIP URL and archived content hash as provenance;
- safely opens the omnibus ZIP and accepts only the two exact Small Cap workbook spellings observed first-party: `ICICI Prudential Small Cap Fund.xlsx` and `ICICI Prudential Smallcap Fund.xlsx`;
- treats ICICI's published numeric section-total rows as structural subtotals rather than duplicate holdings;
- retains the explicit `Cash Margin - Derivatives` leaf so the disclosed portfolio reconciles exactly;
- uses source-specific parser version `icici-portfolios-2026-09-v2`, forcing already-observed source hashes through the corrected parser;
- keeps ICICI discovery in the nightly AMC-report collector;
- fails the push recovery gate instead of silently publishing if both current/prior closed-month snapshots are not verified complete.

No constituent weight was estimated or inferred to close the portfolio.

### Production evidence

Final implementation PR **#176** merged as commit `736ad748aa6b22a9ed126ea55b82d936f8044db8`.

Final production workflow **36217849535** completed successfully:

- build: **success**
- full regression suite: **377 tests passed**
- generated-site/download validation: **success**
- cumulative-history publication: **success**
- GitHub Pages deployment: **success**

Recovered snapshots:

- **31-Aug-2026** — source `https://www.icicipruamc.com/blob/downloads/Files/Monthly%20Portfolio%20Disclosures/2026/Aug/Monthly-Portfolio-Disclosure-August-2026.zip`; hash `345db37f8c8e38b497091f3a9a3580bb77e7803944cad03098a1605938c3c9eb`; **125 positions**; complete; disclosed weight sum **99.99999999936607%**.
- **31-Jul-2026** — source `https://www.icicipruamc.com/blob/downloads/Files/Monthly%20Portfolio%20Disclosures/2026/July/Monthly-Portfolio-Disclosure-July-2026.zip`; hash `fcfe2f11e922eac7bcb9d871d4b7087344b056aaa2607e975e6ddfb250c61c8d`; **136 positions**; complete; disclosed weight sum **99.99999999931627%**.

The implementation was developed through PRs **#174**, **#175** and **#176**. The temporary layout diagnostic used to establish the July/August evidence boundary was removed from the production workflow after the parser repair.

### Portfolio-recovery queue after this batch

The generated queue at **2026-09-26T04:30:01Z** moved from **7 items to 6**:

- items: **6**
- actionable now: **0**
- source changes detected: **0**
- stale partial: **1**
- missing: **1**

Current order:

1. **Union Small Cap Fund** — missing; blocked on first-party transport; retry only after the official Downloads/portfolio transport recovers or an exact first-party attachment appears.
2. **Bajaj Finserv Small Cap Fund** — stale partial; current AMC factsheet names only a subset; Downloads and the tested first-party media-catalog routes remain blocked from the production runner.
3. **Edelweiss Small Cap Fund** — current partial; current AMC factsheet names only Top 10 holdings; statutory portfolio source has not exposed a usable exact monthly attachment.
4. **Bandhan Small Cap Fund** — current partial only because the AMC publishes one or more exact weights as `<0.01%`; do not estimate them.
5. **Sundaram Small Cap Fund** — current partial because a written-off holding is disclosed only as `<0.01%`; do not estimate it.
6. **UTI Small Cap Fund** — current partial because the AMC censors at least one tiny security weight and omits an exact NAV percentage for short-term deposits; do not estimate them.

Authoritative queue files remain `docs/PORTFOLIO-RECOVERY-QUEUE.json` and `docs/PORTFOLIO-RECOVERY-QUEUE.md`.

### Next data-retrieval task

**There is no portfolio recovery item that is actionable now without violating the first-party/no-estimation boundary.** Do not repeatedly re-probe blocked routes or invent alternate attachment URLs.

Continue from the first newly retained source-change signal, in queue order: **Union -> Bajaj Finserv -> Edelweiss**. When a watch changes, review the new first-party evidence first and only then implement recovery. Until such a signal exists, keep Bandhan, Sundaram and UTI partial rather than estimating censored weights.

The older storage-retention work below remains separately approval-gated and should not displace this data-retrieval priority unless the owner explicitly moves back to storage work.

## Source-retention audit — NO deletion authorized (2026-09-25 UTC)

The owner approved classification and savings analysis BEFORE deleting anything. Completed report: `docs/SOURCE-RETENTION-AUDIT.md`; per-hash CSV/JSON inventories and summary are adjacent. Final review run **36093073121** passed **299 tests**. Source-pack measurement run **36092819677** checked all **95** packs against release digests. The exact production checkpoint is unchanged, with **629,225 rows** and **2,519 originals**.

Final link-only candidates: **700 files / 404,498,141 raw bytes / 34,253,903 compressed payload bytes** (ZIP headers excluded). These are superseded discovery responses, not proven duplicates or guaranteed recoverable historical files. Current saved document versions, financial evidence, historical extractions, original reports, unknown requests and fragile transport sources remain protected or under review. **Deleted files/bytes: 0.**

No production workflow, source-retention policy, database schema, collector, UI or schedule was changed. Approval of this audit is NOT approval to delete the candidates or retire the old legacy ZIP. Before any approved migration, make restore, replay, archive serving and publication/download code retention-aware, preserve provenance, validate replacement packs and retain rollback until independently verified.

## Database cleanup (2026-09-25 UTC)

**Read `docs/STORAGE-CLEANUP.md` for the current merge, production verification and cleanup status.** This is the storage batch's completion/handoff record; the validation evidence is in `docs/STORAGE-VALIDATION.json`.

The owner requested unnecessary/redundant database storage cleanup. The four NAV/benchmark tables were migrated to composite-primary-key `WITHOUT ROWID` storage on a production copy. All 273 tests, all-table content equality, integrity/foreign-key checks, idempotence, checkpoint restore and generated-site validation passed. Measured database size: **100,773,888 to 73,322,496 bytes**; checkpoint ZIP **12,851,483 to 7,451,746 bytes**. No logical record or original source was removed.

The legacy cumulative ZIP `state-35791406887-1.zip` (**1,087,514,828 bytes**) remains untouched: its retirement action was blocked, so do not claim this storage was reclaimed. Source-retention policy and fund scope are unchanged. After storage publication is verified, resume the previously documented portfolio source-recovery task below.


Prior storage-retention section updated: 2026-09-26, after refreshed 696-hash historical retention simulation.








## Latest completed batch: refresh historical retention simulation at exactly 696 hashes

**The isolated replacement-pack simulation is now refreshed against the corrected historical candidate set: 696 currently eligible hashes from the original 700-hash review, with all 5 newer post-audit candidates explicitly excluded. No production storage mutation occurred.**

PR **#159** merged as commit `97ecf0d434bdbaabb27bda37e0ec6157ad777ab7`.

The simulator now has a hard boundary gate:

- historical reviewed candidates: **700**
- historical candidates simulated metadata-only: **696**
- historical candidates strengthened/protected: **4**
- separate post-audit delta candidates: **5**
- overlap between historical migration and post-audit delta: **0**

If any of those counts or the zero-overlap condition changes, the simulation aborts instead of emitting a proposal.

Regression coverage was added for the exact **696 / 4 / 5 / 0-overlap** partition.

### Successful isolated run

Workflow **36208730633** completed successfully at **2026-09-26T01:33:38Z**.

Pinned checkpoint:

- active manifest created: **2026-09-26T01:21:17Z**
- database asset: `database-36208080152-1.zip`
- archive hashes: **2,790**
- active source packs: **101**

Artifact commit: `8416fc7d0bcd0003f515c02ad222006d92af73ee`.

PR **#160** merged as commit `e65011ee52f7b6d64d723a45c79aecbb4bf43e86` and removed the completed one-time simulation workflow. The normal daily pipeline contains no retention simulation step.

The implementation push's ordinary tracker workflow **#519 / run 36208730698** also completed successfully, including site generation, cumulative-history publication and Pages upload/deployment.

### Refreshed exact historical proposal

- historical candidates: **696**
- candidate raw bytes: **403,410,385**
- candidate compressed payload bytes: **34,144,511**
- retained hashes in the simulated checkpoint: **2,094**
- affected packs: **50**
- replacement packs: **25**
- packs fully retired: **25**
- proposed steady-state pack count: **76**

Measured assets:

- current source-pack assets: **1,540,491,329 bytes**
- proposed source-pack assets: **1,506,182,012 bytes**
- exact source-pack savings: **34,309,317 bytes**
- current database ZIP: **7,920,465 bytes**
- simulated database ZIP: **7,921,495 bytes**
- exact active-set savings: **34,308,287 bytes**

Actual reclaimed production bytes remain **0**.

### Validation

The refreshed simulation proves:

- non-retention database fingerprints unchanged;
- exact retained-hash manifest coverage;
- duplicate proposed hashes: **0**;
- all **1,051** protected evidence hashes retained;
- metadata-only materialization blocked;
- retained replacement member checksum restoration passed;
- AMC replay gaps: **0**;
- metadata-only archive download blocked;
- metadata-only saved document version hidden;
- full simulated static-site generation/validation passed;
- metadata-only candidates published in simulated site: **0**;
- active packs/database preserved as rollback.

Production mutations:

- release uploads: **0**
- release deletions: **0**
- active manifest switch: **false**
- production binary-state changes: **0**
- source-file deletions: **0**
- legacy ZIP retirement: **false**

The authoritative current historical review artifacts are:

- `deployment/retention-pack-simulation.json`
- `docs/RETENTION-PROPOSED-MANIFEST.json`
- `docs/RETENTION-MIGRATION-CANDIDATES.json`
- `docs/RETENTION-REPLACEMENT-SIMULATION.md`

### Approval boundary

**Do not execute the 696-hash binary reduction without explicit owner approval.** It is now technically simulated and review-ready, but the destructive migration remains separately approval-gated.

The **5 post-audit link-only candidates / 3,851,376 raw bytes** remain a separate delta and are not part of the 696-hash proposal.

Current full retention classification remains:

- retain_evidence: **1,051**
- retain_latest_or_review: **1,038**
- link_only_candidate: **701**
- unclassified: **0**
- binary retained: **2,790 / 2,790**

Current portfolio queue remains **7 items / 0 actionable_now / 0 source changes detected**. BSE TRI remains non-actionable under the free first-party-source constraint.

### Next backend task

**Perform a source-by-source manual evidence review of the 5 new post-audit link-only candidates and produce a separate delta-only simulation if all remain eligible. Do not merge them into the 696-hash proposal.**

Review these exact first-party discovery pages:

1. SAMCO Mutual Fund — statutory-disclosure page;
2. Baroda BNP Paribas — September 2026 Small Cap e-factsheet HTML;
3. Kotak Small Cap — September 2026 factsheet HTML;
4. Kotak Small Cap — July 2026 factsheet HTML;
5. Quantum Small Cap Fund — fund page.

For each hash:

- verify it is truly superseded by a newer retained response for every associated URL;
- confirm no financial metric, portfolio, successful extraction, current document version, replay path or fragile-transport dependency uses the hash;
- keep binary state `retained`;
- record an explicit reviewed decision and evidence;
- if all 5 remain link-only candidates, run a **separate 5-hash isolated pack simulation** and report only its incremental savings;
- do not combine the 5-hash delta with the 696-hash historical proposal and do not execute either migration.

If any portfolio source-change watch becomes actionable first, pause retention work and resume that first-party data repair.

## Latest completed batch: classify 271 post-audit retention hashes and repair self-protection

**All 271 hashes added after the original retention audit are now classified conservatively, every binary remains retained, and the generated-review-artifact self-protection regression is fixed.**

PR **#157** merged as commit `325ab240a9e7fe0629dcf65b970b1ba2273d2b3c`.

### Root-cause repair

The prior simulation artifacts contained complete archive-hash lists. Because the retention scanner deliberately protects literal hash dependencies in code/handoff files, it accidentally treated generated review outputs as new evidence and promoted historical candidates to `retain_evidence`.

Generated retention outputs are now excluded from that dependency class:

- `RETENTION-PROPOSED-*`
- `RETENTION-MIGRATION-*`
- `RETENTION-REPLACEMENT-*`
- the existing `SOURCE-RETENTION-*` exclusions remain.

Regression tests prove these generated files no longer self-protect the hashes they describe.

Retention preparation now derives state from:

1. the original reviewed classification as a historical minimum floor;
2. the corrected current conservative dependency scan;
3. only genuinely independent stored promotions/reviews, such as a later refetch becoming current evidence.

An automated stronger state caused only by the prior scan can therefore be repaired when the corrected scan no longer supports it. Protected evidence and genuine refetch promotions remain protected.

### 271-hash post-audit review

Production review time: **2026-09-26T01:17:22Z**.

Results:

- **67 retain_evidence** — **147,277,130 raw bytes**
- **199 retain_latest_or_review** — **89,172,029 raw bytes**
- **5 link_only_candidate** — **3,851,376 raw bytes**
- **0 unclassified**

Every binary remains `retained`.

Review artifacts:

- `docs/SOURCE-RETENTION-DELTA.json`
- `docs/SOURCE-RETENTION-DELTA.md`
- `docs/SOURCE-RETENTION-NEW-CANDIDATES.json`

The five new candidates remain a **separate proposal delta** and are not merged into the earlier migration set.

### Full current retention state

`deployment/retention-readiness.json` at **2026-09-26T01:17:23Z** reports:

- archive hashes: **2,790**
- binary retained: **2,790**
- binary metadata-only: **0**
- retain_evidence: **1,051**
- retain_latest_or_review: **1,038**
- link_only_candidate: **701**
- unclassified: **0**
- files actually deleted: **0**
- bytes actually deleted: **0**
- source-pack repack: **false**
- rollback/legacy retirement: **false**
- protected archive metadata unchanged: **true**
- all non-retention table fingerprints unchanged: **true**
- current dependency scan missing hashes: **0**

### Production verification

Production workflow **#517 / run 36207892234** completed successfully at **2026-09-26T01:18:37Z**:

- production checkpoint restore passed;
- corrected retention classification preparation passed;
- all normal source-upgrade steps passed;
- database compaction passed;
- **365 tests passed**;
- generated site/download validation passed;
- cumulative-history publication passed;
- build-status recording passed;
- GitHub Pages deployment passed.

Status commit: `1012b753d8d10bebbefe6c8c141908e0d75cbf96`.

Pages artifact **10894692627** is **234,247,457 bytes** with digest `sha256:b2fd805da9aef40e380e063577a2068bc26b112f99d915ef812e0fabd7a0826f`.

Core fund coverage remains **36/36 AUM, fee, TER, BER and benchmark identity**. Portfolio recovery remains **7 queued items / 0 actionable_now / 0 source changes detected**.

### Important effect on the previous simulation

The corrected scan currently strengthens only **4** of the original 700 historical candidates.

Therefore the current historical candidate set is **696**, not the previously simulated 695.

Separately, this batch found **5 new post-audit candidates**.

The old 695-hash migration proposal is now **stale and must not be executed**. The five new candidates must also remain separate until individually reviewed/approved.

### Next backend task

**Refresh the isolated replacement-pack simulation against exactly the 696 currently eligible hashes from the original historical 700-hash review. Do not include the 5 new post-audit candidates.**

The refreshed simulation should:

1. start from the latest exact active checkpoint;
2. derive the original-review subset from `SOURCE-RETENTION-INVENTORY.json`;
3. intersect that set with corrected current retention state;
4. assert exactly **696** historical candidates before simulating;
5. explicitly prove the 5 new delta candidates are excluded;
6. regenerate exact replacement-pack counts and compressed savings;
7. validate protected evidence, restore/materialization, replay, archive/download behavior and full static-site generation;
8. preserve current active packs/database as rollback;
9. perform **0 production mutations**.

Only that refreshed simulation should be considered for any later owner approval. The existing 695-hash simulation artifacts remain historical evidence only.

If a portfolio source-change watch becomes actionable first, pause storage work and resume that first-party data repair.

## Latest completed batch: isolated retention replacement-pack simulation

**The replacement-pack migration has been simulated successfully without changing production storage. The authoritative proposed set is 695 currently eligible hashes, not the original historical 700, because newer evidence protected 5 reviewed candidates.**

Implementation history:

- PR **#150** / commit `d649192948eca5cde370328c63f6d58591255f55` added the isolated replacement-pack simulator and regression coverage.
- PR **#151** / commit `bf527857aed773c7761d1dafdc6a7a0b54ddcf9f` tightened the simulation to restore the exact active database checkpoint rather than an in-flight workflow database.
- PR **#152** / commit `aa7b7d7866638e3cfcda4b1ca985f6cb821c8901` pinned all selective materialization/replay operations to the same captured active manifest.
- PR **#153** / commit `7a2b005e89a27a5ff3c54cda5815849b7953a612` created the dedicated isolated one-time workflow.
- The first successful pinned simulation, run **36194814270**, validated all 700 against the earlier 21:19 checkpoint and produced historical review evidence.
- A subsequent normal tracker run correctly exposed that the old 700-hash set had become stale after newer source evidence strengthened some hashes.
- PR **#154** / commit `49092a076af20f8bb28a7457bc6a2ee7bbac6afd` changed the simulator to intersect the reviewed inventory with the active checkpoint's current retention state and removed simulation from the normal daily workflow.
- Final isolated simulation run **36205872175** completed successfully at **2026-09-26T00:45:24Z**.
- PR **#155** / commit `72dcca3a6934ea511e767cb4f6fd2fd0df069ad2` removed the completed one-time simulation workflow.

The normal daily workflow without the simulation hook also completed successfully as workflow **#514 / run 36205872176**.

### Final current-eligible proposal

Checkpoint:

- active manifest created: **2026-09-25T22:17:18Z**
- database asset: `database-36193281824-1.zip`
- archive hashes: **2,790**
- active source packs: **101**

Candidate evolution:

- historical reviewed link-only candidates: **700**
- currently eligible link-only candidates: **695**
- reviewed hashes promoted/protected by newer evidence: **5**
- retained hashes after proposed migration: **2,095**

The five excluded reviewed hashes are explicitly recorded in `docs/RETENTION-MIGRATION-CANDIDATES.json` with their current `retain_latest_or_review` reasons. They remain binary-retained.

### Exact measured savings

For the 695 currently eligible candidates:

- raw bytes: **403,318,035**
- compressed payload bytes from the reviewed pack audit: **34,139,810**
- affected active packs: **49**
- proposed replacement packs: **24**
- packs fully retired in the proposed steady state: **25**
- proposed source-pack count: **76**

Asset sizes:

- current source-pack assets: **1,540,491,329 bytes**
- proposed source-pack assets: **1,506,186,949 bytes**
- exact source-pack reduction: **34,304,380 bytes**
- current database ZIP: **7,919,692 bytes**
- simulated database ZIP: **7,920,662 bytes**
- exact active-set reduction: **34,303,410 bytes**

This is proposed steady-state savings only. **Actual reclaimed release bytes remain 0.**

### Simulation validation

The committed artifacts prove:

- every non-retention database table fingerprint is unchanged;
- proposed pack coverage is exact with **0 duplicate hashes**;
- all **984** protected evidence hashes remain retained;
- metadata-only materialization is blocked;
- retained replacement members restore and checksum correctly;
- AMC replay has **0 gaps** and no metadata-only eligibility;
- metadata-only archive downloads are unavailable;
- metadata-only document saved copies are hidden;
- full static-site generation/validation succeeds;
- simulated site publishes **0** metadata-only candidates;
- all **101** current active source packs and the current database asset remain preserved as rollback.

Production mutations in this task:

- release uploads: **0**
- release deletions: **0**
- active manifest switches: **0**
- production binary-state changes: **0**
- source-file deletions: **0**
- legacy ZIP retirement: **false**

Review artifacts:

- `deployment/retention-pack-simulation.json`
- `docs/RETENTION-PROPOSED-MANIFEST.json`
- `docs/RETENTION-MIGRATION-CANDIDATES.json`
- `docs/RETENTION-REPLACEMENT-SIMULATION.md`

### Approval boundary and next autonomous task

**Do not execute the 695-hash binary reduction without explicit owner approval.** The proposal is ready, but changing binary states, uploading replacement packs, switching `latest.json`, retiring old packs or deleting any source file is a destructive/storage action that remains separately approval-gated.

Until such approval is given, the next safe backend task is:

**Run a fresh conservative retention classification review for the 271 newer `unclassified + retained` hashes added after the original 2,519-hash audit.**

That next batch should:

1. classify only the 271 newer hashes using the same dependency-first rules;
2. never weaken any existing `retain_evidence` or `retain_latest_or_review` state;
3. keep every binary retained;
4. update the retention inventory/audit counts;
5. report whether any of those 271 are new link-only candidates, but do not merge them into the approved migration set automatically;
6. regenerate a separate proposed-candidate delta for review;
7. pause immediately if `docs/PORTFOLIO-RECOVERY-QUEUE.json` reports an actionable first-party source change.

Current portfolio queue remains **7 items / 0 actionable_now / 0 source changes detected**. BSE TRI remains non-actionable under the free first-party-source constraint.

## Latest completed batch: non-destructive retention-aware storage plumbing

**Retention-aware storage infrastructure is now deployed with every source binary still physically retained. No source file, source pack, rollback checkpoint or legacy ZIP was deleted.**

Implementation PR **#146** merged as commit `c522c313fa03359590e2cdd8c9e9235773e19cde`.

The batch introduced an `archive_retention` table keyed by source hash with:

- monotonic classifications: `unclassified`, `link_only_candidate`, `retain_latest_or_review`, `retain_evidence`;
- binary states: `retained` or `metadata_only`;
- review/reason/update metadata;
- hard guards preventing protected evidence from being downgraded or marked metadata-only.

The reviewed source-retention inventory is loaded conservatively on each build. A current dependency scan is re-run and can only **strengthen** the historical classification. New hashes outside the old audit remain `unclassified + retained`. A previously reviewed candidate that is fetched again as current evidence is promoted to `retain_latest_or_review + retained`.

### Retention-aware execution paths

The following paths now honor logical binary state:

- archive download endpoint;
- fund-document saved-version listings;
- AMC archived-document replay/reprocessing;
- selective source-pack materialization;
- complete restore verification;
- split source-pack planning and validation;
- GitHub Pages publication selection;
- manual cumulative-archive import/superset validation.

A metadata-only record can retain provenance while being absent from saved-copy/download/replay paths. Old checkpoints without the retention table remain backward compatible and are treated as fully retained.

The source-pack publisher intentionally **refuses** a future metadata-only state if the active immutable packs still contain those hashes. A real reduction therefore requires an explicit atomic replacement-pack migration rather than silently changing the meaning of existing packs.

### Production verification

The first production attempt, workflow **#505 / run 36188792392**, passed schema migration, reviewed-classification loading, all source-upgrade steps, final retention validation and database compaction. The regression suite then found an ambiguous SQL `ORDER BY hash` in three test paths plus one overly specific error-message assertion. The workflow failed **before site generation/publication**, so no bad Pages/archive checkpoint was published.

Fix PR **#147** merged as commit `742f84f4412e376ba5bb23d8ddb91c25905bb596`.

Production workflow **#506 / run 36188946719** completed successfully at **2026-09-25T21:00:46Z**:

- production database-only restore passed;
- reviewed retention classifications loaded;
- all normal source-upgrade steps passed;
- final retention reconciliation/readiness validation passed;
- database compaction passed;
- **349 tests passed**;
- generated-site/download validation passed;
- cumulative split history publication passed;
- build-status recording passed;
- GitHub Pages deployment passed.

Status commit: `a15eb4ed74bf015f31d532dc8ab322bd0f9d09b9`.

Pages artifact **10887610870** is **230,661,791 bytes** with digest `sha256:87834a7776b15d50232dc37342c38d8f272d1c3a4593d4f1be820d50b5fd1860`.

### Production retention-readiness result

`deployment/retention-readiness.json` at **2026-09-25T20:59:23Z** reports:

- archive hashes: **2,526**
- historical reviewed hashes: **2,519**
- historical link-only candidates: **700**
- new unclassified hashes: **7**
- binary retained: **2,526**
- binary metadata-only: **0**
- files actually deleted: **0**
- bytes actually deleted: **0**
- source-pack repack performed: **false**
- rollback/legacy assets retired: **false**
- protected archive metadata unchanged: **true**
- all existing non-retention table fingerprints unchanged during migration: **true**
- protected hashes covered by active source packs: **true**
- all 700 historical candidates still covered by active source packs: **true**
- deletion enabled: **false**
- approved for binary deletion: **false**

Current stored classes are **984 retain_evidence**, **835 retain_latest_or_review**, **700 link_only_candidate**, and **7 unclassified**; every one is still binary-retained.

Current core data coverage remains **36/36 AUM, fee, TER, BER and benchmark identity**. Portfolio coverage remains **35/36**, and `docs/PORTFOLIO-RECOVERY-QUEUE.json` still reports **7 items / 0 actionable_now / 0 source changes detected**. The BSE 250 SmallCap TRI history remains explicitly non-actionable under the free first-party-source rule.

### Next backend task

**Build an isolated replacement-pack migration simulation for the 700 reviewed link-only candidates. Do not change production binary state and do not delete/upload/retire any source pack yet.**

The next batch should:

1. copy/restore the current production database and active source-pack manifest into an isolated migration workspace;
2. mark exactly the reviewed 700 hashes as `metadata_only` **only in that isolated copy**;
3. generate a proposed replacement source-pack plan containing every logically retained hash and excluding exactly those 700 candidates;
4. validate proposed pack membership, per-member hashes/bytes, protected-evidence coverage, database/provenance equality, selective materialization behavior, AMC replay expectations, document-download behavior and full static-site generation against the simulated state;
5. calculate exact proposed release-asset byte savings and distinguish raw source bytes from actual compressed pack savings;
6. preserve the current active manifest/packs as rollback and produce an exact migration manifest + candidate-hash list for owner review;
7. perform **no GitHub release upload, deletion, active-manifest switch, binary-state change or legacy-ZIP retirement**.

Only after that simulation is independently green should an actual binary-reduction migration be proposed for explicit approval.

If any portfolio source-change watch becomes positive first, pause this storage simulation and resume that newly actionable first-party data repair.

## Latest completed batch: final unresolved NAV-gap classification

**The last unresolved `nav_large_gap` is now closed with exact option-level AMFI evidence. No NAV observation was added, estimated, interpolated or forward-filled.**

Diagnostic PR **#143** merged as commit `3d8522d5bc5fb9e8e5f0b0eccbb4fa13346b6477` and ran the one-time exact AMFI check in workflow **#502 / run 36185438441**.

The query was:

`https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx?mf=3&frmdt=31-May-2010&todt=08-Jun-2010`

The diagnostic filtered the official response specifically to **AMFI scheme code 105805 — Aditya Birla Sun Life Small Cap Fund · Regular · IDCW**.

Exact result:

- response bytes: **171,465**
- MIME: **text/plain**
- SHA-256: `4b0ab23045b78f1e8b143ea8509f3da3f2dc5aa4d138e668f2a9645fd75db5fb`
- exact code-105805 rows: **2**
- **2010-05-31 — NAV 11.5499**
- **2010-06-08 — NAV 11.4193**
- payout ISIN: **INF209K01EO0**
- reinvestment ISIN: **INF209K01EP7**

No intermediate code-105805 NAV row exists in the authoritative AMFI history for that exact interval.

PR **#144** merged as commit `11cdd6bc017ab23d484ef639a09e978f7c306dbb` and converted that diagnostic evidence into the durable audit classification:

- added a dedicated `verified_official_history_gap` record for scheme **105805** in `tracker/nav_gap_evidence.json`;
- retained the raw 8-calendar-day interval in the audit evidence;
- removed the actionable `nav_large_gap` classification;
- updated `docs/NAV-GAP-AUDIT.md`;
- removed the one-time diagnostic script and workflow step;
- added an exact option-level regression test that checks the scheme code, both ISINs, both boundary observations and the absence of `nav_large_gap`.

### Production verification

Production workflow **#503 / run 36185896041** completed successfully at **2026-09-25T20:29:09Z**:

- production checkpoint restore and all normal source upgrades passed;
- database compaction passed;
- **341 tests passed**, including `test_absl_regular_idcw_gap_is_verified_at_exact_option_level`;
- generated site and download validation passed;
- cumulative-history publication and build-status recording passed;
- Pages deployment passed.

Status commit: `41696a7b21722717d45a1dfbf68728f98ffeb053`.

Pages artifact **10886078886** is **230,661,250 bytes** with digest `sha256:f533aa1c1c5238904d1d2d18e63a2b7bffb24898e209b792b8ef7961c83824c3`.

The production performance audit generated at **2026-09-25T20:28:37Z** now shows for code **105805**:

- raw gap count >7d: **1**
- verified official-history gaps: **1**
- unresolved/actionable gaps: **0**
- `nav_large_gap`: **absent**

The global `issue_counts` no longer contains `nav_large_gap`. Historical performance now contains only:
- structural `history_starts_after_target` young-fund limitations;
- the explicitly non-actionable BSE 250 SmallCap TRI source gap.

### Current data-coverage state after this closeout

Current `COVERAGE-AS-OF.json` reports:

- funds: **36**
- AUM: **36 / 36**
- fee: **36 / 36**
- TER: **36 / 36**
- base expense ratio / BER: **36 / 36**
- benchmark identity: **36 / 36**
- portfolio present: **35 / 36**
- complete portfolios: **29**
- fresh portfolios: **34**
- fresh + complete portfolios: **29**
- partial portfolios: **6**

`docs/PORTFOLIO-RECOVERY-QUEUE.json` currently has **7 items and 0 actionable-now items**. Union remains missing behind first-party transport failure; Bajaj Finserv is stale partial; Edelweiss and ICICI are source-access/subset blockers; Bandhan, Sundaram and UTI require more precise AMC disclosure. No source-change watch is currently positive.

The historical BSE TRI source remains non-actionable under the current free first-party-source rule.

### Next backend task

**Build the non-destructive retention-aware storage plumbing required before any link-only source-file reduction is allowed. Do not delete any candidate files yet.**

The source-retention audit already identified **700 `link_only_candidate` responses / 404,498,141 raw bytes / 34,253,903 compressed payload bytes**, but explicitly prohibits deletion until restore/replay/publication behavior understands binary-retention state.

The next batch should implement only the safe infrastructure prerequisite:

1. add explicit retained-binary state/metadata for archived hashes while preserving every provenance row, URL, observed time and classification;
2. make archive serving, replay/reprocessing, restore verification, source-pack validation and Pages publication selection distinguish:
   - binary retained,
   - metadata-only/link-only candidate,
   - protected evidence;
3. ensure a metadata-only source never appears as a downloadable saved copy and never causes a broken restore/replay path;
4. prevent ordinary collection from immediately re-archiving a deliberately metadata-only superseded discovery response unless it becomes current/protected evidence;
5. add migration/dry-run validation on a production copy, with **zero deletion** and exact row/content equality for all protected evidence;
6. keep current source packs, rollback checkpoint, legacy cumulative ZIP and all 700 candidate binaries untouched until a later separately approved migration;
7. update `docs/SOURCE-RETENTION-AUDIT.md` / storage validation evidence with the new readiness state, but do not report any reclaimed bytes yet.

This work is now the preferred active backend task because:
- core numeric coverage is **36/36** for AUM/TER/BER/benchmark identity;
- historical NAV-gap repair is closed;
- BSE TRI is non-actionable;
- the portfolio recovery queue has **0 actionable-now** entries.

Portfolio/source recovery should resume immediately if a queue source-change watch becomes positive before or during this storage-plumbing work.

## Latest completed batch: performance-audit benchmark semantics cleanup

**The read-only performance coverage audit now matches the deployed evidence-aware backend and hosted UI. All stale global-Nifty `website_default_*` fields and mismatch issues are gone.** PR **#141** merged as commit `7a2a2a777ea16890e0d0f0990bd153c44c49ad83`.

### Audit contract

Top-level policy is now explicit:

- `default_role = reported_benchmark`;
- `automatic_substitution = false`;
- `alternate_comparisons = explicit_request_only`.

Each plan's benchmark audit now exposes:

- `reported_identity` — retained reported benchmark evidence;
- `reported_series` — the canonical reported TRI series and whether it is retained;
- `overlap` / `overlap_horizons` — exact-date overlap with that reported series only;
- `alternate_comparisons` — retained non-reported TRI series that a user may choose explicitly, each labelled `alternate_comparison`.

A retained alternate no longer creates an issue and is never described as a website default. `reported_tri_series_missing` remains the issue when the fund's actual reported TRI history is unavailable.

The old fields/issues were removed completely:

- `website_default_benchmark`;
- `website_default_series`;
- `website_default_overlap`;
- `website_default_overlap_horizons`;
- `website_default_mismatch`;
- `website_default_mismatch_growth_plans`;
- `website_default_benchmark_mismatch`.

### Production result

Production workflow **#500 / run 36182746080** completed successfully at **2026-09-25T19:58:22Z**:

- production checkpoint restore and all normal source upgrades passed;
- database compaction passed;
- **340 tests passed**, including the updated evidence-aware audit tests;
- static site generation and generated-data/download validation passed;
- cumulative-history publication and status recording passed;
- Pages deployment passed.

Status commit: `acb5963d1543177af8290c72549f357076f54c2a`.

Pages artifact **10884504202** is **230,661,269 bytes** with digest `sha256:0b8154c5923bd11fd97478b58dc1da861499b7c2521a21f4f935d31ab0ce34a8`.

The production audit generated at **2026-09-25T19:57:44Z** now reports:

- plans: **143**
- Growth plans: **72**
- reported benchmark identity families: **36 / 36**
- explicit reported TRI identities on Growth plans: **72 / 72**
- reported TRI series retained on Growth plans: **52 / 72**
- reported TRI series missing on Growth plans: **20 / 72**
- Growth plans with at least one retained explicit-only alternate comparison: **20 / 72**
- reported-TRI-ready Growth plans with at least two exact overlapping dates: **52 / 72**

For the 20 BSE-benchmarked Growth plans, `BSE 250 SmallCap TRI` remains the reported series and remains unavailable. The retained `Nifty Smallcap 250 TRI` appears only under `alternate_comparisons`; it is not a default, substitute or issue.

The only performance repair priority left is `collect_bse_250_smallcap_tri`, and it remains **non-actionable** under the current free first-party-source rule because BSE distributes daily index-level history via subscription.

### Remaining performance findings are structural, not missing-data repairs

All current Growth-plan horizon failures are caused by `history_starts_after_target`:

NAV return eligibility:
- 1Y: **10** Growth plans
- 3Y: **24**
- 5Y: **28**

Reported-benchmark overlap eligibility among plans whose reported TRI series is retained:
- 1Y: **10**
- 3Y: **20**
- 5Y: **22**

There are no current `no_observation_within_7d_before_target` Growth-plan failures. These are young-fund/history-length limits, not missing NAV or benchmark rows to invent or backfill.

### Next backend task

**Close the last unresolved NAV-history gap: Aditya Birla Sun Life Small Cap Fund · Regular IDCW · AMFI code 105805, 2010-05-31 → 2010-06-08.**

This is the only plan still carrying `nav_large_gap` in the production audit. It is non-Growth and therefore did not enter the Growth performance repair queue, but it should be classified consistently with the already-reviewed ABSL Regular Growth code 105804 interval.

The next batch should:

- query the exact **105805 Regular IDCW** option and exact **2010-05-31 → 2010-06-08** window from authoritative history;
- use an exact option-level first-party/AMFI source path rather than inferring from Growth code 105804;
- if authoritative history still exposes only the two boundary observations, add a `verified_official_history_gap` evidence record for code 105805 and preserve the raw gap without inventing NAVs;
- if an authoritative intermediate NAV exists, retain its exact date/value/source as a normal NAV observation instead;
- rerun the audit and confirm `nav_large_gap` falls from **1 to 0** if the gap is verified upstream;
- do not change Growth-return eligibility or reopen the blocked BSE TRI task.

After that, the historical-performance audit should contain only structural young-fund limitations plus the explicitly non-actionable BSE TRI source gap.

Portfolio recovery remains gated by `docs/PORTFOLIO-RECOVERY-QUEUE.json`; the **700 link-only retention candidates and legacy cumulative ZIP remain untouched**.

## Latest completed batch: hosted/static benchmark-aware performance integration

**GitHub Pages now follows the same evidence-aware benchmark contract as the Python backend. The public performance UI no longer silently substitutes Nifty Smallcap 250 TRI for funds that explicitly report BSE 250 SmallCap TRI when BSE TRI history is unavailable.**

PR **#139** merged as commit `a770e63e1063aaf68a24aaaebcc16075b3b672c4`.

### Hosted/static contract

`dist/static-data.js` now passes the full retained benchmark registry into the browser analytics layer instead of selecting a benchmark before the contract can resolve the fund's reported identity.

`dist/analytics.js` now mirrors the backend response semantics:

- resolves the latest fund-reported benchmark from `fund.metrics.benchmark`;
- maps only explicit total-return identities to canonical TRI series;
- returns `reported_benchmark` with identity/source/date/availability/status;
- returns `comparison_series` with name, role, status, availability and source;
- defaults to the fund's reported canonical TRI series;
- returns `reported_series_missing` and no comparison when the reported TRI history is unavailable;
- labels an explicitly selected different retained series as `alternate_comparison`;
- preserves IDCW/no-total-return behavior.

`dist/app.js` no longer initializes or resets a fund to a global Nifty fallback. `state.benchmark` is now null by default and is populated only when the user explicitly selects an alternate comparison.

### Public UI behavior

For a fund whose reported benchmark series is retained:

- overview and performance charts use the reported TRI series;
- legends and return-table headings read the resolved comparison from the response contract;
- the benchmark note identifies the fund's reported benchmark and retained TRI history.

For a BSE-benchmarked fund while BSE TRI history is unavailable:

- the default comparison remains **BSE 250 SmallCap TRI**;
- no Nifty line, matched-date table values or substitute benchmark statistics are shown;
- the UI displays **Reported benchmark history unavailable** and explains that no substitute index is shown automatically.

Advanced options still allow a user to choose a retained series such as **Nifty Smallcap 250 TRI**, but the UI labels it **alternate comparison** and continues to show the fund's reported BSE benchmark separately.

The hosted benchmark-coverage note was also corrected: it now states that no alternate comparator is automatically substituted when a reported TRI history is unavailable.

### Regression and production verification

Two new static parity tests were added:

1. browser analytics parity for:
   - reported Nifty default;
   - reported BSE with missing BSE history;
   - explicit Nifty alternate comparison for a BSE-reported fund;
   - IDCW/no-total-return behavior;
2. shipped JavaScript syntax plus a direct assertion that the old client-side Nifty fallback expression is gone.

Production workflow **#498 / run 36180681359** completed successfully at **2026-09-25T19:37:34Z**:

- dependency/syntax setup and production checkpoint restore passed;
- all normal source-upgrade steps passed;
- database compaction passed;
- **340 tests passed**, including both new static parity tests;
- generated GitHub Pages site validation passed;
- cumulative-history publication and build-status recording passed;
- Pages artifact upload passed;
- Pages deployment passed.

Status commit: `3dbdb84658e5ccff36b5822ab87b5b2ec8630aa9`.

Pages artifact **10884112452** is **230,661,408 bytes** with digest `sha256:968b05877f907f0fd9d7734a0f45a79d62c58df56692a96a238bd6e6b6aa262b`.

### Remaining audit inconsistency

The generated performance audit at **2026-09-25T19:37:02Z** still contains the legacy informational fields/issues:

- `website_default_mismatch_growth_plans = 20`;
- `website_default_benchmark_mismatch`;
- `website_default_series` / `website_default_overlap`;
- a note describing Nifty as the website's global default comparison.

Those fields describe the **pre-#139 UI model** and are now stale. They do not mean the deployed UI is still substituting Nifty.

### Next backend task

**Update the performance coverage audit so its benchmark-comparison semantics match the now-deployed evidence-aware API/static UI.**

The next batch should:

- remove or deprecate the stale `website_default_benchmark_mismatch` issue and `website_default_mismatch_growth_plans` summary;
- stop describing Nifty Smallcap 250 TRI as the website's global default benchmark;
- replace the old `website_default_*` structures with evidence-aware fields if useful, for example:
  - reported benchmark series availability;
  - optional alternate-comparison availability;
  - explicit distinction between missing reported-series history and an available alternate comparator;
- keep `reported_tri_series_missing` for funds whose reported TRI series is genuinely unavailable;
- preserve exact-overlap and no-forward-fill rules;
- keep the BSE historical-series repair non-actionable under the current subscription-only first-party source constraint;
- add regression coverage proving that BSE funds can have an available Nifty alternate without being classified as using Nifty by default;
- regenerate `docs/PERFORMANCE-COVERAGE-AUDIT.json` / `.md` and confirm the obsolete website-default mismatch counts disappear.

After that audit cleanup, reassess remaining actionable performance gaps rather than re-opening the blocked BSE source task.

Portfolio recovery remains gated by `docs/PORTFOLIO-RECOVERY-QUEUE.json`; the **700 link-only retention candidates and legacy cumulative ZIP remain untouched**.

## Latest completed batch: evidence-aware performance benchmark API

**The backend performance endpoint no longer silently substitutes the global Nifty Smallcap 250 TRI series when a fund explicitly reports a different benchmark.** PR **#137** merged as commit `40047da14133b585c95146d0f90fcf902448356d`.

### API contract

`GET /api/funds/{code}/performance` now resolves the fund family's latest reported benchmark metric through the same explicit-TRI identity rules used by the performance coverage audit.

The response now includes:

- `reported_benchmark` — reported label, canonical TRI series, source/date/unit, availability and identity status;
- `comparison_series` — the series actually used for comparison, its role, availability/status and source metadata;
- the legacy `benchmark` / `benchmark_source` fields remain for compatibility, but they now reflect the resolved comparison rather than a global default.

Default behavior when no `benchmark` query parameter is supplied:

- if the fund's reported canonical TRI series is retained, that series is used with `comparison_series.role = reported_benchmark`;
- if the reported canonical series is known but unavailable, the API returns that reported series name with `reported_benchmark.status = series_missing`, `comparison_series.status = reported_series_missing`, `comparison_series.available = false`, no benchmark source and **no comparison points**;
- an unverified/unmapped benchmark identity is not silently mapped to Nifty.

Explicit alternate behavior:

- a caller may still request `?benchmark=Nifty Smallcap 250 TRI` or another retained comparison series;
- if that request differs from the fund's reported canonical benchmark, the response labels it `comparison_series.role = alternate_comparison`;
- the `reported_benchmark` object remains unchanged, so an alternate comparison cannot masquerade as the fund's stated benchmark.

This means the **20 Growth plans across the 10 BSE-benchmarked funds** no longer default to Nifty at the backend API layer while the BSE 250 SmallCap TRI series is unavailable.

### Regression and production verification

New regression coverage proves:

1. a Nifty-benchmarked Growth fund defaults to the retained **Nifty Smallcap 250 TRI** and returns a normal reported-benchmark comparison;
2. a BSE-benchmarked Growth fund with no retained BSE TRI history returns **no default substitute comparison**, `reported_series_missing`, and no benchmark source;
3. the same BSE-benchmarked fund can explicitly request Nifty and receives comparison points labelled **alternate_comparison** while its reported BSE identity remains visible.

Production workflow **#496 / run 36178229573** completed successfully on the real restored checkpoint at **2026-09-25T19:14:14Z**:

- syntax/dependency setup and checkpoint restore passed;
- all normal source upgrade steps passed;
- database compaction passed;
- **338 tests passed**, including both new performance benchmark-selection tests;
- site generation and generated-data/download validation passed;
- cumulative-history publication and status recording passed;
- Pages deployment passed.

Status commit: `b24b0747cd6e15c7e0eedf5f461ae9c14706b3e4`.

Pages artifact **10883086851** is **230,659,980 bytes** with digest `sha256:e0612e03ca52272870e0e089edf3512d007e87bdf15110a09ffeffa9e10257d0`.

### Important boundary

**This batch changed the Python/backend API contract only.** The hosted GitHub Pages client currently uses `dist/static-data.js` + `dist/analytics.js` and `dist/app.js`, which still contain the older client-side Nifty fallback behavior. Do not claim the public performance screen is fixed yet.

### Next backend/UI integration task

**Make the hosted/static performance path consume the verified evidence-aware benchmark contract and remove the client-side silent Nifty fallback.**

The next batch should:

- update the static request adapter / analytics response so hosted `/api/funds/{code}/performance` exposes the same `reported_benchmark` and `comparison_series` semantics as the Python API;
- stop `dist/app.js` from falling back to Nifty when a fund reports BSE but the BSE TRI series is unavailable;
- for a missing reported BSE series, show the fund's reported benchmark and a clear **history unavailable** state with no default comparison chart/return table;
- keep the Advanced benchmark control, but label a user-selected Nifty series clearly as an **alternate comparison**, never as the reported benchmark;
- make chart legends, return-table headings, benchmark notes and overview copy read from the API/static response contract rather than from `state.benchmark` assumptions;
- preserve IDCW/no-total-return behavior;
- add Python/static parity regression tests for Nifty default, BSE missing-series default, BSE + explicit Nifty alternate, and IDCW;
- verify the deployed light/minimal UI on GitHub Pages after the static contract is aligned.

The historical BSE TRI source remains blocked under the current free first-party-source rule. Do not substitute the BSE price index, derive TRI, or add an unapproved third-party series.

Portfolio recovery remains gated by `docs/PORTFOLIO-RECOVERY-QUEUE.json`; the **700 link-only retention candidates and legacy cumulative ZIP remain untouched**.

## Latest completed batch: historical NAV-gap source classification

**The five >7-calendar-day Growth-plan NAV intervals flagged for ABSL and DSP are now verified as gaps in the available official histories, not recoverable missing values and not tracker ingestion defects. No NAV value was added, estimated, interpolated or forward-filled.** Read `docs/NAV-GAP-AUDIT.md` and `tracker/nav_gap_evidence.json` for the retained source evidence.

### Evidence trail

PR **#129** merged as commit `f49670b1c8bf07bd91dd58e1576d1153f212c195` and queried AMFI's official historical NAV download by exact AMC/date window and exact scheme code. Production run **#488 / 36167369624** showed that every flagged interval returns **only the two already-retained boundary observations**:

- ABSL Small Cap Regular Growth · code **105804**: **2010-05-31 11.5499 → 2010-06-08 11.4193**;
- DSP Small Cap Regular Growth · code **105989**:
  - **2007-08-08 10.5740 → 2007-08-16 10.1690**
  - **2008-08-27 9.1660 → 2008-09-04 9.3220**
  - **2010-03-17 13.2800 → 2010-03-25 13.4580**
  - **2010-04-07 14.1660 → 2010-04-15 14.4550**

The exact AMFI query URLs and response SHA-256 values are retained in `tracker/nav_gap_evidence.json`.

PRs **#130–#133** then traced the current first-party AMC historical-NAV transports without writing data:
- #130 `d807cd0c14a8b0d1876f90de28943679b306455b` — current AMC source/transport discovery;
- #131 `e7cebf5c2b579e38b81c78f04058a62d9caa34ca` — browser/API contract extraction;
- #132 `441df78faf4d3f0b5b6221431cf6aa9545833bb6` — initial first-party row probe;
- #133 `87e2a1da9542730de2d915c37d85cd1597b7117e` — resilient retry after the initial diagnostic path failed.

DSP's current public NAV page maps Small Cap **Regular Growth** to internal option id **157**. PR **#134**, commit `566b9544529f888d94966af06f73321722d9ac9c`, corrected the probe to use that exact first-party id. Production run **#493 / 36174919035** proved:

- each of the four historical DSP intervals returns **exactly 2 rows**, matching AMFI's boundary NAVs;
- a control request for **2026-09-01 → 2026-09-10** returns **8 daily business-day rows**, so the DSP exporter is functioning and capable of returning ordinary daily NAV history where rows exist.

Official NSE archive checks also show normal-market activity/settlements inside the flagged intervals. That rules out a blanket whole-market weekend/holiday explanation, but it does **not** establish the fund-specific operational reason for the missing dates. The tracker therefore records only the evidence that current authoritative histories do not expose intermediate NAV observations.

### Final audit behavior

PR **#135** merged as commit `b1c7c8272800cc1e7a69f5fcb48692e24736bdcc`.

`tracker/performance_coverage.py` now separates:
- **raw gaps** — the literal >7-day intervals retained in the NAV series;
- **verified official-history gaps** — reviewed intervals where authoritative history does not provide intermediate values;
- **unresolved gaps** — gaps that still require source repair/review.

The five Growth-plan intervals are preserved in the JSON/Markdown audit as `verified_official_history_gap`, but no longer create `nav_large_gap` issues or the actionable `review_nav_history_gaps` repair priority.

Production workflow **#494 / 36176007361** completed successfully at **2026-09-25T18:52:28Z**:
- compile/preflight and production checkpoint restore passed;
- all normal source-upgrade steps passed;
- the temporary NAV diagnostic steps were removed from the workflow;
- **336 tests passed**;
- site generation and generated-data/download validation passed;
- cumulative-history publication and status recording passed;
- Pages deployment passed.

Status commit `4310d5b0e2a3ab55f479abb77a5f56471204ef6b` records the final audit. Pages artifact **10881713134** is **230,660,587 bytes** with digest `sha256:675f134be954e9db6e8f261c459fcba95c270750157a3847d892639defa31121`.

Final production audit generated at **2026-09-25T18:51:55Z**:
- ABSL Growth code **105804**: raw gaps **1**, verified official-history gaps **1**, unresolved gaps **0**;
- DSP Growth code **105989**: raw gaps **4**, verified official-history gaps **4**, unresolved gaps **0**;
- verified official-history Growth gaps: **5 intervals across 2 Growth plans**;
- the actionable `review_nav_history_gaps` priority is **gone**.

ABSL Regular IDCW code **105805** still has the same raw 2010 interval and therefore contributes one non-Growth `nav_large_gap` issue count. It is outside the displayed Growth-return repair queue and was intentionally **not** reclassified without an exact option-level first-party row check.

The BSE historical-series repair is now explicitly marked **non-actionable** in the performance audit under the current source constraint: 10 funds / 20 Growth plans explicitly report BSE 250 SmallCap TRI, but BSE's first-party daily index-level history is subscription-distributed. Do not substitute the price index, derive TRI, or use an unapproved third-party series.

### Next backend task

**Make the performance endpoint benchmark selection evidence-aware so it does not silently present Nifty Smallcap 250 TRI as the fund benchmark for BSE-benchmarked funds.**

Current `/api/funds/{code}/performance` defaults its `benchmark` parameter globally to `Nifty Smallcap 250 TRI`, while the audit correctly records **20 Growth plans** whose explicit reported benchmark is BSE 250 SmallCap TRI and whose relevant BSE series is unavailable.

The next batch should:
- resolve each fund's latest explicit reported benchmark identity before choosing a comparison series;
- use the reported canonical TRI series when it is retained;
- when the reported series is known but unavailable (currently BSE), return an explicit unavailable/missing-series status and **no substitute benchmark comparison** rather than silently using Nifty;
- preserve an explicitly user-selected alternative comparison as a separately labelled comparison, not as the fund's reported benchmark;
- add regression coverage for Nifty-benchmarked funds, BSE-benchmarked funds with no retained BSE series, IDCW/no-total-return cases, and explicit alternate-comparison requests;
- update the static site only after the API contract is verified, keeping the light/minimal UI and clearly distinguishing **reported benchmark** from any optional comparison index.

Portfolio recovery remains gated by `docs/PORTFOLIO-RECOVERY-QUEUE.json`; the **700 link-only retention candidates and legacy cumulative ZIP remain untouched**.

## Latest completed batch: explicit Nifty Smallcap 250 TRI identity repair

**The three previously ambiguous Nifty Smallcap 250 benchmark identities are now resolved from first-party AMC evidence without globally treating an unqualified index name as TRI.** Edelweiss, Franklin India and Groww now all retain explicit **Nifty Smallcap 250 TRI** benchmark identity, while their older unqualified observations remain preserved as historical evidence.

Implementation PR **#125** merged as commit `5b35cfc619612d0f035970e9d111c32c43f16479`. It introduced parser version **v129**, limited to **Edelweiss Small Cap Fund, Franklin India Small Cap Fund and Groww Small Cap Fund**, plus a release verification gate. Production workflow **#484**, run **36160649977**, passed all tests and deployment, but its generated audit correctly exposed that Franklin was still being superseded by the older unqualified August observation.

PR **#126** merged as commit `ec1eb64cabc1e94b1405ac27f84ae3fda52a85e5` and strengthened v129 so the push release fails unless all three targets actually resolve to explicit TRI evidence. Workflow **#485**, run **36161100270**, then **failed intentionally before deployment** because Franklin's client-rendered live page returned only the shell to the GitHub runner. That failure was the expected safety behavior: Edelweiss and Groww verified, Franklin did not, and no false completion was published.

PR **#127** merged as commit `1587ec2f79d6723bd2754a57f8de2769afd299aa`. Franklin now uses the project's existing **reviewed official report** path for publicly readable first-party evidence that cannot be reliably machine-extracted by the runner. The current Franklin fund page observed **2026-09-25** identifies **Nifty Smallcap 250** as the scheme benchmark and explicitly states that benchmark returns are calculated using **Total Return Index** values, so the tracker records **Nifty Smallcap 250 TRI** with the exact official page as source and no synthetic file hash.

The final production workflow **#486**, run **36166599704**, completed successfully at **2026-09-25T17:23:22Z**. Its v129 gate logged:

- Edelweiss Small Cap Fund — **Nifty Smallcap 250 TRI**, as of **2026-08-31**, retained official September factsheet;
- Franklin India Small Cap Fund — **Nifty Smallcap 250 TRI**, observed **2026-09-25**, reviewed current official fund page with explicit Total Return Index statement;
- Groww Small Cap Fund — **Nifty Smallcap 250 TRI**, as of **2026-08-31**, current official scheme-performance page.

The production regression gate passed **335 tests**. Site generation and generated-data/download validation passed. Status commit `c3876383e2d717d599e7b77616ee99943d5fc2a4` records the resulting coverage state. Pages artifact **10877698652** is **230,660,338 bytes** with digest `sha256:efa547f30dca6956d35a5a7aa00ede6493daa1df7b8cfc88d7d2cde4a308ae4e`.

### Performance-audit impact

The production audit generated at **2026-09-25T17:22:46Z** now reports:

- plans: **143**
- Growth plans: **72**
- reported benchmark identity: **36 / 36 funds**
- Growth plans with explicit reported TRI identity: **72 / 72** (up from 66 / 72)
- Growth plans with the relevant reported TRI series and at least two exact overlapping dates: **52 / 72** (up from 46 / 72)
- relevant benchmark overlap eligibility: **1Y 42 / 72**, **3Y 32 / 72**, **5Y 30 / 72**

The former `verify_non_tri_benchmark_identity` repair item is gone. Edelweiss and Franklin have no remaining benchmark-identity issue. Groww's TRI identity is fixed, but its 1Y/3Y/5Y return and overlap periods remain unavailable because the scheme history begins only in **2026**, which is an age limitation rather than a data-identity gap.

The **20 Growth plans across 10 BSE-benchmarked funds** still remain `reported_tri_series_missing` / `website_default_benchmark_mismatch` because the historical **BSE 250 SmallCap TRI** series is not retained. Per `docs/BSE-TRI-SOURCE-AUDIT.md`, that collection task is blocked under the free first-party-source rule because BSE states daily index-level data are available via subscription. Do not substitute the BSE price index, derive TRI, or use a third-party series. Retry only after a material first-party distribution change or separate approval for a licensed source.

### Next backend task

**Review the remaining historical NAV gaps for ABSL and DSP Regular Growth before attempting any backfill.** The audit currently flags only short **8-calendar-day** intervals:

- Aditya Birla Sun Life Small Cap Fund · Regular Growth · AMFI code **105804**: **2010-05-31 → 2010-06-08**;
- DSP Small Cap Fund · Regular Growth · AMFI code **105989**:
  - **2007-08-08 → 2007-08-16**
  - **2008-08-27 → 2008-09-04**
  - **2010-03-17 → 2010-03-25**
  - **2010-04-07 → 2010-04-15**

First determine whether each interval represents a true missing NAV observation or a legitimate valuation/market-calendar gap. Use authoritative retained/AMFI evidence and do not interpolate or manufacture NAV values. If an official missing observation exists, retain its exact date/value/source as a normal NAV observation and rerun the performance audit. If the interval is legitimate, update the audit logic/evidence so it does not classify a valid calendar gap as missing data.

Portfolio recovery remains gated by `docs/PORTFOLIO-RECOVERY-QUEUE.json`; do not retry blocked portfolio sources while the source-change watch is unchanged. The **700 link-only retention candidates and legacy cumulative ZIP remain untouched**.

## Latest completed batch: BSE 250 SmallCap TRI source audit — first-party subscription blocker

**The historical BSE 250 SmallCap TRI collection task was traced to the authoritative provider and deliberately stopped without inserting data because no verified free first-party daily TRI history was found.** Read `docs/BSE-TRI-SOURCE-AUDIT.md` for the bounded source audit and exact source links.

BSE Index Services' official March 2026 factsheet establishes the identity boundary: **SML250** is the Price Return ticker and **SML250T** is the Total Return ticker. The same factsheet prints distinct 30 March 2026 levels — **7043.82 Total Returns** versus **5646.83 Price Returns** — so the public price-index route cannot be relabelled as TRI.

The official BSE Indices Methodology independently maps BSE 250 SmallCap to PR **SML250** / TR **SML250T** and states that **daily constituent and index level data are available via subscription**. A bounded first-party search did not identify a free historical `SML250T` CSV/API/download that satisfies the project's retained-date/source requirements.

No benchmark row, observation, archive, collector, endpoint, UI, source-retention rule or paid service was added. The existing **Nifty Smallcap 250 TRI** series remains separate and unchanged. Do not derive TRI from the price index/dividend yield, use a third-party substitute, or purchase/license data without separate owner approval.

The performance audit therefore intentionally remains unchanged for the **10 funds / 20 Growth plans** that explicitly report BSE 250 SmallCap TRI: they stay `reported_tri_series_missing` and `website_default_benchmark_mismatch` until a trustworthy BSE TRI series exists and fund-specific benchmark selection is separately implemented.

### Next backend task

**Verify the three currently non-TRI benchmark identities from first-party AMC evidence: Edelweiss Small Cap Fund, Franklin India Small Cap Fund and Groww Small Cap Fund.** Promote a benchmark identity to **Nifty Smallcap 250 TRI** only when a current AMC factsheet/KIM/SID/scheme page explicitly establishes total-return identity; otherwise preserve the unqualified benchmark name and record the limitation. This is an identity repair only — do not change the performance UI or default benchmark selection in the same batch.

Retry BSE TRI collection only after a material first-party distribution change or separate approval for a licensed source. Portfolio recovery remains gated by `docs/PORTFOLIO-RECOVERY-QUEUE.json`, and the **700 link-only retention candidates plus legacy cumulative ZIP remain untouched**.

## Latest completed batch: historical performance / benchmark coverage audit

**The backend now publishes a read-only per-plan audit of NAV history, displayed-return eligibility and relevant benchmark-series coverage. No historical return was invented, no benchmark value was forward-filled, no source was fetched by the audit, and no UI behavior changed.**

PR **#122** merged as commit `4a205bb26dc9a622e545f1d8e83f498496a170f6`. Validation run **36155574354** passed compileall, all **332 tests**, restored the production checkpoint, verified that the audit is read-only, and checked the production repair ranking.

Production workflow **#482**, run **36155756588**, then completed successfully through all source upgrades, the **332-test** regression gate, site generation/validation, split history publication, performance-audit/status recording, Pages artifact upload and Pages deployment at **2026-09-25T15:42:46Z**.

Final Pages artifact **10873013694** is **230,748,479 bytes** with digest `sha256:3e025e7427e713a960d4b3c73f27d26b37f6d44653026608d07a7f93728076e1`. Status commit `99dec7b6938f295151f81d1d14358a08b1dca186` records the deployed collection/coverage state and generated audit.

### Audit contract and published evidence

New module `tracker/performance_coverage.py` audits all retained plan NAV series against each fund's latest reported benchmark identity. The normal status recorder now publishes:

- `docs/PERFORMANCE-COVERAGE-AUDIT.json` — machine-readable per-plan evidence;
- `docs/PERFORMANCE-COVERAGE-AUDIT.md` — operator-readable summary and repair queue.

The audit mirrors the website's current **7-day** historical anchor tolerance for displayed 1Y / 3Y / 5Y returns but does not calculate or store substitute returns. Benchmark overlap uses **exact common dates only**; there is no forward-fill or interpolation.

A reported benchmark identity is treated as historical TRI coverage only when the retained identity explicitly establishes a total-return index and a matching retained series exists. The audit separately records the website's current global default benchmark, `Nifty Smallcap 250 TRI`, so a plan can be flagged when the UI is able to compare against Nifty even though the fund explicitly reports a different TRI.

Production audit generated at **2026-09-25T15:42:06Z**:

- plans **143**
- Growth plans **72**
- reported benchmark identity **36/36 funds**
- Growth plans with explicit reported TRI identity **66**
- Growth plans with the relevant reported TRI series and at least two exact overlapping dates **46**
- Growth plans whose explicit reported TRI differs from the website's current Nifty default **20**

Displayed NAV-return eligibility among Growth plans:
- **1Y: 62 / 72**
- **3Y: 48 / 72**
- **5Y: 44 / 72**

Relevant reported-benchmark overlap eligibility:
- **1Y: 38 / 72**
- **3Y: 28 / 72**
- **5Y: 26 / 72**

The tracker currently retains only one historical benchmark series:

- `Nifty Smallcap 250 TRI`
- first observation **2005-04-01**
- latest observation **2026-09-24**
- observations **5,329**
- gaps longer than 7 calendar days **0**

### Repair priorities produced by the audit

**Priority 1 — collect `BSE 250 SmallCap TRI` history.**

Ten funds explicitly report BSE 250 SmallCap TRI (or equivalent Total Return Index wording), affecting **20 Growth plans**, but there is no matching BSE TRI series in the database:

- Aditya Birla Sun Life Small Cap Fund
- Bajaj Finserv Small Cap Fund
- Bandhan Small Cap Fund
- DSP Small Cap Fund
- HDFC Small Cap Fund
- Invesco India Small Cap Fund
- Mahindra Manulife Small Cap Fund
- Quantum Small Cap Fund
- SBI Small Cap Fund
- Union Small Cap Fund

Those plans currently have `reported_tri_series_missing` and `website_default_benchmark_mismatch`. Do **not** treat the existing Nifty comparison as the fund's relevant reported benchmark merely because the website endpoint defaults to Nifty.

**Priority 2 — verify non-TRI benchmark identities.**

Three funds / **6 Growth plans** have retained benchmark identity text that does not explicitly establish TRI:

- Edelweiss Small Cap Fund — `Nifty Smallcap 250`
- Franklin India Small Cap Fund — `Nifty Smallcap 250`
- Groww Small Cap Fund — `Nifty Smallcap 250 Index`

Do not silently map these identities to the retained Nifty TRI series without new first-party evidence explicitly establishing total-return benchmark identity.

**Priority 3 — review true NAV-history gaps.**

The audit found >7-day NAV gaps affecting **2 Growth plans** across:
- Aditya Birla Sun Life Small Cap Fund
- DSP Small Cap Fund

These are separate from normal fund age limitations. Newer funds lacking 3Y/5Y history are correctly marked ineligible because the scheme itself does not yet have enough history.

### Next backend task

**Collect an official historical `BSE 250 SmallCap TRI` series and integrate it without changing the current UI yet.**

Requirements:
- use a free, authoritative first-party BSE / index-provider source only;
- retain exact source URL, observation dates and collection evidence;
- store the series under a distinct canonical key such as `BSE 250 SmallCap TRI`; do not overwrite or alias the existing Nifty series;
- validate identity strictly enough that a price index cannot be mistaken for TRI;
- preserve revisions/observations under the existing benchmark evidence model;
- backfill enough history to support the affected funds' available 1Y / 3Y / 5Y periods where the source permits;
- rerun `docs/PERFORMANCE-COVERAGE-AUDIT.json` and confirm the 20 Growth-plan `website_default_benchmark_mismatch` findings remain visible until the application actually selects each fund's reported benchmark series;
- do not switch the performance endpoint/UI to fund-specific benchmark selection in the same batch unless that change is separately validated after the BSE series itself is trustworthy.

After the BSE series is retained and validated, the following batch should make benchmark selection fund-specific so BSE-benchmarked funds no longer default to Nifty comparisons.

Portfolio recovery remains gated by `docs/PORTFOLIO-RECOVERY-QUEUE.json`; do not re-probe its blocked sources unless the material source-change watch promotes one for review. The source-retention audit remains read-only: the **700 link-only candidates and legacy cumulative ZIP remain untouched**.

## Latest completed batch: Axis full recovery + blocker source-change watch

**Axis Small Cap Fund is no longer a portfolio or fee-coverage gap, and the remaining blocked portfolio queue now watches for material first-party evidence changes without retrying sources automatically.**

### Axis complete monthly portfolio

Commit `c3713ea704e346b427b232c7d5f6b20dda1555c4` recovered Axis's exact first-party monthly Small Cap workbook through the public statutory CMS flow. Validation run **36097681418** passed all **315 tests** plus production-state/site assertions.

Current retained complete Axis snapshot:
- reporting date: **2026-08-31**
- positions: **134**
- complete: **true**
- source: `https://www.axismf.com/1/5/464/560/3622/4549/Monthly_Portfolio_Axis_Small_Cap_Fund_31_August_2026_xlsx_4a112f9ef0.xlsx`

The parser strictly reconciles the constituent table and 100% grand total; no holding was inferred from the older factsheet aggregate. The later intramonth fund-page Top-10 snapshot remains retained history but is not preferred over the complete regulatory month-end. Commit `02ee47f1ebb802b165e7732363d0a8e89add3444` fixed fund/API selection accordingly; validation run **36098102438** passed **315 tests** and verified the static Axis export contains all 134 holdings.

### Axis explicit BER and Total TER

Commit `067748b42f3faa7f0dd6ae049cf822aa0ea3fe92` recovered Axis's public generated Total Expense Ratio workbook through the same first-party CMS transport. Validation run **36101232004** passed **323 tests**, production-checkpoint recovery, 36/36 BER+TER assertions and static-site validation.

Current Axis fee evidence as of **2026-09-24**:
- Regular BER **1.34%**
- Regular Total TER **1.68%**
- Direct BER **0.52%**
- Direct Total TER **0.71%**
- source: `https://www.axismf.com/1/5/2125/Total_Expense_Ratio_2026-09-25_06_04_34.xlsx`

The collector separately retains BER, brokerage, transaction cost, statutory levies and Total TER and cross-checks the browser API against the workbook. Axis's older unqualified fund-page expense ratio remains labelled separately; it was not retroactively promoted.

Production workflow **36101432739** completed successfully after the Axis fee recovery. Current coverage is now:
- funds **36**
- AUM **36/36**
- dated Direct fee **36/36**
- reported TER **36/36**
- BER **36/36**
- benchmark identity **36/36**
- portfolios **35/36**
- complete portfolios **29**
- current portfolios **34**
- current + complete portfolios **29**
- partial portfolios **6**
- latest NAV **2026-09-24**

### Material source-change watch for blocked portfolio recovery

After Axis left the recovery queue, the generated queue had **7** remaining items and **0 actionable-now** targets. The remaining cases are verified source/transport or disclosure-precision boundaries, so repeated blind probing would add noise.

PR **#120** merged as commit `2f08bd61c25666e97ddbb14ba6054a3da3bf11ca`. It extends `tracker/portfolio_recovery_queue.py` with a read-only material-change watch for the four `retry_after_source_change` cases.

A blocked fund is promoted to `review_source_change` only when newly retained first-party evidence materially changes, such as:
- a previously blocked exact recovery URL being fetched successfully after the reviewed blocker baseline;
- an exact recovery source-page check moving out of a blocked status;
- Union's watched host transport recovering;
- a new first-party document classified as a portfolio appearing after blocker review.

Routine timestamp refreshes and repeated identical failures do **not** reopen work. The watch itself performs no fetch, retry or portfolio mutation.

Validation run **36102524816** passed all **327 tests** and the restored production checkpoint. It confirmed:
- TER **36/36**
- BER **36/36**
- complete portfolios **29**
- recovery queue items **7**
- actionable now **0**
- material source changes detected **0**

Production workflow **#481**, run **36102660112**, completed successfully through all source upgrades, **327-test** regression gate, site generation/validation, split history publication, queue/status recording, Pages artifact upload and Pages deployment at **2026-09-25T06:25:31Z**.

Final Pages artifact **10850105587** is **230,748,340 bytes** with digest `sha256:1f9acd42747a0a814033925a971cb65c3cdf1ce45233e50ff371d8f4fe62a986`.

Status commit `6def40910f96157dc96ab35b04ad6c0b38451db4` records:
- plans **143**
- NAV observations **281,442**
- benchmark observations **5,329**
- retained portfolio snapshots **124**
- document versions **1,784**
- database bytes **73,347,072**
- latest NAV **2026-09-24**

Current material-change watch state generated at **2026-09-25T06:24:56Z**:
- Union: unchanged host transport blocker;
- Bajaj Finserv: unchanged exact Downloads 403 blocker;
- Edelweiss: no post-review evidence that the statutory portfolio route recovered;
- ICICI Prudential: no post-review evidence that the monthly ZIP/archive transport recovered.

The queue therefore has no justified portfolio source-recovery target right now. Bandhan, Sundaram and UTI remain disclosure-precision cases and must not be completed by estimating censored weights.

No paid service, external communication, UI change, source deletion or retention-policy change was introduced. The **700 link-only source-retention candidates remain untouched**, and the legacy cumulative ZIP has not been retired.

### Next backend task

**Do not probe any portfolio blocker while `source_changes_detected == 0`.** On future runs, inspect `docs/PORTFOLIO-RECOVERY-QUEUE.json` first; if a blocker is promoted to `review_source_change`, review that retained first-party evidence before any live retry.

While the portfolio queue is closed, move the next backend batch to **historical performance / benchmark coverage auditing**. Build a read-only per-plan audit that identifies:
- first and latest NAV date and observation count;
- eligibility for 1Y / 3Y / 5Y displayed returns;
- first/latest overlapping date with the relevant benchmark series;
- missing or unusually large NAV gaps that can affect chart/comparison periods;
- benchmark-series gaps versus merely reported benchmark identity;
- funds where the website can display benchmark identity but lacks enough overlapping TRI observations for the selected performance period.

Do not invent historical returns, forward-fill benchmark values, add paid data, or change the UI in that audit. Use retained NAV/benchmark evidence only, publish the audit in machine-readable and operator-readable form, and use it to choose the next historical-data repair batch.

## Latest completed batch: read-only portfolio recovery queue

**The backend now publishes a deterministic recovery queue for every partial or missing portfolio, ranked by source actionability rather than retained position count. The queue is read-only: generating it performs no source fetch, retry or portfolio mutation.**

PR **#114** merged as commit `24e8a28a22395e31804223d602467d8f47e316a0`. Isolated validation run **36095583451** passed compileall and all **309 tests**, restored the production checkpoint, verified all eight incomplete/missing funds had retained timestamped fetch/source-page evidence, and confirmed the action split and ranking.

The first production attempt, workflow **#476** / run **36095715032**, passed the 309-test gate, site generation/validation and cumulative archive publication, but correctly stopped before deployment when `scripts/record_build.py` could not import the repo-root `tracker` package from script execution context. No bad Pages deployment occurred.

PR **#115** merged the import-path fix as commit `5efcbeb03ac4bb1ed01baea6c3fc00a2f6b43a25`. Focused validation run **36095854354** again passed all **309 tests** and verified the recorder's script-context import. Production workflow **#477**, run **36095921572**, then completed successfully through tests, generated-site validation, cumulative-history publication, recovery-queue recording, GitHub Pages artifact upload and Pages deployment at **2026-09-25T04:50:20Z**.

Final Pages artifact **10847801270** is **230,742,223 bytes** with digest `sha256:7ea3c5d35db32fed41898b41c2bc965bcd285b684b71b41e4b4fa0030c86a482`. Status commit `5bce311a61e5681a6d9c2b695640e76ff67990af` records the deployed collection/coverage state and generated queue.

### Queue contract and published evidence

New module `tracker/portfolio_recovery_queue.py` combines the existing machine-readable portfolio limitation with retained fetch/source-page/document evidence. It assigns an actionability score and action class; **retained position count is never a ranking input**. A changed unclassified partial is intentionally ranked highest for review.

The normal status recorder now publishes:
- `docs/PORTFOLIO-RECOVERY-QUEUE.json` — structured operator data;
- `docs/PORTFOLIO-RECOVERY-QUEUE.md` — human-readable queue.

Production queue generated at **2026-09-25T04:49:12Z** contains **8** incomplete/missing funds:
- **1 actionable now** — search for a fuller first-party disclosure;
- **4 retry only after source/transport change**;
- **3 cannot improve without a more precise AMC disclosure**;
- **1 stale partial** — Bajaj Finserv;
- **1 missing portfolio** — Union.

Current order:

| Rank | Fund | State | Action | Limitation |
| ---: | --- | --- | --- | --- |
| 1 | Axis Small Cap Fund | current partial | `search_fuller_first_party_disclosure` | `undisclosed_constituents` |
| 2 | Union Small Cap Fund | missing | `retry_after_source_change` | `upstream_source_unavailable` |
| 3 | Bajaj Finserv Small Cap Fund | stale partial | `retry_after_source_change` | `named_subset_only` |
| 4 | Edelweiss Small Cap Fund | current partial | `retry_after_source_change` | `named_subset_only` |
| 5 | ICICI Prudential Small Cap Fund | current partial | `retry_after_source_change` | `undisclosed_constituents` |
| 6 | Bandhan Small Cap Fund | current partial | `requires_more_precise_amc_disclosure` | `non_numeric_source_weight` |
| 7 | Sundaram Small Cap Fund | current partial | `requires_more_precise_amc_disclosure` | `non_numeric_source_weight` |
| 8 | UTI Small Cap Fund | current partial | `requires_more_precise_amc_disclosure` | `non_numeric_source_weight` |

Each queue row includes the exact retained source URL, portfolio reporting date, limitation payload, optional recovery/watch URL, latest exact fetch evidence, latest relevant source-page check, latest matching document evidence, latest evidence timestamp and a concise retry condition.

The queue deliberately prevents repeated blind probes:
- **Union**: retry only after its official portfolio transport becomes reachable or an exact attachment appears.
- **Bajaj**: remains visibly stale, but retry only when the Downloads transport works from production or a current exact attachment appears.
- **Edelweiss**: retry only after its statutory portfolio route/static transport changes or an exact attachment appears.
- **ICICI Prudential**: retry only after its monthly ZIP stops redirecting to the unresolved archive host or another working first-party route appears.
- **Bandhan, Sundaram and UTI**: do not estimate censored/non-numeric weights; wait for more precise AMC disclosure.

No paid service, external communication, UI change, source deletion or portfolio mutation was introduced. The source-retention audit remains read-only: the **700 link-only candidates and legacy cumulative ZIP remain untouched**.

### Next backend task

The queue selects **Axis Small Cap Fund** as the sole actionable-now portfolio recovery target.

Start from retained evidence before any new broad probing. The latest retained snapshot is a **10-position current partial dated 2026-09-16** from:

`https://www.axismf.com/mutual-funds/equity-funds/axis-small-cap-fund/sc-dg/direct`

The queue's latest retained source evidence is **2026-09-24T22:12:17Z**. Earlier Axis audit already proved that the official August full factsheet is reachable but not constituent-complete: it publishes **Equity 92.37%**, named holdings down to 0.50%, the explicit aggregate **Other Domestic Equity (Less than 0.50% of the corpus) 15.20%**, and **Debt, Cash & other current assets 7.63%**.

**Next batch:** search Axis's own statutory/monthly portfolio disclosure surfaces for an exact workbook, ZIP, API payload or other first-party constituent-level source that identifies the holdings hidden by that aggregate. Reuse retained source/fetch evidence first, then perform only a bounded live discovery if needed. Do not split the 15.20% aggregate, infer unnamed constituents, weaken source validation, or mark the factsheet snapshot complete.

Axis is also the only fund without explicitly labelled TER/BER. Keep its current unqualified expense-ratio observation distinct during this portfolio investigation; do not promote it to TER or BER without a separately explicit first-party label.

## Latest completed batch: machine-readable portfolio limitation reasons

**Partial and missing portfolio limitations are now first-class backend data without changing any holdings, weights, dates or completeness flags.**

PR **#112** merged as commit `b3ff3e370e5b6fc478fa4fbedd303949b20c8359`. Isolated validation run **36094891651** passed compileall, all **304 tests**, restored the real production database and verified the exact current limitation classifications while preserving production portfolio counts.

Production workflow **#474**, run **36095002670**, then passed the same **304-test** regression gate, generated-site validation, cumulative-history publication, collection-status recording and GitHub Pages deployment. The build and deploy jobs both completed successfully.

### Backend contract

New module `tracker/portfolio_limitations.py` provides stable evidence classifications for retained partial snapshots and missing portfolios. The classifier is deliberately source-anchored: if a future source changes, an old limitation is **not** silently inherited; it falls back to `partial_reason_unclassified` until reviewed.

The API now exposes `portfolio_limitation` at fund level and `limitation` on portfolio snapshots, including prior snapshots returned by `/api/portfolios/{snapshot_id}`. `COVERAGE-AS-OF.json` exposes the same structured limitation both at fund level and inside the retained portfolio object, plus aggregate `portfolio_limitation_reasons` counts.

Current production limitation codes generated at **2026-09-25T04:35:03Z**:

| Code | Funds | Current examples |
| --- | ---: | --- |
| `undisclosed_constituents` | **2** | Axis, ICICI Prudential |
| `named_subset_only` | **2** | Bajaj Finserv, Edelweiss |
| `non_numeric_source_weight` | **3** | Bandhan, Sundaram, UTI |
| `upstream_source_unavailable` | **1** | Union |

The evidence payload also carries `kind`, `basis`, `source_marker`, `detail` and `scope`. Examples include:
- Axis: AMC aggregate **Other Domestic Equity (Less than 0.50% of the corpus)**;
- ICICI Prudential: **Equity less than 1% of corpus**;
- Edelweiss: **Top 10 Holdings / Top 10 stocks: 23.00%**;
- Bandhan: **Less Than 0.01% of NAV** marker;
- Sundaram: exact **less than 0.01%** workbook footnote;
- UTI: censored `*` weight plus short-term deposits without an exact NAV percentage;
- Union: first-party portfolio transport unavailable from the production collection network.

A changed/unrecognized partial source receives `partial_reason_unclassified` rather than a guessed old reason. Complete snapshots receive no limitation.

### Production invariants after this batch

Production coverage remains unchanged:
- funds **36**
- AUM **36/36**
- dated Direct fee **36/36**
- reported TER **35/36**
- BER **35/36**
- benchmark identity **36/36**
- portfolios **35/36**
- complete portfolios **28**
- current portfolios **34**
- current+complete **28**
- partial portfolios **7**
- latest NAV **2026-09-24**

The production status written at **2026-09-25T04:35:23Z** records **143 plans**, **281,442 NAV observations**, **123 retained portfolio snapshots**, **1,782 document versions**, **73,322,496 database bytes**, and no change to the source-retention policy. The release saved checkpoint `database-36095002670-1.zip` with the existing **95 reusable source packs**.

No censored source marker was converted into a numeric estimate. No portfolio was reclassified complete. No source file was deleted. The source-retention audit remains read-only; the **700 link-only candidates remain untouched** and the legacy cumulative ZIP has not been retired.

### Next backend task

**Build a read-only portfolio recovery queue from the new limitation codes and retained source evidence.** The goal is to stop repeatedly probing already-proven blockers while still surfacing genuinely actionable work.

The queue should:
- rank incomplete/missing portfolios by actionability rather than position count alone;
- distinguish **retry only after source/transport change** from **search for a fuller first-party disclosure** and **cannot improve without more precise AMC disclosure**;
- include the exact source URL, reporting date, limitation code, last relevant source-page check/fetch evidence and a concise retry condition;
- keep stale-but-partial Bajaj visible separately from current partials;
- avoid any new paid service, external communication, source deletion or UI work;
- remain read-only and must not automatically retry or mutate portfolio data.

Use this queue to choose the next source-recovery batch. Do not re-probe Union, ICICI, Edelweiss or Bajaj merely because they rank as incomplete unless the queue shows new first-party transport/source evidence.


## Latest completed batch: ICICI Prudential portfolio transport re-check

**ICICI Prudential Small Cap Fund remains a current partial portfolio because its exact first-party monthly portfolio ZIP transport is still broken upstream. No holdings were fabricated or promoted.**

Diagnostic run **36093923776** re-tested the exact August and July 2026 portfolio URLs from the same GitHub Actions network used by production.

Exact first-party entry URLs:

- August: `https://www.icicipruamc.com/downloads/Files/Monthly%20Portfolio%20Disclosures/2026/Aug/Monthly-Portfolio-Disclosure-August-2026.zip`
- July: `https://www.icicipruamc.com/downloads/Files/Monthly%20Portfolio%20Disclosures/2026/July/Monthly-Portfolio-Disclosure-July-2026.zip`

Both still return **HTTP 307** to the exact first-party archive host:

`https://archive.icicipruamc.com/...`

The archive hostname is still unusable:

- the GitHub runner resolver returns **`gaierror(-5, 'No address associated with hostname')`**;
- Google DNS-over-HTTPS returns **no A Answer**;
- Google DNS-over-HTTPS returns **no CNAME Answer**;
- the authoritative response contains only the `icicipruamc.com` SOA;
- direct August and July archive requests both fail before HTTP because the hostname does not resolve.

This exactly reproduces the earlier blocker documented in runs **36024378270** and **36024773905**. The AMC's public metadata and redirect path remain internally consistent; the failure is the unresolved archive host, not a parser bug or missing filename.

Do **not** work around this by pinning an old IP, disabling TLS verification, using third-party cached ZIPs as financial evidence, or converting the factsheet's separately disclosed **"Equity less than 1% of corpus"** aggregate into invented constituents.

The tracker therefore retains **ICICI Prudential Small Cap Fund · 83 named positions · 2026-08-31 · partial · current**, sourced from the official complete factsheet. Production coverage remains unchanged:

- reported TER **35/36**
- BER **35/36**
- dated Direct fee fallback **36/36**
- AUM **36/36**
- benchmark identity **36/36**
- portfolios **35/36**, **28 complete**, **34 current**, **7 partial**
- latest NAV **2026-09-24**

### Next backend task

The remaining portfolio backlog is now mostly verified source/precision boundaries rather than missing parser work. **Make partial-portfolio limitation reasons first-class machine-readable backend data.**

The current API and `COVERAGE-AS-OF.json` expose `complete: false`, but do not explain why a retained portfolio is partial. Add a conservative structured limitation field for the latest retained portfolio without changing holdings or inventing weights. It should distinguish at minimum:

- **source aggregate / undisclosed constituents** — ICICI Prudential, Axis;
- **source publishes only top/named holdings** — Edelweiss, Bajaj where applicable;
- **censored/non-numeric source weight** — Bandhan, Sundaram, UTI;
- **upstream transport/source unavailable** — use for missing-portfolio cases such as Union, not as a substitute for a retained partial snapshot.

Prefer storing/deriving the limitation from exact parser/source evidence rather than a free-form UI label. Expose it through the fund/portfolio API and coverage JSON, add regression tests, and keep existing completeness semantics unchanged. Censored source markers such as `<0.01%`, dollar-sign footnotes, or `*` must never become estimated numeric weights.

The source-retention audit remains **read-only**: no deletion of the 700 link-only candidates or retirement of the legacy cumulative ZIP is authorized by this batch.

No production data, parser rules, UI, paid service, permissions, schedule cadence, source-retention policy or archive files changed in the ICICI transport re-check. The temporary diagnostic workflow was removed before this handoff update.

## Latest completed batch: Edelweiss portfolio source audit

**Edelweiss Small Cap Fund remains a verified current partial portfolio. No holding or weight was fabricated or promoted in this batch.**

The exact production September factsheet was recovered from the tracker's cumulative archive rather than re-downloaded from the AMC because current GitHub Actions requests to Edelweiss's factsheet/statutory routes return **HTTP 403 Forbidden**. Retained evidence:

- source: `https://www.edelweissmf.com/Files/MF/Downloads/FACTSHEETS/FACTSHEETS/Edelweiss_Factsheet_September_2026_15092026193426.pdf`
- SHA-256: `ecda95db8183525b4b429c835d10d883b4db0757dabff2b562002d5a16cec366`
- bytes: **16,733,406**
- portfolio reporting date: **2026-08-31**

The exact Small Cap page publishes only **Top 10 Holdings**, not a complete constituent table. The retained rows are City Union Bank 3.17%, Karur Vysya Bank 2.64%, Multi Commodity Exchange of India 2.64%, PNB Housing Finance 2.34%, Avalon Technologies 2.27%, Gabriel India 2.18%, KEI Industries 2.06%, Ajanta Pharma 1.94%, Fortis Healthcare 1.92% and Radico Khaitan 1.84%. They reconcile to the factsheet's explicit **Top 10 stocks: 23.00%** total.

The same page contains an **Additional Information pertaining to Portfolio of the scheme** section. PDF annotation inspection in successful diagnostic run **36089827060** proved that all five portfolio-related "Click Here" links resolve to the exact first-party route:

`https://www.edelweissmf.com/statutory/portfolio-of-schemes`

The tracker history contains prior successful fetches of that exact page. The newest retained HTML is:

- fetched: **2026-09-24T04:43:04Z**
- SHA-256: `c2978d8fc61804b4afad5e3c65d98131ed2d6f74c31c45980212518deea5ab6a`
- bytes: **795,717**

Runs **36089882783**, **36089930620** and **36090041993** inspected the retained page and database history. The archived page is an Angular application shell; it contains no exact monthly workbook attachment, no child portfolio document already retained by the tracker, and no directly usable Small Cap holding payload. Its client bundle is referenced as `main.0411e4933dfdb2cb.js`, but the current production runner receives **HTTP 403** when requesting that bundle as well. Current direct requests to the statutory page and September PDF likewise return 403.

This establishes a transport/discovery boundary rather than a parser-completeness bug. The existing conservative Top-30 parser is not applicable to the current September factsheet because that PDF genuinely publishes a Top-10 table. Do not expand the 10 named holdings by inference, reuse an older month's Top-30 list as current, guess workbook filenames, or mark the snapshot complete.

Published coverage therefore remains unchanged:
- reported TER **35/36**
- BER **35/36**
- dated Direct fee fallback **36/36**
- AUM **36/36**
- benchmark identity **36/36**
- portfolios **35/36**, **28 complete**, **34 current**, **7 partial**
- latest NAV **2026-09-24**

### Next backend task

Do **not** repeat Edelweiss source probing unless its first-party statutory route or static bundle becomes reachable again, or an exact monthly attachment URL becomes available.

**ICICI Prudential Small Cap Fund is the next preferred portfolio source-recovery target for a bounded transport re-check.** Earlier work already identified exact first-party August/July monthly portfolio ZIP metadata, but the files redirected to `archive.icicipruamc.com`, whose authoritative public DNS did not resolve at the time. First verify whether that exact official transport has materially changed. If the host still has no usable public transport, record the unchanged blocker and do not guess alternate filenames or use third-party copies.

Bandhan, Sundaram and UTI remain disclosure-precision blockers because their source files contain censored or non-numeric tiny positions; Axis remains an aggregate-disclosure blocker; Union and Bajaj remain the transport/source-discovery blockers documented in the previous batch. Axis also remains the only fund without explicitly labelled TER and BER.

No UI, paid-service, permission, archive-retention policy, schedule cadence or production data changed in this audit. Temporary diagnostic workflows were removed before merge.

## Latest completed batch: Union + Bajaj portfolio source re-audit

**No portfolio values were invented or promoted in this batch. The two highest-priority portfolio gaps were re-checked from the same GitHub Actions network used by production, and both remain transport/source-discovery blockers.**

Diagnostic run **36088945502** retried Union's exact official portfolio routes from a GitHub-hosted runner:
- `https://www.unionmf.com/about-us/downloads`
- `https://www.unionmf.com/about-us/downloads/monthly-portfolio`

Both still fail before page/script discovery with **`URLError: [Errno 111] Connection refused`**. This reproduces the prior production-network boundary. A separate public web crawl can currently read Union's Downloads page and confirms that Union advertises Monthly Portfolios there, but that does not provide the production updater with a fetchable first-party attachment. No guessed filename, alternate IP, TLS bypass, third-party copy or inferred holding was used. **Union Small Cap Fund therefore remains the sole fund with no retained portfolio.**

The handoff-directed fallback, **Bajaj Finserv Small Cap Fund**, was then re-checked. Bajaj's official public Downloads page at `https://www.bajajamc.com/downloads` visibly contains a dedicated **Monthly Portfolio** section with year/month selectors, and Bajaj scheme documents state that portfolio disclosure is provided as a downloadable spreadsheet. However, combined diagnostic run **36089063486** received **HTTP 403 Forbidden** when the GitHub runner requested that Downloads page, before its client-side scripts/API could be traced. A bounded public-source search found the existing lagged Small Cap factsheet but did not expose a concrete current August 2026 monthly Small Cap spreadsheet URL. The tracker therefore retains Bajaj's existing **13-position partial dated 2026-07-31**; it was not relabelled as August merely because the factsheet filename says August 2026.

Current published coverage remains unchanged from production #473:
- reported TER **35/36**
- BER **35/36**
- dated Direct fee fallback **36/36**
- AUM **36/36**
- benchmark identity **36/36**
- portfolios **35/36**, **28 complete**, **34 current**, **7 partial**
- latest NAV **2026-09-24**

### Next backend task

Do **not** repeat Union or Bajaj source probing unless their first-party transport materially changes or an exact current attachment URL becomes available. **Edelweiss Small Cap Fund is the next preferred portfolio-recovery target** because it is a current partial and is more likely to yield incremental source recovery than the already-proven Axis, Sundaram, UTI, Union and Bajaj boundaries. Re-read the prior Edelweiss v89-v103 source tracing before any new attempt; promote only exact first-party named holdings and preserve partial status if the source itself is incomplete.

Axis remains the only fund without explicitly labelled TER and BER. Its current official Direct `expense_ratio` must remain unqualified unless a first-party source explicitly labels TER or BER.

No UI, paid-service, permissions, archive-retention policy, schedule cadence or production data was changed in this audit. Temporary diagnostic workflows were removed before merge.

## Latest completed batch: UTI Small Cap explicit BER recovery

**UTI Small Cap Fund now has explicitly labelled Direct and Regular BER from UTI Mutual Fund's own public YTD TER workbook. The tracker did not use or bypass UTI's authenticated scheduler API.**

PR #103 merged as commit `2e02b0e1fa11df72c4ced20675d8e47b385e4383`. Isolated validation run **36087658254** passed compileall, all **259 tests**, and a live first-party UTI CMS metadata → YTD TER workbook → strict Small Cap parser check. Production workflow **#473**, run **36087719595**, then passed the one-time UTI recovery, the same **259-test** regression gate, generated-site/download validation, cumulative-history publication, status recording and GitHub Pages deployment. The production run completed successfully at **2026-09-25T02:49:01Z**.

### UTI source discovery and exact observations

UTI's current production web application publishes the public CMS metadata endpoint:

`https://www.utimf.com/api/page/get-ytd-ter-disc-page-data`

At recovery time that endpoint exposed the current-financial-year file:

- CMS title: **Daily TER YTD 01042026-12072026**
- source workbook: `https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/2026-07/daily_ter_ytd_01042026_12072026_imp.xlsx?VersionId=IkGh3zzgPAsjAuVAMH.mIny_xn3zhpxb`
- workbook SHA-256: `f1ec288c456330387706a4ad32e59f381c320e200eb145c0d9978212179f9094`
- CMS YTD end date: **2026-07-12**

UTI's production JavaScript also exposes a scheduler route named `getTerData` under `https://prod-api-investor.utimf.com/api/v1/scheduler/getTerData`. Direct unauthenticated requests returned **401 Unauthorized**. The tracker does **not** attempt to obtain or bypass credentials for that route; the public CMS workbook is the auditable source used here.

The workbook's **YTD TER** sheet has these exact published columns:

`PORTFOLIO, NSDL_CODE, PORTFOLIO_NAME, TRANS_DATE, BER_REG, BRK_REG, TRAN_REG, STAT_REG, TOTALTER_REG, WTD_TER_REG, BER_DIR, BRK_DIR, TRAN_DIR, STAT_DIR, TOTALTER_DIR, WTD_TER_DIR`

The parser requires exact UTI Small Cap identity:

- portfolio code: **751**
- NSDL scheme code: **UTIM/O/E/SCF/20/03/0094**
- scheme name: **UTI Small Cap Fund**

Newest exact row in the public YTD file: **2026-07-12**

| Plan | BER | Brokerage | Transaction cost | Statutory levies | Total TER |
| --- | ---: | ---: | ---: | ---: | ---: |
| Regular | **1.59%** | 0.00% | 0.00% | 0.20% | **1.79%** |
| Direct | **0.56%** | 0.00% | 0.00% | 0.10% | **0.66%** |

The workbook also publishes WTD TER columns. Those are validated as part of the source schema but are not promoted into the daily Total TER metric. The tracker stores only the explicitly published BER, brokerage, transaction cost, statutory levies and Total TER fields.

The parser rejects changed headers, wrong portfolio/NSDL/scheme identity, future rows, duplicate latest rows, missing/out-of-range values, Total TER below BER, and component totals that fail reconciliation within rounding tolerance. The CMS selector requires the title dates and workbook filename dates to agree, requires the current financial year to start on 1 April, rejects future end dates and accepts only UTI's registered public CloudFront path.

`scripts/refresh_uti_expenses.py` performs the idempotent push recovery and records `source_upgrade_uti-ber-v1` only after a current-financial-year Regular/Direct BER+TER pair exists on one exact date from one UTI YTD workbook with one non-empty source hash. Normal nightly collection remains active through `amc_expenses.update`.

Production #473 logged:

`UTI Small Cap Fund: official BER/TER as of 2026-07-12 (Direct 0.56%/0.66% BER/TER; YTD file through 2026-07-12)`

with the exact source and hash above.

### Date precedence and retained UTI TER

The new YTD workbook establishes BER, but it is **not** UTI's newest retained Total TER observation. The tracker already has UTI's official Fund Watch observation:

- Direct Total TER: **0.86%**
- reporting date: **2026-07-31**
- source: `https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/2026-08/uti_fund_watch_active_august_2026_rv2.pdf?VersionId=B2XKeBTyWsZMGfHUqI3nbdnzhATN16Ax`

Because reporting date remains the primary ordering rule, the website continues to show **Direct TER 0.86% as of 2026-07-31** while separately exposing **Direct BER 0.56% as of 2026-07-12**. No value was derived or forward-filled.

Status commit `7eae627ec707c681b43f71902ac034eeeec2e561` records the published state. Final Pages artifact **10844880313** is **230,729,840 bytes**, digest `sha256:78b2a09036b06ae4273478e89a03b66a9c6595f4b3b2348229bf0a8cb95223fe`.

### Expense and portfolio coverage after UTI

Coverage generated at **2026-09-25T02:48:03Z** is:

- reported TER: **35 / 36**
- base expense ratio / BER: **35 / 36** (up from 34 / 36)
- dated Direct fee fallback: **36 / 36**
- AUM: **36 / 36**
- benchmark identity: **36 / 36**
- portfolios: **35 / 36**, **28 complete**, **34 current**, **7 partial**
- latest included NAV: **2026-09-24**

UTI's current AUM is **₹5,404.066 crore as of 2026-09-23** via AMFI. Its August portfolio remains current but partial at **108 retained positions as of 2026-08-31**.

**Axis Small Cap Fund is now the only fund without both explicitly labelled TER and BER.** Its official fund page still publishes only an unqualified Direct **Expense Ratio 0.71% as of 2026-09-23**. Keep that value classified as `expense_ratio`; do not promote it to TER or BER without an explicitly labelled first-party disclosure.

### Next backend task

The expense-source pass is now complete for every fund except the deliberate Axis classification boundary. **Return to portfolio recovery, with Union Small Cap Fund as the next preferred target because it is the sole fund with no retained portfolio at all.**

Before retrying Union, re-read the prior Union source/transport investigations in this handoff and current source-page evidence. Union has previously been an official-host transport blocker. Retry only if its current first-party disclosure route, robots policy, attachment path or transport has materially changed; do not guess filenames, weaken host checks or invent holdings simply to close the gap. If Union remains unchanged/unreachable after a bounded evidence-based check, move to **Bajaj Finserv Small Cap Fund**, which remains the only stale collected portfolio.

Other current portfolio boundaries remain:
- **Bajaj Finserv Small Cap Fund**: stale collected portfolio.
- **Axis, Edelweiss, ICICI Prudential, Sundaram and UTI**: current partials with existing source/access/data-precision constraints.
- **Sundaram**: one holding is disclosed only as less than 0.01%; do not fabricate an exact weight.
- **UTI**: current source abbreviates/censors small positions; do not infer exact weights.
- completed structured recoveries such as SBI, Tata, TRUSTMF, Invesco and JM should not be rerun without new source evidence.

No UI, paid-service, permission, archive-retention policy or schedule-cadence change was made in this UTI batch.

## Latest completed batch: Groww Small Cap current BER recovery

**Groww Small Cap Fund now has current, explicitly labelled Direct and Regular BER from Groww Mutual Fund's own signed BER notice. Future/conditional revised BER values were deliberately not promoted.**

PR #101 merged as commit `aa0e04e33154f2d1628d0f22d07090b60298fe04`. Isolated validation run **36086300920** passed compileall, all **254 tests**, and a live first-party expense-page → BER notice → strict Smallcap row parse. Production workflow **#471**, run **36086366140**, passed the one-time Groww recovery, the same **254-test** regression gate, generated-site/download validation, cumulative-history publication, status recording and GitHub Pages deployment. Production #471 completed successfully at **2026-09-25T02:29:25Z**.

A small correctness follow-up was then completed in PR #102, merged as commit `3b045693161208b31628d27b677d88bc8616efb4`. Family-level fee-like coverage summaries now prefer **Direct** when Regular and Direct observations share the same reporting date, while reporting date remains the primary ordering rule. Isolated validation run **36086652916** passed **255 tests**. Production workflow **#472**, run **36086706291**, passed the full **255-test** regression gate, site/download validation, cumulative-history publication and Pages deployment, completing successfully at **2026-09-25T02:34:31Z**.

### Groww source discovery and exact observations

Current first-party expense-ratio page:

`https://www.growwmf.in/downloads/expense-ratio`

The current 2026–27 page publishes signed BER notices on Groww's registered asset host. The newest notice containing **Groww Smallcap Fund** at recovery time is:

`https://assets-netstorage.growwmf.in/compliance_docs/Downloads/Expense%20Ratio/Notice%20-%20Change%20in%20TER/2026%20-%202027/26.%20Notice%20-%20Change%20in%20BER.pdf`

Exact PDF SHA-256:

`ab1e3bbff3e527d8d43124578738d36929088b3c5758e433ef760b38a4efffa1`

Notice identity: **26/2026–2027**. It was signed **2026-09-24** and explicitly labels the current values as **Current BER**, with footnote **As on September 23, 2026**.

| Plan | Current BER as of 2026-09-23 | Revised BER shown in notice | Effective date |
| --- | ---: | ---: | --- |
| Direct | **0.42%** | 0.49% | 2026-09-30 |
| Regular | **1.94%** | 1.94% (No change) | 2026-09-30 |

The revised BER column is **not** stored as a current exact observation. The notice says the revised BER may be lower depending on the applicable AUM slab/regulatory requirements on the effective date, and its effective date was still in the future when collected. The tracker therefore retains only the exact **Current BER** observations dated 2026-09-23.

The preceding Notice 24 independently exposed **Direct Current BER 0.45% as of 2026-08-31** with Regular shown as **NA** and a conditional revised Direct BER of 0.51% effective 2026-09-05. The collector treats NA as missing and never infers a Regular value.

The parser/discovery path requires:
- current-financial-year **Notice - Change in BER.pdf** identity;
- exact registered Groww asset host and expense-ratio path;
- exact BER notice heading and Current BER/Revised BER table headings;
- exact scheme text **Groww Smallcap Fund**;
- valid as-of, signed and effective dates with non-future observation/publication dates;
- numeric Current BER within the accepted range;
- one exact Smallcap row in the notice.

`scripts/refresh_groww_expenses.py` performs the idempotent push recovery and records `source_upgrade_groww-ber-v1` only after recent Regular/Direct BER observations exist on one date from one exact Groww notice with one non-empty hash. Normal nightly collection remains active through `amc_expenses.update`.

Production #471 logged:

`Groww Small Cap Fund: official Current BER as of 2026-09-23 (Direct 0.42%, Regular 1.94%); notice 2026-09-24, revised BER effective 2026-09-30 not promoted`

with the exact source and hash above.

### Coverage-summary correction

Before PR #102, the generic `base_expense_ratio` field in `COVERAGE-AS-OF.json` could surface Groww's Regular 1.94% row because Regular and Direct were tied on the same reporting date. The database observations were both correct; only the family-level representative row was nondeterministic.

`tracker/coverage.py` now orders fee-like summary metrics by:
1. newest reporting date;
2. Direct before Regular when the reporting date is equal;
3. observation timestamp after the date/plan tie.

A regression test also confirms that a genuinely newer Regular observation still outranks an older Direct one. Final published Groww BER is therefore **Direct 0.42% as of 2026-09-23**, while the Regular 1.94% observation remains retained in history.

Final Pages artifact from production #472 is **10844591043**, **230,727,776 bytes**, digest `sha256:3786e28ed05b5b41b8dd987ba4ee41ca2660f81ec6a5b9c681dcc2197133a6dc`. Final status commit `e0f880294a8245188198fd247b10f5b3cc3dec70` records the corrected published state.

### Expense and portfolio coverage after Groww

Coverage generated at **2026-09-25T02:33:30Z** is:

- reported TER: **35 / 36**
- base expense ratio / BER: **34 / 36** (up from 33 / 36)
- dated Direct fee fallback: **36 / 36**
- AUM: **36 / 36**
- benchmark identity: **36 / 36**
- portfolios: **35 / 36**, **28 complete**, **34 current**, **7 partial**
- latest included NAV: **2026-09-24**

Groww now has **Direct BER 0.42% as of 2026-09-23** and **Regular BER 1.94% as of 2026-09-23**. Its retained explicitly reported Direct Total TER remains **1.12% as of 2026-04-30** from the official April factsheet; the BER notice does not publish a current Total TER, so no TER was derived from BER. Current AUM remains **₹948.2145 crore as of 2026-09-23** via AMFI, and the August portfolio remains complete at **62 positions as of 2026-08-31**.

The sole fund without explicitly reported Total TER remains **Axis Small Cap Fund**. The remaining BER gaps are now only **Axis Small Cap Fund** and **UTI Small Cap Fund**. **Union Small Cap Fund** remains the sole zero-portfolio fund, and **Bajaj Finserv Small Cap Fund** remains the only stale collected portfolio.

### Next backend task

**UTI Small Cap Fund is the next preferred expense-source target.** The tracker currently retains Direct Total TER **0.86% as of 2026-07-31** from UTI's official Fund Watch but still has no explicitly labelled BER. Trace UTI's current first-party statutory TER/expense disclosure route for a dated, explicitly labelled BER. Prefer current structured disclosure/API/workbook evidence when available; preserve exact source URL/document identity/date/hash and do not derive BER from Total TER or components.

**Axis remains a deliberate classification boundary:** its official fund page currently publishes only an unqualified Direct **Expense Ratio 0.71% as of 2026-09-23**. Keep that observation as `expense_ratio`; do not promote it to TER or BER without an explicitly labelled first-party source.

Portfolio recovery remains secondary to the current expense-coverage pass: **Union Small Cap Fund** is the only fund with no retained portfolio; Bajaj Finserv remains stale; existing partial-source precision rules must not be weakened merely to close coverage.

No UI, paid-service, permission, archive-retention policy or schedule-cadence change was made in this Groww batch.

## Latest completed batch: Mirae Asset Small Cap explicit Total TER/BER recovery

**Mirae Asset Small Cap Fund now has current, explicitly labelled BER and Total TER from Mirae Asset Mutual Fund's own daily statutory-disclosure workbook.**

PR #100 merged as commit `9f8431ac94f6e5ecbad323f55632e2bb45e905cf`. Isolated validation run **36084851382** passed compileall, all **249 tests**, and a live first-party statutory service → current TER workbook → strict Small Cap parser check. Production workflow **#470**, run **36084922795**, then passed the one-time Mirae recovery, the same **249-test** regression gate, generated-site/download validation, cumulative-history publication, status recording and GitHub Pages deployment. The production run completed successfully at **2026-09-25T02:08:49Z**.

### Mirae source discovery and exact observations

Current first-party statutory TER page:

`https://www.miraeassetmf.co.in/downloads/statutory-disclosure/total-expense-ratio`

Mirae's production browser loads the disclosure list from the public same-origin service:

`https://www.miraeassetmf.co.in/AjaxService/GetDownloadsData`

using the exact module name **TotalExpenseRatio** plus bounded from/to dates and pagination. No investor login, account credential, token or private secret is used.

For **2026-09-23**, the service returned the exact record:

- title: **Total Expense Ratio -23 Sep 2026**
- workbook: `https://www.miraeassetmf.co.in/DailyUploads/TotalExpenseRatio/IN_MF_EXPENSE_RATIO_SEBI_V3_23092026.xls`
- publish date: **2026-09-23**
- workbook SHA-256: `ad2faa3e9140f121268b2385d2b81d7b5e3d2b0af5b2c87b6c3e13bba9541722`

The legacy XLS has one **Report** sheet and explicit columns for BER, brokerage, transaction cost, statutory levies including GST and **Total TER** for both Regular and Direct plans. The parser requires exact scheme name **Mirae Asset Small Cap Fund**, exact NSDL code **MIRA/O/E/SCF/24/10/0075**, exact two-row header identity and the newest unique non-future row.

Newest exact row: **2026-09-23**

| Plan | BER | Brokerage | Transaction cost | Statutory levies incl. GST | Total TER |
| --- | ---: | ---: | ---: | ---: | ---: |
| Regular | **1.57%** | 0.07% | 0.01% | 0.47% | **2.12%** |
| Direct | **0.32%** | 0.07% | 0.01% | 0.24% | **0.64%** |

The tracker stores the workbook's explicit **Total TER** fields. It does **not** derive Total TER from BER or components. Component arithmetic is only a rejection check. Metadata title date, workbook filename date and published date must all agree. The parser also rejects changed workbook layout, wrong scheme/NSDL identity, future dates, duplicate latest rows, missing/out-of-range values, Total TER below BER, and component totals that fail reconciliation within rounding tolerance.

`scripts/refresh_mirae_expenses.py` performs the idempotent push recovery and records `source_upgrade_mirae-ter-v1` only after recent Regular/Direct BER+TER observations exist on one date from one exact Mirae daily TER workbook with one non-empty hash. Normal nightly collection remains active through `amc_expenses.update`.

Production #470 logged:

`Mirae Asset Small Cap Fund: official BER/TER as of 2026-09-23 (Direct 0.32%/0.64% BER/TER)`

with the exact source and workbook hash above. Status commit `eadc871b7d90f9f2b5584fd174b471c580835769` records the published coverage state.

### Expense and portfolio coverage after Mirae

Coverage generated at **2026-09-25T02:07:40Z** is:

- reported TER: **35 / 36** (up from 34 / 36)
- base expense ratio / BER: **33 / 36**
- dated Direct fee fallback: **36 / 36**
- AUM: **36 / 36**
- benchmark identity: **36 / 36**
- portfolios: **35 / 36**, **28 complete**, **34 current**, **7 partial**
- latest included NAV: **2026-09-24**

Mirae's published Direct fee is now **TER 0.64% with BER 0.32%, both as of 2026-09-23**, replacing the older **0.34% BER as of 2026-07-31** fallback. Its current AUM is **₹5,965.3286 crore as of 2026-09-23** via AMFI. Its August portfolio remains complete at **86 positions as of 2026-08-31**.

The sole fund without explicitly reported Total TER is now **Axis Small Cap Fund**. The remaining BER gaps are **Axis, Groww and UTI**. The sole zero-portfolio fund is **Union Small Cap Fund**; **Bajaj Finserv Small Cap Fund** remains the only stale collected portfolio.

### Next backend task

**Groww Small Cap Fund is the next preferred expense-source target.** The tracker has a dated Direct TER **1.12% as of 2026-04-30** from Groww Mutual Fund's official factsheet but still has no explicit BER. Trace Groww's current first-party statutory TER/expense disclosure route for a current explicitly labelled BER and, if available, a fresher Total TER. Preserve exact source identity/date/hash and do not derive BER or TER from components.

After Groww, investigate **UTI Small Cap Fund** for an explicitly labelled BER. **Axis remains a deliberate classification boundary:** its official fund page currently publishes only an unqualified Direct **Expense Ratio 0.71% as of 2026-09-23**. Keep that observation as `expense_ratio`; do not promote it to TER or BER without an explicitly labelled first-party source.

Portfolio recovery remains secondary to the current expense-coverage pass: **Union Small Cap Fund** is still the only fund with no retained portfolio; Bajaj Finserv remains stale; existing partial-source precision rules must not be weakened merely to close coverage.

No UI, paid-service, permission, archive-retention policy or schedule-cadence change was made in this Mirae expense-recovery batch.

## Latest completed batch: Mahindra Manulife Small Cap current TER/BER recovery

**Mahindra Manulife Small Cap Fund now has current, explicitly labelled BER and Total TER from Mahindra Manulife Mutual Fund's own mandatory-disclosure workbook.**

PR #99 merged as commit `29b755558280871e7237a01a25d6968628b7f897`. Isolated validation run **36080863767** passed compileall, all **245 tests**, and a live downloads-metadata → current TER workbook → strict Small Cap parser check. Production workflow **#469**, run **36080964116**, then passed the one-time Mahindra recovery, the same **245-test** regression gate, generated-site/download validation, cumulative-history publication, status recording and GitHub Pages deployment. The production run completed successfully at **2026-09-25T01:13:37Z**.

### Mahindra source discovery and exact observations

Mahindra's current public Downloads page is:

`https://www.mahindramanulife.com/downloads`

Its production browser loads the public downloads tree from:

`https://investorapi.mahindramanulife.com/api/v1/web/preLogin/downloads`

The response is wrapped using AES-CBC constants published in Mahindra's production browser bundle. The tracker mirrors only that public browser transport; **no investor login, account credential, token or private secret is used**. The decoded AMC metadata is walked through the exact category path:

`MANDATORY DISCLOSURES > Total Expense Ratio of Mutual Fund Schemes > Total Expense Ratio`

The tracker then selects the exact current-financial-year workbook from AMC metadata rather than guessing or hardcoding a rotating filename. For 2026–27 the production source is:

`https://www.mahindramanulife.com/uploads/download/6d61db84-f11d-4987-b7a6-929a71d43967.xlsx`

Mahindra also publishes a **FROM APRIL 01 2026** last-six-months entry; at validation time it resolved to the same **234,648-byte** workbook with the same SHA-256, so the annual **TOTAL EXPENSE RATIO - 2026-27** metadata entry is retained as the canonical source.

Exact workbook SHA-256:

`2945005fb6e4cef4922fad976ee57a0dc53b602f1f97ced855eaa29f4b0b00d3`

The parser requires exact NSDL scheme code **MAHM/O/E/SCF/22/07/0020**, exact scheme name **Mahindra Manulife Small Cap Fund**, the exact two-row Regular/Direct TER header, and the newest unique non-future row.

Newest exact row: **2026-09-24**

| Plan | BER | Brokerage | Transaction cost | Statutory levies incl. GST | Total TER |
| --- | ---: | ---: | ---: | ---: | ---: |
| Regular | **1.59%** | 0.12% | 0.01% | 0.48% | **2.20%** |
| Direct | **0.47%** | 0.12% | 0.01% | 0.32% | **0.92%** |

The tracker stores the workbook's explicit **Total TER** fields. It does **not** calculate Total TER from BER or components. Component arithmetic is only a rejection check. The parser rejects changed sheet/header layout, wrong scheme/NSDL identity, future dates, duplicate latest rows, missing/out-of-range values, Total TER below BER and component totals that fail reconciliation within rounding tolerance.

`scripts/refresh_mahindra_expenses.py` performed the idempotent push recovery and records `source_upgrade_mahindra-ter-v1` only after recent Regular/Direct BER+TER observations exist on one date from one exact Mahindra workbook with one non-empty hash. Normal nightly collection remains active through `amc_expenses.update`.

Production #469 logged:

`Mahindra Manulife Small Cap Fund: official BER/TER as of 2026-09-24 (Direct 0.47%/0.92% BER/TER)`

with the exact source and workbook hash above.

Status commit `8bd8bc0ad5d397a50e9302b8570aa4154695613c` records the published state. Pages artifact **10841938013** is **230,727,478 bytes** with digest `sha256:21f68bebf1b08555d08681a4265aa5d4b95145b778ae48b570bc58ff16e54a3a`.

### Expense coverage after Mahindra

Coverage generated at **2026-09-25T01:12:32Z** is:

- reported TER: **34 / 36** (up from 33 / 36)
- base expense ratio / BER: **33 / 36**
- dated Direct fee fallback: **36 / 36**
- AUM: **36 / 36**
- benchmark identity: **36 / 36**
- portfolios: **35 / 36**, **28 complete**, **34 current**, **7 partial**
- latest NAV date in deployment status: **2026-09-24**

Mahindra's published Direct fee is now **TER 0.92% with BER 0.47%, both as of 2026-09-24**, replacing the older August BER-only fallback. Its current AUM is **₹5,528.25 crore as of 2026-09-23** via AMFI. Its August portfolio remains complete at **82 positions as of 2026-08-31**.

The two remaining funds without reported TER are **Axis Small Cap Fund** and **Mirae Asset Small Cap Fund**. The three remaining BER gaps remain **Axis, Groww and UTI**.

### Next backend task

**Mirae Asset Small Cap Fund is the next preferred TER target.** The tracker currently retains Direct BER **0.34% as of 2026-07-31** from the official August factsheet and a complete August portfolio from:

`https://www.miraeassetmf.co.in/docs/default-source/portfolios/mascf_aug2026.xlsx`

Trace Mirae Asset's current first-party statutory/expense disclosure route for an explicitly labelled Total TER and exact reporting date. Prefer a current AMC disclosure table/workbook/API over the older factsheet BER observation. Store Total TER only if Mirae publishes it directly; do not derive it from BER, GST, brokerage or transaction-cost components. Preserve exact source identity/date/hash.

**Axis remains special:** its current official fund page publishes only an unqualified Direct **Expense Ratio 0.71% as of 2026-09-23**, while explicit TER and BER are still absent. Keep that value as `expense_ratio`; do not promote it to TER or BER without an explicitly labelled official source.

No UI, paid-service, permission, archive-retention policy or schedule-cadence change was made in this Mahindra expense-recovery batch.

## Latest completed batch: JM Small Cap current TER/BER recovery

**JM Small Cap Fund now has current, explicitly labelled BER and Total TER from JM Financial Mutual Fund's own Scheme Expense Ratio API.**

PR #98 merged as commit `65983a16fe8c34f0502e6cd2a3a1523158771727`. Isolated validation run **36077070883** passed compileall, all **239 tests**, and a live first-party JM TER API check. Production workflow **#468**, run **36077163847**, then passed the one-time JM recovery, the same **239-test** regression gate, generated-site/download validation, cumulative-history publication, status recording and GitHub Pages deployment. The production run completed successfully at **2026-09-25T00:23:21Z**.

### JM source and exact observations

Current first-party Scheme Expense Ratio page:

`https://www.jmfinancialmf.com/Scheme-Expense-Ratio`

JM's live browser posts public JSON requests to the same first-party API host already used by the tracker for JM monthly portfolio discovery. The current TER table uses:

`https://jmmfapi.jmfinancialmf.com/api/GetTerPageLatest`

with the browser's unfiltered latest-table request:

`{"IICategory":0,"IVFundCode":""}`

The API wraps its response payload using the AES-CBC key/IV published in JM's production browser bundle. The tracker reuses the already-validated read-only JM browser transport; **no investor login, account credential, token or private secret is used**. For TER evidence, the tracker archives the decoded first-party financial JSON that the browser renders rather than treating the encrypted transport envelope as the source artifact.

The collector accepts only the exact identity:

- scheme name: **JM Small Cap Fund**
- scheme code: **SC**
- NSDL scheme code: **JMFI/O/E/SCF/23/11/0016**

Newest exact row: **2026-09-24**

| Plan | BER | Brokerage | Transaction cost | Statutory levies incl. GST | Total TER |
| --- | ---: | ---: | ---: | ---: | ---: |
| Regular | **1.94%** | 0.09% | 0.01% | 0.50% | **2.54%** |
| Direct | **0.59%** | 0.09% | 0.01% | 0.28% | **0.97%** |

The tracker stores JM's explicit **Total TER** fields. It does **not** calculate Total TER from BER or components. Component arithmetic is only a rejection check. The parser rejects a changed response shape, wrong scheme/code/NSDL identity, future dates, duplicate latest rows, missing or out-of-range values, Total TER below BER, and component totals that do not reconcile within rounding tolerance.

Decoded production evidence SHA-256:

`3b4e875ae00865fb9e36ecf7feb1d0e6f194198a8d9e7b7bf59b8692bfeb7dbd`

`scripts/refresh_jm_expenses.py` performed the idempotent push recovery and records `source_upgrade_jm-ter-v1` only after recent Regular/Direct BER+TER observations exist on one date from the exact JM TER endpoint with one non-empty source hash. Normal nightly collection remains active through `amc_expenses.update`; a source failure preserves prior observations.

Production #468 logged:

`Jm Small Cap Fund: official BER/TER as of 2026-09-24 (Direct 0.59%/0.97% BER/TER)`

with source `https://jmmfapi.jmfinancialmf.com/api/GetTerPageLatest` and the exact decoded-evidence hash above.

Status commit `5378c91c43cf152943024dd5a7a9bcb9387501c3` records the published state. Pages artifact **10840805225** is **230,728,268 bytes** with digest `sha256:e9c7ee8d331b2d36408ff7a2f9fd075e4e39da9689fb0bf1e9d71ef37ab9694f`.

### Expense coverage after JM

Coverage generated at **2026-09-25T00:22:01Z** is:

- reported TER: **33 / 36** (up from 32 / 36)
- base expense ratio / BER: **33 / 36**
- dated Direct fee fallback: **36 / 36**
- AUM: **36 / 36**
- benchmark identity: **36 / 36**
- portfolios: **35 / 36**, **28 complete**, **34 current**, **7 partial**
- latest NAV date in deployment status: **2026-09-24**

JM's published Direct fee is now **TER 0.97% with BER 0.59%, both as of 2026-09-24**, replacing the older August BER-only fallback. Its current AUM is **₹955.1431 crore as of 2026-09-23** via AMFI. Its August portfolio remains complete at **85 positions as of 2026-08-31**.

The three remaining funds without reported TER are **Axis, Mahindra Manulife and Mirae Asset**. The three remaining BER gaps remain **Axis, Groww and UTI**.

### Next backend task

**Mahindra Manulife Small Cap Fund is the next preferred TER target.** The tracker already retains Direct BER **0.47% as of 2026-08-31** from the official August digital factsheet:

`https://www.mahindramanulife.com/digital-factsheet/august-2026/Equity-funds/Small-Cap-Fund.html`

Trace Mahindra Manulife's current first-party statutory/expense disclosure route for an explicitly labelled Total TER and exact reporting date. Store Total TER only if the AMC publishes it directly; do not derive it from BER, GST, brokerage or transaction-cost components. Preserve exact source URL/document/API identity and source hash.

After Mahindra Manulife, continue **Mirae Asset Small Cap Fund**. **Axis** remains special: its current official fund page publishes an unqualified Direct **Expense Ratio 0.71% as of 2026-09-23**, while BER is still absent. Keep that value as `expense_ratio`; do not promote it to TER or BER without an explicitly labelled official source.

No UI, paid-service, permission, archive-retention policy or schedule-cadence change was made in this JM expense-recovery batch.

## Latest completed batch: Invesco India Small Cap current TER/BER recovery

**Invesco India Small Cap Fund now has current, explicitly labelled BER and Total TER from Invesco Mutual Fund's own statutory-disclosure API.**

PR #97 merged as commit `6c3fd457f2f15623d8d5066fad0398f950a22c38`. Isolated validation run **36073035236** passed compileall, all **235 tests**, and a live read of the exact current Invesco TER endpoint. Production workflow **#467**, run **36073145561**, then passed the one-time Invesco recovery, the same **235-test** regression gate, generated-site/download validation, cumulative-history publication, status recording and GitHub Pages deployment. The run completed successfully at **2026-09-24T23:32:42Z**.

### Invesco source and exact observations

Current first-party TER page:
`https://www.invescomutualfund.com/statutory-disclosures/ter-mutual-fund-since-2026/ter`

The production browser component uses the public plan list at:
`https://www.invescomutualfund.com/api/Common/GetAllPlans`

and loads TER rows from:
`https://www.invescomutualfund.com/api/TotalExpenseRatioOfMutualFundSchemePolicy/GetTERExpenseData?title=<scheme>&fincialYear=<start-year>&month=<month-number>`

The collector requires the exact scheme name **Invesco India Small Cap Fund** and exact NSDL scheme code **INVM/O/E/SCF/18/07/0030**. It checks the current month first and the immediately preceding month as a bounded fallback, including the April/March financial-year boundary.

Production source for the latest retained observation:
`https://www.invescomutualfund.com/api/TotalExpenseRatioOfMutualFundSchemePolicy/GetTERExpenseData?title=Invesco+India+Small+Cap+Fund&fincialYear=2026&month=9`

The source response retained in production has SHA-256:
`4f2681e5a50ed4b7609537a226d56cab713dbcfc9763012179b70d4493bb0de7`

Newest exact row: **2026-09-23**

| Plan | BER | Brokerage | Transaction cost | Statutory levies incl. GST | Total TER |
| --- | ---: | ---: | ---: | ---: | ---: |
| Regular | **1.44%** | 0.05% | 0.00% | 0.34% | **1.83%** |
| Direct | **0.41%** | 0.05% | 0.00% | 0.17% | **0.63%** |

The tracker stores the API's explicit **Total TER** value. It does **not** calculate TER from BER or components. Component reconciliation is only a rejection check. The parser rejects a changed response shape, wrong scheme or NSDL identity, future dates, duplicate latest rows, missing/out-of-range values, Total TER below BER, and component totals that do not reconcile within rounding tolerance.

`scripts/refresh_invesco_expenses.py` performs the idempotent push recovery and records `source_upgrade_invesco-ter-v1` only after recent Regular/Direct BER+TER observations exist on one date from one exact Invesco TER API source with one non-empty source hash. Normal nightly collection remains active in `amc_expenses.update`.

Production #467 logged:
`Invesco India Small Cap Fund: official BER/TER as of 2026-09-23 (Direct 0.41%/0.63% BER/TER)`

Status commit `e559c7b4c8bd27fdd74b1cb708fea502bca6b77e` records the published coverage state. Pages artifact **10838957887** is **230,728,637 bytes** with digest `sha256:2afd9b34e0e4a53f1ad2f60d645205644b2d58136ce3b78ab480b72680de3176`.

### ICICI Prudential state catch-up

The prior handoff still named ICICI Prudential as the next target, but that recovery completed before the Invesco batch began. PR #96 merged as commit `46eb738ee80f98c6d15517a48e7a618de70a21bc`; production workflow **#466**, run **36070920935**, completed successfully at **2026-09-24T23:06:35Z** and passed **230 tests**.

ICICI's production source is the exact TER workbook discovered through its first-party Financials & Disclosures API:
`https://app.beta.icicipruamc.com/blob/financials-disclosures-files/Files/Total%20Expense%20Ratio/2026-2027/TotalExpenseRatioSep2026.xlsx`

Retained workbook SHA-256:
`d40c69429f907bd1f967a908884ab3feb330ecb7395d402f7a50c64976cd5488`

Latest ICICI Prudential Small Cap observation is **2026-09-23**: Regular **BER 1.50% / Total TER 2.10%** and Direct **BER 0.70% / Total TER 1.18%**. The retained workbook is **238,073 bytes**. The collector discovers the workbook from ICICI's exact current TER category/subcategory metadata, parses the source OOXML rows conservatively, and stores only explicit published BER/Total TER values. Production #466 Pages artifact **10838356588** is **230,726,093 bytes** with digest `sha256:039a593f3bb605eeccfb53eabe0adbb41347cf0ef5045a678b2125aeb663008b`.

### Expense coverage after ICICI + Invesco

Coverage generated at **2026-09-24T23:31:41Z** is:

- reported TER: **32 / 36** (up from 30 / 36 at the last handoff)
- base expense ratio / BER: **33 / 36**
- dated Direct fee fallback: **36 / 36**
- AUM: **36 / 36**
- benchmark identity: **36 / 36**
- portfolios: **35 / 36**, **28 complete**, **34 current**, **7 partial**
- latest NAV date in deployment status: **2026-09-24**

Invesco's published Direct fee is now **TER 0.63% as of 2026-09-23**, replacing the older BER fallback. Its current AUM observation is **₹16,523.94 crore as of 2026-09-23** from AMFI.

The four remaining funds without reported TER are **Axis, JM, Mahindra Manulife and Mirae Asset**. The three remaining BER gaps remain **Axis, Groww and UTI**.

### Next backend task

**JM Small Cap Fund is the next preferred TER target.** The tracker already retains Direct BER **0.59% as of 2026-08-31** from JM Financial Mutual Fund's official September 2026 factsheet, and the project already has a validated read-only JM public-API transport for monthly portfolio disclosures. Trace JM's first-party expense/TER disclosure route for an explicitly labelled Total TER and exact reporting date. Reuse public browser/API mechanics only when the AMC itself exposes them; do not derive Total TER from BER, GST, brokerage or transaction-cost components.

After JM, continue with **Mahindra Manulife** and **Mirae Asset**. **Axis** remains special: its current fund page exposes only an unqualified Direct **Expense Ratio 0.71% as of 2026-09-23**. Keep that as `expense_ratio`; do not promote it to TER or BER without an explicitly labelled official source.

No UI, paid-service, permission, archive-retention policy or schedule-cadence change was made in the ICICI/Invesco expense-recovery batches.

## Latest completed batch: HSBC Small Cap detailed TER/BER recovery
**HSBC Small Cap Fund now has current, explicitly labelled AMC-published BER and Total TER from the detailed TER workbook linked by HSBC's own factsheet.**

PR #95 merged as commit `1077f6887d07b1e81de1dbf9ab1c03e88dd66096`. Isolated validation run **36064819731** passed compileall, all **224 tests**, and a live end-to-end AMC-link -> CAMS browser transport -> decoded workbook -> strict HSBC row parse. Production workflow **#465**, run **36064999961**, then passed the one-time HSBC recovery, the same **224-test** regression gate, generated-site/download validation, cumulative-history publication, status recording and GitHub Pages deployment. The production run completed successfully at **2026-09-24T22:16:34Z**.

### Source chain and retained evidence

HSBC's exact retained August factsheet is:

`https://www.assetmanagement.hsbc.co.in/-/media/Files/attachments/india/mutual-funds/factsheet/the-asset-august-2026.pdf`

Its HSBC Small Cap page publishes **Base Expense Ratio (BER)** only — Regular **1.42%**, Direct **0.56%**, as of **2026-08-31** — and explicitly directs readers to the detailed TER workbook:

`https://digital.camsonline.com/dnlresult/hsbc_ter_report.xlsx`

That public CAMS route is an Angular download application rather than raw XLSX bytes. Its browser performs a public `GET_UPD_MB_RESULT` request to `https://digital.camsonline.com/api/v1/camsonline` and receives the workbook as base64 inside its encrypted transport envelope. `tracker/amc_expenses.py` mirrors only that public browser transport using constants embedded in the public application bundle; **no investor login, account credential, token, or private secret is used**. The decoded XLSX itself is archived and hashed as source evidence; the transient encrypted API response is not treated as the financial source.

Exact decoded workbook evidence:

- source link: `https://digital.camsonline.com/dnlresult/hsbc_ter_report.xlsx`
- bytes: **5,493,673**
- SHA-256: `2fab33e3ece2a39e8dd73832672059a41bb02d605f53471717504665f5b5866c`
- required sheet: **TER**
- exact scheme code: **HEMIDF**
- exact NSDL scheme code: **LTMF/O/E/SCF/14/02/0023**
- exact scheme name: **HSBC Small Cap Fund**

The newest non-future HSBC Small Cap row in the verified workbook is **2026-09-23**:

| Plan | BER | Brokerage | Transaction cost | Statutory levies incl. GST | Total TER |
| --- | ---: | ---: | ---: | ---: | ---: |
| Regular | **1.42%** | 0.03% | 0.00% | 0.33% | **1.78%** |
| Direct | **0.56%** | 0.03% | 0.00% | 0.18% | **0.77%** |

The tracker stores the workbook's explicit **Total TER** field; it does **not** calculate TER from the components. Component reconciliation is only a rejection check. The parser also rejects a changed TER-sheet title/header, wrong scheme/NSDL identity, duplicate latest rows, future dates, invalid ranges, Total TER below BER, and component totals that fail the published Total TER within rounding tolerance.

`scripts/refresh_hsbc_expenses.py` performed the idempotent push recovery and records `source_upgrade_hsbc-detailed-ter-v1` only after recent Regular/Direct BER+TER observations exist with the exact CAMS source and one non-empty workbook hash. Normal nightly collection remains active through `amc_expenses.update`; a source failure preserves prior observations.

Production #465 logged:
`HSBC Small Cap Fund: official detailed BER/TER as of 2026-09-23 (Direct 0.56%/0.77% BER/TER)`
and retained hash `2fab33e3ece2a39e8dd73832672059a41bb02d605f53471717504665f5b5866c`.

Status commit `5b0beffa3cf85bd55c21014d75dab0c0fc6fb001` records the published state. Pages artifact **10836118342** is **230,723,187 bytes** with digest `sha256:3cf0cc15bab4c9240d3dfe3bb1bd6e26f1c0b836e998b54dc38d2c371c8e0251`.

### Coverage after this batch

Coverage generated at **2026-09-24T22:15:26Z** is:

- reported TER: **30 / 36** (up from 29 / 36)
- base expense ratio / BER: **33 / 36**
- dated Direct fee fallback: **36 / 36**
- AUM: **36 / 36**
- benchmark identity: **36 / 36**
- portfolios: **35 / 36**, **28 complete**, **34 current**, **7 partial**

HSBC's published Direct fee is now **TER 0.77% as of 2026-09-23** rather than the older BER fallback. Its current AUM observation is **₹19,210.586 crore as of 2026-09-23** from AMFI, while the complete August portfolio remains **115 positions as of 2026-08-31**.

The six remaining funds without reported TER are **Axis, ICICI Prudential, Invesco India, JM, Mahindra Manulife and Mirae Asset**. The three remaining BER gaps are **Axis, Groww and UTI**.

### Next backend task

**ICICI Prudential Small Cap Fund is the next preferred TER target.** The tracker already retains Direct BER **0.70% as of 2026-08-31** from the official ICICI Prudential complete factsheet:
`https://www.icicipruamc.com/blob/knowledgecentre/factsheet-complete/Complete.pdf`.

Trace the current ICICI Prudential first-party expense/TER disclosure path for an explicitly labelled Total TER. The earlier ICICI *portfolio ZIP* archive-DNS blocker is a separate issue and does not establish a TER blocker; do not conflate those source paths. Store Total TER only if published directly by ICICI Prudential/its explicitly delegated public disclosure route. Do not derive TER from BER, GST or other expense components.

After ICICI Prudential, continue Invesco India, JM, Mahindra Manulife and Mirae Asset. Axis remains special because its current fund page exposes only an unqualified **Expense Ratio** observation; preserve that as `expense_ratio` until an explicitly labelled TER/BER source is found.

No UI, paid-service, permission, archive-retention policy or schedule-cadence change was made in this HSBC batch.

## Latest completed batch: Canara Robeco current TER/BER recovery

**Canara Robeco Small Cap Fund now has current, explicitly labelled AMC-published TER and BER.**

PR #94 merged as commit `886de8b4eeaaf223d41dc3eb2609a5c6f6a0427b`. Production workflow **#463**, run **36062579037**, passed cumulative-history restore, the one-time Canara recovery, all **219 tests**, site generation/validation, cumulative-history publication, status recording and GitHub Pages deployment. The run completed successfully at **2026-09-24T21:38:17Z**.

Canara's current Expense Ratio app is client-rendered. Its production browser bundle calls the first-party read-only endpoint:

`https://www.canararobeco.com/wp-json/ter/v1/records?from_date=<YYYY-MM-DD>&to_date=<YYYY-MM-DD>`

The public JSON identifies the scheme by exact name **Canara Robeco Small Cap Fund** and scheme code **SC**, and publishes separate rows for `Regular Plan` and `Direct Plan`. The tracker now requires exactly one row for each plan on the newest complete non-future date. It stores only the AMC-published `base_ter` as **base expense ratio / BER** and `total_ter` as **TER**. It does **not** recompute TER from brokerage, transaction-cost or statutory-levy components.

Production source:
`https://www.canararobeco.com/wp-json/ter/v1/records?from_date=2026-09-18&to_date=2026-09-24`

Published observations retained for **2026-09-24**:

| Plan | BER | Total TER |
| --- | ---: | ---: |
| Regular | **1.46%** | **1.84%** |
| Direct | **0.46%** | **0.68%** |

The collector rejects wrong scheme names/codes, incomplete plan pairs, duplicate plan rows, future dates, missing/non-numeric values, out-of-range values, and a Total TER below BER. Failure retains the previous observations. `tracker/amc_expenses.py` runs inside the normal nightly metrics job, while `scripts/refresh_canara_expenses.py` performed a one-time push backfill and records `source_upgrade_canara-expense-v1` only after all four recent metrics are present from the exact API.

Isolated validation run **36062414901** passed compileall, all **219 tests**, and a live API check that returned the same 2026-09-24 Regular/Direct values above. Production #463 independently passed the same **219-test** regression gate. Status commit `05f2bd2f9fbe1740275ed3a551ac9bc0830caa48` records the published state.

Pages artifact **10835206674** is **231,215,086 bytes** with digest `sha256:593cbe84c1914ef4f5128821b6919aae00cb69128b3f27836fa1340d1e303ded`.

### Expense coverage after this batch

Coverage generated at **2026-09-24T21:37:12Z** is:

- reported TER: **29 / 36** (up from 28 / 36)
- base expense ratio / BER: **33 / 36**
- dated Direct fee fallback: **36 / 36**
- AUM: **36 / 36**
- benchmark identity: **36 / 36**
- portfolios: **35 / 36**, **28 complete**, **34 current**

The seven remaining funds without a reported TER are **Axis, HSBC, ICICI Prudential, Invesco India, JM, Mahindra Manulife and Mirae Asset**. The three remaining BER gaps are **Axis, Groww and UTI**.

The source audit before implementation is important: diagnostic run **36061083795** showed that AMFI's current September Small Cap TER query returns **572 daily records** covering the 28 tracker families that already matched, while the eight then-missing TER families were absent rather than merely misspelled. Diagnostic run **36061192992** traced AMFI's live TER page bundle and confirmed the browser uses the same `populate-te-rdata-revised` endpoint/filter structure. Do not add fuzzy aliases merely to force absent AMFI rows to match. Canara was recovered from its own exact first-party disclosure API instead.

### Next backend task

**HSBC Small Cap Fund is the next preferred TER target.** The retained official August source already provides Direct BER **0.56% as of 2026-08-31** from `https://www.assetmanagement.hsbc.co.in/-/media/Files/attachments/india/mutual-funds/factsheet/the-asset-august-2026.pdf`, but no TER is currently stored. Inspect the same/current HSBC first-party factsheet or TER disclosure path for an explicitly labelled total TER for Regular and/or Direct plan. Store it only if the AMC publishes the value directly; do not derive Total TER from BER or expense components.

After HSBC, continue through ICICI Prudential, Invesco India, JM, Mahindra Manulife and Mirae Asset using exact AMC/AMFI disclosures. Axis remains special: its live fund page currently exposes only an unqualified **Expense Ratio** observation, so keep that metric distinct unless an explicit TER/BER source is found.

No UI, permission, paid-service, archive-retention or schedule-cadence change was made in this batch.

## Latest completed batch: Bandhan production recovery plus UTI/Axis/Union source audit

Bandhan's recovery is now production-verified. PR #92 merged as commit `a8c630c5ff36c9cd7d790035f3cedd62845523d8`. Production workflow **#462**, run **36042284692**, passed the release gate and GitHub Pages deployment; Pages artifact **10826922439** is **231,213,983 bytes** with digest `sha256:b44b4a3f985820b8e3643d905d60c1a0563a268fd8a7839e138576b175faa138`. Status commit `540070cfedc193e1f4d0ce925eb47cb37e84d114` records the post-deployment collection state.

Bandhan's public first-party finance disclosure path now resolves the exact Small Cap monthly workbooks through the exact scheme disclosure page and its own post ID. The tracker accepts only the Bandhan Google Cloud Storage bucket returned by that API. Retained official sources are:

- August: `https://storage.googleapis.com/nonprod-static-assets-121to59kaawfgfi7bol/2026/09/51a82e61-bandhan-small-cap-fund-31-august-2026.xlsx` — SHA-256 `f793184232eb89f776bfab87cc6729dd203af3fce6d054ca23332d6667828975`
- July: `https://storage.googleapis.com/nonprod-static-assets-121to59kaawfgfi7bol/2026/08/797467c3-bandhan-small-cap-fund_74dec064-fd93-4fe8-950a-e55f077e1a6d_31-july-2026.xlsx` — SHA-256 `4e5980ac2cbbe4231b73dabce6765003bc8766e68981fe82b213c50f5ec590b0`

August retains **260 numeric positions**, July **263**, and both reconcile to **100.00% known numeric weight**. They intentionally remain **partial** because Bandhan publishes several tiny equities with the literal marker `$ = Less Than 0.01% of NAV`; those censored positions are not assigned fabricated numeric weights. August workbook AUM is **₹34,176.024349 crore** and July is **₹31,103.029413 crore**. The isolated validation run **36041997427** passed **214 tests** and verified exact URL/host identity, the censored-weight rule, explicit TREPS/cash leaves, idempotency and both month-end workbooks.

### UTI completeness audit — verified disclosure-precision blocker

Diagnostic run **36056204470** inspected the exact already-retained August UTI ZIP:
`https://d3ce1o48hc5oli.cloudfront.net/s3fs-public/2026-09/fw_uti_mf_scheme_portfolios_31.08.2026_1.zip?VersionId=HDm7fGngbSbB9olwo6wnStXgJC1XWJ16`.

The relevant first-party workbook is `Sebi Exposure as on 31 Aug 2026_final.xlsx`. The UTI Small Cap block confirms why the current snapshot must remain partial:

- the tracker retains **108** equity rows with exact numeric weights;
- `MTAR TECHNOLOGIES LTD` (ISIN `INE864I01014`, quantity **1**, market value **₹0.07 lakh**) has the literal NAV-weight marker **`*`**, not a number;
- the workbook publishes a **SHORT TERM DEPOSITS** amount of **₹127 lakh** without an exact `% TO NAV` value;
- Net Current Assets is separately published at **3.96%**;
- total UTI Small Cap market value is **₹544,764.68 lakh**.

Do not calculate the censored MTAR weight or a deposit weight from market value/AUM. Under the standing evidence rules, UTI remains **108 positions · 2026-08-31 · partial**.

### Axis completeness audit — current official factsheet still aggregates undisclosed holdings

The current Axis August e-factsheet route was recovered and verified in diagnostic runs **36058054003**, **36058173359**, **36058283743**, **36058525795** and **36058742161**.

Exact first-party sources:

- e-factsheet: `https://www.axismf.com/efactsheet/Aug-2026/Innerpage/SMALL-CAP.html`
- full official PDF: `https://www.axismf.com/efactsheet/Aug-2026/Innerpage/Axis%20Fund%20Factsheet%20August%202026%20Final.pdf`

The full PDF is reachable from GitHub Actions, **8,488,816 bytes**, **171 pages**, unencrypted. Its printed page 16 is the exact Axis Small Cap page, anchored by the mandate, **29 November 2013** allotment date, **Nifty Smallcap 250 TRI**, and **₹31,448.32 crore as of 2026-08-31**.

The portfolio table itself is not a complete constituent disclosure. It publishes **Equity 92.37%**, named holdings down to 0.50%, then the explicit aggregate **Other Domestic Equity (Less than 0.50% of the corpus) 15.20%**, followed by **Debt, Cash & other current assets 7.63%** and **Grand Total 100.00%**. Therefore this source cannot establish the unnamed constituents inside the 15.20% aggregate or split the debt/cash aggregate. Do not mark it complete or turn either aggregate into invented securities. Axis's newer **10-position partial dated 2026-09-16** remains the latest retained snapshot.

This supersedes the older statement that Axis's full factsheet route was inaccessible: the current August full PDF is reachable, but its disclosure format itself prevents a complete named portfolio.

### Union source audit — runner transport still blocked

Union's public Downloads page states that monthly portfolio statements are hosted under its Factsheets & Portfolios section, but the GitHub production network still cannot fetch the application. Diagnostic run **36058957582** requested the exact official page `https://www.unionmf.com/about-us/downloads` and received **`URLError: [Errno 111] Connection refused`** before any client-side API/script discovery could run.

A bounded public-source search found indexed Union factsheets and older disclosure material but no concrete current August Small Cap monthly portfolio attachment that can replace the blocked live transport. No guessed URL, third-party copy, stale IP, TLS bypass or inferred holding was used. Union therefore remains the **only 0-position fund** and a transport/source-discovery blocker.

### Production coverage and next backend target

Post-Bandhan production coverage at **2026-09-24T18:36:27Z** is **36 funds; 35 with a portfolio; 28 complete; 34 current; 28 current+complete; 7 partial**. AUM, a dated Direct fee figure and benchmark identity remain **36/36**. The only zero-portfolio fund is **Union Small Cap Fund**. Current partials are Axis, Bandhan, Edelweiss, ICICI Prudential, Sundaram and UTI; Bajaj Finserv is the only stale partial.

The portfolio backlog is now dominated by verified upstream disclosure/transport limitations rather than untried parser relaxations. Do not re-audit UTI or Axis unless their AMC disclosure format changes, and do not retry Union until a working first-party transport or exact attachment appears.

**Next preferred backend task:** return to expense-metric precision/coverage. Current coverage has reported TER for **28/36** funds and base expense ratio for **33/36**. Missing reported TER: Axis, Canara Robeco, HSBC, ICICI Prudential, Invesco India, JM, Mahindra Manulife and Mirae Asset. Missing base expense ratio: Axis, Groww and UTI. Start with official AMFI revised-TER data and exact AMC disclosures; preserve TER and BER as distinct metrics and never relabel an unqualified expense ratio as TER.

No production parser/data mutation was made by the UTI/Axis/Union audit. Temporary diagnostic workflows are removed before merge.

## Latest completed task: JM complete current + prior monthly portfolio recovery

Merged PR #91 as commit `c9f813dcdbe895ef28d051fda1a879ed3b5ddd7e`. Production workflow **#461**, run **36028576004**, passed cumulative-history restore, parser v128 recovery, all **206 tests**, generated-site/download validation, cumulative-history publication and GitHub Pages deployment. The published coverage was built at **2026-09-24T16:37:11Z**, status was recorded at **2026-09-24T16:37:33Z**, and the workflow completed successfully at **2026-09-24T16:38:18Z**.

JM Financial's live Downloads SPA exposes the public first-party API `https://jmmfapi.jmfinancialmf.com/api/`. The browser uses **Portfolio Disclosure** category ID 2 and **Monthly Portfolio of Schemes** subcategory ID 4. Its API responses are AES-CBC encoded with key/IV constants embedded in JM's production browser bundle; these are public application constants, not account credentials. The tracker mirrors the browser-side decode using the system OpenSSL already available on the GitHub runner, with no new Python dependency.

Discovery now reads the public category/listing endpoints, accepts only the exact **JM Small Cap Fund** title, registered JM publication host and XLS/XLSX file type, and selects only the newest two closed calendar month-ends. API listing responses are transient and are **not archived**; only the actual official workbooks and their hashes are retained.

Official source evidence retained in production:

| Reporting date | Positions | Complete | Weight | Quantities | Workbook AUM | SHA-256 |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| 2026-08-31 | 85 | Yes | 100.00% | 83 | ₹929.496506 Cr | `a1060a5d303c8d94e96428afb67aff66e0d00291e184edbbd9341d76149ece24` |
| 2026-07-31 | 83 | Yes | 100.00% | 81 | ₹868.317695 Cr | `17e9e333b30ebbe2b435d574ad0ed0be184945c94325fca089f1f43d14c2dfb5` |

Exact official workbooks:
- August: `https://www.jmfinancialmf.com/CMS/downloads/Portfolio%20Disclosure/Monthly%20Portfolio%20of%20Schemes/Monthly%20Portfolio%20-%20JM%20Small%20Cap%20Fund%20-%20Aug%2031,%202026.xlsx`
- July: `https://www.jmfinancialmf.com/CMS/downloads/Portfolio%20Disclosure/Monthly%20Portfolio%20of%20Schemes/Monthly%20Portfolio%20-%20JM%20Small%20Cap%20Fund%20-%20July%2031,%202026.xlsx`

The generic structured workbook parser already handled all named equities and explicit cash. The only completeness blocker was JM's exact section **`TREPS / Reverse Repo Investments / Corporate Debt Repo`**, whose leaf is **`CCIL`** without an ISIN. Because that heading contains the word "Debt", the generic section-order rule had classified it as Debt before the repo rule. V128 narrowly classifies that exact JM section as Money market and accepts the exact `CCIL` leaf. The retained CCIL weights are **1.1951124861% for August** and **1.0602825455% for July**. No residual/balancing holding is created; all identity, unknown-row, duplicate, market-value, weight and grand-total reconciliation checks remain active.

The website's latest displayed AUM remains the newer **₹955.64 crore as of 2026-09-22** observation; workbook AUM remains separate historical evidence.

Final isolated validation run **36028297259** passed **206 tests** and live API -> browser-compatible AES decode -> workbook ingestion for both months. It verified exact URLs, hashes, AUM, 85/83 position counts, 83/81 quantities, CCIL classification, 100% reconciliation, idempotent second ingestion and non-archival of transient API responses. Production #461 independently logged: **JM current and prior complete portfolios verified: 2026-08-31, 85 positions, 100.000000% weight, complete=1; prior 2026-07-31, 83 positions, 100.000000% weight, complete=1**.

Pages artifact **10820293566** was generated at **231,175,257 bytes** with digest `sha256:2202eb39718fcf682151a23edc0fe7452aad2667ac8c6aac386292b74f40ca23`. JM is now included in normal nightly AMC discovery. No UI, schedule, paid-service, permission, archive-retention policy or Python dependency changes were made.

Evidence: PR https://github.com/Vasuki8/Smallcap-Ledger/pull/91 ; validation https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36028297259 ; production https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36028576004 .

## Previous completed task: ICICI complete-portfolio source audit — upstream archive DNS blocker

No production data was promoted in this batch. The purpose was to determine whether **ICICI Prudential Small Cap Fund**, currently **83 named positions dated 2026-08-31 and partial**, has a first-party complete monthly portfolio route that can be collected without inventing the factsheet's separately disclosed **"Equity less than 1% of corpus"** aggregate.

The current ICICI downloads application was traced end to end. Its public API base is `https://apimf.icicipruamc.com`. The live Downloads page uses:

- categories: `GET /nms/v1/downloads/categories?userType=Investor`
- files: `POST /nms/v1/downloads/files`
- category: **Other Scheme Disclosures**
- exact subcategory: **Monthly Portfolio Disclosures**
- subcategory ID: `26a073d7-08d2-4a95-95fa-f83a4ee51e40`
- category code passed by the live UI: `OTHERS`

The API only returns the current monthly portfolio records when the exact Monthly Portfolio subcategory is requested without the broken financial-year filter. The first current records include:

- **Monthly Portfolio Disclosure August 2026** -> `/downloads/Files/Monthly Portfolio Disclosures/2026/Aug/Monthly-Portfolio-Disclosure-August-2026.zip`
- **Monthly Portfolio Disclosure July 2026** -> `/downloads/Files/Monthly Portfolio Disclosures/2026/July/Monthly-Portfolio-Disclosure-July-2026.zip`

The live `www.icicipruamc.com` August ZIP URL responds **307** and redirects to the first-party archive host:
`https://archive.icicipruamc.com/downloads/Files/Monthly%20Portfolio%20Disclosures/2026/Aug/Monthly-Portfolio-Disclosure-August-2026.zip`.

That archive host is currently not publicly resolvable. The GitHub runner receives a DNS failure, and an independent public DNS-over-HTTPS check on 2026-09-24 returned **no A and no CNAME Answer** for both `archive.icicipruamc.com` and `www.archive.icicipruamc.com`; the authoritative response contains only the `icicipruamc.com` SOA. The historical `archive.icicipruamc.trafficmanager.net` alias also returns NXDOMAIN. Requesting the same archive path on `apimf.icicipruamc.com` returns the API wrapper's **404 Resource not found**. Therefore the tracker cannot currently obtain the ZIP bytes from a working first-party transport.

Do **not** bypass this by assigning an old IP address, disabling TLS verification, using a third-party cached ZIP as source evidence, or turning the factsheet aggregate into fabricated holdings. ICICI remains **83 positions · 2026-08-31 · partial · current** until the AMC restores a resolvable archive host or exposes the portfolio archive through another working first-party endpoint.

Temporary investigation workflow was removed from the working branch. No production code, parser rule, UI, dependency, permission, schedule, archive-retention policy or source-trust rule changed in this batch. The production state therefore remains the verified Invesco deployment below.

Investigation evidence is in temporary branch Actions runs **36024082115** (exact download category), **36024181676** (valid request variants), **36024378270** (307 redirect target), and **36024773905** (public DNS verification). These runs are diagnostic evidence only; `main` remains the production source of truth.

## Previous completed task: Invesco complete current + prior monthly portfolio recovery

Merged PR #90 as commit `fb2548153b360612366006afe6c7a8a0f36f0970`. Production workflow **#460**, run **36019462111**, passed cumulative-history restore, parser v127 recovery, all **199 tests**, generated-site/download validation, cumulative-history publication and GitHub Pages deployment. The published coverage was built at **2026-09-24T15:20:56Z**, status was recorded at **2026-09-24T15:21:18Z**, and the workflow completed successfully at **2026-09-24T15:21:58Z**.
Invesco's current Next.js site exposes the same first-party read-only API used by its Monthly Holdings page: `GET https://www.invescomutualfund.com/api/CompleteMonthlyHoldings?year=<YEAR>&classification=equity`. The API returns exact fund/month workbook URLs. Discovery now selects only the exact **Invesco India Small Cap Fund** row and only the newest two closed calendar months, including January/year rollover handling. Registered-host and workbook-extension checks remain mandatory.

Official source evidence retained in production:

| Reporting date | Positions | Complete | Weight | Quantities | Workbook AUM | SHA-256 |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| 2026-08-31 | 72 | Yes | 100.00% | 70 | ₹15,744.4025 Cr | `f8c3405c0c83ed24502bb4b2f95bff7a0e1022d4dceaf7df3b414029716df83d` |
| 2026-07-31 | 67 | Yes | 100.00% | 65 | ₹14,474.7868 Cr | `7d4924d152355a89a3359176857e5cb7d20d9df1071d3fd3387b5e2e6277fb00` |

Exact official workbooks:
- August: `https://www.invescomutualfund.com/docs/default-source/completes-monthly-holding/small-cap.xlsx?sfvrsn=7d249fc2_0`
- July: `https://www.invescomutualfund.com/docs/default-source/completes-monthly-holding/smallcap1d1dfe07eee8616aaa28ff00007d74af.xlsx?sfvrsn=6f59fc2_0`

No holdings-parser relaxation was required. The existing structured parser already reconciles the August workbook's **95.25% equity section + 5.19% Triparty Repo + other explicit rows to Grand Total 100%**, with no unknown rows. July also reconciles to 100%. The source-reported quantities are retained, so current/prior share-change comparisons can use 70 August and 65 July quantity-bearing positions where the holdings align.

The website's latest displayed AUM remains the newer **₹16,369.99 crore as of 2026-09-22** observation; the August/July workbook AUM values remain separate historical evidence and are not promoted over a newer observation.

`amc_discovery` now includes Invesco in the normal nightly collector. Parser v127's one-time push recovery is marked successful only after **both** the August current and July prior snapshots are complete and reconcile to 100%. Failed retrieval preserves prior data and leaves the upgrade retryable.

Final isolated validation run **36019264349** passed **199 tests** and live API → workbook ingestion. It verified exact scheme identity, two closed months, January rollover, registered-host rejection, nightly integration, the verified Triparty Repo workbook layout, exact hashes/dates/position counts/AUM, and 70/65 source quantities. Production #460 independently logged: **Invesco current and prior complete portfolios verified: 2026-08-31, 72 positions, 100.00% weight, complete=1; prior 2026-07-31, 67 positions, 100.00% weight, complete=1**.

Pages artifact **10815962825** was generated at **231,158,139 bytes** with digest `sha256:b584e3dad71a95cdf36b0bdd49079d33c4b3f9365110077d4bb4393a06802c32`. No UI, dependency, permission, schedule, paid-service or archive-retention changes were made.

Evidence: PR https://github.com/Vasuki8/Smallcap-Ledger/pull/90 ; validation https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36019264349 ; production https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36019462111 .

## Previous completed task: Sundaram richer current portfolio with verified completeness blocker

Merged PR #89 as commit `49a271401b12813465b69a4f9b8a64b294b29ff5`. Production workflow **#459**, run **36017028358**, passed cumulative-history restore, parser v126 recovery, all regression tests, generated-site/download validation, cumulative-history publication and GitHub Pages deployment. The published coverage was built at **2026-09-24T15:01:33Z**, status was recorded at **2026-09-24T15:01:56Z**, and the workflow completed successfully at **2026-09-24T15:03:15Z**.

Sundaram's existing first-party `Fund_Card_data.json` points directly to the official August workbook:

- URL: `https://www.sundarammutual.com/Downloads_Pdf/Portfolio_Archives/2026/Aug/Equity/SMILE.xlsx`
- SHA-256: `663e7170e2810e7f8e89cef9422cb6c4b653b098591eb6530ff61b4d582cb031`
- reporting date: **2026-08-31**
- workbook month-end AUM: **₹4,155.352174 crore**
- retained exact numeric rows: **77 positions**
- known numeric weight sum: **100.000005%**
- completeness: **partial by design**

Before this batch the retained snapshot had **73 positions / 96.560709%** because the generic fallback kept mainly numeric ISIN rows and omitted several explicit non-equity rows. V126 now retains the richer exact-source partial, including **TREPS 5.145861%**, **Margin Money For Derivatives 0.006016%**, and **Cash and Other Net Current Assets -1.761188%**.

The one remaining holding cannot be assigned an exact numeric weight without fabrication. The official workbook gives **Hindustan Dorr Oliver Ltd @**, ISIN `INE551A01022`, quantity 375,961, with the literal percentage cell **`#`**. Sundaram's own footnote defines `#` as **"percentage to NAV of security is less than 0.01%"** and states that the security was delisted on 18 July 2018 and written off in FY 2018-19. The cell is a literal string, not a formula or hidden numeric value. Therefore do **not** convert it to zero, derive an exact ratio, or mark this snapshot complete under the current numeric-weight schema.

The same-source partial-refresh path added in `disclosures.portfolio(..., replace_existing_partial=True)` is deliberately narrow: it can replace holdings only for the exact retained **partial** snapshot with the same source hash. Complete snapshots and different source hashes are untouched.

Final isolated validation run **36016841718** passed **195 tests**. Live ingestion produced **77 positions, complete=0, 100.000005% known numeric weight**, retained the exact source hash/AUM/date above, and confirmed the censored holding was not stored with a fabricated weight. Production #459 independently logged: **Sundaram richer partial portfolio verified: 2026-08-31, 77 positions, 100.000005% known weight, complete=0**, then passed the full site and deployment path.

Pages artifact **10814549515** was generated at **231,253,234 bytes** with digest `sha256:59cd39c0ad8f0c72d575d20c37682638934cd802732b55e22a29e10f76bb02db`. Sundaram's normal nightly discovery remains active through the existing first-party JSON `PORTFOLIO_PATH`. No UI, dependency, permission, schedule, paid-service or archive-retention changes were made.

Evidence: PR https://github.com/Vasuki8/Smallcap-Ledger/pull/89 ; validation https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36016841718 ; production https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36017028358 .

## Previous completed task: TRUSTMF complete monthly portfolio recovery

Merged PR #88 as commit `e9a085165dca5354a533757087222874d348074d`. Production workflow **#458**, run **36013433301**, passed cumulative-history restore, parser v125 recovery, all regression tests, static-site generation/validation, cumulative-history publication and GitHub Pages deployment. The published coverage was built at **2026-09-24T14:32:07Z**, status was recorded at **2026-09-24T14:32:29Z**, and the workflow completed successfully at **2026-09-24T14:34:04Z**.

Before this batch, **TRUSTMF Small Cap Fund** had a current **70-position partial** snapshot dated 2026-08-31. The existing first-party disclosure discovery already exposed the exact monthly workbook through TRUSTMF's read-only API:

- title: **TRUSTMF Monthly Portfolio Report as on 31.08.2026**
- URL: `https://trustmf.com/Content/2026/9/Monthly%20Port_20260909123835.xlsx`
- SHA-256: `834f1709a30b972b5fb5f6322b3dd5687262daaadf32d38ded33df4c6b5ae102`
- parsed portfolio: **73 positions, complete=1, 100.00% weight, as_of=2026-08-31**
- workbook month-end AUM: **₹3,438.9023 crore as of 2026-08-31**

The workbook already reconciled **95.50%** through named securities. The only blocking row was the explicitly published money-market position `TRP_010926 · TREPS 01-Sep-2026` at **4.50%**. Parser v125 recognizes that exact TRUSTMF row only when it appears in the workbook's money-market section. No cash residual, balancing holding or inferred weight is created. Existing scheme-identity, unknown-row, duplicate, market-value, weight and grand-total checks still gate completeness.

The website's latest AUM remains the newer AMFI observation, **₹3,861.35 crore as of 2026-09-22**; the workbook's August AUM is retained separately as dated source evidence.

Final isolated validation run **36013257862** passed **193 tests** and live end-to-end ingestion of the exact official workbook. It produced 73 positions at exactly 100.00%, retained the TREPS row as `Money market`, and retained the workbook AUM/hash/date above. Production run #458 independently verified **TRUSTMF current complete portfolio: 2026-08-31, 73 positions, 100.00% weight, complete=1**, then passed the full site-validation and deployment path.

Pages artifact **10813342822** was generated at **231,252,779 bytes** with digest `sha256:8e9c3f96f5c3ee00f00a7913a2bb1207a04f00120e2db6ad2b2ebea09ed1a299`. The normal nightly `amc_discovery` path already includes TRUSTMF's first-party monthly-disclosure API, so future monthly workbooks remain automatically discoverable after the one-time v125 upgrade. No UI, dependency, permission, schedule, paid-service or archive-retention changes were made.

Evidence: PR https://github.com/Vasuki8/Smallcap-Ledger/pull/88 ; validation https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36013257862 ; production https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/36013433301 .

## Previous completed task: Tata complete monthly portfolio recovery

Merged PR #87 as commit `9e503300fd917c6d98e7b4c991322ab6a682c5a5`. Production workflow **#457**, run **35969060794**, passed the full build, archive, static-site validation and GitHub Pages deployment. The published coverage was built at **2026-09-24T07:20:42Z** and the status audit at **2026-09-24T07:20:59Z**.

Before this batch, **Tata Small Cap Fund** exposed only the official top-10 view in the tracker and was stored as a current partial portfolio. Tata's live portfolio page is client-rendered, but its production frontend calls the public read-only endpoint `https://prod-dist-api.tatamfdev.com/cms-data/api/CMSDATA_portfolio?type=monthly`. Discovery now uses that exact endpoint and accepts only dated workbook URLs on Tata's registered publication domain.

The official August workbook is:

- title: **Portfolio as on 31st August, 2026**
- URL: `https://betacms.tatamutualfund.com/system/files/2026-09/Monthly%20Portfolio%20as%20on%2031st%20August%202026.xlsx`
- SHA-256: `40de15ff002fbfa93a7bbc9e54bbb4f0c547e643cd1b6779dd3bf33011457f37`
- parsed portfolio: **67 positions, complete=1, 100.00% weight, as_of=2026-08-31**
- workbook month-end AUM: **₹13,093.88375 crore as of 2026-08-31**

The workbook's 67 positions are the explicitly published securities plus its explicit `I) REPO` and `CASH / NET CURRENT ASSET` rows. Completeness uses the workbook's own `NET ASSETS` value/weight total. No balancing position is inferred. The current AMFI daily AUM observation remains separate and newer; the website therefore still prefers **₹13,471.89 crore as of 2026-09-22** for its latest-AUM display while retaining the August workbook AUM as historical source evidence.

Parser v124 adds only verified structured-layout support: numeric `31-08-26` report dates, the `MKT VAL` header abbreviation, repeated asset-section headers, Tata's explicit repo/cash leaves and Tata's `NET ASSETS` grand total. Existing unknown-row, duplicate, market-value, weight and scheme-identity checks still gate completeness.

Final isolated validation run **35968914879** passed **191 tests** and live end-to-end ingestion of the exact official workbook. Production run #457 independently recovered Tata as **67 complete positions**, then passed the same regression suite, site generation, `validate_site.py`, cumulative-history publication, status recording and Pages deployment. Pages artifact **10795242635** was generated at 231,260,634 bytes with digest `sha256:b383479fa3c1da9787ed1cf142caafbeb60d68cc0e929aad4edd7e2b8eccb5c7`.

Normal nightly `amc_discovery` already includes Tata, so future monthly workbooks use the API-first route automatically. The previous conservative HTML/file-link discovery remains as a fallback if Tata changes frontend transport.

### Axis investigation completed without a data promotion

Axis was investigated first because it was the previous handoff priority. Its official statutory-disclosure area confirms a portfolio section, but the complete download list is client-rendered. The nested first-party CMS route returned access failures from the GitHub runner, alternate static disclosure routes did not expose workbook bytes, and bounded current-month filename probes returned 404. No third-party source, guessed value or weakened source check was used.

**Axis therefore remains a valid 10-position partial snapshot dated 2026-09-16.** Treat the complete Axis portfolio as a verified source-access/discovery blocker until a genuinely reachable first-party workbook/API path appears. Do not repeatedly probe guessed filenames.

## Previous completed task: SBI monthly portfolio recovery

Merged PR #86 as commit `12307fefd86bce92f34b5c56d6f47302acd5cc03`. Production workflow **#456**, run **35965260621**, successfully built, validated, saved cumulative history and deployed GitHub Pages. Deployment completed **2026-09-24T06:37:13Z**. The published coverage was built at **2026-09-24T06:36:16Z**.

Before this batch, SBI's latest portfolio was a **68-position partial snapshot dated 2026-07-31**. It is now a **73-position complete snapshot dated 2026-08-31**, with the **74-position complete July workbook** retained as its prior-month comparator. Both workbooks reconcile to 100.00% using explicitly disclosed rows, actual values and the stated grand total. No balancing holding was invented.

| Reporting date | Positions | Completeness | Weight sum | SHA-256 |
| --- | ---: | --- | ---: | --- |
| 2026-08-31 | 73 | Complete | 100.00% | `71b589984c9b3db4bbb1baf7365072e0e6f604cf18ccfc215a1dc9c1d3183b48` |
| 2026-07-31 | 74 | Complete | 100.00% | `b080c169962567f08b34dc4117368dcfb0fe4e49c182a2f60da842682e6dd1c1` |

Exact official sources:
- August: https://www.sbimf.com/docs/default-source/scheme-portfolios/sbi-small-cap-fund-monthly-portfolio---august-2026.xlsx?sfvrsn=9c20b052_2
- July: https://www.sbimf.com/docs/default-source/scheme-portfolios/sbi-small-cap-fund-monthly-portfolio---july-2026.xlsx?sfvrsn=e69601db_2

## Implementation and safety boundaries

`tracker/sbi_portfolios.py` uses the public endpoint called by SBI's Portfolios.js: `POST https://www.sbimf.com/ajaxcall/CMS/GetSchemePortfolioSheets`, with `FundId: 0`, `PSYear`, `PSMonth` and `PSFrequency: Monthly`. It checks only the latest two closed calendar months. It accepts the exact SBI Small Cap Fund monthly workbook title and rejects passive Smallcap index funds/ETFs, mismatched periods, non-workbooks and unregistered hosts. The separate recent-portfolios endpoint returned a server error; do not revert to it or guess attachment filenames.

The verified workbooks contain the exact leaf `Margin amount for Derivative positions`. The parser now recognizes that explicit SBI row as cash/margin. Unknown rows, duplicate holdings, and value/weight mismatches still prevent completeness. Negative receivables are retained; supplementary derivative turnover after the grand total is not added to portfolio assets.

`amc_discovery` includes SBI in normal nightly collection. `scripts/refresh_sbi_portfolios.py` runs a one-time push recovery, with setting `source_upgrade_sbi-monthly-portfolio-v1`. It is marked complete only after successful collection and a current complete portfolio. Failure preserves prior data and a retryable state. The source-scoped extraction key `sbi-monthly-portfolio-v1` retains older extraction audit rows without superseding the independent Quant upgrade. Future scheduled collection remains active after the one-time key is set.

The existing daily schedule remains **18:30 UTC / midnight Asia/Kolkata**. No UI, dependency, permission, paid-service or archive-retention changes were made.

## Validation and publication evidence

Eight new regression tests cover exact source identity/period/host filtering, two-month/year rollover, nightly integration, explicit margin and negative receivables, reconciliation failure cases, source-scoped replay, and retry/idempotency behavior. **All 188 tests passed** with locked dependencies in successful validation run **35965069569**; both real official workbooks also passed live end-to-end ingestion and an idempotent second invocation. Production run #456 passed its full regression gate, generated-site/download validation, cumulative-history save and Pages deployment.

The exact deployed Pages artifact was downloaded and independently checked: artifact **10794395282**, ZIP SHA-256 `db97a0e8916c008381d98654231ac9b610c1dc296d51a8b3721b11833cf89ec8`. It contains SBI snapshot **243** (August, 73 positions, complete, 100.00%) and prior snapshot **244** (July, 74 positions, complete), with the official source hashes above. The August payload has **69 reported equity quantities with prior-month/share-change values**. Its CSV export has 73 rows and the comparison columns. All SBI plan/option entries use the current complete family portfolio.

Verification boundary: the successful Pages deployment and the exact published artifact/data/CSV were verified. Direct HTTP/browser inspection of the public Pages URL was unavailable through this environment's web tool; do not claim a visual browser check was performed. Temporary investigation workflow and encoded patch transport were removed before merge. An initial runner push was rejected for workflow-write permissions after its tests had passed; publication was completed using the authorized connector for workflow edits, without changing permissions or credentials.

Evidence: PR https://github.com/Vasuki8/Smallcap-Ledger/pull/86 ; validation https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/35965069569 ; production https://github.com/Vasuki8/Smallcap-Ledger/actions/runs/35965260621 . This final handoff-only commit intentionally skips CI; it does not change deployed code or data.

## Verified coverage after this batch

Coverage at **2026-09-24T16:37:11Z**: **36 funds; 143 NAV series; 281,300 NAV observations; latest NAV 2026-09-23**. AUM, a dated Direct fee figure and reported benchmark identity each have **36/36** coverage.

Portfolios are now **34/36 with holdings; 28 complete; 33 current; 28 current and complete; 6 partial**. The expected month-end is **2026-08-31**. JM improved complete/current-complete coverage **27 -> 28** without changing the 33-fund freshness count because its Top-25 factsheet snapshot was already current.

The remaining collected partials are **Axis, Bajaj Finserv, Edelweiss, ICICI Prudential, Sundaram and UTI**. Bajaj Finserv is the only stale collected portfolio; the other five partials are current under the August freshness target.

The production status audit at **2026-09-24T16:37:33Z** records **113 retained portfolio snapshots, 1,489 archived document records, 1,929,550,764 archive bytes, 99,340,288 database bytes and 2,028,891,052 total retained bytes**. The Pages publication-file budget remains unchanged at 250 MiB.

## Next backend task and remaining blockers

1. **Bandhan Small Cap Fund is the next preferred source-recovery target because it is one of only two funds with no retained portfolio at all.** Re-read the existing WordPress attachment/API discovery and prior failure evidence first. Recover holdings only from an obtainable first-party Bandhan portfolio workbook/PDF/structured attachment; do not promote top-holdings or inferred rows merely to close the zero gap.
2. **Union Small Cap Fund** is the other zero-portfolio gap and remains an official-host transport blocker. Do not weaken source or robots checks.
3. **ICICI Prudential** is a documented first-party transport blocker: its live API exposes exact August/July monthly portfolio ZIPs, but both redirect to `archive.icicipruamc.com`, whose authoritative public DNS had no A/CNAME record on 2026-09-24. Retry only if that official transport changes.
4. **Sundaram** remains a source-precision/data-model blocker because one written-off holding is disclosed only as `<0.01%`. **UTI** remains partial because its current exposure source abbreviates small/short-term positions. Do not infer exact weights.
5. **Axis** remains a first-party access/discovery blocker. **Edelweiss** remains a supported top/named-holdings partial; prior v89-v103 source tracing should be reviewed before any new attempt.
6. **Bajaj Finserv** remains the only stale collected portfolio: **13 partial positions dated 2026-07-31**. Retry only with genuinely new first-party access evidence.
7. Quant, SBI, Tata, TRUSTMF, Invesco and JM are completed structured recovery targets; do not rerun those batches unnecessarily. Re-read `main`, this handoff, current coverage and latest Actions/deployment state before continuing.

Continue backend/data work only unless UI changes are explicitly requested. Preserve exact source URL/hash/report date, units, nulls, conflicts and original archive bytes. Retain the current plus immediately previous calendar-month holdings window and cumulative original evidence. Never invent an exact number or unnamed constituent merely to improve completeness. Avoid broad historical reparses unless a source/parser change genuinely requires them. Update this handoff after the next completed batch.