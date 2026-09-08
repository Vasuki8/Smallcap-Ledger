# Publication association corrections

## SBI Small Cap: Franklin Templeton disclosure link

The collector followed the [Franklin Templeton disclosures section hosted on SBI's website](https://www.sbimf.com/sbimf-franklin-templeton-disclosures). Its generic “Factsheets” link led to a June 2023 portfolio report for six Franklin schemes being wound up. The SBI domain was valid, but the document did not belong to SBI Small Cap Fund.

The corrected collector excludes that section from SBI discovery, rejects its documents when saving or extracting SBI publications, and disables the previously discovered source. Existing unrelated associations are omitted from the fund API and static site. Historical document records, versions, original files and financial observations remain in the cumulative archive.

The [SBI Small Cap July 2026 factsheet](https://www.sbimf.com/docs/default-source/scheme-factsheets/sbi-small-cap-fund-factsheet-july-2026.pdf) remains linked to SBI. Generic report labels now use the report filename when available, so the fund name and month are visible. The SBI AUM record and 68-position equity snapshot already cite this correct report and are unaffected.

Regression checks cover existing archives, discovery, direct downloads, extraction, source disabling, descriptive titles and preservation of correct documents. Generated-site validation also rejects this incorrect association before publishing.
