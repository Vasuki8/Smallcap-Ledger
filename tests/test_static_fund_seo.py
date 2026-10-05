"""Static fund discoverability export regressions."""
import json
import re
import tempfile
from pathlib import Path

from scripts import export_site


def row(code,family,plan="Direct",option="Growth"):
    return {
        "code":code,
        "family":family,
        "amc":"Example Mutual Fund",
        "plan":plan,
        "option":option,
        "nav":{"date":"2026-10-05","value":123.4567},
        "metrics":{
            "aum":{"value":"1234.5","as_of":"2026-10-01"},
            "ter":{"value":"0.72","as_of":"2026-10-04"},
            "benchmark":{"value":"Nifty Smallcap 250 TRI","as_of":"2026-10-05"},
        },
        "returns":{"1":11.2,"3":14.3,"5":16.4},
        "portfolio":{"as_of":"2026-08-31","complete":1},
    }


def test_fund_slug_is_stable_and_url_safe():
    assert export_site.fund_slug("Axis Small Cap Fund")=="axis-small-cap-fund"
    assert export_site.fund_slug("Bank Of India Small Cap Fund")=="bank-of-india-small-cap-fund"


def test_preferred_family_series_selects_direct_growth():
    rows=[
        row(3,"Example Small Cap Fund","Regular","Growth"),
        row(2,"Example Small Cap Fund","Direct","IDCW"),
        row(1,"Example Small Cap Fund","Direct","Growth"),
    ]
    selected=export_site.preferred_family_series(rows)
    assert len(selected)==1
    assert selected[0]["code"]==1


def test_static_fund_page_has_canonical_content_and_valid_json_ld():
    base="https://vasuki8.github.io/Smallcap-Ledger/"
    rendered=export_site.render_fund_landing(row(1,"Axis Small Cap Fund"),base)
    assert '<link rel="canonical" href="'+base+'funds/axis-small-cap-fund/">' in rendered
    assert "Axis Small Cap Fund · Smallcap Ledger" in rendered
    assert "Nifty Smallcap 250 TRI" in rendered
    assert "2026-08-31" in rendered
    match=re.search(r'<script type="application/ld\+json">(.*?)</script>',rendered,re.S)
    assert match
    structured=json.loads(match.group(1).replace("<\\/","</"))
    assert structured["@type"]=="FinancialProduct"
    assert structured["name"]=="Axis Small Cap Fund"
    assert structured["provider"]["name"]=="Example Mutual Fund"


def test_discoverability_writes_directory_sitemap_robots_and_one_page_per_family():
    rows=[
        row(2,"Beta Small Cap Fund","Regular","Growth"),
        row(1,"Beta Small Cap Fund","Direct","Growth"),
        row(3,"Alpha Small Cap Fund","Direct","Growth"),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        selected=export_site.write_discoverability(
            root,{"funds":rows},"Vasuki8/Smallcap-Ledger")
        assert [x["family"] for x in selected]==[
            "Alpha Small Cap Fund","Beta Small Cap Fund"]
        assert (root/"funds"/"index.html").is_file()
        assert (root/"funds"/"alpha-small-cap-fund"/"index.html").is_file()
        assert (root/"funds"/"beta-small-cap-fund"/"index.html").is_file()
        sitemap=(root/"sitemap.xml").read_text(encoding="utf-8")
        assert "https://vasuki8.github.io/Smallcap-Ledger/funds/alpha-small-cap-fund/" in sitemap
        assert sitemap.count("<url>")==4  # root + directory + 2 fund families
        robots=(root/"robots.txt").read_text(encoding="utf-8")
        assert "Sitemap: https://vasuki8.github.io/Smallcap-Ledger/sitemap.xml" in robots
