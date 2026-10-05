"""Publication ownership exceptions verified against the original AMC pages."""
import re
from urllib.parse import unquote, urlparse


def exclusion_reason(amc, url, title=''):
    """A hosting domain alone does not establish which fund a report covers.

    Keep historical files/evidence, but exclude verified cross-scheme
    associations before they can appear on an unrelated Small Cap fund page.
    """
    parsed = urlparse(url)
    path = unquote(parsed.path).lower()
    if re.search(r'\babakkus\b', amc, re.I):
        combined=(str(title or '')+' '+path).lower()
        if re.search(r'\babakkus[\s_-]*liquid[\s_-]*fund[\s_-]*presentation\b',combined):
            return 'Abakkus Liquid Fund presentation; unrelated to Abakkus Small Cap Fund'
    if not re.search(r'\bsbi\b', amc, re.I):
        return None
    host = (parsed.hostname or '').lower()
    if host != 'sbimf.com' and not host.endswith('.sbimf.com'):
        return None
    foreign_section = re.search(r'(?:^|[/_-])frankline?[-_ ]+templeton(?:[/_-]|$)', path)
    foreign_title = re.match(r'^\s*frankline?\s+templeton\s+disclosures\b', title, re.I)
    if foreign_section or foreign_title:
        return 'Franklin Templeton scheme disclosures hosted by SBI; unrelated to SBI Small Cap Fund'
    return None
