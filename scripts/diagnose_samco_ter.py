"""Follow observed AMFI pagination and inspect the public Samco page contract."""
import hashlib,json,re
from datetime import datetime,timezone
from urllib.parse import urlencode
import httpx
from bs4 import BeautifulSoup

def main():
    result={'observed_at':datetime.now(timezone.utc).isoformat(),'mode':'read_only','attempts':[]}
    with httpx.Client(timeout=30,follow_redirects=True,headers={'User-Agent':'Mozilla/5.0'}) as client:
        def read(url):
            response=client.get(url);response.raise_for_status()
            if len(response.content)>2*1024*1024:raise ValueError('oversized response')
            entry={'source':url,'sha256':hashlib.sha256(response.content).hexdigest(),'bytes':len(response.content)}
            result['attempts'].append(entry)
            return response.content,entry
        for page in (2,3):
            url='https://www.amfiindia.com/api/populate-te-rdata-revised?'+urlencode({'MF_ID':'74','Month':'09-2026','strCat':'-1','strType':'1','page':page,'pageSize':1000})
            try:
                raw,entry=read(url);obj=json.loads(raw);rows=obj['data']
                entry['meta']=obj.get('meta');entry['scheme_categories']=sorted(set((r.get('Scheme_Name'),r.get('SchemeCat_Desc')) for r in rows))
                target=[r for r in rows if re.sub('[^a-z0-9]','',str(r.get('Scheme_Name','')).lower())=='samcomidcapfund']
                entry['exact_midcap_rows']=sorted(target,key=lambda r:r.get('TER_Date',''))[-3:]
            except Exception as exc:result['attempts'].append({'source':url,'error':str(exc)[:200]})
        raw,entry=read('https://www.samcomf.com/total-expense-ratio')
        soup=BeautifulSoup(raw,'html.parser')
        entry['midcap_elements']=[str(t)[:2500] for t in soup.select('[data-scheme], [data-scheme-code], input, button') if re.search('mid|export|scheme',str(t),re.I)][:20]
        scripts='\n'.join(s.get_text() for s in soup.select('script:not([src])'))
        pattern=r'\$\.ajax|url\s*:|fetch\(|loadTer|terData|terList|exportTer|downloadTer|data-scheme'
        entry['contract_hints']=[scripts[max(0,m.start()-200):m.end()+550] for m in list(re.finditer(pattern,scripts,re.I))[:35]]
    print('SAMCO_DIAGNOSTIC_BEGIN');print(json.dumps(result,indent=2,ensure_ascii=False));print('SAMCO_DIAGNOSTIC_END')
if __name__=='__main__':main()
