"""Read-only Helios monthly portfolio discovery for the staged Mid Cap audit."""
from __future__ import annotations

from datetime import date, datetime
import hashlib
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from . import providers


FAMILY = "Helios Mid Cap Fund"
AMC = "Helios Mutual Fund"
PAGE = "https://www.heliosmf.in/portfolio-disclosure"
PARSER_VERSION = "helios-midcap-monthly-workbook-v1"


def _clean(value):
    return " ".join(str(value or "").split())


def inspect(expected, fetch_fn=providers.fetch):
    from .midcap_portfolio_structured import _parse_workbook

    day = date.fromisoformat(expected)
    if day > date.today():
        raise ValueError("Helios portfolio reporting date is in the future")
    body, _, media = fetch_fn(PAGE, archive=False, max_bytes=12 * 1024 * 1024)
    if str(media).split(";", 1)[0].strip().casefold() not in ("text/html", "application/xhtml+xml"):
        raise ValueError("Helios portfolio disclosure page did not return HTML")
    soup = BeautifulSoup(body, "html.parser")
    monthly = []
    for item in soup.select('.hlx-dl-cat-item[data-depth="1"]'):
        heading = item.find("h3", recursive=False)
        if heading and _clean(heading.get_text(" ", strip=True)).casefold() == "monthly portfolio":
            monthly.append(item)
    if len(monthly) != 1:
        raise ValueError("Helios disclosure page lacks one exact Monthly Portfolio section")
    schemes = []
    for item in monthly[0].select('.hlx-dl-cat-item[data-depth="2"]'):
        heading = item.find("h4", recursive=False)
        if heading and _clean(heading.get_text(" ", strip=True)).casefold() == FAMILY.casefold():
            schemes.append(item)
    if len(schemes) != 1:
        raise ValueError("Helios monthly section lacks one exact Mid Cap scheme")

    sources = set()
    for anchor in schemes[0].select("a.hlx-dl-file[href]"):
        if _clean(anchor.get_text(" ", strip=True)).casefold() != day.strftime("%B %Y").casefold():
            continue
        source = urljoin(PAGE, anchor["href"])
        parsed = urlparse(source)
        if (parsed.scheme != "https" or parsed.hostname != "www.heliosmf.in"
                or parsed.username is not None or parsed.password is not None
                or parsed.port not in (None, 443)
                or parsed.query or parsed.fragment):
            raise ValueError("Helios monthly workbook URL is not an approved first-party source")
        match = re.fullmatch(
            r"/wp-content/uploads/20\d{2}/\d{2}/helios-mid-cap-fund-monthly-portfolio-as-on-"
            r"(\d{1,2})(?:st|nd|rd|th)?-([a-z]+)-(20\d{2})\.xlsx",
            parsed.path, re.I,
        )
        if not match:
            raise ValueError("Helios monthly workbook filename does not prove the exact scheme and date")
        file_day = datetime.strptime(" ".join(match.groups()), "%d %B %Y").date()
        if file_day != day:
            raise ValueError("Helios monthly workbook filename reports a different portfolio date")
        sources.add(source)
    if len(sources) != 1:
        raise ValueError(f"Helios monthly section exposed {len(sources)} exact current workbooks")
    source = sources.pop()
    content, _, content_type = fetch_fn(source, archive=False, max_bytes=15 * 1024 * 1024)
    snapshot = _parse_workbook(content, FAMILY, expected)
    return {
        "family": FAMILY, "amc": AMC, "status": "recovered",
        **snapshot, "scope": "structured_monthly_portfolio",
        "source": source, "source_sha256": hashlib.sha256(content).hexdigest(),
        "source_content_type": content_type,
        "discovery_source": PAGE, "discovery_source_sha256": hashlib.sha256(body).hexdigest(),
        "discovery_source_content_type": media,
        "source_locator": "Monthly Portfolio / Helios Mid Cap Fund / " + day.strftime("%B %Y"),
        "parser_version": PARSER_VERSION,
    }
