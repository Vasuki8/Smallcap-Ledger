"""Offline category expansion boundaries."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
import hashlib
import unittest

from tracker.categories import (
    REGISTRY,assert_publication_scope,category_from_amfi_header,get_category,identity_issues,
)
from tracker.category_catalogue import parse_catalogue
from tracker.category_readiness import report
from scripts.preview_category_expansion import build_preview

TODAY=date(2026,9,27)
HEADER="Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Plan;Option;Net Asset Value;Date"
SMALL="Open Ended Schemes(Equity Scheme - Small Cap Fund)"
MID="Open Ended Schemes(Equity Schemes - Mid Cap Fund)"


def row(code=1,name="Example Fund",plan="Direct Plan",option="Growth",nav="12.5000",day="25-Sep-2026"):
    return f"{code};INF000000001;-;{name};{plan};{option};{nav};{day}"


def feed(*sections):
    return ("\ufeff"+HEADER+"\n"+"\n".join(sections)).encode()


def scheme(code=1,family="Example Small Cap Fund",category="small-cap",amc="Example AMC"):
    return dict(code=code,family=family,category=category,amc=amc)


class CategoryIdentityTests(unittest.TestCase):
    def test_small_live_mid_staged(self):
        self.assertEqual(get_category("small-cap").stage,"live")
        self.assertEqual(get_category("mid-cap").stage,"staged")
        with self.assertRaises(TypeError):REGISTRY["unknown"]=get_category("mid-cap")

    def test_unknown_category_never_falls_back(self):
        with self.assertRaises(ValueError):get_category("large-and-mid-cap")

    def test_official_singular_plural_and_midcap_headers(self):
        self.assertEqual(category_from_amfi_header(SMALL),"small-cap")
        self.assertEqual(category_from_amfi_header(MID),"mid-cap")
        self.assertEqual(category_from_amfi_header("Open Ended Schemes ( Equity Scheme - Midcap Fund )"),"mid-cap")

    def test_nearby_categories_and_fund_names_do_not_match(self):
        for header in (
            "Example Mid Cap Fund",
            "Open Ended Schemes(Equity Scheme - Large & Mid Cap Fund)",
            "Open Ended Schemes(Other Scheme - Index Funds)",
            "Open Ended Schemes(Equity Scheme - Mid Cap Fund of Funds)",
            "Close Ended Schemes(Equity Scheme - Mid Cap Fund)",
        ):
            with self.subTest(header=header):self.assertIsNone(category_from_amfi_header(header))

    def test_duplicate_code_and_family_collisions_are_flagged(self):
        self.assertEqual(identity_issues([scheme(1),scheme(1)])[0]["code"],"duplicate_scheme_code")
        issues=identity_issues([scheme(),scheme(2,category="mid-cap")])
        self.assertEqual(issues[0]["code"],"ambiguous_family_key")

    def test_publication_allows_only_live_identity_safe_rows(self):
        records=[scheme(1),scheme(2)]
        before=deepcopy(records);assert_publication_scope(records);self.assertEqual(records,before)
        with self.assertRaisesRegex(ValueError,"category_not_live"):
            assert_publication_scope([scheme(category="mid-cap")])
        with self.assertRaisesRegex(ValueError,"unknown_category"):
            assert_publication_scope([scheme(category="unregistered")])


class CatalogueTests(unittest.TestCase):
    def test_keeps_exact_codes_plans_options_and_source_evidence(self):
        content=feed(SMALL,"Example AMC",row(1),MID,"Example AMC",
                     row(2,option="IDCW Reinvestment"),row(3,plan="Regular Plan",option="Bonus"))
        result=parse_catalogue(content,today=TODAY)
        self.assertEqual({r["code"] for r in result["rows"]},{1,2,3})
        self.assertEqual(result["production_writes"],0)
        self.assertEqual(result["source_sha256"],hashlib.sha256(content).hexdigest())
        self.assertEqual(result["source_bytes"],len(content))
        self.assertEqual(next(r for r in result["rows"] if r["code"]==2)["option_raw"],"IDCW Reinvestment")

    def test_fund_name_never_overrides_official_bucket(self):
        result=parse_catalogue(feed(SMALL,"Example AMC",row(1,name="Renamed Opportunities"),
                                    MID,"Example AMC",row(2,name="A Name With Small Cap In It")),today=TODAY)
        self.assertEqual({r["code"]:r["category"] for r in result["rows"]},{1:"small-cap",2:"mid-cap"})

    def test_unknown_section_clears_prior_category(self):
        result=parse_catalogue(feed(SMALL,"Example AMC",row(1),
                                    "Open Ended Schemes(Other Scheme - Index Funds)",
                                    "Example AMC",row(2,name="Example Small Cap 250 Index Fund")),today=TODAY)
        self.assertEqual([r["code"] for r in result["rows"]],[1])

    def test_missing_amc_does_not_inherit_previous_section(self):
        result=parse_catalogue(feed(SMALL,"Example AMC",row(1),MID,row(2)),today=TODAY)
        self.assertEqual(len(result["rows"]),1)
        self.assertEqual(result["rejected_rows"][0]["reason"],"missing_scheme_identity")

    def test_invalid_future_and_conflicting_values_stop_or_surface(self):
        result=parse_catalogue(feed(MID,"Example AMC",row(1,nav="NaN"),row(2,nav="0"),
                                    row(3,day="01-Jan-2099"),row(4,day="unknown")),today=TODAY)
        self.assertEqual(result["rows"],[]);self.assertEqual(len(result["rejected_rows"]),4)
        with self.assertRaisesRegex(ValueError,"Conflicting AMFI rows"):
            parse_catalogue(feed(SMALL,"Example AMC",row(1),MID,"Example AMC",row(1)),today=TODAY)

    def test_identical_duplicate_collapses(self):
        result=parse_catalogue(feed(SMALL,"Example AMC",row(1),row(1)),today=TODAY)
        self.assertEqual(len(result["rows"]),1);self.assertEqual(result["identical_duplicates"],1)

    def test_explicit_category_selection_and_header_validation(self):
        content=feed(SMALL,"Example AMC",row(1),MID,"Example AMC",row(2))
        self.assertEqual([r["code"] for r in parse_catalogue(content,category_ids=("mid-cap",),today=TODAY)["rows"]],[2])
        with self.assertRaisesRegex(ValueError,"header"):parse_catalogue(b"<html>not nav</html>",today=TODAY)
        with self.assertRaises(ValueError):parse_catalogue(content,category_ids=(),today=TODAY)


class ReadinessAndPreviewTests(unittest.TestCase):
    def test_readiness_separates_categories_and_keeps_mid_blocked(self):
        records=[scheme(1),scheme(2),scheme(3,"Example Mid Cap Fund","mid-cap")]
        rows=[
            {"family":"Example Small Cap Fund","aum":{"value":"1"},"fee":{},"portfolio":{"as_of":"2026-08-31"},
             "portfolio_complete":True,"portfolio_fresh":True,"benchmark":{"value":"Nifty Smallcap 250 TRI"}},
            {"family":"Example Mid Cap Fund","aum":None},
        ]
        coverage={"built_at":"2026-09-27T00:00:00Z","funds":rows,"counts":{"funds":2,"aum":1}}
        result=report(records,coverage)
        self.assertEqual(result["by_category"]["small-cap"]["schemes"],2)
        self.assertEqual(result["by_category"]["mid-cap"]["counts"]["funds"],1)
        self.assertFalse(result["mid_cap_launch_ready"])
        self.assertEqual(result["global_counts"],coverage["counts"])

    def test_preview_requires_smallcap_parity_and_never_enables_import(self):
        content=feed(SMALL,"Example AMC",row(1),MID,"Example AMC",row(2))
        result=build_preview(
            content,family_name=lambda name:name,plan_type=lambda raw,name:raw,option_type=lambda raw,name:raw,
            legacy_parse_amfi=lambda text:[{"code":1,"date":"2026-09-25","nav":12.5}],
            coverage={"funds":[{"amc":"Example AMC"}]},today=TODAY)
        self.assertTrue(result["smallcap_parser_parity"])
        self.assertEqual(result["summary"]["mid-cap"]["scheme_codes"],1)
        self.assertEqual(result["production_writes"],0)
        self.assertFalse(result["mid_cap_launch_ready"])
        with self.assertRaisesRegex(ValueError,"parity failed"):
            build_preview(
                feed(SMALL,"Example AMC",row(1,nav="13.5"),MID,"Example AMC",row(2)),
                family_name=lambda name:name,plan_type=lambda raw,name:raw,option_type=lambda raw,name:raw,
                legacy_parse_amfi=lambda text:[{"code":1,"date":"2026-09-25","nav":12.5}],today=TODAY)


if __name__=="__main__":unittest.main()
