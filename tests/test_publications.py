"""Regressions for Franklin disclosures incorrectly attached to SBI Small Cap."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ['SMALLCAP_NO_SCHEDULER']='1'
from tracker import db, providers, disclosures, amc_reports
from tracker.app import documents
from tracker.publications import exclusion_reason

SBI='SBI Small Cap Fund'
GOOD='https://www.sbimf.com/docs/default-source/scheme-factsheets/sbi-small-cap-fund-factsheet-july-2026.pdf'
WRONG='https://www.sbimf.com/docs/default-source/frankline-templeton-files/security-level-portfolio-as-on-june-15-2023-for-6-schemes-being-wound-up-(1).pdf'
SECTION='https://www.sbimf.com/sbimf-franklin-templeton-disclosures'


class PublicationTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        patched=patch.object(db,'DATA',Path(temp.name));patched.start();self.addCleanup(patched.stop)
        db.init()
        with db.connect() as c:
            c.execute('INSERT INTO schemes(code,name,family,amc,plan,option,category_source) VALUES(?,?,?,?,?,?,?)',
                      (125497,SBI,SBI,'SBI Mutual Fund','Direct','Growth','https://www.amfiindia.com/'))

    def old_document(self,title,url,kind='factsheet'):
        # Simulate a pre-fix archive without using the new ingestion guard.
        h=db.archive(b'Archived original: '+url.encode(),'application/pdf')
        with db.connect() as c:
            did=c.execute('INSERT INTO documents(family,title,kind,scope,url,first_seen,last_seen,origin) VALUES(?,?,?,?,?,?,?,?)',
                          (SBI,title,kind,'AMC',url,db.now(),db.now(),'AMC')).lastrowid
        providers.doc_version(did,h)
        return h

    def test_old_associations_hidden_without_deleting_history(self):
        hashes=[self.old_document('Factsheets',WRONG),
                self.old_document('Franklin Templeton Disclosures',SECTION,'source page'),
                self.old_document('Official factsheet',GOOD)]
        db.metric(SBI,'All','aum','2026-07-31',39942.33,'INR crore',GOOD,hashes[-1])
        shown=documents(125497)
        self.assertEqual([d['url'] for d in shown],[GOOD])
        self.assertEqual(shown[0]['title'],'SBI small cap fund factsheet july 2026')
        self.assertEqual(shown[0]['versions'][0]['hash'],hashes[-1])
        self.assertEqual(db.one('SELECT COUNT(*) n FROM documents')['n'],3)
        self.assertEqual(db.one('SELECT COUNT(*) n FROM document_versions')['n'],3)
        self.assertEqual(db.one('SELECT value FROM metrics')['value'],'39942.33')
        for row in db.rows('SELECT path FROM archives'):
            self.assertTrue((db.DATA/row['path']).is_file())

    def test_known_foreign_sections_rejected_before_download(self):
        self.assertFalse(disclosures.official_publication_url(WRONG,'SBI'))
        self.assertTrue(disclosures.official_publication_url(GOOD,'SBI'))
        with patch.object(disclosures,'fetch') as fetch:
            result=disclosures.ingest_source({'amc_match':'SBI','url':SECTION,'label':'Factsheets'})
            self.assertTrue(result.startswith('Excluded:'))
            fetch.assert_not_called()
        with self.assertRaisesRegex(ValueError,'Franklin Templeton'):
            providers.save_document(SBI,'Factsheets',WRONG)
        with patch.object(disclosures,'factsheet_pdf') as parse:
            self.assertEqual(amc_reports.extract(b'%PDF',SBI,WRONG,'old-hash'),0)
            parse.assert_not_called()

    def test_discovery_keeps_sbi_report_and_skips_foreign_navigation(self):
        page='https://www.sbimf.com/factsheets'
        html=f'<a href="{SECTION}">Franklin Templeton Disclosures</a><a href="{WRONG}">Factsheets</a><a href="{GOOD}">Download PDF</a>'.encode()
        bodies={page:html,GOOD:b'%PDF-1.4 synthetic SBI report'}
        fetched=[]
        def fetch(url,**kwargs):
            fetched.append(url);body=bodies[url]
            typ='text/html' if url==page else 'application/pdf'
            return body,db.archive(body,typ),typ
        with patch.object(disclosures,'can_crawl'),patch.object(disclosures,'fetch',side_effect=fetch),patch.object(amc_reports,'extract',return_value=0):
            disclosures.ingest_source({'amc_match':'SBI','url':page,'label':'Factsheets'})
        self.assertEqual(fetched,[page,GOOD])
        self.assertEqual({d['url'] for d in documents(125497)},{page,GOOD})
        self.assertFalse(db.one('SELECT id FROM source_pages WHERE url=?',(SECTION,)))

    def test_old_foreign_source_disabled_and_correct_source_kept(self):
        with db.connect() as c:
            c.executemany('INSERT INTO source_pages(amc_match,url,label) VALUES(?,?,?)',
                          [('SBI',SECTION,'Franklin Templeton Disclosures'),('SBI',GOOD,'Official factsheet')])
        disclosures.seed_sources();disclosures.seed_sources()
        old=db.one('SELECT * FROM source_pages WHERE url=?',(SECTION,))
        self.assertEqual(old['enabled'],0);self.assertEqual(old['status'],'Excluded')
        self.assertEqual(db.one('SELECT enabled FROM source_pages WHERE url=?',(GOOD,))['enabled'],1)

    def test_abakkus_liquid_fund_presentation_is_not_small_cap_communication(self):
        family='Abakkus Small Cap Fund';code=9902
        wrong=('https://www.abakkusmf.com/img/docs/LiquidFund/'
               'Abakkus_Liquid_Fund_Presentation.pdf')
        with db.connect() as c:
            c.execute('INSERT INTO schemes(code,name,family,amc,plan,option,category_source) VALUES(?,?,?,?,?,?,?)',
                      (code,'Abakkus Small Cap Direct Growth',family,
                       'Abakkus Mutual Fund','Direct','Growth','test'))
            did=c.execute('''INSERT INTO documents(
              family,title,kind,scope,url,first_seen,last_seen,origin)
              VALUES(?,?,?,?,?,?,?,?)''',
              (family,'Scheme Presentation','market view','AMC',wrong,db.now(),db.now(),'AMC')).lastrowid
        h=db.archive(b'%PDF-1.7 historical liquid-fund presentation','application/pdf')
        providers.doc_version(did,h)

        self.assertEqual(documents(code),[])
        self.assertIn('Liquid Fund',exclusion_reason('Abakkus Mutual Fund',wrong,'Scheme Presentation'))
        with self.assertRaisesRegex(ValueError,'Liquid Fund presentation'):
            providers.save_document(family,'Scheme Presentation',wrong,'market view','AMC',origin='AMC')

        # Evidence stays retained even though the cross-scheme association is hidden.
        self.assertEqual(db.one('SELECT COUNT(*) n FROM documents WHERE id=?',(did,))['n'],1)
        self.assertEqual(db.one('SELECT COUNT(*) n FROM document_versions WHERE document_id=?',(did,))['n'],1)
        self.assertTrue(db.archive_binary_path(h).is_file())

    def test_helios_other_fund_product_material_is_not_small_cap_communication(self):
        family='Helios Small Cap Fund';code=9903
        foreign=[
            ('Helios Flexi Cap Fund','https://www.heliosmf.in/wp-content/uploads/2025/04/FLexicap-Fund-Product-Note_.pdf'),
            ('Helios Overnight Fund','https://www.heliosmf.in/wp-content/uploads/2025/04/Overnight-Fund-Product-Note.pdf'),
            ('Helios Mid Cap Fund','https://www.heliosmf.in/wp-content/uploads/2025/04/Mid-Cap-Fund-Product-Note_.pdf'),
            ('Helios Large & Mid Cap Fund','https://www.heliosmf.in/wp-content/uploads/2025/04/Large-Mid-Cap-Fund-Product-Note_.pdf'),
            ('Helios Financial Services Fund','https://www.heliosmf.in/wp-content/uploads/2025/04/Financial-Services-Fund-Product-Note.pdf'),
            ('Helios Arbitrage Fund','https://www.heliosmf.in/wp-content/uploads/2026/03/Helios-Arbitrage-Fund-NFO-Presentation.pdf'),
        ]
        own=('Helios Small Cap Fund',
             'https://www.heliosmf.in/wp-content/uploads/2025/10/Helios-Small-Cap-Fund-Product-Note.pdf')
        with db.connect() as c:
            c.execute('INSERT INTO schemes(code,name,family,amc,plan,option,category_source) VALUES(?,?,?,?,?,?,?)',
                      (code,'Helios Small Cap Direct Growth',family,
                       'Helios Mutual Fund','Direct','Growth','test'))
            for title,url in foreign+[own]:
                c.execute('''INSERT INTO documents(
                  family,title,kind,scope,url,first_seen,last_seen,origin)
                  VALUES(?,?,?,?,?,?,?,?)''',
                  (family,title,'market view','AMC',url,db.now(),db.now(),'AMC'))

        shown=documents(code)
        self.assertEqual([(d['title'],d['url']) for d in shown],[own])
        for title,url in foreign:
            self.assertIn('non-Small-Cap',exclusion_reason('Helios Mutual Fund',url,title))
            with self.assertRaisesRegex(ValueError,'non-Small-Cap'):
                providers.save_document(family,title,url,'market view','AMC',origin='AMC')
        self.assertIsNone(exclusion_reason('Helios Mutual Fund',own[1],own[0]))
        providers.save_document(family,own[0],own[1],'market view','AMC',origin='AMC')

    def test_bandhan_foreign_presentation_and_hsbc_directory_are_excluded(self):
        cases=[
            (
                'Bandhan Small Cap Fund',9904,'Bandhan Mutual Fund',
                'Next Presentation on Bandhan Nifty Midcap150 Index Fund – May’26>Partners>Fund House>Presentation',
                'https://cmsnew.bandhanmutual.com/presentation-on-bandhan-nifty-midcap150-index-fund-may26partnersfund-housepresentation/',
                'Midcap150 Index Fund',
            ),
            (
                'HSBC Small Cap Fund',9905,'HSBC Mutual Fund',
                'Performance - Equity Hybrid Debt Global Funds',
                'https://www.assetmanagement.hsbc.co.in/en/mutual-funds/investor-resources?Date=&Cap=&Doc=product-note-and-deck#&module-17=1',
                'product-note/deck directory',
            ),
        ]
        with db.connect() as c:
            for family,code,amc,title,url,_ in cases:
                c.execute('INSERT INTO schemes(code,name,family,amc,plan,option,category_source) VALUES(?,?,?,?,?,?,?)',
                          (code,family+' Direct Growth',family,amc,'Direct','Growth','test'))
                c.execute('''INSERT INTO documents(
                  family,title,kind,scope,url,first_seen,last_seen,origin)
                  VALUES(?,?,?,?,?,?,?,?)''',
                  (family,title,'market view','AMC',url,db.now(),db.now(),'AMC'))
        for family,code,amc,title,url,reason in cases:
            with self.subTest(family=family):
                self.assertEqual(documents(code),[])
                self.assertIn(reason,exclusion_reason(amc,url,title))
                with self.assertRaises(ValueError):
                    providers.save_document(family,title,url,'market view','AMC',origin='AMC')

        # Verified AMC-wide communications remain eligible.
        self.assertIsNone(exclusion_reason(
            'Bandhan Mutual Fund',
            'https://cmsnew.bandhanmutual.com/market_outlook/market-outlook-equity-september-2026/',
            'Market Outlook - Equity - September 2026'))
        self.assertIsNone(exclusion_reason(
            'HSBC Mutual Fund',
            'https://www.assetmanagement.hsbc.co.in/en/mutual-funds/news-and-insights/rbi-monetary-policy-review-august-2026',
            'RBI Monetary Policy Review - August 2026'))

    def test_rules_preserve_legitimate_communications_and_titles(self):
        self.assertTrue(exclusion_reason('SBI Mutual Fund',WRONG.replace('frankline-templeton','Franklin%2DTempleton')))
        self.assertIsNone(exclusion_reason('Franklin Templeton Mutual Fund',WRONG))
        self.assertIsNone(exclusion_reason('SBI Mutual Fund','https://www.sbimf.com/market-outlook'))
        self.assertEqual(providers.document_title('Factsheets','https://www.sbimf.com/factsheets'),'Factsheets')
        self.assertEqual(providers.document_title('SBI investment outlook',GOOD),'SBI investment outlook')


if __name__=='__main__':unittest.main()
