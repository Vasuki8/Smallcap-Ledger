"""ITI/Mahindra retained AMC communication recovery checks."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tracker import db,disclosures,providers
from scripts import refresh_amc_communications as upgrade


class CommunicationRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.patch=patch.object(db,"DATA",Path(self.tmp.name))
        self.patch.start()
        db.init()
        with db.connect() as c:
            c.executemany(
                """INSERT INTO schemes(code,name,family,amc,plan,option,category_source)
                   VALUES(?,?,?,?,?,?,?)""",
                [
                    (9701,"ITI Direct Growth","Iti Small Cap Fund","ITI Mutual Fund","Direct","Growth","test"),
                    (9702,"Mahindra Direct Growth","Mahindra Manulife Small Cap Fund","Mahindra Manulife Mutual Fund","Direct","Growth","test"),
                    (9703,"Kotak Direct Growth","Kotak Small Cap Fund","Kotak Mahindra Mutual Fund","Direct","Growth","test"),
                ],
            )
            c.executemany(
                """INSERT INTO source_pages(amc_match,url,label,status)
                   VALUES(?,?,?,'Checked')""",
                [(amc,url,label) for _,amc,label,url in upgrade.TARGETS],
            )
        for family,_amc,label,url in upgrade.TARGETS:
            body=(family+" "+label).encode()
            digest=db.archive(body,"text/html")
            old_kind=("factsheet" if "Update" in label else "source page")
            did=providers.save_document(
                family,label,url,old_kind,"AMC",published=None,origin="AMC")
            providers.doc_version(did,digest)

        # Historical wrong association can remain auditable, but it must never
        # be promoted into Kotak's communications.
        digest=db.archive(b"wrong historical association","text/html")
        did=providers.save_document(
            "Kotak Small Cap Fund","Market Outlook",upgrade.TARGETS[3][3],
            "source page","AMC",published=None,origin="AMC")
        providers.doc_version(did,digest)

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_explicit_market_update_title_outranks_digitalfactsheet_url(self):
        self.assertEqual(
            providers.classify(
                "Equity Market Update",
                "https://www.itiamc.com/digitalfactsheet/July2026/equity-update.html"),
            "market view",
        )
        self.assertEqual(
            providers.classify(
                "Debt Market Update",
                "https://www.itiamc.com/digitalfactsheet/July2026/debt-update.html"),
            "market view",
        )
        self.assertEqual(
            providers.classify("Monthly Factsheet",
                               "https://www.itiamc.com/digitalfactsheet/July2026/factsheet.html"),
            "factsheet",
        )

    def test_only_dated_monthly_communication_pages_are_promotable(self):
        self.assertEqual(
            disclosures.dated_communication_source_kind(
                "Market Outlook",
                "https://www.mahindramanulife.com/digital-factsheet/july-2026/Outlook.html"),
            "market view",
        )
        self.assertEqual(
            disclosures.dated_communication_source_kind(
                "Equity Market Update",
                "https://www.itiamc.com/digitalfactsheet/July2026/equity-update.html"),
            "market view",
        )
        self.assertIsNone(disclosures.dated_communication_source_kind(
            "Market updates","https://www.hdfcfund.com/market-update"))
        self.assertIsNone(disclosures.dated_communication_source_kind(
            "Factsheet","https://www.itiamc.com/digitalfactsheet/July2026/innerpages/Small-Cap.html"))

    def test_registered_source_family_resolution_separates_kotak_and_mahindra(self):
        self.assertEqual(
            [x["family"] for x in disclosures.source_families("Mahindra")],
            ["Mahindra Manulife Small Cap Fund"],
        )
        self.assertEqual(
            [x["family"] for x in disclosures.source_families("Kotak")],
            ["Kotak Small Cap Fund"],
        )
        self.assertEqual(
            [x["family"] for x in disclosures.source_families("ITI")],
            ["Iti Small Cap Fund"],
        )

    def test_retained_repair_promotes_exact_four_without_inventing_dates(self):
        self.assertTrue(upgrade.run())
        self.assertTrue(upgrade.run())
        iti=db.rows("""SELECT title,kind,published_at FROM documents
                       WHERE family='Iti Small Cap Fund'
                         AND url LIKE 'https://www.itiamc.com/digitalfactsheet/July2026/%'
                       ORDER BY title""")
        self.assertEqual(len(iti),3)
        self.assertTrue(all(row["kind"]=="market view" for row in iti))
        self.assertTrue(all(row["published_at"] is None for row in iti))
        mahindra=db.one("""SELECT kind,published_at FROM documents
                           WHERE family='Mahindra Manulife Small Cap Fund'
                             AND url=?""",(upgrade.TARGETS[3][3],))
        self.assertEqual(mahindra["kind"],"market view")
        self.assertIsNone(mahindra["published_at"])
        kotak=db.one("""SELECT kind FROM documents
                        WHERE family='Kotak Small Cap Fund' AND url=?""",
                     (upgrade.TARGETS[3][3],))
        self.assertEqual(kotak["kind"],"source page")
        self.assertTrue(db.setting(upgrade.UPGRADE_KEY,False))


if __name__=="__main__":
    unittest.main()
