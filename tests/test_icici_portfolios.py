import io
import json
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

import openpyxl

from tracker import amc_discovery, amc_reports, db, disclosures, icici_portfolios as icici
from tracker.portfolio_parser import parse_sheet
from scripts import refresh_icici_portfolios as upgrade


def categories():
    return [{
        "id": "parent",
        "internalName": "other-scheme-disclosures",
        "title": {"text": icici.CATEGORY_TITLE, "code": icici.CATEGORY_CODE},
        "isEnabled": True,
        "subCategory": [{
            "id": "child",
            "internalName": icici.SUBCATEGORY_INTERNAL,
            "title": {"text": icici.SUBCATEGORY_TITLE, "code": icici.SUBCATEGORY_CODE},
            "isEnabled": True,
        }],
    }]


def file_row(month, year=2026):
    return {
        "title": {
            "text": f"Monthly Portfolio Disclosure {month} {year}",
            "code": f"Monthly Portfolio Disclosure {month} {year}",
        },
        "fileType": "Document",
        "url": f"/downloads/Files/Monthly Portfolio Disclosures/{year}/{month[:3]}/"
               f"Monthly-Portfolio-Disclosure-{month}-{year}.zip",
        "isEnabled": True,
        "userType": "Both",
        "category": icici.SUBCATEGORY_CODE,
        "categoryName": icici.SUBCATEGORY_TITLE,
        "level1Id": "parent",
        "level2Id": "child",
    }


def workbook_bytes():
    rows = [
        ["ICICI Prudential Mutual Fund", None, None, None, None, None, None],
        [icici.FAMILY, None, None, None, None, None, None],
        ["Portfolio as on Aug 31,2026", None, None, None, None, None, None],
        ["Company/Issuer/Instrument Name", "ISIN", "Coupon", "Industry/Rating",
         "Quantity", "Exposure/Market Value(Rs.Lakh)", "% to Nav"],
        ["Equity & Equity Related Instruments", None, None, None, None, None, None],
        ["Alpha Industries Ltd", "INE000A01011", None, "Industrial Products",
         1000, 9900, 99],
        ["TREPS", None, None, None, None, 100, 1],
        ["Grand Total", None, None, None, None, 10000, 100],
    ]
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "SMALL"
    for row in rows:
        sheet.append(row)
    out = io.BytesIO()
    book.save(out)
    return out.getvalue(), rows


def zip_bytes(*, duplicate=False, unsafe=False):
    book, _ = workbook_bytes()
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(icici.WORKBOOK_NAME, book)
        if duplicate:
            archive.writestr("nested/" + icici.WORKBOOK_NAME, book)
        if unsafe:
            archive.writestr("../escape.txt", b"x")
    return out.getvalue()


class IciciPortfolioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data_patch = patch.object(db, "DATA", Path(self.tmp.name))
        self.data_patch.start()
        db.init()

    def tearDown(self):
        self.data_patch.stop()
        self.tmp.cleanup()

    def test_closed_months_roll_year_boundary(self):
        self.assertEqual(
            list(icici.closed_month_ends(date(2027, 2, 5))),
            [date(2027, 1, 31), date(2026, 12, 31)],
        )

    def test_category_identity_is_exact(self):
        self.assertEqual(icici._category_ids(categories()), ("parent", "child"))
        bad = categories()
        bad[0]["subCategory"].append(dict(bad[0]["subCategory"][0]))
        with self.assertRaisesRegex(ValueError, "not uniquely identified"):
            icici._category_ids(bad)

    def test_listing_selects_exact_two_closed_months_and_blob_delivery(self):
        rows = [
            file_row("August"),
            dict(file_row("August")),  # harmless duplicate API record
            file_row("July"),
            file_row("September"),  # current open month is never selected
            {**file_row("August"), "level2Id": "other"},
        ]
        found = icici.listing_candidates(rows, "parent", "child", date(2026, 9, 24))
        self.assertEqual([x[0] for x in found],
                         [date(2026, 8, 31), date(2026, 7, 31)])
        self.assertTrue(all(x[1].startswith(
            "https://www.icicipruamc.com/blob/downloads/Files/Monthly%20Portfolio%20Disclosures/")
            for x in found))
        self.assertTrue(found[0][1].endswith("Monthly-Portfolio-Disclosure-August-2026.zip"))

    def test_listing_rejects_missing_prior_closed_month(self):
        with self.assertRaisesRegex(ValueError, "both closed-month"):
            icici.listing_candidates(
                [file_row("August")], "parent", "child", date(2026, 9, 24))

    def test_discover_replays_public_api_contract_without_archiving_metadata(self):
        calls = []
        files = {"files": [file_row("August"), file_row("July")]}

        def read(url, body=None, archive=True, headers=None):
            calls.append((url, body, archive, headers))
            payload = categories() if "categories" in url else files
            return json.dumps({"success": {"data": payload}}).encode(), None, "application/json"

        found = list(icici.discover(read, date(2026, 9, 24)))
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0][0], icici.FAMILY)
        self.assertFalse(calls[0][2])
        self.assertFalse(calls[1][2])
        self.assertEqual(calls[1][1]["categoryId"], "child")
        self.assertEqual(calls[1][1]["categoryName"], icici.CATEGORY_CODE)
        self.assertEqual(calls[1][1]["filter"], [])
        self.assertIn("requestAPIId", calls[1][3])

    def test_real_layout_reconciles_complete_portfolio(self):
        _book, rows = workbook_bytes()
        formats = [["General"] * 7 for _ in rows]
        parsed = parse_sheet(rows, formats, icici.FAMILY)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["day"], "2026-08-31")
        self.assertTrue(parsed["complete"], parsed)
        self.assertEqual(parsed["aum"], 100)
        self.assertEqual(len(parsed["positions"]), 2)
        self.assertEqual(parsed["positions"][0]["quantity"], 1000)
        self.assertAlmostEqual(sum(x["weight"] for x in parsed["positions"]), 100)

    def test_zip_extracts_only_exact_smallcap_workbook_and_rejects_unsafe_archives(self):
        source = ("https://www.icicipruamc.com/blob/downloads/Files/Monthly%20Portfolio%20Disclosures/"
                  "2026/Aug/Monthly-Portfolio-Disclosure-August-2026.zip")
        with patch("tracker.disclosures.spreadsheet", return_value=9) as parse:
            self.assertEqual(icici.extract_zip(zip_bytes(), icici.FAMILY, source, "hash"), 9)
            workbook = parse.call_args.args[0]
            self.assertTrue(workbook.startswith(b"PK"))
            self.assertEqual(parse.call_args.args[1:], (icici.FAMILY, source, "hash"))
        with self.assertRaisesRegex(ValueError, "exactly one"):
            icici.extract_zip(zip_bytes(duplicate=True), icici.FAMILY, source, "hash")
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            icici.extract_zip(zip_bytes(unsafe=True), icici.FAMILY, source, "hash")

    def test_store_report_uses_icici_parser_version_and_nightly_discovery_is_wired(self):
        source = ("https://www.icicipruamc.com/blob/downloads/Files/Monthly%20Portfolio%20Disclosures/"
                  "2026/Aug/Monthly-Portfolio-Disclosure-August-2026.zip")
        with patch("tracker.amc_discovery.read",
                   return_value=(zip_bytes(), "hash", "application/x-zip-compressed")), \
             patch("tracker.amc_reports.extract", return_value=3) as extract:
            self.assertEqual(
                amc_discovery.store_report("ICICI", icici.FAMILY, source, "Monthly Portfolio Disclosure"),
                3,
            )
            self.assertEqual(extract.call_args.kwargs["parser_version"], icici.PARSER_VERSION)

        with patch("tracker.icici_portfolios.discover",
                   return_value=iter([("family", "url", "title")])) as discover:
            self.assertEqual(list(amc_discovery.discover("ICICI")), [("family", "url", "title")])
            discover.assert_called_once_with(amc_discovery.read)

        seen = []
        with patch.object(amc_discovery, "discover",
                          side_effect=lambda amc: seen.append(amc) or []):
            amc_discovery.update()
        self.assertIn("ICICI", seen)

    def test_upgrade_requires_two_complete_current_snapshots_and_is_idempotent(self):
        august = ("https://www.icicipruamc.com/blob/downloads/Files/Monthly%20Portfolio%20Disclosures/"
                  "2026/Aug/Monthly-Portfolio-Disclosure-August-2026.zip")
        july = ("https://www.icicipruamc.com/blob/downloads/Files/Monthly%20Portfolio%20Disclosures/"
                "2026/July/Monthly-Portfolio-Disclosure-July-2026.zip")

        def store(_amc, _family, url, _title):
            day = "2026-08-31" if "August" in url else "2026-07-31"
            positions = [
                {"name": f"Position {i}", "weight": 1.0, "asset_type": "Equity"}
                for i in range(100)
            ]
            disclosures.portfolio(icici.FAMILY, day, positions, True, url, day + "-hash")
            return len(positions)

        rows = [
            (icici.FAMILY, august, "August"),
            (icici.FAMILY, july, "July"),
        ]
        with patch.object(amc_discovery, "discover", return_value=rows), \
             patch.object(amc_discovery, "store_report", side_effect=store) as save:
            self.assertTrue(upgrade.run())
            self.assertTrue(upgrade.run())
            self.assertEqual(save.call_count, 2)
        self.assertTrue(db.setting(upgrade.UPGRADE_KEY, False))


if __name__ == "__main__":
    unittest.main()
