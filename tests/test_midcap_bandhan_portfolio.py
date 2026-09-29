"""Tests for exact Bandhan Mid Cap monthly portfolio discovery."""
import json
import unittest
from datetime import date
from unittest.mock import patch

from tracker import midcap_bandhan_portfolio as bandhan
from tracker import midcap_portfolio_batch5 as batch5


DAY=date(2026,8,31)
POST_ID=166401


def page(title=None):
    title=title or "Monthly and Half-yearly – Bandhan Mid cap Fund 31 August 2026"
    return f"""<html><body class="postid-{POST_ID}">
      <article id="post-{POST_ID}"><h1 class="entry-title">{title}</h1></article>
    </body></html>""".encode()


def api_payload(*,fund="Bandhan Mid Cap Fund",bucket=bandhan.MEDIA_BUCKET,
                title="Monthly and Half-yearly – Bandhan Mid cap Fund 31 August 2026"):
    return json.dumps({
        "status":"200",
        "data":[{
            "id":POST_ID,
            "title":title,
            "acf_fields":{
                "funds_mapping":{"post_title":fund},
                "financial_year":"2026",
                "disclosures_type":"Monthly and Half-yearly Disclosures",
                "disclosure_files":[{
                    "document_name":"Bandhan Mid Cap Fund 31 August 2026",
                    "month":"August",
                    "document_link":{
                        "uploaded_to":POST_ID,
                        "mime_type":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "url":(
                            f"https://storage.googleapis.com/{bucket}/2026/09/"
                            "abc-bandhan-mid-cap-fund-31-august-2026.xlsx"
                        ),
                    },
                }],
            },
        }],
    }).encode()


class BandhanMidCapPortfolioTests(unittest.TestCase):
    def test_exact_page_identity_exposes_post_id(self):
        self.assertEqual(bandhan.post_id_from_page(page(),DAY),POST_ID)
        self.assertIsNone(bandhan.post_id_from_page(
            page("Monthly and Half-yearly – Bandhan Small Cap Fund 31 August 2026"),DAY
        ))
        self.assertEqual(
            bandhan.page_url(DAY),
            "https://cmsnew.bandhanmutual.com/"
            "monthly-and-half-yearly-bandhan-mid-cap-fund-31-august-2026/",
        )

    def test_api_requires_exact_fund_date_and_official_workbook(self):
        row=bandhan.attachment_from_api(api_payload(),POST_ID,DAY)
        self.assertEqual(row["post_id"],POST_ID)
        self.assertTrue(row["source"].startswith(
            "https://storage.googleapis.com/"+bandhan.MEDIA_BUCKET+"/"
        ))
        self.assertIsNone(bandhan.attachment_from_api(
            api_payload(fund="Bandhan Small Cap Fund"),POST_ID,DAY
        ))
        self.assertIsNone(bandhan.attachment_from_api(
            api_payload(bucket="another-bucket"),POST_ID,DAY
        ))
        self.assertIsNone(bandhan.attachment_from_api(
            api_payload(title="Monthly and Half-yearly – Bandhan Mid cap Fund 31 July 2026"),
            POST_ID,DAY,
        ))

    def test_discovery_uses_page_then_exact_post_api(self):
        requested=[]
        def fetch(url,**kwargs):
            requested.append((url,kwargs))
            if url==bandhan.page_url(DAY):
                return page(),None,"text/html; charset=utf-8"
            if url==bandhan.API+"?id="+str(POST_ID):
                return api_payload(),None,"application/json"
            raise AssertionError(url)
        row=bandhan.discover_source(fetch,"2026-08-31")
        self.assertEqual(row["post_id"],POST_ID)
        self.assertEqual(len(requested),2)
        self.assertTrue(all(call[1].get("archive") is False for call in requested))

    def test_batch5_parses_discovered_workbook_with_existing_structured_parser(self):
        source=(
            "https://storage.googleapis.com/"+bandhan.MEDIA_BUCKET+
            "/2026/09/abc-bandhan-mid-cap-fund-31-august-2026.xlsx"
        )
        def fetch(url,**kwargs):
            if url==bandhan.page_url(DAY):
                return page(),None,"text/html"
            if url==bandhan.API+"?id="+str(POST_ID):
                return api_payload(),None,"application/json"
            if url==source:
                return b"PKfixture",None,"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            raise AssertionError(url)
        parsed={
            "sheet":"MIDCAP","as_of":"2026-08-31","positions_observed":71,
            "complete":False,"unknown_rows":[],"aum":None,
        }
        with patch.object(batch5,"_parse_workbook",return_value=parsed) as parser:
            row=batch5._bandhan_result(fetch,"2026-08-31")
        parser.assert_called_once_with(b"PKfixture",bandhan.FAMILY,"2026-08-31")
        self.assertEqual(row["family"],bandhan.FAMILY)
        self.assertEqual(row["positions_observed"],71)
        self.assertFalse(row["complete"])
        self.assertEqual(row["scope"],"structured_monthly_portfolio")
        self.assertEqual(row["disclosure_post_id"],POST_ID)

    def test_collect_routes_bandhan_only_when_staged(self):
        expected={"family":bandhan.FAMILY,"status":"recovered","as_of":"2026-08-31",
                  "positions_observed":10,"complete":False}
        with patch.object(batch5.db,"rows",return_value=[{"family":bandhan.FAMILY}]), \
             patch.object(batch5,"COLLECTORS",((bandhan.FAMILY,lambda f,e:dict(expected)),)):
            result=batch5.collect(fetch_fn=lambda *a,**k:None,today=date(2026,9,29))
        self.assertEqual(result["recovered"],1)
        self.assertEqual(result["failed"],0)
        self.assertEqual(result["portfolio_expected_as_of"],"2026-08-31")


if __name__=="__main__":
    unittest.main()
