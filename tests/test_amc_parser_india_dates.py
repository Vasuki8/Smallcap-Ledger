"""AMC parser date guards must use the Asia/Kolkata reporting calendar."""
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from tracker import db, disclosures, amc_metrics
from tracker.report_parser import dated


class AmcParserIndiaDateTests(unittest.TestCase):
    def test_shared_report_parser_accepts_india_current_day(self):
        with patch('tracker.report_parser.india_today',return_value=date(2026,9,10)):
            self.assertIsNone(dated('11 Sep 2026'))
        with patch('tracker.report_parser.india_today',return_value=date(2026,9,11)):
            self.assertEqual(dated('11 Sep 2026'),'2026-09-11')

    def test_disclosure_report_date_rejects_future_general_pattern(self):
        with patch('tracker.disclosures.india_today',return_value=date(2026,9,10)):
            self.assertIsNone(disclosures.report_date('Portfolio as on 11 Sep 2026'))
        with patch('tracker.disclosures.india_today',return_value=date(2026,9,11)):
            self.assertEqual(disclosures.report_date('Portfolio as on 11 Sep 2026'),'2026-09-11')

    def test_amc_page_accepts_date_that_is_current_in_india(self):
        url=next(x[2] for x in amc_metrics.PAGES if x[1]=='Axis Small Cap Fund')
        body='<h1>Axis Small Cap Fund</h1><div>AUM (In Cr.) ₹ 31,448.32 As On September 11, 2026</div>'.encode()
        with tempfile.TemporaryDirectory() as tmp, patch.object(db,'DATA',Path(tmp)):
            db.init();h=db.archive(body,'text/html')
            with patch('tracker.amc_metrics.india_today',return_value=date(2026,9,11)), \
                 patch('tracker.disclosures.india_today',return_value=date(2026,9,11)), \
                 patch('tracker.report_parser.india_today',return_value=date(2026,9,11)):
                saved=amc_metrics.parse_page(body,'Axis Small Cap Fund',url,h)
            self.assertEqual(saved,1)
            row=db.one("SELECT as_of,value FROM metrics WHERE hash=? AND metric='aum'",(h,))
            self.assertEqual(row['as_of'],'2026-09-11')
            self.assertAlmostEqual(float(row['value']),31448.32)

    def test_target_parser_files_no_longer_use_process_local_date_today(self):
        root=Path(__file__).resolve().parents[1]
        for rel in ('tracker/disclosures.py','tracker/amc_metrics.py','tracker/report_parser.py'):
            with self.subTest(path=rel):
                self.assertNotIn('date.today()', (root/rel).read_text(encoding='utf-8'))


if __name__=='__main__':
    unittest.main()
