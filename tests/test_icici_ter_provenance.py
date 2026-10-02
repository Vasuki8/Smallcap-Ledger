"""Workbook rejection diagnostics must preserve evidence without proving TER.

The changed headers and Mid Cap values below reproduce the archived September
30 investigation. They are a small XML fixture, not the archived workbook itself.
"""
import hashlib
import io
import json
import struct
import unittest
import zipfile
from datetime import date
from unittest.mock import patch
from xml.etree import ElementTree as ET

from scripts.audit_midcap_ter_first_party import markdown
from tracker import amc_expenses, midcap_ter_first_party
from tracker.midcap_ter_readiness import reconcile


FAMILY = "ICICI Prudential Mid Cap Fund"
AMC = "ICICI Prudential Mutual Fund"
TODAY = date(2026, 9, 30)
SOURCE = (
    "https://app.beta.icicipruamc.com/blob/financials-disclosures-files/Files/"
    "Total%20Expense%20Ratio/2026-2027/TotalExpenseRatioSep2026.xlsx"
)
UNTRUSTED_FETCH_HASH = "0" * 64
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

LEGACY_HEADER = {
    "A": "Scheme Name",
    "B": "Date (DD/MM/YYYY)",
    "C": "Base Expense Ratio (BER) (%)",
    "D": "Brokerage cost (%)",
    "E": "Transaction Cost incurred for the purpose of execution of trade (%)",
    "F": "Statutory Levies (including GST) (%)",
    "G": "Total TER (%)",
    "H": "Base Expense Ratio (BER) (%)",
    "I": "Brokerage cost (%)",
    "J": "Transaction Cost incurred for the purpose of execution of trade (%)",
    "K": "Statutory Levies (including GST) (%)",
    "L": "Total TER (%)",
}
OBSERVED_HEADER = {
    **LEGACY_HEADER,
    "C": "Base TER (%)¹",
    "D": "Additional expense as per Regulation 52(6A)(b) (%)²",
    "E": "Additional expense as per Regulation 52(6A)(c) (%)³",
    "F": "GST (%)⁴",
    "H": "Base TER(%)¹",
    "I": "Additional expense as per Regulation 52(6A)(b)(%)²",
    "J": "Additional expense as per Regulation 52(6A)(c)(%)³",
    "K": "GST(%)⁴",
    "L": "Total TER(%)",
}
OBSERVED_MIDCAP_ROW = {
    "A": FAMILY,
    "B": "29/09/2026",
    "C": "1.53%", "D": "0.01%", "E": "0.00%", "F": "0.31%", "G": "1.85%",
    "H": "0.89%", "I": "0.01%", "J": "0.00%", "K": "0.31%", "L": "1.11%",
}


