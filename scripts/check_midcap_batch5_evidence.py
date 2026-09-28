"""Inspect batch-5 public evidence without restoring or writing production data."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bs4 import BeautifulSoup
from tracker import providers
from tracker.midcap_portfolio_batch5 import KOTAK_URL, MAHINDRA_URL, SUNDARAM_CARD


def main():
    report = {"production_writes": 0, "public_export_enabled": False, "sources": []}
    for label, url in (("Mahindra", MAHINDRA_URL), ("Sundaram", SUNDARAM_CARD), ("Kotak", KOTAK_URL)):
        item = {"label": label, "source": url}
        try:
            body, _, media = providers.fetch(url, archive=False, max_bytes=12 * 1024 * 1024)
            item.update(bytes=len(body), content_type=media, sha256=hashlib.sha256(body).hexdigest())
            if label == "Sundaram":
                rows = json.loads(body)
                item["scheme_rows"] = [r for r in rows if re.sub(r"[^a-z0-9]", "", str(r.get("GROUP_NAME", "")).lower()) == "sundarammidcapfund"]
            else:
                soup = BeautifulSoup(body, "html.parser")
                item["headings"] = [x.get_text(" ", strip=True) for x in soup.select("h1,h2,h3")][:12]
                item["text_start"] = soup.get_text(" ", strip=True)[:300]
                item["tables"] = []
                for table in soup.find_all("table"):
                    text = table.get_text(" ", strip=True)
                    if not re.search(r"Company\s*/\s*Issuer|Issuer/Instrument", text, re.I):
                        continue
                    selected = []
                    for tr in table.find_all("tr"):
                        cells = tr.find_all(["th", "td"], recursive=False)
                        values = [c.get_text(" ", strip=True) for c in cells]
                        selected.append({"values": values, "row_attrs": tr.attrs,
                                         "cell_attrs": [c.attrs for c in cells],
                                         "emphasis": [bool(c.find(["b", "strong"])) for c in cells]})
                    item["tables"].append(selected[:40])
                item["tables"] = item["tables"][:2]
        except Exception as exc:
            item["error"] = str(exc)[:500]
        report["sources"].append(item)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
