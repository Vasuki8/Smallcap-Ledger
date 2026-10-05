"""Publication ownership exceptions verified against the original AMC pages."""
import re
from urllib.parse import unquote, urlparse


def exclusion_reason(amc, url, title=''):
    """A hosting domain alone does not establish which fund a report covers.

    Keep historical files/evidence, but exclude verified cross-scheme
    associations before they can appear on an unrelated Small Cap fund page.
    """
    parsed = urlparse(url)
    host = (parsed.hostname or '').lower()
    path = unquote(parsed.path).lower()
    if re.search(r'\babakkus\b', amc, re.I):
        combined=(str(title or '')+' '+path).lower()
        if re.search(r'\babakkus[\s_-]*liquid[\s_-]*fund[\s_-]*presentation\b',combined):
            return 'Abakkus Liquid Fund presentation; unrelated to Abakkus Small Cap Fund'
    if re.search(r'\bhelios\b', amc, re.I):
        combined=(str(title or '')+' '+path).lower()
        foreign_scheme=re.search(
            r'\bhelios[\s_-]*(?:flexi[\s_-]*cap|overnight|(?:large[\s&_-]*)?mid[\s_-]*cap|'
            r'financial[\s_-]*services|arbitrage)[\s_-]*fund\b',
            combined,
        )
        product_material=re.search(r'product[\s_-]*note|presentation',combined)
        if foreign_scheme and product_material:
            return 'Helios non-Small-Cap fund product material; unrelated to Helios Small Cap Fund'
    if re.search(r'\bbandhan\b', amc, re.I):
        combined=(str(title or '')+' '+path).lower()
        if (re.search(r'\bbandhan[\s_-]*nifty[\s_-]*midcap150[\s_-]*index[\s_-]*fund\b',combined)
            and re.search(r'presentation',combined)):
            return 'Bandhan Nifty Midcap150 Index Fund presentation; unrelated to Bandhan Small Cap Fund'
    if re.search(r'\bhsbc\b', amc, re.I):
        if (host in ('www.assetmanagement.hsbc.co.in','assetmanagement.hsbc.co.in')
            and path.rstrip('/')=='/en/mutual-funds/investor-resources'
            and 'doc=product-note-and-deck' in parsed.query.lower()):
            return 'HSBC generic product-note/deck directory; not an AMC communication document'
    if re.search(r'\bquant\b', amc, re.I):
        combined=(str(title or '')+' '+path).lower()
        if (path.rstrip('/') in ('/distributorhub/nfopresentation','/distributorhub/nfopresentation.aspx')):
            return 'Quant generic NFO-presentation directory; not an AMC communication document'
        if (re.search(r'(?:silver[\s_%+-]*etf|income[\s_%+-]*plus[\s_%+-]*arbitrage[\s_%+-]*active[\s_%+-]*fof)',combined)
            and re.search(r'presentation',combined)):
            return 'Quant non-Small-Cap NFO presentation; unrelated to Quant Small Cap Fund'
    if re.search(r'\bmirae\b', amc, re.I):
        if (host in ('www.miraeassetmf.co.in','miraeassetmf.co.in')
            and path.rstrip('/')=='/downloads/product-presentations'):
            return 'Mirae generic product-presentations directory; not an AMC communication document'
    if not re.search(r'\bsbi\b', amc, re.I):
        return None
    if host != 'sbimf.com' and not host.endswith('.sbimf.com'):
        return None
    foreign_section = re.search(r'(?:^|[/_-])frankline?[-_ ]+templeton(?:[/_-]|$)', path)
    foreign_title = re.match(r'^\s*frankline?\s+templeton\s+disclosures\b', title, re.I)
    if foreign_section or foreign_title:
        return 'Franklin Templeton scheme disclosures hosted by SBI; unrelated to SBI Small Cap Fund'
    return None
