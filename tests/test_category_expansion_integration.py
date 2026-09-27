"""Production integration boundaries for staged categories."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tracker import db,providers
from scripts import export_site
from scripts.preview_category_expansion import build_preview
from test_category_foundation import feed,row,SMALL,MID,TODAY


class CategoryExpansionIntegrationTests(unittest.TestCase):
    def test_new_and_legacy_smallcap_parsers_agree(self):
        content=feed(SMALL,"Example AMC",row(1,name="Example Small Cap Fund"),
                     row(2,name="Example Small Cap Fund",option="IDCW Reinvestment"),
                     MID,"Example AMC",row(3,name="Example Mid Cap Fund"))
        result=build_preview(
            content,family_name=providers.family_name,plan_type=providers.plan_type,
            option_type=providers.option_type,legacy_parse_amfi=providers.parse_amfi,today=TODAY)
        self.assertTrue(result["smallcap_parser_parity"])
        self.assertEqual(result["summary"]["small-cap"]["candidate_fund_groups"],1)
        self.assertEqual(result["summary"]["small-cap"]["option_counts"],{"Growth":1,"IDCW":1})
        self.assertEqual(result["summary"]["mid-cap"]["scheme_codes"],1)

    def test_staged_category_rejects_export_without_erasing_previous_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with patch.object(db,"DATA",root/"data"):
                db.init()
                with db.connect() as conn:
                    conn.execute("""INSERT INTO schemes(code,name,family,amc,plan,option,category,category_source)
                        VALUES(1,'Mid Cap Direct','Example Mid Cap Fund','Example AMC','Direct','Growth','mid-cap','fixture')""")
                output=root/"previous-site";output.mkdir();marker=output/"index.html"
                marker.write_text("last known good site")
                with self.assertRaisesRegex(ValueError,"category_not_live"):
                    export_site.export(output)
                self.assertEqual(marker.read_text(),"last known good site")
                self.assertEqual(db.one("SELECT category FROM schemes WHERE code=1")["category"],"mid-cap")

    def test_legacy_family_url_identity_is_not_migrated(self):
        family="Example Small Cap Fund";old=hashlib.sha256(family.encode()).hexdigest()[:20]
        from tracker.categories import assert_publication_scope
        records=[dict(code=1,family=family,amc="Example AMC",category="small-cap")]
        assert_publication_scope(records)
        self.assertEqual(hashlib.sha256(records[0]["family"].encode()).hexdigest()[:20],old)


if __name__=="__main__":unittest.main()
