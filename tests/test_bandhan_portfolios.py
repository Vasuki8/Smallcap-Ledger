"""Bandhan public monthly disclosure discovery and censored-weight safety."""
import io
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import openpyxl

from tracker import amc_discovery, amc_reports, db, disclosures
from tracker import bandhan_portfolios as bandhan
from tracker.portfolio_parser import parse_sheet
from scripts import refresh_bandhan_portfolios as upgrade


def page(day, post_id, title=None):
    title = title or bandhan.expected_title(day)
    return f'''<html><body class="postid-{post_id}">
      <article id="post-{post_id}"><h1 class="entry-title">{title}</h1></article>
    </body></html>'''.encode()


def api_payload(day, post_id, *, fund=bandhan.FAMILY, bucket=bandhan.MEDIA_BUCKET):
    name=f'Bandhan Small Cap Fund {day.day} {day.strftime("%B %Y")}'
    slug_date=day.strftime('%d-%B-%Y').lower()
    return json.dumps({
      'status':'200',
      'data':[{
        'id':post_id,
        'title':bandhan.expected_title(day),
        'acf_fields':{
          'funds_mapping':{'post_title':fund},
          'financial_year':str(day.year),
          'disclosures_type':'Monthly and Half-yearly Disclosures',
          'disclosure_files':[{
            'document_name':name,
            'month':day.strftime('%B'),
            'document_link':{
              'uploaded_to':post_id,
              'mime_type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
              'url':f'https://storage.googleapis.com/{bucket}/{day.year}/{day.month%12+1:02d}/abc-bandhan-small-cap-fund-{slug_date}.xlsx'
            }
          }]
        }
      }]
    }).encode()


def workbook():
    rows=[
      [None,'Bandhan Small Cap Fund'],
      [None,'Portfolio Statement as on August 31,2026'],
      ['Code','Name of the Instrument','ISIN','Industry / Rating','Quantity',
       'Market/Fair Value ( Rs. in Lacs)','% to NAV','YTM'],
      ['EQ01','Alpha Industries Limited','INE123456789','Industrials',100,8100,81,None],
      ['EQ02','Censored Industries Limited','INE987654321','Industrials',1,.01,'$',None],
      [None,'Money Market Instruments',None,None,None,None,None,None],
      [None,'TREPS / Reverse Repo Instrument',None,None,None,None,None,None],
      ['TRP_010926','Triparty Repo TRP_010926',None,None,None,1500,15,None],
      [None,'OTHERS',None,None,None,None,None,None],
      [None,'Cash Margin - CCIL',None,None,None,100,1,None],
      [None,'Cash Margin - Derivatives',None,None,None,100,1,None],
      [None,'Cash / Bank Balance',None,None,None,300,3,None],
      [None,'Net Receivables/Payables',None,None,None,-100,-1,None],
      [None,'Net Current Assets',None,None,None,400,4,None],
      [None,'GRAND TOTAL',None,None,None,10000,100,None],
      [None,'$ Less Than 0.01% of NAV'],
    ]
    formats=[['General']*8 for _ in rows]
    return rows,formats


class BandhanPortfolioTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.data_patch=patch.object(db,'DATA',Path(self.tmp.name));self.data_patch.start()
        db.init()

    def tearDown(self):
        self.data_patch.stop();self.tmp.cleanup()

    def test_exact_page_and_api_identity_are_required(self):
        day=date(2026,8,31);post=158853
        self.assertEqual(bandhan.post_id_from_page(page(day,post),day),post)
        self.assertIsNone(bandhan.post_id_from_page(page(day,post,'Bandhan Mid Cap Fund'),day))
        row=bandhan.attachment_from_api(api_payload(day,post),post,day)
        self.assertEqual(row[0],bandhan.FAMILY)
        self.assertTrue(row[1].startswith(
            'https://storage.googleapis.com/'+bandhan.MEDIA_BUCKET+'/'))
        self.assertIsNone(bandhan.attachment_from_api(
            api_payload(day,post,fund='Bandhan Flexi Cap Fund'),post,day))
        self.assertIsNone(bandhan.attachment_from_api(
            api_payload(day,post,bucket='another-bucket'),post,day))

    def test_discovery_uses_only_two_closed_exact_posts(self):
        requested=[]
        posts={(2026,8):158853,(2026,7):155405}
        def read(url,body=None):
            requested.append(url)
            for (year,month),post in posts.items():
                day=date(year,month,31)
                if url==bandhan.page_url(day):return page(day,post),'page','text/html'
                if url==bandhan.API+'?id='+str(post):return api_payload(day,post),'api','application/json'
            raise AssertionError(url)
        rows=list(bandhan.discover(read,date(2026,9,24)))
        self.assertEqual(len(rows),2)
        self.assertIn('31-august-2026.xlsx',rows[0][1])
        self.assertIn('31-july-2026.xlsx',rows[1][1])
        self.assertEqual(list(bandhan.closed_month_ends(date(2026,1,1))),
                         [date(2025,12,31),date(2025,11,30)])
        self.assertEqual(len(requested),4)

    def test_bandhan_media_bucket_allowance_is_narrow(self):
        good='https://storage.googleapis.com/nonprod-static-assets-121to59kaawfgfi7bol/2026/09/a.xlsx'
        bad='https://storage.googleapis.com/other-bucket/2026/09/a.xlsx'
        self.assertTrue(disclosures.official_publication_url(good,'Bandhan'))
        self.assertFalse(disclosures.official_publication_url(bad,'Bandhan'))
        self.assertFalse(disclosures.official_publication_url(good,'SBI'))

    def test_bandhan_is_wired_into_nightly_discovery(self):
        with patch('tracker.bandhan_portfolios.discover',
                   return_value=iter([('family','url','title')])) as mock:
            self.assertEqual(list(amc_discovery.discover('Bandhan')),
                             [('family','url','title')])
            mock.assert_called_once_with(amc_discovery.read)

    def test_censored_equity_stays_partial_and_cash_subtotal_is_not_duplicated(self):
        rows,formats=workbook()
        parsed=parse_sheet(rows,formats,bandhan.FAMILY)
        self.assertEqual(parsed['day'],'2026-08-31')
        self.assertFalse(parsed['complete'])
        self.assertEqual(parsed['unknown_rows'],['Censored Industries Limited'])
        self.assertEqual(len(parsed['positions']),6)
        self.assertAlmostEqual(sum(x['weight'] for x in parsed['positions']),100.0,places=6)
        self.assertFalse(any(x['name']=='Net Current Assets' for x in parsed['positions']))
        repo=next(x for x in parsed['positions'] if x['name'].startswith('Triparty Repo'))
        self.assertEqual(repo['asset_type'],'Money market')
        self.assertEqual(next(x for x in parsed['positions'] if x['name']=='Cash / Bank Balance')['asset_type'],
                         'Cash and net current assets')

    def test_spreadsheet_retains_all_numeric_rows_but_not_censored_weight(self):
        rows,_=workbook();book=openpyxl.Workbook();ws=book.active;ws.title='IDF271'
        for row in rows:ws.append(row)
        out=io.BytesIO();book.save(out);book.close()
        source=('https://storage.googleapis.com/'+bandhan.MEDIA_BUCKET+
                '/2026/09/abc-bandhan-small-cap-fund-31-august-2026.xlsx')
        count=disclosures.spreadsheet(out.getvalue(),bandhan.FAMILY,source,'hash')
        self.assertEqual(count,7)  # 1 AUM + 6 numeric positions
        snap=db.one('''SELECT p.complete,COUNT(h.id) positions,SUM(h.weight) weight
          FROM portfolios p JOIN holdings h ON h.snapshot_id=p.id
          WHERE p.family=? GROUP BY p.id''',(bandhan.FAMILY,))
        self.assertEqual(snap['complete'],0)
        self.assertEqual(snap['positions'],6)
        self.assertAlmostEqual(snap['weight'],100.0,places=6)
        self.assertIsNone(db.one('''SELECT h.id FROM holdings h JOIN portfolios p ON p.id=h.snapshot_id
          WHERE p.family=? AND h.name='Censored Industries Limited' ''',(bandhan.FAMILY,)))
        self.assertEqual(db.one("SELECT value FROM metrics WHERE metric='aum'")['value'],'100.0')

    def test_store_report_uses_source_scoped_parser_and_rejects_non_workbook(self):
        rows,_=workbook();book=openpyxl.Workbook();ws=book.active
        for row in rows:ws.append(row)
        out=io.BytesIO();book.save(out);body=out.getvalue();book.close()
        url=('https://storage.googleapis.com/'+bandhan.MEDIA_BUCKET+
             '/2026/09/abc-bandhan-small-cap-fund-31-august-2026.xlsx')
        digest=db.archive(body)
        with patch.object(amc_discovery,'read',return_value=(body,digest,'spreadsheet')):
            self.assertEqual(amc_discovery.store_report('Bandhan',bandhan.FAMILY,url,'Bandhan Small Cap Fund 31 August 2026'),7)
        row=db.one('SELECT parser_version FROM document_extractions WHERE family=?',(bandhan.FAMILY,))
        self.assertEqual(row['parser_version'],bandhan.PARSER_VERSION)
        with patch.object(amc_discovery,'read',return_value=(b'<html>no</html>','bad','text/html')):
            with self.assertRaises(ValueError):
                amc_discovery.store_report('Bandhan',bandhan.FAMILY,url,'monthly')

    def test_upgrade_requires_current_substantial_snapshot_and_is_idempotent(self):
        url=('https://storage.googleapis.com/'+bandhan.MEDIA_BUCKET+
             '/2026/09/current-bandhan-small-cap-fund.xlsx')
        def store(*args):
            disclosures.portfolio(bandhan.FAMILY,'2026-08-31',
                [{'name':f'Position {i}','weight':.5,'asset_type':'Equity'} for i in range(200)],
                False,url,'hash')
            return 200
        with patch.object(amc_discovery,'discover',return_value=[(bandhan.FAMILY,url,'monthly')]), \
             patch.object(amc_discovery,'store_report',side_effect=store) as save, \
             patch.object(upgrade,'expected_portfolio_as_of',return_value='2026-08-31'):
            self.assertTrue(upgrade.run())
            self.assertTrue(upgrade.run())
            self.assertEqual(save.call_count,1)
        self.assertTrue(db.setting(upgrade.UPGRADE_KEY))

        # A source failure in a fresh DB must remain retryable.
        with db.connect() as c:
            c.execute('DELETE FROM settings WHERE key=?',(upgrade.UPGRADE_KEY,))
        with patch.object(amc_discovery,'discover',side_effect=ValueError('unavailable')):
            self.assertFalse(upgrade.run())
        self.assertFalse(db.setting(upgrade.UPGRADE_KEY,False))


if __name__=='__main__':
    unittest.main()
