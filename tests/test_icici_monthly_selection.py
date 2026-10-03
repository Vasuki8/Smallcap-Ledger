"""Validate real ICICI workbooks before choosing a reviewed monthly fallback."""
import hashlib
import io
import socket
import unittest
import zipfile
from datetime import date
from unittest.mock import patch
from xml.etree import ElementTree as ET

from tracker import amc_expenses, midcap_ter_first_party as first_party
from tracker.midcap_ter_readiness import reconcile


FAMILY = "ICICI Prudential Mid Cap Fund"
AMC = "ICICI Prudential Mutual Fund"
TODAY = date(2026, 10, 3)
BASE = (
    "https://app.beta.icicipruamc.com/blob/financials-disclosures-files/Files/"
    "Total%20Expense%20Ratio/"
)
CURRENT = BASE + "2026-2027/TotalExpenseRatioOct2026.xlsx"
PREVIOUS = BASE + "2026-2027/TotalExpenseRatioSep2026.xlsx"
API_ERROR = "API unavailable"
MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
HEADER = {
    "A": "Scheme Name", "B": "Date (DD/MM/YYYY)",
    "C": "Base Expense Ratio (BER) (%)", "D": "Brokerage cost (%)",
    "E": "Transaction Cost incurred for the purpose of execution of trade (%)",
    "F": "Statutory Levies (including GST) (%)", "G": "Total TER (%)",
    "H": "Base Expense Ratio (BER) (%)", "I": "Brokerage cost (%)",
    "J": "Transaction Cost incurred for the purpose of execution of trade (%)",
    "K": "Statutory Levies (including GST) (%)", "L": "Total TER (%)",
}


def scheme_row(day="02/10/2026", **changes):
    return {
        "A": FAMILY, "B": day,
        "C": "1.53%", "D": "0.01%", "E": "0.00%", "F": "0.31%", "G": "1.85%",
        "H": "0.89%", "I": "0.01%", "J": "0.00%", "K": "0.31%", "L": "1.21%",
        **changes,
    }


