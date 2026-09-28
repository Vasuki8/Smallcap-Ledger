"""Integration regressions for the read-only batch-5 evidence fixes."""
import hashlib
import json
import unittest
from unittest.mock import Mock, patch

from tracker.midcap_portfolio_batch5 import (
    MAHINDRA_PARSER_VERSION, SUNDARAM_CARD, _mahindra_result, _sundaram_result,
)


class Batch5EvidenceQualityTests(unittest.TestCase):
    def card_fetch(self, day="31-Aug-2026", body=b"PKworkbook"):
        calls = []
        source = "https://www.sundarammutual.com/fixture.xlsx"
        def fetch(url, **kwargs):
            self.assertFalse(kwargs.get("archive", True))
            calls.append(url)
            if url == SUNDARAM_CARD:
                return json.dumps([{
                    "GROUP_NAME": "Sundaram Mid Cap Fund", "AUMASONDATE": day,
                    "PORTFOLIO_PATH": source,
                }]).encode(), None, "application/json"
            self.assertEqual(url, source)
            return body, None, "application/octet-stream"
        return fetch, calls, source

    def test_sundaram_unlabelled_date_field_uses_date_parser(self):
        fetch, calls, source = self.card_fetch()
        snapshot = {"as_of": "2026-08-31", "positions_observed": 12, "complete": False}
        with patch("tracker.midcap_portfolio_batch5._parse_workbook", return_value=snapshot) as parse:
            result = _sundaram_result(fetch, "2026-08-31")
        self.assertEqual(result["source"], source)
        self.assertEqual(result["positions_observed"], 12)
        self.assertEqual(len(calls), 2)
        parse.assert_called_once_with(b"PKworkbook", "Sundaram Mid Cap Fund", "2026-08-31")

    def test_stale_card_is_rejected_before_downloading_portfolio(self):
        fetch, calls, _ = self.card_fetch(day="31-Jul-2026")
        with self.assertRaisesRegex(ValueError, "not current"):
            _sundaram_result(fetch, "2026-08-31")
        self.assertEqual(calls, [SUNDARAM_CARD])

    def test_missing_card_date_is_not_filled_from_expected_date(self):
        fetch, calls, _ = self.card_fetch(day="")
        with self.assertRaisesRegex(ValueError, "not current"):
            _sundaram_result(fetch, "2026-08-31")
        self.assertEqual(calls, [SUNDARAM_CARD])

    def test_current_card_does_not_override_workbook_date_failure(self):
        fetch, _, _ = self.card_fetch()
        with patch("tracker.midcap_portfolio_batch5._parse_workbook",
                   side_effect=ValueError("No exact current portfolio sheet")):
            with self.assertRaisesRegex(ValueError, "No exact current"):
                _sundaram_result(fetch, "2026-08-31")

    def test_pdf_is_an_explicit_parser_gap_not_an_html_portfolio(self):
        fetch, _, _ = self.card_fetch(body=b"%PDF-1.7 fixture")
        with self.assertRaisesRegex(ValueError, "dedicated PDF portfolio parser"):
            _sundaram_result(fetch, "2026-08-31")

    def test_mahindra_recovery_retains_only_issuers_and_source_hash(self):
        body = ("<h1>Mahindra Manulife Mid Cap Fund</h1>"
                "<p>Data as on 31 August 2026</p><table>"
                "<tr><th>Company / Issuer</th><th>% of Net Assets</th></tr>"
                "<tr><td>Healthcare</td><td>9.70%</td></tr>"
                "<tr><td>Power</td><td>1.90%</td></tr>"
                "<tr><td>Consumer Services</td><td>0.85%</td></tr>"
                "<tr><td>Services</td><td>2.67%</td></tr>" +
                "".join(f"<tr><td>{name} Limited</td><td>1.00%</td></tr>"
                        for name in ("Alpha", "Beta", "Gamma", "Delta", "Epsilon")) +
                "</table>").encode()
        fetch = Mock(return_value=(body, None, "text/html"))
        result = _mahindra_result(fetch, "2026-08-31")
        self.assertEqual(result["positions_observed"], 5)
        self.assertFalse(result["complete"])
        self.assertEqual(result["parser_version"], MAHINDRA_PARSER_VERSION)
        self.assertEqual(result["source_sha256"], hashlib.sha256(body).hexdigest())
        self.assertFalse(fetch.call_args.kwargs["archive"])


if __name__ == "__main__":
    unittest.main()
