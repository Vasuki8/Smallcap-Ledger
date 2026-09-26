"""Read-only ICICI monthly portfolio transport probe using current blob delivery."""
from __future__ import annotations
import io,sys,zipfile
from pathlib import Path,PurePosixPath
from urllib.parse import urlparse
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

OLD=('https://www.icicipruamc.com/downloads/Files/Monthly%20Portfolio%20Disclosures/'
     '2026/Aug/Monthly-Portfolio-Disclosure-August-2026.zip')
BLOBS=[
 ('August','https://www.icicipruamc.com/blob/downloads/Files/Monthly%20Portfolio%20Disclosures/'
           '2026/Aug/Monthly-Portfolio-Disclosure-August-2026.zip'),
 ('July','https://www.icicipruamc.com/blob/downloads/Files/Monthly%20Portfolio%20Disclosures/'
         '2026/July/Monthly-Portfolio-Disclosure-July-2026.zip'),
]

def safe(url):
    host=(urlparse(url).hostname or '').lower()
    return host=='www.icicipruamc.com' or host.endswith('.icicipruamc.com')

def probe(url,follow):
    if not safe(url):raise ValueError('Refusing non-ICICI host')
    with httpx.Client(
        timeout=httpx.Timeout(30,read=60),follow_redirects=follow,
        headers={'User-Agent':'Mozilla/5.0','Accept':'*/*',
                 'Referer':'https://www.icicipruamc.com/'}) as client:
        r=client.get(url)
        print('ICICI_BLOB_HTTP url='+url+' follow='+str(follow).lower()+
              f' status={r.status_code} bytes={len(r.content)} content_type={r.headers.get("content-type","")}'+
              ' location='+str(r.headers.get('location') or '')+' final='+str(r.url),flush=True)
        return r

def main():
    try:
        old=probe(OLD,False)
        location=old.headers.get('location')
        if location and location.startswith('https://') and safe(location):
            try:probe(location,True)
            except Exception as exc:
                print('ICICI_REDIRECT_ERROR '+(str(exc) or type(exc).__name__).splitlines()[0][:700],flush=True)
    except Exception as exc:
        print('ICICI_OLD_ERROR '+(str(exc) or type(exc).__name__).splitlines()[0][:700],flush=True)
    for month,blob in BLOBS:
        try:
            r=probe(blob,True)
            print('ICICI_BLOB_MONTH '+month+' signature='+r.content[:32].hex(),flush=True)
            if r.status_code==200 and r.content.startswith(b'PK'):
                print('ICICI_BLOB_ZIP_OK month='+month+' bytes='+str(len(r.content)),flush=True)
                with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                    entries=z.infolist()
                    print(f'ICICI_ZIP_ENTRIES month={month} count={len(entries)} total_uncompressed={sum(x.file_size for x in entries)}',flush=True)
                    spreadsheets=[]
                    for entry in entries:
                        p=PurePosixPath(entry.filename)
                        member_safe=not (p.is_absolute() or '..' in p.parts or '\\' in entry.filename or entry.flag_bits&1)
                        if ('small' in entry.filename.lower() or 'icici prudential' in entry.filename.lower()):
                            print('ICICI_ZIP_MATCH month='+month+' member='+entry.filename+
                                  f' bytes={entry.file_size} safe={member_safe}',flush=True)
                        if member_safe and p.suffix.lower() in ('.xls','.xlsx') and 0<entry.file_size<=40*1024*1024:
                            spreadsheets.append(entry)
                    print(f'ICICI_ZIP_SPREADSHEETS month={month} count={len(spreadsheets)}',flush=True)
                    import openpyxl,xlrd
                    from tracker.portfolio_parser import parse_sheet
                    from tracker.icici_portfolios import FAMILY
                    for entry in spreadsheets:
                        if 'small' not in entry.filename.lower():continue
                        with z.open(entry) as fh:body=fh.read()
                        try:
                            if body.startswith(b'PK'):
                                book=openpyxl.load_workbook(io.BytesIO(body),read_only=True,data_only=True)
                                print('ICICI_WORKBOOK month='+month+' '+entry.filename+' sheets='+repr(book.sheetnames),flush=True)
                                for sh in book.worksheets:
                                    cells=list(sh.iter_rows())
                                    rows=[[c.value for c in row] for row in cells]
                                    formats=[[c.number_format or '' for c in row] for row in cells]
                                    parsed=parse_sheet(rows,formats,FAMILY)
                                    if parsed is not None:
                                        print('ICICI_PARSED month='+month+' member='+entry.filename+' sheet='+sh.title+
                                              ' day='+str(parsed.get('day'))+' complete='+str(parsed.get('complete'))+
                                              ' aum='+str(parsed.get('aum'))+' positions='+str(len(parsed.get('positions') or []))+
                                              ' weight='+str(sum(float(x.get('weight') or 0) for x in parsed.get('positions') or []))+
                                              ' unknown='+repr(parsed.get('unknown_rows')),flush=True)
                                        hi=None
                                        for i,row in enumerate(rows[:35]):
                                            vals=[str(v or '').lower() for v in row]
                                            if any('isin' in v for v in vals) and any('%' in v and ('nav' in v or 'aum' in v or ('net' in v and 'asset' in v)) for v in vals):
                                                hi=i;break
                                        if hi is not None:
                                            for ri,row in enumerate(rows[hi+1:],hi+2):
                                                text=' | '.join(str(x or '')[:120] for x in row[:12])
                                                if any(str(u) and str(u) in text for u in parsed.get('unknown_rows') or []):
                                                    print('ICICI_UNKNOWN_ROW month='+month+' row='+str(ri)+' '+text,flush=True)
                                            print('ICICI_TAIL month='+month+' '+repr([
                                                [str(x)[:140] if x is not None else '' for x in row[:12]]
                                                for row in rows[-30:]
                                            ]),flush=True)
                                book.close()
                            elif body.startswith(b'\xd0\xcf'):
                                book=xlrd.open_workbook(file_contents=body,on_demand=True)
                                print('ICICI_WORKBOOK month='+month+' '+entry.filename+' sheets='+repr(book.sheet_names()),flush=True)
                                book.release_resources()
                        except Exception as exc:
                            print('ICICI_WORKBOOK_ERROR month='+month+' '+entry.filename+' '+(str(exc) or type(exc).__name__).splitlines()[0][:500],flush=True)
        except Exception as exc:
            print('ICICI_BLOB_ERROR month='+month+' '+(str(exc) or type(exc).__name__).splitlines()[0][:700],flush=True)
if __name__=='__main__':main()
