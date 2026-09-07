from __future__ import annotations
import argparse
import json
import os
import socket
import threading
import urllib.request
import webbrowser
from . import db


def main():
    parser=argparse.ArgumentParser(description='Smallcap Ledger local Windows app')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args()
    if not 1024<=args.port<=65535:parser.error('Choose a port from 1024 to 65535')
    url=f'http://127.0.0.1:{args.port}'
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url+'/api/health',timeout=2) as r:
            data=json.load(r)
            if data.get('app')=='smallcap-ledger':
                print('Smallcap Ledger is already running at '+url)
                if not args.no_browser:webbrowser.open(url)
                return
    except Exception:pass
    if not (db.DATA/'ledger.sqlite3').exists() and (db.ROOT/'bootstrap/manifest.json').is_file() and (not db.DATA.exists() or not any(db.DATA.iterdir())):
        from scripts.github_state import restore_seed
        print('Preparing the included historical data for the first launch…',flush=True)
        restore_seed(db.ROOT/'bootstrap',db.DATA)
    db.DATA.mkdir(parents=True,exist_ok=True)
    lock=(db.DATA/'running.lock').open('a+b')
    lock.seek(0);lock.write(b'1');lock.flush();lock.seek(0)
    try:
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:
        print('This data folder is already open in another tracker process. Close that process first.')
        return
    print('\nSmallcap Ledger\nOpen '+url+'\nKeep this window open for automatic updates.\nPress Ctrl+C to stop.\nData: '+str(db.DATA)+'\n')
    def open_when_ready():
        for _ in range(40):
            try:
                with opener.open(url+'/api/health',timeout=1) as r:
                    if r.status==200:webbrowser.open(url);return
            except Exception:threading.Event().wait(.5)
    if not args.no_browser:threading.Thread(target=open_when_ready,daemon=True).start()
    import uvicorn
    try:uvicorn.run('tracker.app:app',host='127.0.0.1',port=args.port,log_level='warning')
    finally:lock.close()


if __name__=='__main__':main()
