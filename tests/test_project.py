import sqlite3
import time
import pytest
from fastapi.testclient import TestClient
from backend import main,storage,auth,monitoring
from backend.analysis import analyze,redact,retrieve

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(storage,'DB_PATH',tmp_path/'test.db')
    monkeypatch.setenv('RESOLVEIQ_MONITOR_ENABLED','0')
    with TestClient(main.app) as c:
        response=c.post('/api/auth/setup',json={'name':'Test Admin','username':'admin','password':'a long test password 123','code':auth.SETUP_CODE})
        assert response.status_code==201,response.text
        c.headers['X-CSRF-Token']=response.json()['csrf']
        yield c

def add(client,role,name):
    r=client.post('/api/team',json={'name':name,'username':name.lower(),'password':'another long password 123','role':role})
    assert r.status_code==201,r.text
    return r.json()
def sign_in(client,name):
    r=client.post('/api/auth/login',json={'username':name.lower(),'password':'another long password 123'})
    assert r.status_code==200,r.text
    client.headers['X-CSRF-Token']=r.json()['csrf']

def update_body(client,iid,**kwargs):
    d=client.get(f'/api/incidents/{iid}').json()
    return {'version':d['version'],'status':d['status'],'resolution':d['resolution'],'assignee_id':d['assignee_id']}|kwargs

@pytest.mark.parametrize('message,family',[('ERROR ECONNREFUSED','database'),('FATAL heap out of memory','memory'),('ERROR upstream timed out','timeout'),('ERROR Unauthorized token expired','auth'),('ERROR ENOSPC No space left on device','disk')])
def test_rule_evidence(message,family):
    f=analyze('INFO starting\n'+message)['findings'][0]
    assert f['id']==family and f['evidence'][0]=={'line':2,'text':message}
def test_unknown():
    result=analyze('ERROR unknown failure xyz');assert result['findings']==[] and 'does not mean' in result['summary']
def test_redaction():
    text=redact('password=secret123 api_key=private123 Bearer abc.def.ghi')
    assert all(s not in text for s in ['secret123','private123','abc.def.ghi'])

def test_full_incident_workflow(client):
    engineer=add(client,'Engineer','Engineer')
    item=client.post('/api/incidents',json={'title':'Checkout incident','service':'checkout-api','logs':'ERROR ECONNREFUSED password=secret123'}).json()
    iid=item['id'];assert 'secret123' not in item['logs']
    d=client.get(f'/api/incidents/{iid}').json();assert d['similar'][0]['id']==2
    body=update_body(client,iid,status='Resolved')
    assert client.put(f'/api/incidents/{iid}',json=body).status_code==422
    body=update_body(client,iid,status='Investigating',assignee_id=engineer['id'])
    assert client.put(f'/api/incidents/{iid}',json=body).status_code==200
    assert client.put(f'/api/incidents/{iid}',json=body).status_code==409  # stale edit
    v=client.get(f'/api/incidents/{iid}').json()['version']
    assert client.put(f'/api/incidents/{iid}/logs',json={'version':v,'logs':'INFO recovered'}).status_code==200
    assert client.put(f'/api/incidents/{iid}',json=update_body(client,iid,status='Resolved',resolution='Synthetic test: verified successful recovery.')).status_code==200
    exported=client.get(f'/api/incidents/{iid}/export').json()
    assert exported['status']=='Resolved' and exported['analysis']['findings']==[]
    assert len(exported['events'])==4
    with storage.db() as c:assert c.execute('SELECT assignee_id FROM incidents WHERE id=?',(iid,)).fetchone()[0]==engineer['id']

def test_auth_required_logout_csrf_origin(client):
    client.headers.pop('X-CSRF-Token')
    assert client.post('/api/incidents',json={'title':'Blocked','service':'api'}).status_code==403
    csrf=client.get('/api/auth/me').json()['csrf'];client.headers['X-CSRF-Token']=csrf
    assert client.post('/api/incidents',json={'title':'Blocked','service':'api'},headers={'Origin':'https://evil.example'}).status_code==403
    assert client.post('/api/auth/logout',json={}).status_code==200
    for path in ['/api/incidents','/api/incidents/1','/api/incidents/1/export','/api/team','/api/monitor']:
        assert client.get(path).status_code==401

def test_viewer_permissions(client):
    add(client,'Viewer','Viewer');sign_in(client,'Viewer')
    assert client.get('/api/incidents').status_code==200
    assert client.get('/api/incidents/1/export').status_code==200
    assert client.post('/api/incidents',json={'title':'Blocked','service':'api'}).status_code==403
    assert client.put('/api/incidents/1',json=update_body(client,1,status='Investigating')).status_code==403
    assert client.put('/api/incidents/1/logs',json={'version':1,'logs':'ERROR'}).status_code==403
    assert client.post('/api/team',json={'name':'New User','username':'newuser','password':'password long enough','role':'Admin'}).status_code==403
    assert client.post('/api/monitor/scenario',json={'mode':'database'}).status_code==403
    assert client.get('/api/audit').status_code==403