def workbook(header, data_row):
    """Build actual inlineStr cells with the source's malformed A1 dimension."""
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    root = ET.Element("worksheet", xmlns=ns)
    ET.SubElement(root, "dimension", ref="A1")
    sheet_data = ET.SubElement(root, "sheetData")
    rows = [
        {"A": "Total Expense Ratio (TER) for Mutual Fund Schemes"},
        {"C": "Regular Plan", "H": "Direct Plan"},
        header,
        data_row,
    ]
    for row_number, values in enumerate(rows, start=1):
        row = ET.SubElement(sheet_data, "row", r=str(row_number))
        for column, value in values.items():
            cell = ET.SubElement(row, "c", r=f"{column}{row_number}", t="inlineStr")
            inline = ET.SubElement(cell, "is")
            ET.SubElement(inline, "t").text = value
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        info = zipfile.ZipInfo("xl/worksheets/sheet1.xml", date_time=(2026, 9, 30, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, ET.tostring(root, encoding="utf-8", xml_declaration=True))
    return output.getvalue()


def provenance(content):
    return {"source": SOURCE, "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}


class IciciTerProvenanceTests(unittest.TestCase):
    def collect_workbook(self, content=None):
        def fetch(url, **kwargs):
            if kwargs.get("archive") is not False:
                raise AssertionError("TER diagnostics must use archive=False")
            if content is None:
                raise ValueError("workbook unavailable")
            if url != SOURCE:
                raise AssertionError("unexpected workbook source")
            return content, UNTRUSTED_FETCH_HASH, XLSX_MIME

        with patch.object(amc_expenses, "_icici_api", side_effect=ValueError("API unavailable")), \
             patch.object(midcap_ter_first_party.providers, "fetch", side_effect=fetch), \
             patch.object(midcap_ter_first_party.db, "rows", return_value=[{"family": FAMILY}]), \
             patch.object(midcap_ter_first_party.db, "connect", side_effect=AssertionError("No production DB writes")), \
             patch.object(midcap_ter_first_party, "COLLECTORS", {FAMILY: midcap_ter_first_party._icici}):
            return midcap_ter_first_party.collect(today=TODAY)

    def assert_rejected(self, report, message):
        self.assertEqual(report["results"], [])
        self.assertEqual(report["recovered"], 0)
        self.assertEqual(report["failed"], 1)
        self.assertEqual(report["errors"][0]["error"], message)
        self.assertEqual(report["production_writes"], 0)
        self.assertFalse(report["public_export_enabled"])
        return report["errors"][0]

    def assert_provenance(self, error, content):
        self.assertEqual(
            {key: error.get(key) for key in ("source", "sha256", "bytes")},
            provenance(content),
        )

    def test_observed_changed_headers_rejected_with_actual_workbook_provenance(self):
        content = workbook(OBSERVED_HEADER, OBSERVED_MIDCAP_ROW)
        report = self.collect_workbook(content)
        error = self.assert_rejected(report, "ICICI TER workbook columns changed")
        self.assert_provenance(error, content)

    def test_legacy_inconsistent_components_rejected_with_workbook_provenance(self):
        # Legacy labels do not make 0.89 + 0.01 + 0 + 0.31 reconcile to 1.11.
        content = workbook(LEGACY_HEADER, OBSERVED_MIDCAP_ROW)
        report = self.collect_workbook(content)
        error = self.assert_rejected(report, "ICICI Mid Cap Direct TER components do not reconcile")
        self.assert_provenance(error, content)

    def test_corrupt_worksheet_crc_rejected_with_acquired_workbook_provenance(self):
        content = bytearray(workbook(LEGACY_HEADER, {**OBSERVED_MIDCAP_ROW, "L": "1.21%"}))
        # Alter only the worksheet's central-directory checksum. ZIP opening
        # succeeds, but reading the actual sheet raises zipfile.BadZipFile.
        crc_offset = content.index(b"PK\x01\x02") + 16
        crc = struct.unpack_from("<I", content, crc_offset)[0]
        struct.pack_into("<I", content, crc_offset, crc ^ 0xFFFFFFFF)
        content = bytes(content)
        report = self.collect_workbook(content)
        error = self.assert_rejected(report, "Bad CRC-32 for file 'xl/worksheets/sheet1.xml'")
        self.assert_provenance(error, content)

    def test_missing_exact_family_rejected_with_workbook_provenance(self):
        content = workbook(LEGACY_HEADER, {**OBSERVED_MIDCAP_ROW, "A": "ICICI Prudential Small Cap Fund"})
        report = self.collect_workbook(content)
        error = self.assert_rejected(report, "ICICI exact Mid Cap scheme name is not unique")
        self.assert_provenance(error, content)

    def test_unavailable_workbook_does_not_fabricate_provenance(self):
        report = self.collect_workbook()
        error = self.assert_rejected(
            report, "ICICI financial disclosure API and reviewed TER workbook paths are unavailable"
        )
        self.assertTrue({"source", "sha256", "bytes"}.isdisjoint(error))

    def test_legacy_reconciling_plan_pair_remains_recovered(self):
        content = workbook(LEGACY_HEADER, {**OBSERVED_MIDCAP_ROW, "L": "1.21%"})
        report = self.collect_workbook(content)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["recovered"], 1)
        self.assertEqual(report["failed"], 0)
        result = report["results"][0]
        self.assertEqual(result["status"], "recovered")
        self.assertEqual(result["as_of"], "2026-09-29")
        self.assertEqual(result["direct_ter"], 1.21)
        self.assertEqual(result["regular_ter"], 1.85)
        self.assertEqual(result["identity"], {"scheme_name": FAMILY})
        self.assertEqual(result["source"], SOURCE)
        self.assertEqual(result["sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(result["discovery_channel"], "reviewed_monthly_workbook_fallback")
        self.assertEqual(report["production_writes"], 0)
        self.assertFalse(report["public_export_enabled"])

    def test_failure_provenance_does_not_increase_readiness_or_enable_export(self):
        content = workbook(OBSERVED_HEADER, OBSERVED_MIDCAP_ROW)
        report = self.collect_workbook(content)
        self.assert_rejected(report, "ICICI TER workbook columns changed")
        # Exercise readiness with the approved error shape independently of
        # whether collect() has implemented the diagnostic fields yet.
        report["errors"][0].update(provenance(content))
        source_audit = {"families": [{
            "family": FAMILY, "amc": AMC, "direct_ter_available": False, "ter": None,
        }]}
        readiness = reconcile(source_audit, report)
        self.assertEqual(readiness["counts"]["direct_ter"], 0)
        self.assertEqual(readiness["counts"]["first_party_amc"], 0)
        self.assertEqual(readiness["counts"]["remaining"], 1)
        self.assertEqual(readiness["remaining_families"], [FAMILY])
        row = readiness["families"][0]
        self.assertFalse(row["direct_ter_available"])
        self.assertIsNone(row["direct_ter"])
        self.assertIsNone(row["regular_ter"])
        self.assertIsNone(row["evidence_channel"])
        self.assertEqual(readiness["production_writes"], 0)
        self.assertFalse(readiness["public_export_enabled"])

    def test_markdown_shows_failed_source_with_hash_and_size_retained_in_json(self):
        content = workbook(OBSERVED_HEADER, OBSERVED_MIDCAP_ROW)
        report = self.collect_workbook(content)
        self.assert_rejected(report, "ICICI TER workbook columns changed")
        report["errors"][0].update(provenance(content))
        rendered = markdown(report)
        failed_line = next(line for line in rendered.splitlines() if line.startswith(f"| {FAMILY} |"))
        cells = [cell.strip() for cell in failed_line.strip("|").split("|")]
        self.assertEqual(cells[6], SOURCE)
        self.assertEqual(cells[2:6], ["failed", "", "", ""])
        self.assertNotIn(provenance(content)["sha256"], rendered)
        restored_error = json.loads(json.dumps(report))["errors"][0]
        self.assert_provenance(restored_error, content)


if __name__ == "__main__":
    unittest.main()
