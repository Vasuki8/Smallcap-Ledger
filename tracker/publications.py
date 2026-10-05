"""Publication ownership exceptions verified against the original AMC pages."""
import re
from urllib.parse import unquote, urlparse


def exclusion_reason(amc, url, title=''):
    """Exclude reviewed cross-scheme/foreign associations without deleting evidence.

    A hosting domain establishes AMC ownership, not that every linked document
    belongs on every scheme page. Keep the original retained record/version for
    audit history while filtering associations that are demonstrably about a
    different fund or fund house.
    """
    parsed = urlparse(url)
    host = (parsed.hostname or '').lower()
    path = unquote(parsed.path).lower()
    label = str(title or '').lower()

    if re.search(r'\bsbi\b', str(amc), re.I):
        if host == 'sbimf.com' or host.endswith('.sbimf.com'):
            foreign_section = re.search(r'(?:^|[/_-])frankline?[-_ ]+templeton(?:[/_-]|$)', path)
            foreign_title = re.match(r'^\s*frankline?\s+templeton\s+disclosures\b', title, re.I)
            if foreign_section or foreign_title:
                return 'Franklin Templeton scheme disclosures hosted by SBI; unrelated to SBI Small Cap Fund'

    if re.search(r'\babakkus\b', str(amc), re.I):
        if host == 'abakkusmf.com' or host.endswith('.abakkusmf.com'):
            liquid_path = bool(re.search(r'(?:^|/)liquid[-_ ]?fund(?:/|$)', path, re.I))
            liquid_title = bool(re.search(r'\babakkus\s+liquid\s+fund\b|\bliquid\s+fund\s+presentation\b', label, re.I))
            if liquid_path or liquid_title:
                return 'Abakkus Liquid Fund material; unrelated to Abakkus Small Cap Fund'

    return None