def test_engineer_permissions(client):
    add(client,'Engineer','Engineer');sign_in(client,'Engineer')
    assert client.post('/api/incidents',json={'title':'Allowed incident','service':'api'}).status_code==201
    assert client.put('/api/monitor',json={'enabled':False}).status_code==403
    assert client.get('/api/audit').status_code==403

def test_deactivation_revokes_sessions(client):
    member=add(client,'Engineer','Engineer')
    admin_cookie=client.cookies.get(auth.COOKIE);admin_csrf=client.headers['X-CSRF-Token']
    sign_in(client,'Engineer');member_cookie=client.cookies.get(auth.COOKIE)
    client.cookies.clear();client.cookies.set(auth.COOKIE,admin_cookie);client.headers['X-CSRF-Token']=admin_csrf
    assert client.put('/api/team/'+str(member['id']),json={'role':'Engineer','active':False}).status_code==200
    client.cookies.clear();client.cookies.set(auth.COOKIE,member_cookie)
    assert client.get('/api/auth/me').status_code==401

def test_password_change_and_expiry(client):
    old=client.cookies.get(auth.COOKIE)
    r=client.post('/api/auth/password',json={'current_password':'a long test password 123','new_password':'a different long phrase 456'})
    assert r.status_code==200
    assert old!=client.cookies.get(auth.COOKIE)
    with storage.db() as c:
        assert not c.execute('SELECT 1 FROM sessions WHERE token_hash=?',(auth.digest(old),)).fetchone()
        stored=c.execute('SELECT password_hash FROM users WHERE id=1').fetchone()[0]
        assert 'a different' not in stored and stored.startswith('scrypt$')
        c.execute('UPDATE sessions SET expires=?',(time.time()-1,))
    assert client.get('/api/auth/me').status_code==401

def test_login_throttle_and_setup_closed(client):
    assert client.post('/api/auth/setup',json={'name':'Other Admin','username':'other','password':'long enough password','code':auth.SETUP_CODE}).status_code==409
    for _ in range(8):assert client.post('/api/auth/login',json={'username':'admin','password':'wrong'}).status_code==401
    assert client.post('/api/auth/login',json={'username':'admin','password':'wrong'}).status_code==429

def test_monitor_dedup_recovery_and_closure(client):
    monitoring.record_check('Down',3,503,'ERROR database ECONNREFUSED')
    assert len(client.get('/api/incidents').json())==8
    monitoring.record_check('Down',4,503,'ERROR database ECONNREFUSED')
    monitoring.record_check('Down',4,503,'ERROR database ECONNREFUSED')
    assert len(client.get('/api/incidents').json())==9
    iid=client.get('/api/monitor').json()['incident_id']
    assert client.put(f'/api/incidents/{iid}',json=update_body(client,iid,status='Resolved',resolution='Test recovery verified.')).status_code==409
    assert client.put(f'/api/incidents/{iid}/logs',json={'version':client.get(f'/api/incidents/{iid}').json()['version'],'logs':'replace'}).status_code==409
    monitoring.record_check('Up',2,200,'INFO synthetic checkout completed')
    result=client.get(f'/api/incidents/{iid}').json()
    assert result['status']=='Open' and any('recovered' in e['message'] for e in result['events'])
    assert client.put(f'/api/incidents/{iid}',json=update_body(client,iid,status='Resolved',resolution='Verified a successful HTTP probe on the demo service.')).status_code==200
    monitoring.record_check('Down',3,503,'ERROR database ECONNREFUSED');monitoring.record_check('Down',3,503,'ERROR database ECONNREFUSED')
    assert len(client.get('/api/incidents').json())==10

def test_pause_retention(client):
    assert client.put('/api/monitor',json={'enabled':False}).status_code==200
    monitoring.record_check('Down',3,None,'Offline')
    assert client.get('/api/monitor').json()['sample_count']==0
    assert client.put('/api/monitor',json={'enabled':True}).status_code==200
    with storage.db() as c:
        c.executemany("INSERT INTO checks(checked_at,state,latency_ms,http_status,detail) VALUES(?,'Up',1,200,'ok')",[(storage.now(),)]*725)
    monitoring.record_check('Up',1,200,'ok')
    assert client.get('/api/monitor').json()['sample_count']==720

def test_validation_static_and_retrieval(client):
    assert client.get('/').status_code==200
    assert client.get('/api/incidents/99999').status_code==404
    assert client.post('/api/incidents',json={'title':'   ','service':'api'}).status_code==422
    assert client.put('/api/incidents/1/logs',json={'version':1,'logs':'x'*100001}).status_code==422
    assert client.put('/api/incidents/1/logs',json={'version':1,'logs':'x'*550001}).status_code==413
    assert client.get('/api/incidents').headers['cache-control']=='no-store'
    assert client.get('/api/health',headers={'host':'evil.example'}).status_code==400
    result=client.get('/api/incidents/2').json()
    assert 2 not in [x['id'] for x in result['similar']]
    for item in result['similar']:assert client.get('/api/incidents/'+str(item['id'])).json()['status']=='Resolved'

