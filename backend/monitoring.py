"""Five-second real HTTP probes against a fixed localhost demo target."""
import asyncio
import os
import time
import httpx
from .storage import db,now,insert,event
from .analysis import redact
URL='http://127.0.0.1:8010'

def record_check(state,latency,status,detail):
    stamp=now()
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        monitor=dict(c.execute('SELECT * FROM monitors WHERE id=1').fetchone())
        if not monitor['enabled']: return
        c.execute('INSERT INTO checks(checked_at,state,latency_ms,http_status,detail) VALUES(?,?,?,?,?)',(stamp,state,round(latency,2),status,redact(detail)[:3000]))
        c.execute('DELETE FROM checks WHERE id NOT IN (SELECT id FROM checks ORDER BY id DESC LIMIT 720)')
        failures=monitor['failures']+1 if state=='Down' else 0
        iid=monitor['incident_id']
        linked=c.execute('SELECT * FROM incidents WHERE id=?',(iid,)).fetchone() if iid else None
        if state=='Down' and failures>=2:
            if not linked or linked['status']=='Resolved':
                iid=insert(c,{'title':'Live demo: checkout service unavailable','service':'checkout-demo','severity':'High',
                    'description':'Automatically created after two consecutive failed HTTP probes to the isolated local demo service.',
                    'logs':f'{stamp} {detail}'},True,'Monitor')
                c.execute('UPDATE incidents SET monitor_id=1 WHERE id=?',(iid,))
            elif failures==2:
                event(c,iid,'Service failed again; repeated HTTP probes confirm outage','Monitor')
            if iid:
                log=c.execute('SELECT logs FROM incidents WHERE id=?',(iid,)).fetchone()[0]
                line=f'{stamp} {redact(detail)}'
                # Keep the newest bounded evidence, not an unbounded log file.
                new='\n'.join((log+'\n'+line).splitlines()[-80:])[-100000:]
                c.execute('UPDATE incidents SET logs=?,updated_at=?,version=version+1 WHERE id=?',(new,stamp,iid))
        elif state=='Up' and monitor['last_state']=='Down' and linked and linked['status']!='Resolved':
            event(c,iid,'HTTP health probe recovered. Human resolution review is still required.','Monitor')
            c.execute('UPDATE incidents SET updated_at=?,version=version+1 WHERE id=?',(stamp,iid))
        c.execute('UPDATE monitors SET last_state=?,failures=?,incident_id=?,last_checked=? WHERE id=1',(state,failures,iid,stamp))

async def probe():
    begin=time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=2,trust_env=False,follow_redirects=False) as client:
            response=await client.get(URL+'/health')
        payload=response.json()
        state='Up' if response.status_code==200 and payload.get('status')=='up' else 'Down'
        record_check(state,(time.perf_counter()-begin)*1000,response.status_code,str(payload.get('log','Unexpected health response')))
    except (httpx.HTTPError,ValueError,AttributeError) as exc:
        record_check('Down',(time.perf_counter()-begin)*1000,None,'ERROR demo service unreachable: '+type(exc).__name__)
async def monitor_loop():
    while True:
        with db() as c: enabled=c.execute('SELECT enabled FROM monitors WHERE id=1').fetchone()[0]
        if enabled:
            await probe()
        await asyncio.sleep(5)
async def set_mode(mode):
    try:
        async with httpx.AsyncClient(timeout=3,trust_env=False,follow_redirects=False) as client:
            response=await client.post(URL+'/control',json={'mode':mode},headers={'X-Demo-Token':os.environ.get('RESOLVEIQ_DEMO_TOKEN','')})
        response.raise_for_status();return response.json()
    except httpx.HTTPError:
        from fastapi import HTTPException
        raise HTTPException(503,'Demo service is unavailable. Start both services using start_windows.bat or python run.py.')
