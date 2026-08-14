from __future__ import annotations
import hashlib, json, os, sqlite3, sys, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT=Path(os.environ.get('NAVIGATOR_PROJECT_ROOT',r'C:\COGNIZANT HACKATHON'))
sys.path.insert(0,str(ROOT/'model_runtime'/'python_packages'))
import joblib, pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

MODEL=joblib.load(ROOT/'model_artifacts'/'repeat_ed_risk_model.joblib')
REPORT=json.loads((ROOT/'model_artifacts'/'model_report.json').read_text())
FEATURES=REPORT['feature_columns']; THRESHOLD=REPORT['selected_operating_threshold']
DB=ROOT/'backend'/'backend_state.sqlite'; DB.parent.mkdir(exist_ok=True)

def conn():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
 with conn() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS interventions(intervention_id TEXT PRIMARY KEY,case_id TEXT,member_id TEXT,reviewer_id TEXT,review_date TEXT,safety_status TEXT,reviewer_cleared INTEGER,final_pathway TEXT,status TEXT,notes TEXT,created_at TEXT); CREATE TABLE IF NOT EXISTS outcomes(outcome_id TEXT PRIMARY KEY,intervention_id TEXT,anchor_type TEXT,anchor_date TEXT,window_days INTEGER,repeat_ed INTEGER,outpatient_followup INTEGER,inpatient_event INTEGER,calculated_at TEXT); CREATE TABLE IF NOT EXISTS audit_events(event_id TEXT PRIMARY KEY,at TEXT,actor TEXT,method TEXT,path TEXT,status INTEGER,request_hash TEXT);''')
  columns={r[1] for r in c.execute('PRAGMA table_info(outcomes)')}
  if 'anchor_type' not in columns: c.execute('ALTER TABLE outcomes ADD COLUMN anchor_type TEXT')
  if 'anchor_date' not in columns: c.execute('ALTER TABLE outcomes ADD COLUMN anchor_date TEXT')
init()
def now(): return datetime.now(timezone.utc).isoformat()
def auth(x_api_key:str|None=Header(default=None)):
 expected=os.environ.get('NAVIGATOR_API_KEY','change-me')
 if x_api_key!=expected: raise HTTPException(401,'Unauthorized')
 return 'api-user'
def kg_case(case_id):
 c=sqlite3.connect(ROOT/'kg_rag'/'evidence_graph.sqlite'); c.row_factory=sqlite3.Row
 row=c.execute("SELECT attributes_json FROM nodes WHERE node_type='cms_case' AND node_id=?",(case_id,)).fetchone(); drivers=c.execute("SELECT evidence_text FROM edges WHERE source_type='cms_case' AND source_id=? AND relation='HAS_DRIVER'",(case_id,)).fetchall(); c.close()
 if not row: raise HTTPException(404,{'status':'DATA_NOT_FOUND','message':'Case not found.'})
 return json.loads(row['attributes_json']),[x['evidence_text'] for x in drivers]
def provider_search(pathway:str,state:str|None,require_telehealth:bool,limit:int):
 specialties={'PRIMARY_CARE':['GENERAL PRACTICE','FAMILY PRACTICE','INTERNAL MEDICINE','GERIATRIC MEDICINE'],'TELEHEALTH':['GENERAL PRACTICE','FAMILY PRACTICE','INTERNAL MEDICINE'],'CARE_MANAGEMENT':['CLINICAL SOCIAL WORKER','NURSE PRACTITIONER','GENERAL PRACTICE','INTERNAL MEDICINE'],'URGENT_CARE':['EMERGENCY MEDICINE','FAMILY PRACTICE','GENERAL PRACTICE','INTERNAL MEDICINE']}[pathway]
 where=['('+' OR '.join('UPPER(primary_specialty) LIKE ?' for _ in specialties)+')']; params=[f'%{x}%' for x in specialties]
 if state: where.append('UPPER(state)=?'); params.append(state.upper())
 if require_telehealth: where.append("telehealth_available='YES'")
 params.append(limit); sql=f"SELECT NPI,first_name,last_name,primary_specialty,telehealth_available,city,state,zip,phone,mips_score,quality_data_available,affiliated_facility_count,affiliated_facility_types FROM providers WHERE {' AND '.join(where)} ORDER BY CASE WHEN mips_score IS NULL THEN 1 ELSE 0 END,mips_score DESC,affiliated_facility_count DESC LIMIT ?"
 c=sqlite3.connect(ROOT/'provider_catalog'/'provider_catalog.sqlite'); c.row_factory=sqlite3.Row; rows=[dict(x) for x in c.execute(sql,params).fetchall()]; c.close(); return rows
class ScoreRequest(BaseModel): features:dict[str,float|int|None]
class PathwayRequest(BaseModel): case_id:str; reviewer_id:str; safety_status:str; reviewer_cleared:bool=False; telehealth_preferred:bool=False
class InterventionRequest(BaseModel): case_id:str; member_id:str; reviewer_id:str; safety_status:str; reviewer_cleared:bool; final_pathway:str|None=None; status:str='REVIEWED'; notes:str=''

app=FastAPI(title='Avoidable ED Navigator Backend',version='1.0.0')
@app.middleware('http')
async def audit(request:Request,call_next):
 r=await call_next(request)
 with conn() as c: c.execute('INSERT INTO audit_events VALUES(?,?,?,?,?,?,?)',(str(uuid.uuid4()),now(),request.headers.get('x-api-key','anonymous'),request.method,request.url.path,r.status_code,hashlib.sha256(str(request.query_params).encode()).hexdigest()))
 return r
@app.get('/health')
def health(): return {'status':'ok','model_target':'REPEAT_ED_UTILIZATION','safety':'human-review-required'}
@app.get('/v1/cases/{case_id}',dependencies=[Depends(auth)])
def get_case(case_id:str):
 risk,drivers=kg_case(case_id); return {'case_id':case_id,'risk':risk,'drivers':drivers,'safety_status':'INSUFFICIENT_CURRENT_CLINICAL_DATA','navigation_eligible':False}
@app.post('/v1/score',dependencies=[Depends(auth)])
def score(body:ScoreRequest):
 missing=[f for f in FEATURES if f not in body.features]
 if missing: raise HTTPException(422,{'status':'INSUFFICIENT_FEATURE_DATA','missing_features':missing})
 x=pd.DataFrame([{f:body.features.get(f) for f in FEATURES}]); p=float(MODEL.predict_proba(x)[0,1])
 return {'risk_score':p,'risk_band':'HIGH' if p>=THRESHOLD else 'LOW','threshold':THRESHOLD,'target':'repeat ED-candidate utilization within 90 days','notice':'Decision support only; not avoidability or clinical triage.'}
@app.post('/v1/pathways',dependencies=[Depends(auth)])
def pathway(b:PathwayRequest):
 risk,drivers=kg_case(b.case_id)
 if b.safety_status in {'POSSIBLE_EMERGENCY','INSUFFICIENT_CLINICAL_DATA','CLINICAL_REVIEW_REQUIRED'} or not b.reviewer_cleared:
  return {'status':'CLINICAL_REVIEW_REQUIRED','pathway':None,'reason':'Safety status or reviewer clearance prevents automated navigation.'}
 if b.telehealth_preferred: return {'status':'CARE_MANAGER_REVIEW','pathway':'TELEHEALTH','reason':'Reviewer-cleared pathway preference.'}
 if risk['risk_band']=='HIGH' and any('No outpatient' in x for x in drivers): return {'status':'CARE_MANAGER_REVIEW','pathway':'CARE_MANAGEMENT','reason':'High risk and no recent outpatient utilization.'}
 return {'status':'CARE_MANAGER_REVIEW','pathway':'PRIMARY_CARE','reason':'Reviewer-cleared navigation candidate.'}
@app.post('/v1/interventions',dependencies=[Depends(auth)])
def create_intervention(b:InterventionRequest):
 kg_case(b.case_id); iid=str(uuid.uuid4())
 with conn() as c: c.execute('INSERT INTO interventions VALUES(?,?,?,?,?,?,?,?,?,?,?)',(iid,b.case_id,b.member_id,b.reviewer_id,now(),b.safety_status,int(b.reviewer_cleared),b.final_pathway,b.status,b.notes,now()))
 return {'intervention_id':iid,'status':b.status}
@app.get('/v1/interventions/{intervention_id}',dependencies=[Depends(auth)])
def get_intervention(intervention_id:str):
 with conn() as c: r=c.execute('SELECT * FROM interventions WHERE intervention_id=?',(intervention_id,)).fetchone()
 if not r: raise HTTPException(404,{'status':'DATA_NOT_FOUND'})
 return dict(r)
def outcome_for_anchor(events,member_id,anchor_date,window_days):
 w=events[(events.member_id.astype(str)==member_id)&(events.start_date>anchor_date)&(events.start_date<=anchor_date+pd.Timedelta(days=window_days))]
 return {'repeat_ed':int(w.ed_candidate_flag.astype(int).any()),'outpatient_followup':int(w.encounter_type.eq('OUTPATIENT').any()),'inpatient_event':int(w.encounter_type.eq('INPATIENT').any())}
@app.post('/v1/interventions/{intervention_id}/outcomes',dependencies=[Depends(auth)])
def calculate_outcomes(intervention_id:str,window_days:int=90):
 with conn() as c: i=c.execute('SELECT * FROM interventions WHERE intervention_id=?',(intervention_id,)).fetchone()
 if not i: raise HTTPException(404,{'status':'DATA_NOT_FOUND'})
 risk,_=kg_case(i['case_id']); index_date=pd.Timestamp(risk['index_date']); intervention_date=pd.Timestamp(i['review_date']).tz_localize(None)
 e=pd.read_csv(ROOT/'cleaned_model_inputs'/'claim_events_clean.csv',parse_dates=['start_date'])
 output={}
 with conn() as c:
  for anchor_type,anchor_date in [('INDEX_ENCOUNTER',index_date),('POST_INTERVENTION',intervention_date)]:
   result=outcome_for_anchor(e,str(i['member_id']),anchor_date,window_days); oid=str(uuid.uuid4())
   c.execute('INSERT INTO outcomes(outcome_id,intervention_id,anchor_type,anchor_date,window_days,repeat_ed,outpatient_followup,inpatient_event,calculated_at) VALUES(?,?,?,?,?,?,?,?,?)',(oid,intervention_id,anchor_type,anchor_date.isoformat(),window_days,result['repeat_ed'],result['outpatient_followup'],result['inpatient_event'],now()))
   output[anchor_type]={'outcome_id':oid,'anchor_date':anchor_date.date().isoformat(),**result}
 return {'window_days':window_days,'outcomes':output,'notice':'Index outcomes measure subsequent utilization; post-intervention outcomes measure follow-up after the recorded intervention. Claims absence is not proof of success.'}
@app.get('/v1/providers/search',dependencies=[Depends(auth)])
def providers(pathway:str,state:str|None=None,require_telehealth:bool=False,limit:int=5):
 if pathway not in {'PRIMARY_CARE','TELEHEALTH','CARE_MANAGEMENT','URGENT_CARE'}: raise HTTPException(422,{'status':'INVALID_PATHWAY'})
 if not 1<=limit<=20: raise HTTPException(422,{'status':'INVALID_LIMIT'})
 return {'pathway':pathway,'providers':provider_search(pathway,state,require_telehealth,limit),'notice':'Directory options only; verify network, availability, accessibility and clinical fit.'}
@app.get('/v1/rag/search',dependencies=[Depends(auth)])
def rag(query:str):
 docs=json.loads((ROOT/'kg_rag'/'rag_document_index.json').read_text()); words=set(query.lower().split()); ranked=[]
 for d in docs:
  if d['approved_for_retrieval']: ranked.append({'document_id':d['document_id'],'score':len(words&set(d['text'].lower().split())),'text':d['text']})
 return {'documents':sorted(ranked,key=lambda x:x['score'],reverse=True),'notice':'Approved guidance only; no clinical determination.'}
