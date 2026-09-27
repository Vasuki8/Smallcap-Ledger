"""Category registry and publication-scope safety boundaries."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class CategorySpec:
    id: str
    label: str
    amfi_bucket: str
    stage: str
    default_benchmark_family: str | None = None


_registry={
    "small-cap":CategorySpec(
        id="small-cap",
        label="Small Cap",
        amfi_bucket="Small Cap Fund",
        stage="live",
        default_benchmark_family=None,
    ),
    "mid-cap":CategorySpec(
        id="mid-cap",
        label="Mid Cap",
        amfi_bucket="Mid Cap Fund",
        stage="staged",
        default_benchmark_family=None,
    ),
}
REGISTRY=MappingProxyType(_registry)

_AMFI_CATEGORY=re.compile(
    r"^Open\s+Ended\s+Schemes\s*\(\s*Equity\s+Schemes?\s*-\s*"
    r"(?P<bucket>Small\s*Cap|Mid\s*Cap|Midcap)\s+Fund\s*\)\s*$",
    re.I,
)


def get_category(category_id):
    key=str(category_id or "").strip().lower()
    if key not in REGISTRY:
        raise ValueError(f"Unknown mutual-fund category: {category_id!r}")
    return REGISTRY[key]


def registry_payload():
    return {key:asdict(value) for key,value in REGISTRY.items()}


def category_from_amfi_header(value):
    text=re.sub(r"[–—]", "-", str(value or "").strip())
    text=re.sub(r"\s+", " ", text)
    match=_AMFI_CATEGORY.fullmatch(text)
    if not match:
        return None
    bucket=re.sub(r"\s+", "", match.group("bucket")).lower()
    return "small-cap" if bucket=="smallcap" else "mid-cap"


def identity_issues(records):
    issues=[];seen_codes={};family_keys={}
    for index,record in enumerate(records):
        code=record.get("code")
        family=str(record.get("family") or "").strip()
        amc=str(record.get("amc") or "").strip()
        category=record.get("category")
        if isinstance(code,bool) or not isinstance(code,int) or code<=0:
            issues.append({"code":"invalid_scheme_code","index":index,"scheme_code":code})
        if not family or not amc:
            issues.append({"code":"missing_scheme_identity","index":index,"scheme_code":code})
        try:
            get_category(category)
        except ValueError:
            issues.append({"code":"unknown_category","index":index,"scheme_code":code,"category":category})
        if isinstance(code,int) and not isinstance(code,bool) and code>0:
            prior=seen_codes.get(code)
            if prior is not None:
                issues.append({"code":"duplicate_scheme_code","scheme_code":code,"indexes":[prior,index]})
            else:
                seen_codes[code]=index
        if family:
            key=(str(category or ""),amc)
            prior=family_keys.get(family)
            if prior is None:
                family_keys[family]=key
            elif prior!=key:
                issues.append({
                    "code":"ambiguous_family_key","family":family,
                    "first":{"category":prior[0],"amc":prior[1]},
                    "second":{"category":key[0],"amc":key[1]},
                })
    return issues


def assert_publication_scope(records):
    issues=identity_issues(records)
    if issues:
        raise ValueError("Unsafe category identity for publication: "+issues[0]["code"])
    staged=sorted({
        record["category"] for record in records
        if get_category(record["category"]).stage!="live"
    })
    if staged:
        raise ValueError("category_not_live: "+", ".join(staged))
    return True
