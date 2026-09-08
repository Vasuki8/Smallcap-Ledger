"""Publication ownership exceptions verified against the original AMC pages."""
import re
from urllib.parse import unquote, urlparse


def exclusion_reason(amc, url, title=''):
    """A hosting domain alone does not establish which AMC's schemes a report covers.

    SBI hosts a separate Franklin Templeton winding-up disclosure section. Those
    reports are not SBI fund communications, even when labelled just Factsheets.
    Match the section URL/title, never a passing mention in a report's body or
    shared website navigation. Keep historical files; exclude their association.
    """
    if not re.search(r'\bsbi\b', amc, re.I):
        return None
    parsed = urlparse(url)
    host = (parsed.hostname or '').lower()
    if host != 'sbimf.com' and not host.endswith('.sbimf.com'):
        return None
    path = unquote(parsed.path).lower()
    foreign_section = re.search(r'(?:^|[/_-])frankline?[-_ ]+templeton(?:[/_-]|$)', path)
    foreign_title = re.match(r'^\s*frankline?\s+templeton\s+disclosures\b', title, re.I)
    if foreign_section or foreign_title:
        return 'Franklin Templeton scheme disclosures hosted by SBI; unrelated to SBI Small Cap Fund'
    return None
