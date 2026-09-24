"""Start the isolated demo and authenticated workspace from one terminal."""
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parent

def main():
    os.chdir(ROOT)
    for port in (8000,8010):
        with socket.socket() as s:
            try:s.bind(('127.0.0.1',port))
            except OSError:
                print(f'Port {port} is already in use. Stop the previous ResolveIQ terminal with Ctrl+C and try again.');return 1
    env=os.environ.copy();env['RESOLVEIQ_DEMO_TOKEN']=secrets.token_urlsafe(32)
    env['PYTHONUNBUFFERED']='1'
    children=[]
    try:
        for module,port in [('backend.demo_service:app',8010),('backend.main:app',8000)]:
            children.append(subprocess.Popen([sys.executable,'-m','uvicorn',module,'--host','127.0.0.1','--port',str(port),'--no-access-log'],cwd=ROOT,env=env))
        print('\nResolveIQ v2: open http://127.0.0.1:8000 after startup.\nKeep this terminal open. Ctrl+C stops both services.\n',flush=True)
        while all(p.poll() is None for p in children):time.sleep(.5)
        print('A service stopped. See the error above.');return 1
    except KeyboardInterrupt:
        print('\nStopping ResolveIQ...');return 0
    finally:
        for p in children:
            if p.poll() is None:p.terminate()
        for p in children:
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill();p.wait()
if __name__=='__main__':sys.exit(main())
