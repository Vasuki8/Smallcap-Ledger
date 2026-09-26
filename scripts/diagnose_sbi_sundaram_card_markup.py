"""Read-only markup probe for current SBI/Sundaram communication cards."""
from pathlib import Path
import sys
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tracker import providers

TARGETS=(
 ("SBI","https://www.sbimf.com/","Monthly Presentation on Economy & Markets - July 2026"),
 ("SBI","https://www.sbimf.com/cio-desk","July 2026"),
 ("Sundaram","https://www.sundarammutual.com/","Outlook September 2026"),
 ("Sundaram","https://www.sundarammutual.com/knowledge-hub","Outlook September 2026"),
)

def main():
  for amc,url,needle in TARGETS:
    print("COMM7_START",amc,url,"needle="+needle,flush=True)
    try:
      providers.can_crawl(url)
      body,_,typ=providers.fetch(url,archive=False,max_bytes=12*1024*1024)
      soup=BeautifulSoup(body,"html.parser")
      txt=body.decode("utf-8","ignore")
      idx=txt.lower().find(needle.lower())
      print("COMM7_RAW_INDEX",amc,url,idx,flush=True)
      if idx>=0:
        print("COMM7_RAW_CONTEXT",amc,url,repr(txt[max(0,idx-3500):idx+7000]),flush=True)
      for node in soup.find_all(string=lambda x: x and needle.lower() in str(x).lower()):
        parent=node.parent
        for level in range(6):
          if parent is None:break
          print("COMM7_NODE",amc,url,"level="+str(level),
                repr(parent.get_text(" ",strip=True)[:1200]),
                repr(str(parent)[:9000]),flush=True)
          parent=parent.parent
          if level>=2 and ("href=" in str(parent) or "data-" in str(parent)):break
      for script in soup.find_all("script"):
        raw=(script.string or script.get_text() or "")
        if needle.lower() in raw.lower():
          i=raw.lower().find(needle.lower())
          print("COMM7_SCRIPT_CONTEXT",amc,url,
                repr(raw[max(0,i-4000):i+9000]),flush=True)
    except Exception as exc:
      print("COMM7_ERROR",amc,url,(str(exc) or type(exc).__name__).splitlines()[0][:1200],flush=True)

if __name__=="__main__":main()