def workbook(*data_rows, header_changes=None):
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    root = ET.Element("worksheet", xmlns=ns)
    ET.SubElement(root, "dimension", ref="A1")
    data = ET.SubElement(root, "sheetData")
    rows = [
        {"A": "Total Expense Ratio (TER) for Mutual Fund Schemes"},
        {"C": "Regular Plan", "H": "Direct Plan"},
        {**HEADER, **(header_changes or {})},
        *data_rows,
    ]
    for number, values in enumerate(rows, 1):
        row = ET.SubElement(data, "row", r=str(number))
        for column, value in values.items():
            cell = ET.SubElement(row, "c", r=f"{column}{number}", t="inlineStr")
            ET.SubElement(ET.SubElement(cell, "is"), "t").text = value
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as package:
        info = zipfile.ZipInfo("xl/worksheets/sheet1.xml", date_time=(2026, 10, 3, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        package.writestr(info, ET.tostring(root, encoding="utf-8", xml_declaration=True))
    return output.getvalue()


def evidence(source, content, message=None):
    fields = {"source": source, "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}
    if message is not None:
        fields["error"] = message
    return fields


def api_listing():
    categories = [{
        "id": "parent", "internalName": "total-expense-ratio", "isEnabled": True,
        "title": {"text": "Total Expense Ratio", "code": "TOTAL_EXPENSE_RATIO"},
        "subCategory": [{
            "id": "child", "internalName": "Total Expense Ratio", "isEnabled": True,
            "title": {"text": "Total Expense Ratio", "code": "TOTAL_EXPENSE_RATIO"},
            "filter": [
                {"key": {"code": "SHOW"}, "value": [{"code": "TER Details"}]},
                {"key": {"code": "FINANCIAL_YEAR"}, "value": [{"code": "2026-2027"}]},
            ],
        }],
    }]
    files = {"files": [{
        "title": {"text": "TotalExpenseRatioOctober2026"},
        "url": "/financials-disclosures-files/Files/Total Expense Ratio/2026-2027/TotalExpenseRatioOct2026.xlsx",
        "category": "TOTAL_EXPENSE_RATIO", "categoryName": "Total Expense Ratio",
        "isEnabled": True, "FINANCIAL_YEAR": ["2026-2027"], "SHOW": ["TER Details"],
        "level1Id": "parent", "level2Id": "child",
    }]}
    return [categories, files]


class IciciMonthlySelectionTests(unittest.TestCase):
    def collect_sources(self, sources, *, today=TODAY, api_selected=False):
        requests = []

        def fetch(source, **kwargs):
            requests.append(source)
            if kwargs.get("archive") is not False:
                raise AssertionError("No source archival in read-only collection")
            response = sources[source]
            if isinstance(response, Exception):
                raise response
            # The collector must hash the actual response, not this supplied hash.
            return response, "0" * 64, MIME

        api_response = api_listing() if api_selected else ValueError(API_ERROR)
        dns_answer = [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443))]
        with patch.object(amc_expenses, "_icici_api", side_effect=api_response), \
             patch.object(first_party.providers, "fetch", side_effect=fetch), \
             patch.object(first_party.providers.socket, "getaddrinfo", return_value=dns_answer), \
             patch.object(first_party.db, "rows", return_value=[{"family": FAMILY}]), \
             patch.object(first_party.db, "connect", side_effect=AssertionError("Database connections forbidden")), \
             patch.object(first_party, "COLLECTORS", {FAMILY: first_party._icici}):
            report = first_party.collect(today=today)
        self.assertEqual(report["production_writes"], 0)
        self.assertFalse(report["public_export_enabled"])
        return report, requests

    def recovered(self, report, source, content, as_of):
        self.assertEqual(report["failed"], 0)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["recovered"], 1)
        result = report["results"][0]
        self.assertEqual(result["status"], "recovered")
        self.assertEqual(result["source"], source)
        self.assertEqual(result["sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(result["as_of"], as_of)
        self.assertEqual(result["identity"], {"scheme_name": FAMILY})
        return result

    def failed(self, report, message):
        self.assertEqual(report["recovered"], 0)
        self.assertEqual(report["results"], [])
        self.assertEqual(report["failed"], 1)
        error = report["errors"][0]
        self.assertEqual(error["error"], message)
        return error

    def assert_fallback_channel(self, record):
        self.assertEqual(record.get("discovery_channel"), "reviewed_monthly_workbook_fallback")
        self.assertEqual(record.get("discovery_api_error"), API_ERROR)

    def test_valid_current_workbook_stops_before_previous_request(self):
        content = workbook(scheme_row())
        report, requests = self.collect_sources({CURRENT: content})
        result = self.recovered(report, CURRENT, content, "2026-10-02")
        self.assertEqual(requests, [CURRENT])
        self.assertEqual(result.get("rejected_candidates", []), [])
        self.assert_fallback_channel(result)

    def test_invalid_current_header_advances_to_valid_previous_with_rejection_provenance(self):
        current = workbook(scheme_row(), header_changes={"C": "Base TER (%)¹"})
        previous = workbook(scheme_row("29/09/2026"))
        report, requests = self.collect_sources({CURRENT: current, PREVIOUS: previous})
        result = self.recovered(report, PREVIOUS, previous, "2026-09-29")
        self.assertEqual(requests, [CURRENT, PREVIOUS])
        self.assertEqual(result.get("rejected_candidates"), [evidence(CURRENT, current, "ICICI TER workbook columns changed")])
        self.assert_fallback_channel(result)

    def test_strict_validation_rejections_advance_to_previous_without_promoting_current(self):
        identity_error = "ICICI exact Mid Cap scheme name is not unique"
        component_error = "ICICI Mid Cap Direct TER components do not reconcile"
        cases = [
            ("wrong_family", workbook(scheme_row(A="ICICI Prudential Small Cap Fund")), identity_error),
            ("duplicate_latest", workbook(scheme_row(), scheme_row()), "ICICI TER workbook has duplicate exact rows for 2026-10-02"),
            ("future_only", workbook(scheme_row("04/10/2026")), identity_error),
            ("components_outside_tolerance", workbook(scheme_row(L="1.18%")), component_error),
            ("ter_below_ber", workbook(scheme_row(H="1.40%")), "ICICI Mid Cap Direct Total TER is below BER"),
            ("latest_invalid_despite_earlier_valid", workbook(scheme_row("01/10/2026"), scheme_row(L="1.11%")), component_error),
        ]
        previous = workbook(scheme_row("29/09/2026"))
        for label, current, message in cases:
            with self.subTest(reason=label):
                report, _ = self.collect_sources({CURRENT: current, PREVIOUS: previous})
                result = self.recovered(report, PREVIOUS, previous, "2026-09-29")
                self.assertEqual(result.get("rejected_candidates"), [evidence(CURRENT, current, message)])
                self.assert_fallback_channel(result)

    def test_component_difference_within_existing_tolerance_remains_accepted(self):
        content = workbook(scheme_row(L="1.20%"))
        report, requests = self.collect_sources({CURRENT: content})
        result = self.recovered(report, CURRENT, content, "2026-10-02")
        self.assertEqual(result["direct_ter"], 1.20)
        self.assertEqual(requests, [CURRENT])

    def test_both_invalid_preserve_first_workbook_error_provenance_and_all_rejections(self):
        current = workbook(scheme_row(A="ICICI Prudential Small Cap Fund"))
        previous = workbook(scheme_row("29/09/2026"), header_changes={"C": "Base TER (%)¹"})
        first_message = "ICICI exact Mid Cap scheme name is not unique"
        report, requests = self.collect_sources({CURRENT: current, PREVIOUS: previous})
        error = self.failed(report, first_message)
        self.assertEqual({key: error.get(key) for key in ("source", "sha256", "bytes")}, evidence(CURRENT, current))
        self.assertEqual(error.get("rejected_candidates"), [
            evidence(CURRENT, current, first_message),
            evidence(PREVIOUS, previous, "ICICI TER workbook columns changed"),
        ])
        self.assertEqual(requests, [CURRENT, PREVIOUS])
        self.assert_fallback_channel(error)

    def test_all_rejected_workbooks_remain_excluded_from_ter_readiness(self):
        current = workbook(scheme_row(A="ICICI Prudential Small Cap Fund"))
        previous = workbook(scheme_row("29/09/2026", L="1.11%"))
        report, _ = self.collect_sources({CURRENT: current, PREVIOUS: previous})
        self.failed(report, "ICICI exact Mid Cap scheme name is not unique")
        readiness = reconcile({"families": [{
            "family": FAMILY, "amc": AMC, "direct_ter_available": False, "ter": None,
        }]}, report)
        self.assertEqual(readiness["counts"]["direct_ter"], 0)
        self.assertEqual(readiness["counts"]["first_party_amc"], 0)
        self.assertEqual(readiness["remaining_families"], [FAMILY])
        self.assertFalse(readiness["families"][0]["direct_ter_available"])
        self.assertFalse(readiness["public_export_enabled"])

    def test_unavailable_transports_record_sources_without_fabricated_hashes(self):
        report, requests = self.collect_sources({
            CURRENT: RuntimeError("current workbook unavailable"),
            PREVIOUS: RuntimeError("previous workbook unavailable"),
        })
        error = self.failed(report, "ICICI financial disclosure API and reviewed TER workbook paths are unavailable")
        self.assertTrue({"source", "sha256", "bytes"}.isdisjoint(error))
        self.assertEqual(error.get("rejected_candidates"), [
            {"source": CURRENT, "error": "current workbook unavailable"},
            {"source": PREVIOUS, "error": "previous workbook unavailable"},
        ])
        self.assertEqual(requests, [CURRENT, PREVIOUS])
        self.assert_fallback_channel(error)

    def test_invalid_current_then_previous_transport_failure_keeps_provenance_separate(self):
        current = workbook(scheme_row(A="ICICI Prudential Small Cap Fund"))
        message = "ICICI exact Mid Cap scheme name is not unique"
        report, requests = self.collect_sources({
            CURRENT: current, PREVIOUS: RuntimeError("previous workbook unavailable"),
        })
        error = self.failed(report, message)
        self.assertEqual({key: error.get(key) for key in ("source", "sha256", "bytes")}, evidence(CURRENT, current))
        self.assertEqual(error.get("rejected_candidates"), [
            evidence(CURRENT, current, message),
            {"source": PREVIOUS, "error": "previous workbook unavailable"},
        ])
        self.assertEqual(requests, [CURRENT, PREVIOUS])
        self.assert_fallback_channel(error)

    def test_transport_failure_then_previous_success_retains_rejected_source_without_hash(self):
        previous = workbook(scheme_row("29/09/2026"))
        report, _ = self.collect_sources({CURRENT: RuntimeError("current workbook unavailable"), PREVIOUS: previous})
        result = self.recovered(report, PREVIOUS, previous, "2026-09-29")
        self.assertEqual(result.get("rejected_candidates"), [{"source": CURRENT, "error": "current workbook unavailable"}])
        self.assert_fallback_channel(result)

    def test_api_selected_invalid_workbook_fails_closed_with_api_channel_metadata(self):
        current = workbook(scheme_row(), header_changes={"C": "Base TER (%)¹"})
        previous = workbook(scheme_row("29/09/2026"))
        report, requests = self.collect_sources({CURRENT: current, PREVIOUS: previous}, api_selected=True)
        error = self.failed(report, "ICICI TER workbook columns changed")
        self.assertEqual(requests, [CURRENT])
        self.assertEqual({key: error.get(key) for key in ("source", "sha256", "bytes")}, evidence(CURRENT, current))
        self.assertEqual(error.get("discovery_channel"), "financial_disclosure_api")
        self.assertIn("discovery_api_error", error)
        self.assertIsNone(error["discovery_api_error"])
        self.assertEqual(error.get("rejected_candidates", []), [])

    def test_api_selected_valid_workbook_keeps_existing_success_channel(self):
        content = workbook(scheme_row())
        report, requests = self.collect_sources({CURRENT: content}, api_selected=True)
        result = self.recovered(report, CURRENT, content, "2026-10-02")
        self.assertEqual(requests, [CURRENT])
        self.assertEqual(result["discovery_channel"], "financial_disclosure_api")
        self.assertIsNone(result["discovery_api_error"])

    def test_api_non_xlsx_acquisition_keeps_existing_reviewed_path_fallback(self):
        previous = workbook(scheme_row("29/09/2026"))
        report, requests = self.collect_sources(
            {CURRENT: b"not an XLSX package", PREVIOUS: previous}, api_selected=True
        )
        result = self.recovered(report, PREVIOUS, previous, "2026-09-29")
        self.assertEqual(requests, [CURRENT, CURRENT, PREVIOUS])
        self.assertEqual(result["discovery_channel"], "reviewed_monthly_workbook_fallback")
        self.assertEqual(result["discovery_api_error"], "ICICI TER source is not XLSX")

    def test_fiscal_year_rollover_validates_previous_folder_and_retains_row_date(self):
        current_source = BASE + "2027-2028/TotalExpenseRatioApr2027.xlsx"
        previous_source = BASE + "2026-2027/TotalExpenseRatioMar2027.xlsx"
        current = workbook(scheme_row("01/04/2027", A="ICICI Prudential Small Cap Fund"))
        previous = workbook(scheme_row("31/03/2027"))
        report, requests = self.collect_sources(
            {current_source: current, previous_source: previous}, today=date(2027, 4, 2)
        )
        result = self.recovered(report, previous_source, previous, "2027-03-31")
        self.assertEqual(requests, [current_source, previous_source])
        self.assertEqual(result.get("rejected_candidates"), [
            evidence(current_source, current, "ICICI exact Mid Cap scheme name is not unique"),
        ])
        self.assert_fallback_channel(result)


if __name__ == "__main__":
    unittest.main()