def test_ai_disabled(client,monkeypatch):
    monkeypatch.delenv('RESOLVEIQ_AI',raising=False)
    assert client.post('/api/incidents/1/explain',json={}).status_code==503

def test_ai_adapter_contract(client,monkeypatch):
    monkeypatch.setenv('RESOLVEIQ_AI','1')
    class Reply:
        def raise_for_status(self):pass
        def json(self):return {'message':{'content':'[L2] Connection refused; check the configured port.'}}
    class FakeClient:
        def __init__(self,**kwargs):assert kwargs['trust_env'] is False
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,url,**kwargs):
            assert url=='http://127.0.0.1:11434/api/chat'
            assert kwargs['json']['stream'] is False
            return Reply()
    monkeypatch.setattr(main.httpx,'AsyncClient',FakeClient)
    r=client.post('/api/incidents/1/explain',json={})
    assert r.status_code==200 and r.json()['evidence_lines']==[2]

def test_v1_migration_preserves_data(tmp_path,monkeypatch):
    path=tmp_path/'legacy.db';monkeypatch.setattr(storage,'DB_PATH',path)
    c=sqlite3.connect(path)
    c.executescript('''CREATE TABLE incidents(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,service TEXT NOT NULL,severity TEXT NOT NULL,status TEXT NOT NULL,description TEXT NOT NULL,logs TEXT NOT NULL,resolution TEXT NOT NULL,is_demo INTEGER NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
      CREATE TABLE events(id INTEGER PRIMARY KEY AUTOINCREMENT,incident_id INTEGER NOT NULL,created_at TEXT NOT NULL,message TEXT NOT NULL);
      CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT);
      INSERT INTO metadata VALUES('seeded','true');
      INSERT INTO incidents VALUES(42,'My incident','my-api','High','Investigating','Saved description','ERROR memory','Saved note',0,'2026-09-24','2026-09-24');
      INSERT INTO events VALUES(1,42,'2026-09-24','Existing history');''');c.commit();c.close()
    storage.initialize();storage.initialize()
    with storage.db() as c:
        row=dict(c.execute('SELECT * FROM incidents WHERE id=42').fetchone())
        assert row['resolution']=='Saved note' and row['version']==1
        assert c.execute('SELECT COUNT(*) FROM incidents').fetchone()[0]==1
        assert c.execute('SELECT message FROM events').fetchone()[0]=='Existing history'

def test_first_setup_guidance_and_login(tmp_path,monkeypatch):
    monkeypatch.setattr(storage,'DB_PATH',tmp_path/'test.db')
    monkeypatch.setattr(main,'ROOT',tmp_path)
    monkeypatch.setenv('RESOLVEIQ_MONITOR_ENABLED','0')
    body={'name':'Amogha C V','username':'amogha_cv','password':'test-only long passphrase 456','code':'1929'}
    with TestClient(main.app) as c:
        actual=(tmp_path/'SETUP_CODE.txt').read_text().splitlines()[1]
        assert actual==auth.SETUP_CODE and actual!='1929'
        assert c.post('/api/auth/setup',json=body|{'username':'amogha@example.com'}).status_code==422
        assert c.post('/api/auth/setup',json=body).status_code==403
        r=c.post('/api/auth/setup',json=body|{'code':actual})
        assert r.status_code==201,r.text
        assert c.get('/api/incidents').status_code==200
        c.headers['X-CSRF-Token']=r.json()['csrf']
        assert c.post('/api/auth/logout',json={}).status_code==200
        assert c.post('/api/auth/login',json=body).status_code==200
    with TestClient(main.app) as c:
        assert not (tmp_path/'SETUP_CODE.txt').exists()
        assert not c.get('/api/auth/status').json()['setup_required']
        assert c.post('/api/auth/login',json=body).status_code==200

def test_setup_throttle_expires(tmp_path,monkeypatch):
    monkeypatch.setattr(storage,'DB_PATH',tmp_path/'test.db')
    monkeypatch.setattr(main,'ROOT',tmp_path)
    monkeypatch.setenv('RESOLVEIQ_MONITOR_ENABLED','0')
    body={'name':'Test User','username':'testuser','password':'test-only long passphrase','code':'incorrect'}
    with TestClient(main.app) as c:
        for _ in range(8):assert c.post('/api/auth/setup',json=body).status_code==403
        assert c.post('/api/auth/setup',json=body|{'code':auth.SETUP_CODE}).status_code==429
        with storage.db() as con:con.execute('UPDATE login_limits SET window_start=?',(time.time()-901,))
        assert c.post('/api/auth/setup',json=body|{'code':auth.SETUP_CODE}).status_code==201
