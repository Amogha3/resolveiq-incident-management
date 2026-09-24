export let csrf='';
export function setCSRF(value){csrf=value||''}
export async function api(path,options={}){
 const response=await fetch('/api'+path,{...options,headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,...options.headers}});
 let body;try{body=await response.json()}catch{throw new Error('Unexpected server response.')}
 if(!response.ok){
   if(response.status===401&&!path.startsWith('/auth/'))window.dispatchEvent(new Event('session-expired'));
   throw new Error(typeof body.detail==='string'?body.detail:body.detail?.map(x=>`${x.loc?.slice(1).join('.') || 'Field'}: ${x.msg}`).join('; ')||'Request failed.');
 }
 return body;
}
