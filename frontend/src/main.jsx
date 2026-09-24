import React, {useEffect, useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {Activity, ArrowLeft, ArrowUpRight, Check, CheckCircle2, ChevronRight, CircleHelp, Clock3, Download, FileText, Layers3, LoaderCircle, Plus, Search, ShieldCheck, Terminal, Upload, X, Zap} from 'lucide-react';
import './styles.css';
import {api} from './api';
import Account from './Account';
import {Monitoring,Team,AIExplanation} from './Advanced';

const ICONS = {Open: Clock3, Investigating: Activity, Resolved: CheckCircle2};
const code = id => `INC-${String(id).padStart(3,'0')}`;
const date = value => new Date(value).toLocaleString([], {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'});
function Badge({children, type=''}) { return <span className={'badge '+String(type||children).toLowerCase()}>{children}</span> }

function App({user,onLogout}){
  const canEdit=user.role!=="Viewer";
  const [members,setMembers]=useState([]),[assignee,setAssignee]=useState("");
  useEffect(()=>{api("/team").then(setMembers).catch(e=>setError(e.message))},[]);
  const [items,setItems]=useState([]), [detail,setDetail]=useState(null), [selected,setSelected]=useState(null);
  const [query,setQuery]=useState(''), [view,setView]=useState('All incidents'), [filter,setFilter]=useState('All statuses');
  const [loading,setLoading]=useState(true), [busy,setBusy]=useState(false), [error,setError]=useState(''), [toast,setToast]=useState('');
  const [showCreate,setShowCreate]=useState(false), [showHelp,setShowHelp]=useState(false), [tab,setTab]=useState('Investigation');
  const [logs,setLogs]=useState(''), [status,setStatus]=useState(''), [resolution,setResolution]=useState('');
  const detailRequest=useRef(0), fileRef=useRef(null);
  const toastTimer=useRef();
  function notify(message){setToast(message); clearTimeout(toastTimer.current); toastTimer.current=setTimeout(()=>setToast(''),4000)}
  async function refresh(){const data=await api('/incidents');setItems(data)}
  useEffect(()=>{refresh().catch(e=>setError(e.message)).finally(()=>setLoading(false)); return ()=>clearTimeout(toastTimer.current)},[]);
  useEffect(()=>{const timer=setInterval(()=>refresh().catch(()=>{}),10000);refresh().catch(()=>{});return()=>clearInterval(timer)},[view]);
  async function open(id){
    const request=++detailRequest.current; setSelected(id);setDetail(null);setError('');setTab('Investigation');
    try{ const d=await api('/incidents/'+id);if(request===detailRequest.current){setDetail(d);setLogs(d.logs);setStatus(d.status);setResolution(d.resolution);setAssignee(d.assignee_id||'')} }
    catch(e){if(request===detailRequest.current)setError(e.message)}
  }
  function back(){++detailRequest.current;setSelected(null);setDetail(null);setError('')}
  async function save(kind){
    setBusy(true);setError('');
    try {
      await api(`/incidents/${detail.id}${kind==='logs'?'/logs':''}`,{method:'PUT',body:JSON.stringify(kind==='logs'?{logs,version:detail.version}:{status,resolution,assignee_id:assignee?Number(assignee):null,version:detail.version})});
      const d=await api('/incidents/'+detail.id);setDetail(d);setLogs(d.logs);setStatus(d.status);setResolution(d.resolution);setAssignee(d.assignee_id||'');await refresh();
      notify(kind==='logs'?'Evidence saved and analysis updated':'Incident updated');if(kind==='logs')setTab('Investigation');
    }catch(e){setError(e.message)}finally{setBusy(false)}
  }
  async function readFile(e){
    const file=e.target.files?.[0];if(!file)return;
    try{if(file.size>100000)throw new Error('Choose a UTF-8 text log smaller than 100 KB.');const text=await file.text();if(text.includes('\u0000'))throw new Error('This appears to be a binary file. Choose a text log.');setLogs(text);notify('Log loaded. Select Save & analyze to attach it.')}catch(e){setError(e.message)}finally{e.target.value=''}
  }
  const stats={open:items.filter(x=>x.status!=='Resolved').length,critical:items.filter(x=>x.severity==='Critical'&&x.status!=='Resolved').length,resolved:items.filter(x=>x.status==='Resolved').length};
  const filtered=items.filter(x=>(view!=='Resolution library'||x.status==='Resolved')&&(filter==='All statuses'||x.status===filter)&&`${x.title} ${x.service} ${code(x.id)}`.toLowerCase().includes(query.toLowerCase()));
  return <div className="app">
    <aside className="sidebar">
      <a href="#" className="brand" onClick={e=>{e.preventDefault();back();setView('All incidents')}}><span className="brand-icon"><Activity size={23}/></span>Resolve<span className="brand-iq">IQ</span></a>
      <div className="workspace-label">ENGINEERING WORKSPACE</div>
      <nav aria-label="Main navigation">{[['All incidents',Layers3],['Resolution library',ShieldCheck],['Live monitoring',Activity],['Team & access',ShieldCheck]].map(([label,Icon])=><button key={label} className={'nav-item '+(view===label?'active':'')} onClick={()=>{back();setView(label);setFilter('All statuses');setQuery('')}}><Icon size={19}/>{label}{label==='All incidents'&&<span className="nav-count">{items.length}</span>}</button>)}</nav>
      <div className="sidebar-card"><span className="small-icon"><Terminal size={19}/></span><strong>Evidence before action.</strong><p>Investigate the signal. Verify the fix. Keep what you learn.</p><button onClick={()=>setShowHelp(true)}>How it works <ArrowUpRight size={15}/></button></div>
      <div className="profile"><div className="avatar">{user.name.slice(0,2).toUpperCase()}</div><div><strong>{user.name}</strong><span>{user.role}</span></div><button className="signout" onClick={onLogout}>Sign out</button></div>
    </aside>
    <main>
      <header className="topbar"><div className="breadcrumb">Workspace <ChevronRight size={14}/><strong>{selected?code(selected):view}</strong></div><button className="help" onClick={()=>setShowHelp(true)}><CircleHelp size={18}/><span>Project guide</span></button></header>
      <div className="content">
        <div className="demo-notice"><span className="demo-dot"/> Demo workspace <span className="notice-separator">/</span><span>Sample incidents are synthetic. New incidents stay on your machine.</span></div>
        {error&&<div role="alert" className="error">{error}<button aria-label="Dismiss error" onClick={()=>setError('')}><X size={17}/></button></div>}
        {selected===null&&view==='Live monitoring'?<Monitoring user={user} onOpen={open}/>:selected===null&&view==='Team & access'?<Team user={user}/>:selected===null?<>
          <div className="page-heading"><div><div className="eyebrow">OBSERVE · INVESTIGATE · RESOLVE</div><h1>{view==='Resolution library'?'Past fixes. Future answers.':'Incident command center'}</h1><p>{view==='Resolution library'?'Search documented resolutions and reuse what worked.':'Turn application errors into a clear next step.'}</p></div><button className="primary" disabled={!canEdit} onClick={()=>setShowCreate(true)}><Plus size={18}/>New incident</button></div>
          <div className="stats"><Stat label="Active incidents" value={stats.open} icon={Activity} caption="Open + investigating" color="blue"/><Stat label="Critical & active" value={stats.critical} icon={Zap} caption="Prioritize these first" color="orange"/><Stat label="Resolved incidents" value={stats.resolved} icon={ShieldCheck} caption="Available for similar-incident search" color="green"/></div>
          <section className="incident-panel"><div className="panel-heading"><div><h2>{view==='Resolution library'?'Resolution library':'Incident queue'} <span className="count">{filtered.length}</span></h2><p>{view==='Resolution library'?'Documented fixes, with verification notes.':'Select an incident to inspect evidence and suggested next steps.'}</p></div></div>
            <div className="toolbar"><label className="search"><Search size={18}/><input aria-label="Search incidents" placeholder="Search incidents, services, or ID…" value={query} onChange={e=>setQuery(e.target.value)}/></label>{view!=='Resolution library'&&<select aria-label="Filter by status" value={filter} onChange={e=>setFilter(e.target.value)}>{['All statuses','Open','Investigating','Resolved'].map(x=><option key={x}>{x}</option>)}</select>}</div>
            {loading?<div className="empty"><LoaderCircle className="spin"/>Loading workspace…</div>:filtered.length===0?<div className="empty"><Search size={30}/><h3>No incidents found</h3><p>Change your search or create a new incident.</p></div>:<div className="table-wrap"><table><thead><tr><th>INCIDENT / SERVICE</th><th>SEVERITY</th><th>STATUS</th><th>UPDATED</th><th><span className="sr-only">Open</span></th></tr></thead><tbody>{filtered.map(item=>{const Icon=ICONS[item.status];return <tr key={item.id}><td><button className="incident-title" onClick={()=>open(item.id)}><span className="incident-code">{code(item.id)}{item.is_demo===1&&<span className="sample">SAMPLE</span>}</span><strong>{item.title}</strong><span className="service">{item.service}{item.assignee_id?` · ${members.find(m=>m.id===item.assignee_id)?.name||"Assigned"}`:""}{item.monitor_id?" · LIVE MONITOR":""}</span></button></td><td><Badge>{item.severity}</Badge></td><td><span className={'status '+item.status.toLowerCase()}><Icon size={15}/>{item.status}</span></td><td className="date">{date(item.updated_at)}</td><td><button className="icon-button" aria-label={'Open '+code(item.id)} onClick={()=>open(item.id)}><ArrowUpRight size={19}/></button></td></tr>})}</tbody></table></div>}
          </section><div className="bottom-note"><ShieldCheck size={15}/>Local processing · Rule-based analysis · No paid API required</div>
        </>:<>
          <button className="back" onClick={back}><ArrowLeft size={16}/>Back to incidents</button>
          {!detail?<div className="empty"><LoaderCircle className="spin"/>Loading incident…</div>:<>
            <div className="page-heading detail-heading"><div><div className="eyebrow">{code(detail.id)} · {detail.service} {detail.is_demo===1?'· SYNTHETIC SAMPLE':''}</div><h1>{detail.title}</h1><p>{detail.description||'No description added.'}</p></div><a className="secondary" href={`/api/incidents/${detail.id}/export`} download><Download size={17}/>Export JSON</a></div>
            <div className="detail-meta"><Badge>{detail.severity}</Badge><span className={'status '+detail.status.toLowerCase()}>{detail.status}</span><span>Updated {date(detail.updated_at)}</span></div>
            <div className="detail-grid"><section className="investigation-panel"><div className="tabs" role="tablist" aria-label="Incident details">{['Investigation','Log evidence','Activity'].map(x=><button key={x} role="tab" aria-selected={tab===x} onClick={()=>setTab(x)}>{x}</button>)}</div>
              <div className="tab-content" role="tabpanel">
                {tab==='Investigation'&&<><div className="analysis-header"><div className="analysis-symbol"><Zap size={22}/></div><div><h2>Evidence-led analysis</h2><p>{detail.analysis.summary}</p></div></div><div className="mini-metrics"><span><strong>{detail.analysis.line_count}</strong> log lines</span><span><strong>{detail.analysis.error_lines}</strong> error / fatal lines</span><span><strong>{detail.analysis.findings.length}</strong> patterns</span></div>
                  {detail.analysis.findings.length===0&&<div className="guidance">Add logs under <strong>Log evidence</strong>, or investigate manually if no supported pattern matches.</div>}
                  {detail.analysis.findings.map(f=><article className="finding" key={f.id}><div className="finding-top"><h3>{f.name}</h3><Badge type="hypothesis">Hypothesis</Badge></div><p>{f.cause}</p><div className="evidence-title">MATCHED EVIDENCE · {f.matched_lines} LINE{f.matched_lines!==1?'S':''}</div><div className="evidence">{f.evidence.map(e=><div key={e.line}><span>L{e.line}</span><code>{e.text}</code></div>)}</div>{f.matched_lines>20&&<p className="muted">Showing the first 20 matching lines.</p>}<h4>Suggested checks</h4><ol className="steps">{f.steps.map(s=><li key={s}>{s}</li>)}</ol><div className="verify"><ShieldCheck size={18}/><div><strong>Verify recovery</strong><p>{f.verify}</p></div></div></article>)}
                  <p className="method-note">Suggestions are predefined troubleshooting guidance, not confirmed root causes. No commands are executed automatically.</p><AIExplanation incident={detail} user={user}/>
                </>}
                {tab==='Log evidence'&&<><div className="section-title"><div><h2>Log evidence</h2><p>{detail.monitor_id?"Live monitor evidence is collected automatically. Refresh this incident to see recent checks.":"Paste logs or choose a .log / .txt file, up to 100 KB."}</p></div><button className="secondary" disabled={!canEdit||!!detail.monitor_id} onClick={()=>fileRef.current?.click()}><Upload size={16}/>Choose file</button><input ref={fileRef} type="file" accept=".txt,.log" hidden onChange={readFile}/></div><label className="sr-only" htmlFor="logs">Application logs</label><textarea id="logs" readOnly={!canEdit||!!detail.monitor_id} className="log-editor" spellCheck={false} maxLength={100000} value={logs} onChange={e=>setLogs(e.target.value)} placeholder="ERROR database ECONNREFUSED db.internal:5432"/><div className="editor-footer"><span>{logs.length.toLocaleString()} / 100,000 characters</span><button className="primary" disabled={busy||!canEdit||!!detail.monitor_id} onClick={()=>save('logs')}>{busy?<LoaderCircle className="spin" size={17}/>:<Zap size={17}/>}Save & analyze</button></div><p className="method-note">Common token and password formats are masked on save. Redaction is best-effort: use synthetic logs and review them before sharing.</p></>}
                {tab==='Activity'&&<><h2>Incident history</h2><div className="timeline">{detail.events.map(e=><div key={e.id}><span className="timeline-dot"/><strong>{e.message}</strong><time>{date(e.created_at)}</time></div>)}</div></>}
              </div>
            </section><aside className="detail-aside"><section className="side-panel"><h2>Manage incident</h2><label>Status<select disabled={!canEdit} value={status} onChange={e=>setStatus(e.target.value)}>{['Open','Investigating','Resolved'].map(x=><option key={x}>{x}</option>)}</select></label><label>Assign engineer<select disabled={!canEdit} value={assignee} onChange={e=>setAssignee(e.target.value)}><option value="">Unassigned</option>{members.filter(m=>m.active&&m.role!=="Viewer").map(m=><option key={m.id} value={m.id}>{m.name}</option>)}</select></label><label>Resolution & verification<textarea readOnly={!canEdit} rows={5} value={resolution} maxLength={5000} onChange={e=>setResolution(e.target.value)} placeholder="What changed? How did you verify recovery?"/></label><button className="primary full" disabled={busy||!canEdit} onClick={()=>save('status')}><Check size={17}/>Save changes</button></section>
              <section className="side-panel"><h2><Layers3 size={18}/>Similar resolved incidents</h2><p className="muted">Ranked by text similarity, not confidence.</p>{detail.similar.length===0?<p className="guidance">No sufficiently similar resolved incidents found.</p>:detail.similar.map(s=><article className="similar" key={s.id}><div><span className="incident-code">{code(s.id)}</span><span className="similarity">{Math.round(s.score*100)}% similarity</span></div><button onClick={()=>open(s.id)}>{s.title}<ArrowUpRight size={15}/></button><p>{s.resolution}</p></article>)}</section>
            </aside></div>
          </>}
        </>}
      </div>
    </main>
    {toast&&<div className="toast" role="status"><CheckCircle2 size={18}/>{toast}</div>}
    {showCreate&&<CreateModal onClose={()=>setShowCreate(false)} onCreated={async item=>{setShowCreate(false);await refresh();await open(item.id);notify('Incident created')}}/>}
    {showHelp&&<Modal title="Inside ResolveIQ" onClose={()=>setShowHelp(false)}><div className="help-content"><p>A local incident investigation project built with React, FastAPI, and SQLite.</p><h3>Try the 3-minute demo</h3><ol><li>Open <strong>Checkout cannot reach its database</strong>.</li><li>Review the matched log lines and the similar historical incident.</li><li>Open <strong>Log evidence</strong>, paste or upload a sample log, then save.</li><li>Set status to Investigating. Add your proposed fix and verification steps.</li><li>After verifying your simulated fix, mark it Resolved and export the incident.</li></ol><h3>What powers the suggestions?</h3><p>Five rule families detect connection, timeout, memory, authentication, and disk errors. TF-IDF cosine similarity retrieves resolved incidents. Optional local Ollama explanations are available after setup. The default investigation remains rule-based.</p><p className="guidance">This local team workspace has Admin, Engineer, and Viewer roles. Live monitoring probes the included demo service every five seconds. Use the Failure lab to trigger a synthetic fault, then restore it and investigate the automatically created incident. It is not connected to a production application.</p></div></Modal>}
  </div>
}
function Stat({label,value,icon:Icon,caption,color}){return <section className="stat"><div className="stat-top"><span>{label}</span><span className={'stat-icon '+color}><Icon size={20}/></span></div><strong className="stat-value">{String(value).padStart(2,'0')}</strong><span className="stat-caption">{caption}</span></section>}
function Modal({title,onClose,children}){
  const ref=useRef(null);
  useEffect(()=>{const previous=document.activeElement;const dialog=ref.current;dialog.showModal();return()=>{dialog.close();previous?.focus()}},[]);
  return <dialog ref={ref} className="modal" onCancel={e=>{e.preventDefault();onClose()}}><div className="modal-heading"><h2>{title}</h2><button className="icon-button" aria-label="Close dialog" onClick={onClose}><X size={20}/></button></div>{children}</dialog>
}
function CreateModal({onClose,onCreated}){
  const [form,setForm]=useState({title:'',service:'',severity:'Medium',description:'',logs:''}),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const field=key=>({value:form[key],onChange:e=>setForm({...form,[key]:e.target.value})});
  async function submit(e){e.preventDefault();setBusy(true);setError('');try{const item=await api('/incidents',{method:'POST',body:JSON.stringify(form)});await onCreated(item)}catch(e){setError(e.message);setBusy(false)}}
  return <Modal title="Create incident" onClose={onClose}><form className="create-form" onSubmit={submit}>{error&&<div role="alert" className="error">{error}</div>}<label>Incident title<input required minLength={3} maxLength={160} placeholder="Checkout requests failing after deployment" {...field('title')}/></label><div className="form-row"><label>Service<input required minLength={3} maxLength={80} placeholder="checkout-api" {...field('service')}/></label><label>Severity<select {...field('severity')}>{['Low','Medium','High','Critical'].map(x=><option key={x}>{x}</option>)}</select></label></div><label>Description<textarea rows={3} maxLength={5000} placeholder="What happened? What is affected?" {...field('description')}/></label><label>Initial logs <span className="optional">optional</span><textarea rows={4} maxLength={100000} spellCheck={false} placeholder="Paste synthetic or sanitized application logs" {...field('logs')}/></label><div className="modal-actions"><button type="button" className="secondary" onClick={onClose}>Cancel</button><button className="primary" disabled={busy}>{busy?'Creating…':'Create incident'}<ChevronRight size={17}/></button></div></form></Modal>
}
createRoot(document.getElementById('root')).render(<Account>{(user,onLogout)=><App user={user} onLogout={onLogout}/>}</Account>);
