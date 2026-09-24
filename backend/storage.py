"""SQLite persistence with additive v1 -> v2 migration."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import os
import sqlite3
from .analysis import redact
from .seed import SAMPLES

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get('RESOLVEIQ_DB', str(ROOT/'data'/'resolveiq.db')))
def now():
    return datetime.now(timezone.utc).isoformat()
@contextmanager
def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=15)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()
def event(c, iid, text, actor='System'):
    c.execute('INSERT INTO events(incident_id,created_at,message) VALUES (?,?,?)', (iid,now(),f'{actor}: {text}'))
def audit(c, actor, action):
    c.execute('INSERT INTO audit(actor,action,created_at) VALUES (?,?,?)',(actor,action,now()))
def insert(c,item,demo=False,actor='System'):
    stamp=now()
    q=c.execute('''INSERT INTO incidents(title,service,severity,status,description,logs,resolution,is_demo,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)''',
        (redact(item['title']),item['service'],item['severity'],item.get('status','Open'),redact(item.get('description','')),
         redact(item.get('logs','')),redact(item.get('resolution','')),int(demo),stamp,stamp))
    event(c,q.lastrowid,'Synthetic sample loaded' if demo else 'Incident created',actor)
    return q.lastrowid

def initialize():
    with db() as c:
        c.execute('PRAGMA journal_mode=WAL')
        c.executescript('''
        CREATE TABLE IF NOT EXISTS incidents(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,service TEXT NOT NULL,
          severity TEXT NOT NULL,status TEXT NOT NULL,description TEXT NOT NULL,logs TEXT NOT NULL DEFAULT '',
          resolution TEXT NOT NULL DEFAULT '',is_demo INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,incident_id INTEGER NOT NULL REFERENCES incidents(id),created_at TEXT NOT NULL,message TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT);
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,username TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('Admin','Engineer','Viewer')),active INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),csrf TEXT NOT NULL,expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS login_limits(key TEXT PRIMARY KEY,attempts INTEGER NOT NULL,window_start REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,actor TEXT NOT NULL,action TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS monitors(id INTEGER PRIMARY KEY CHECK(id=1),name TEXT NOT NULL,enabled INTEGER NOT NULL DEFAULT 1,
          last_state TEXT NOT NULL DEFAULT 'Unknown',failures INTEGER NOT NULL DEFAULT 0,incident_id INTEGER REFERENCES incidents(id),last_checked TEXT);
        CREATE TABLE IF NOT EXISTS checks(id INTEGER PRIMARY KEY AUTOINCREMENT,checked_at TEXT NOT NULL,state TEXT NOT NULL,
          latency_ms REAL NOT NULL,http_status INTEGER,detail TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
        CREATE INDEX IF NOT EXISTS idx_events_incident ON events(incident_id,id);
        CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions(expires);
        ''')
        columns={r['name'] for r in c.execute('PRAGMA table_info(incidents)')}
        for name,definition in [('assignee_id','INTEGER REFERENCES users(id)'),('version','INTEGER NOT NULL DEFAULT 1'),('monitor_id','INTEGER')]:
            if name not in columns:
                c.execute(f'ALTER TABLE incidents ADD COLUMN {name} {definition}')
        if not c.execute("SELECT 1 FROM metadata WHERE key='seeded'").fetchone():
            for sample in SAMPLES: insert(c,sample,True)
            c.execute("INSERT INTO metadata VALUES('seeded','true')")
        c.execute("INSERT OR IGNORE INTO monitors(id,name) VALUES(1,'Checkout demo service')")
        c.execute("INSERT OR REPLACE INTO metadata VALUES('schema_version','2')")
