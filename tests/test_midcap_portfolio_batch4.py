"""Tests for staged Mid Cap portfolio batch 4."""
import unittest
from unittest.mock import patch
from tracker.midcap_portfolio_batch4 import _walk,_scan_zip

class MidCapPortfolioBatch4Tests(unittest.TestCase):
    def test_recursive_pgim_payload_walk(self):
        data={"a":[{"title":"x"},{"b":{"title":"y"}}]}
        titles=[x.get("title") for x in _walk(data) if x.get("title")]
        self.assertEqual(titles,["x","y"])

    def test_zip_scan_accepts_only_exact_strong_family(self):
        import io,zipfile
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,"w") as z:
            z.writestr("other.xlsx",b"PKother")
            z.writestr("mid.xlsx",b"PKmid")
        parsed={"day":"2026-08-31","positions":[{"name":str(i)} for i in range(15)],
                "positions_observed":15,"complete":False,"unknown_rows":[]}
        def fake_parse(body,family,expected):
            if body==b"PKmid":return parsed
            raise ValueError("wrong")
        with patch("tracker.midcap_portfolio_batch4._parse_workbook",side_effect=fake_parse):
            entry,body,row=_scan_zip(buf.getvalue(),"Aditya Birla Sun Life Midcap Fund","2026-08-31","fixture")
        self.assertEqual(entry,"mid.xlsx")
        self.assertEqual(body,b"PKmid")
        self.assertEqual(row["positions_observed"],15)

if __name__=="__main__":unittest.main()
