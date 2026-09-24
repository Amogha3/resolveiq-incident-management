"""Isolated synthetic checkout service. Never connects to a real database."""
import os
import secrets
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Literal

app=FastAPI(title='ResolveIQ isolated checkout demo')
STATE='healthy'
TOKEN=os.environ.get('RESOLVEIQ_DEMO_TOKEN') or secrets.token_urlsafe(32)
class Mode(BaseModel): mode:Literal['healthy','database','memory']
@app.get('/health')
def health():
    if STATE=='database':return JSONResponse({'status':'down','log':'ERROR database ECONNREFUSED simulated checkout dependency'},status_code=503)
    if STATE=='memory':return JSONResponse({'status':'down','log':'FATAL heap out of memory in simulated export worker'},status_code=503)
    return {'status':'up','log':'INFO synthetic checkout completed status=200'}
@app.post('/control')
def control(body:Mode,x_demo_token:str=Header(default='')):
    global STATE
    if not secrets.compare_digest(x_demo_token,TOKEN):raise HTTPException(403,'Invalid demo control token')
    STATE=body.mode
    return {'mode':STATE}
