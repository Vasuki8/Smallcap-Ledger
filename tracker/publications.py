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

    if re.search(r'\baxis\b', str(amc), re.I):
        combined=(str(title or '')+' '+path).lower()
        if re.search(r'axis[\s_-]*greater[\s_-]*china[\s_-]*(?:equity[\s_-]*)?fund[\s_-]*of[\s_-]*fund',combined):
            return 'Axis Greater China Fund of Fund article; unrelated to Axis Small Cap Fund'

    if re.search(r'\bhelios\b', str(amc), re.I):
        combined=(str(title or '')+' '+path).lower()
        foreign_scheme=re.search(
            r'\bhelios[\s_-]*(?:flexi[\s_-]*cap|overnight|(?:large[\s&_-]*)?mid[\s_-]*cap|'
            r'financial[\s_-]*services|arbitrage)[\s_-]*fund\b',
            combined,
        )
        product_material=re.search(r'product[\s_-]*note|presentation',combined)
        if foreign_scheme and product_material:
            return 'Helios non-Small-Cap fund product material; unrelated to Helios Small Cap Fund'

    if re.search(r'\bbandhan\b', str(amc), re.I):
        combined=(str(title or '')+' '+path).lower()
        if (re.search(r'\bbandhan[\s_-]*nifty[\s_-]*midcap150[\s_-]*index[\s_-]*fund\b',combined)
            and re.search(r'presentation',combined)):
            return 'Bandhan Nifty Midcap150 Index Fund presentation; unrelated to Bandhan Small Cap Fund'

    if re.search(r'\bhsbc\b', str(amc), re.I):
        if (host in ('www.assetmanagement.hsbc.co.in','assetmanagement.hsbc.co.in')
            and path.rstrip('/')=='/en/mutual-funds/investor-resources'
            and 'doc=product-note-and-deck' in parsed.query.lower()):
            return 'HSBC generic product-note/deck directory; not an AMC communication document'

    if re.search(r'\bquant\b', str(amc), re.I):
        combined=(str(title or '')+' '+path).lower()
        if path.rstrip('/') in ('/distributorhub/nfopresentation','/distributorhub/nfopresentation.aspx'):
            return 'Quant generic NFO-presentation directory; not an AMC communication document'
        if (re.search(r'(?:silver[\s_%+-]*etf|income[\s_%+-]*plus[\s_%+-]*arbitrage[\s_%+-]*active[\s_%+-]*fof)',combined)
            and re.search(r'presentation',combined)):
            return 'Quant non-Small-Cap NFO presentation; unrelated to Quant Small Cap Fund'

    if re.search(r'\bsundaram\b', str(amc), re.I):
        if (host in ('www.sundarammutual.com','sundarammutual.com')
            and path.rstrip('/')=='/report/amcp'):
            return 'Sundaram AMC corporate presentation; not a Small Cap fund communication'

    if re.search(r'\bmirae\b', str(amc), re.I):
        if (host in ('www.miraeassetmf.co.in','miraeassetmf.co.in')
            and path.rstrip('/')=='/downloads/product-presentations'):
            return 'Mirae generic product-presentations directory; not an AMC communication document'

    if re.search(r'aditya|birla', str(amc), re.I):
        filename=path.rsplit('/',1)[-1]
        if re.search(r'(?:^|[_-])public[_-]?notice(?:[_-]|\.|$)',filename,re.I):
            return 'AMC public notice; not a market-view communication document'

    if re.search(r'\bdsp\b', str(amc), re.I):
        combined=(str(title or '')+' '+path).lower()
        foreign_scheme=re.search(
            r'dsp[\s_-]*(?:quant|us[\s_-]*flexible[\s_-]*equity|world[\s_-]*(?:gold|agriculture|mining|energy)|'
            r'government[\s_-]*securities|floater|equity[\s_-]*savings|equity[\s&_-]*bond|'
            r'dynamic[\s_-]*asset[\s_-]*allocation|global[\s_-]*allocation)[\s_-]*fund',
            combined,
        )
        if foreign_scheme and re.search(r'unitholder|fundamental|corrigendum|letter',combined):
            return 'DSP non-Small-Cap scheme unitholder material; unrelated to DSP Small Cap Fund'
        if path.rstrip('/')=='/mandatory-disclosures/unitholder-letter-for-change-in-fundamental-attribute':
            return 'DSP Global Allocation Fund of Fund unitholder-letter page; unrelated to DSP Small Cap Fund'

    if re.search(r'\bquantum\b', str(amc), re.I):
        combined=(str(title or '')+' '+path).lower()
        if re.search(r'quantum[\s_-]*diversified[\s_-]*equity[\s_-]*all[\s_-]*cap[\s_-]*active[\s_-]*(?:fof|fund[\s_-]*of[\s_-]*fund)',combined):
            return 'Quantum Diversified Equity All Cap Active FOF letter; unrelated to Quantum Small Cap Fund'

    if re.search(r'\bsamco\b', str(amc), re.I):
        combined=(str(title or '')+' '+path).lower()
        compact=re.sub(r'[^a-z0-9]','',combined)
        if 'lienrequestletterfromunitholder' in compact or 'requestletterforlien' in compact:
            return 'Samco lien-request form; not an AMC communication document'

    return None
