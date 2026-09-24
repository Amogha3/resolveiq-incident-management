"""Local accounts, scrypt password hashes, expiring server-side sessions, CSRF."""
import hashlib
import hmac
import os
import re
import secrets
import time
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from .storage import db, now, audit

router=APIRouter(prefix='/api')
SETUP_CODE=secrets.token_urlsafe(18)
COOKIE='resolveiq_session'
SECURE_COOKIE=os.environ.get('RESOLVEIQ_COOKIE_SECURE')=='1'
DUMMY_SALT='00000000000000000000000000000000'

def digest(token): return hashlib.sha256(token.encode()).hexdigest()
def password_hash(password,salt=None):
    salt=salt or secrets.token_hex(16)
    value=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=32768,r=8,p=3,maxmem=67108864).hex()
    return f'scrypt${salt}${value}'
def verify(password,encoded):
    try:
        _,salt,_=encoded.split('$')
        return hmac.compare_digest(password_hash(password,salt),encoded)
    except (ValueError,TypeError): return False

def public(user): return {k:user[k] for k in ('id','name','username','role','active')}
def current(request:Request):
    token=request.cookies.get(COOKIE,'')
    with db() as c:
        row=c.execute('''SELECT users.*,sessions.csrf FROM sessions JOIN users ON users.id=sessions.user_id
            WHERE token_hash=? AND expires>? AND active=1''',(digest(token),time.time())).fetchone()
    if not row: raise HTTPException(401,'Please sign in again.')
    if request.method not in ('GET','HEAD','OPTIONS'):
        if not hmac.compare_digest(request.headers.get('X-CSRF-Token',''),row['csrf']):
            raise HTTPException(403,'Session verification failed. Refresh the page and retry.')
    return dict(row)
def editor(user=Depends(current)):
    if user['role'] not in ('Admin','Engineer'): raise HTTPException(403,'An Admin or Engineer account is required.')
    return user
def admin(user=Depends(current)):
    if user['role']!='Admin': raise HTTPException(403,'An Admin account is required.')
    return user

def limit(key,max_attempts=8):
    t=time.time()
    with db() as c:
        c.execute('DELETE FROM login_limits WHERE window_start<?',(t-900,))
        row=c.execute('SELECT * FROM login_limits WHERE key=?',(key,)).fetchone()
        if row and row['attempts']>=max_attempts: raise HTTPException(429,'Too many attempts. Try again after 15 minutes.')
        c.execute('''INSERT INTO login_limits VALUES(?,1,?) ON CONFLICT(key) DO UPDATE SET attempts=attempts+1''',(key,t))

def session(c,user,response):
    token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(32)
    c.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
    c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(digest(token),user['id'],csrf,time.time()+28800))
    response.set_cookie(COOKIE,token,httponly=True,samesite='strict',secure=SECURE_COOKIE,max_age=28800,path='/')
    return {'user':public(user),'csrf':csrf}

class Account(BaseModel):
    name:str=Field(min_length=2,max_length=80)
    username:str=Field(min_length=3,max_length=40)
    password:str=Field(min_length=15,max_length=128)
    @field_validator('username')
    @classmethod
    def username_check(cls,v):
        v=v.lower().strip()
        if not re.fullmatch(r'[a-z0-9_.-]{3,40}',v): raise ValueError('Use 3–40 letters, numbers, dots, dashes, or underscores.')
        return v
    @field_validator('name')
    @classmethod
    def name_check(cls,v):
        if len(v.strip())<2: raise ValueError('Enter a name.')
        return v.strip()
class Setup(Account): code:str=Field(max_length=100)
class Login(BaseModel):
    username:str=Field(min_length=1,max_length=40)
    password:str=Field(min_length=1,max_length=128)

@router.get('/auth/status')
def auth_status():
    with db() as c: needed=c.execute('SELECT COUNT(*) FROM users').fetchone()[0]==0
    return {'setup_required':needed}
@router.post('/auth/setup',status_code=201)
def setup(body:Setup,response:Response,request:Request):
    limit('setup:'+str(request.client.host))
    if not hmac.compare_digest(body.code,SETUP_CODE): raise HTTPException(403,'Setup code does not match. Open SETUP_CODE.txt in the project folder and copy the code on its second line. Reopen the file if you restarted the server.')
    hashed=password_hash(body.password)
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        if c.execute('SELECT COUNT(*) FROM users').fetchone()[0]: raise HTTPException(409,'Setup is already complete. Sign in instead.')
        uid=c.execute("INSERT INTO users(name,username,password_hash,role,created_at) VALUES(?,?,?,'Admin',?)",(body.name,body.username,hashed,now())).lastrowid
        user=dict(c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone())
        audit(c,body.username,'Workspace administrator created')
        return session(c,user,response)
@router.post('/auth/login')
def login(body:Login,response:Response,request:Request):
    limit('login:'+str(request.client.host),max_attempts=30)
    name=body.username.lower().strip(); limit('account:'+name)
    with db() as c:
        user=c.execute('SELECT * FROM users WHERE username=?',(name,)).fetchone()
        encoded=user['password_hash'] if user else password_hash('dummy value',DUMMY_SALT)
        valid=verify(body.password,encoded)
        if not user or not valid or not user['active']: raise HTTPException(401,'Incorrect username or password.')
        c.execute('DELETE FROM login_limits WHERE key=?',('account:'+name,))
        audit(c,name,'Signed in')
        return session(c,dict(user),response)
@router.get('/auth/me')
def me(user=Depends(current)): return {'user':public(user),'csrf':user['csrf']}
@router.post('/auth/logout')
def logout(request:Request,response:Response,user=Depends(current)):
    with db() as c:
        c.execute('DELETE FROM sessions WHERE token_hash=?',(digest(request.cookies.get(COOKIE,'')),))
        audit(c,user['username'],'Signed out')
    response.delete_cookie(COOKIE,path='/');return {'ok':True}
class PasswordChange(BaseModel):
    current_password:str=Field(min_length=1,max_length=128)
    new_password:str=Field(min_length=15,max_length=128)
@router.post('/auth/password')
def change_password(body:PasswordChange,response:Response,user=Depends(current)):
    limit('password:'+str(user['id']))
    if not verify(body.current_password,user['password_hash']): raise HTTPException(400,'Current password does not match.')
    with db() as c:
        c.execute('UPDATE users SET password_hash=? WHERE id=?',(password_hash(body.new_password),user['id']))
        c.execute('DELETE FROM sessions WHERE user_id=?',(user['id'],));audit(c,user['username'],'Password changed; all previous sessions revoked')
        return session(c,user,response)
