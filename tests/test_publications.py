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

    def test_rules_preserve_legitimate_communications_and_titles(self):
        self.assertTrue(exclusion_reason('SBI Mutual Fund',WRONG.replace('frankline-templeton','Franklin%2DTempleton')))
        self.assertIsNone(exclusion_reason('Franklin Templeton Mutual Fund',WRONG))
        self.assertIsNone(exclusion_reason('SBI Mutual Fund','https://www.sbimf.com/market-outlook'))
        self.assertEqual(providers.document_title('Factsheets','https://www.sbimf.com/factsheets'),'Factsheets')
        self.assertEqual(providers.document_title('SBI investment outlook',GOOD),'SBI investment outlook')


if __name__=='__main__':unittest.main()
