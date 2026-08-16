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
from backend.safety_gate import evaluate_safety
from backend.opportunity_engine import calculate_opportunity
from backend.driver_engine import generate_drivers
from backend.pathway_engine import recommend_pathways

def conn():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
 with conn() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS interventions(intervention_id TEXT PRIMARY KEY,case_id TEXT,member_id TEXT,reviewer_id TEXT,review_date TEXT,safety_status TEXT,reviewer_cleared INTEGER,final_pathway TEXT,status TEXT,notes TEXT,created_at TEXT); CREATE TABLE IF NOT EXISTS outcomes(outcome_id TEXT PRIMARY KEY,intervention_id TEXT,anchor_type TEXT,anchor_date TEXT,window_days INTEGER,repeat_ed INTEGER,outpatient_followup INTEGER,inpatient_event INTEGER,calculated_at TEXT); CREATE TABLE IF NOT EXISTS audit_events(event_id TEXT PRIMARY KEY,at TEXT,actor TEXT,method TEXT,path TEXT,status INTEGER,request_hash TEXT); CREATE TABLE IF NOT EXISTS safety_sessions(session_id TEXT PRIMARY KEY,case_id TEXT,patient_id TEXT,attempt_count INTEGER,current_context TEXT,safety_status TEXT,created_at TEXT,updated_at TEXT); CREATE TABLE IF NOT EXISTS opportunity_sessions(opportunity_id TEXT PRIMARY KEY,safety_session_id TEXT,case_id TEXT,opportunity_level TEXT,opportunity_score INTEGER,drivers TEXT,evidence TEXT,created_at TEXT); CREATE TABLE IF NOT EXISTS driver_sessions(driver_session_id TEXT PRIMARY KEY,opportunity_session_id TEXT,case_id TEXT,driver_status TEXT,drivers TEXT,summary TEXT,created_at TEXT); CREATE TABLE IF NOT EXISTS pathway_sessions(pathway_session_id TEXT PRIMARY KEY,driver_session_id TEXT,case_id TEXT,recommended_pathway TEXT,alternative_pathways TEXT,supporting_drivers TEXT,reason TEXT,created_at TEXT); CREATE TABLE IF NOT EXISTS provider_sessions(provider_session_id TEXT PRIMARY KEY,pathway_session_id TEXT,case_id TEXT,recommended_pathway TEXT,providers TEXT,created_at TEXT); CREATE TABLE IF NOT EXISTS care_manager_reviews(review_id TEXT PRIMARY KEY,provider_session_id TEXT,case_id TEXT,reviewer_id TEXT,decision TEXT,original_pathway TEXT,original_provider_id TEXT,modified_pathway TEXT,modified_provider_id TEXT,reason TEXT,created_at TEXT); CREATE TABLE IF NOT EXISTS member_history(event_id TEXT PRIMARY KEY,member_id TEXT,event_type TEXT,event_date TEXT,source TEXT,details TEXT,created_at TEXT);''')
  columns={r[1] for r in c.execute('PRAGMA table_info(outcomes)')}
  if 'anchor_type' not in columns: c.execute('ALTER TABLE outcomes ADD COLUMN anchor_type TEXT')
  if 'anchor_date' not in columns: c.execute('ALTER TABLE outcomes ADD COLUMN anchor_date TEXT')
  cols_int={r[1] for r in c.execute('PRAGMA table_info(interventions)')}
  if 'review_id' not in cols_int: c.execute('ALTER TABLE interventions ADD COLUMN review_id TEXT')
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
class PathwayRequest(BaseModel): case_id:str; reviewer_id:str; driver_session_id:str|None=None; reviewer_cleared:bool=False; telehealth_preferred:bool=False
class OpportunityRequest(BaseModel): case_id:str; safety_session_id:str
class DriverRequest(BaseModel): case_id:str; opportunity_session_id:str
class CareManagerReviewRequest(BaseModel): provider_session_id:str; reviewer_id:str; decision:str; modified_pathway:str|None=None; modified_provider_id:str|None=None; reason:str|None=None
class InterventionRequest(BaseModel): review_id:str
class SafetyRequest(BaseModel): session_id:str|None=None; case_id:str; patient_id:str; new_context:dict[str,Any]
class ProviderRequest(BaseModel): pathway_session_id:str; state:str|None=None; require_telehealth:bool=False; limit:int=5

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
 x=pd.DataFrame([{f:body.features.get(f) for f in FEATURES}]); p=float(MODEL.predict_proba(x)[0][1])
 return {'risk_score':p,'risk_band':'HIGH' if p>=THRESHOLD else 'LOW','threshold':THRESHOLD,'target':'repeat ED-candidate utilization within 90 days','notice':'Decision support only; not avoidability or clinical triage.'}

@app.post('/v1/safety/assess',dependencies=[Depends(auth)])
def assess_safety(b:SafetyRequest):
 sid=b.session_id or str(uuid.uuid4())
 with conn() as c:
  row=c.execute("SELECT attempt_count,current_context FROM safety_sessions WHERE session_id=?",(sid,)).fetchone()
  if row:
   attempt_count=row['attempt_count']+1; context=json.loads(row['current_context']); context.update(b.new_context)
  else:
   attempt_count=0; context=b.new_context
  result=evaluate_safety(context,attempt_count)
  c.execute('''INSERT INTO safety_sessions(session_id,case_id,patient_id,attempt_count,current_context,safety_status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(session_id) DO UPDATE SET attempt_count=excluded.attempt_count,current_context=excluded.current_context,safety_status=excluded.safety_status,updated_at=excluded.updated_at''',(sid,b.case_id,b.patient_id,attempt_count,json.dumps(context),result['safety_status'],now(),now()))
 return {'session_id':sid,**result}
@app.post('/v1/navigation-opportunity',dependencies=[Depends(auth)])
def assess_opportunity(b:OpportunityRequest):
 with conn() as c:
  session=c.execute("SELECT * FROM safety_sessions WHERE session_id=?",(b.safety_session_id,)).fetchone()
 if not session or session['case_id']!=b.case_id:
  raise HTTPException(400,'Invalid or missing safety session.')
 if session['safety_status']!='NO_EMERGENCY_INDICATOR':
  raise HTTPException(400,'Safety status blocks navigation opportunity evaluation.')
 risk,drivers=kg_case(b.case_id)
 result=calculate_opportunity(risk)
 oid=str(uuid.uuid4())
 with conn() as c:
  c.execute("INSERT INTO opportunity_sessions(opportunity_id,safety_session_id,case_id,opportunity_level,opportunity_score,drivers,evidence,created_at) VALUES(?,?,?,?,?,?,?,?)",(oid,b.safety_session_id,b.case_id,result['navigation_opportunity_level'],result['navigation_opportunity_score'],json.dumps(result['drivers']),json.dumps(result['evidence']),now()))
 return {'opportunity_id':oid, 'safety_status':session['safety_status'], 'navigation_allowed':True, **result}

@app.post('/v1/navigation-drivers',dependencies=[Depends(auth)])
def analyze_drivers(b:DriverRequest):
 with conn() as c:
  opp_session=c.execute("SELECT * FROM opportunity_sessions WHERE opportunity_id=?",(b.opportunity_session_id,)).fetchone()
 if not opp_session or opp_session['case_id']!=b.case_id:
  raise HTTPException(400,'Invalid or missing opportunity session.')
 with conn() as c:
  session=c.execute("SELECT * FROM safety_sessions WHERE session_id=?",(opp_session['safety_session_id'],)).fetchone()
 if not session or session['safety_status']!='NO_EMERGENCY_INDICATOR':
  raise HTTPException(400,'Safety status blocks driver analysis.')
 risk, _ = kg_case(b.case_id)
 result = generate_drivers(risk, opp_session['opportunity_level'])
 did = str(uuid.uuid4())
 with conn() as c:
  c.execute("INSERT INTO driver_sessions(driver_session_id,opportunity_session_id,case_id,driver_status,drivers,summary,created_at) VALUES(?,?,?,?,?,?,?)",
            (did,b.opportunity_session_id,b.case_id,result['driver_status'],json.dumps(result['drivers']),result['summary'],now()))
 return {'driver_session_id':did, **result}

@app.post('/v1/pathways',dependencies=[Depends(auth)])
def pathway(b:PathwayRequest):
 if not b.driver_session_id:
  return {'status':'CLINICAL_REVIEW_REQUIRED','recommended_pathway':None,'reason':'Missing driver session. Automated navigation blocked.'}
 with conn() as c:
  driver_session=c.execute("SELECT * FROM driver_sessions WHERE driver_session_id=?",(b.driver_session_id,)).fetchone()
 if not driver_session or driver_session['case_id']!=b.case_id:
  return {'status':'CLINICAL_REVIEW_REQUIRED','recommended_pathway':None,'reason':'Invalid or mismatched driver session.'}
 
 with conn() as c:
  opp_session=c.execute("SELECT * FROM opportunity_sessions WHERE opportunity_id=?",(driver_session['opportunity_session_id'],)).fetchone()
  safe_session=c.execute("SELECT * FROM safety_sessions WHERE session_id=?",(opp_session['safety_session_id'],)).fetchone()
 
 if safe_session['safety_status'] in {'POSSIBLE_EMERGENCY','INSUFFICIENT_INFORMATION','INSUFFICIENT_CLINICAL_DATA','CLINICAL_REVIEW_REQUIRED'} or not b.reviewer_cleared:
  return {'status':'CLINICAL_REVIEW_REQUIRED','recommended_pathway':None,'reason':'Safety status or reviewer clearance prevents automated navigation.'}
 
 opp_level = opp_session['opportunity_level']
 drivers_json = json.loads(driver_session['drivers'])
 
 result = recommend_pathways(opp_level, drivers_json, b.telehealth_preferred)
 pid = str(uuid.uuid4())
 
 with conn() as c:
  c.execute("INSERT INTO pathway_sessions(pathway_session_id,driver_session_id,case_id,recommended_pathway,alternative_pathways,supporting_drivers,reason,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (pid,b.driver_session_id,b.case_id,result['recommended_pathway'],json.dumps(result['alternative_pathways']),json.dumps(result['supporting_drivers']),result['reason'],now()))
            
 return {'pathway_session_id':pid, 'status':'CARE_MANAGER_REVIEW', **result}
@app.post('/v1/interventions',dependencies=[Depends(auth)])
def create_intervention(b:InterventionRequest):
 with conn() as c:
  existing = c.execute('SELECT * FROM interventions WHERE review_id=?',(b.review_id,)).fetchone()
  if existing: return {'intervention_id':existing['intervention_id'],'status':existing['status']}
  review = c.execute('SELECT * FROM care_manager_reviews WHERE review_id=?',(b.review_id,)).fetchone()
  if not review: raise HTTPException(404,{'status':'REVIEW_NOT_FOUND'})
  if review['decision'] not in ('APPROVE','MODIFY'): raise HTTPException(422,{'status':'INVALID_DECISION','message':'Intervention cannot proceed without an APPROVE or MODIFY decision.'})
  
  ps = c.execute('SELECT * FROM pathway_sessions JOIN care_manager_reviews ON pathway_sessions.pathway_session_id = care_manager_reviews.provider_session_id WHERE review_id=?',(b.review_id,)).fetchone()
  iid=str(uuid.uuid4())
  
  c.execute('INSERT INTO interventions (intervention_id,case_id,member_id,reviewer_id,review_date,safety_status,reviewer_cleared,final_pathway,status,notes,created_at,review_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
            (iid,review['case_id'],review['case_id'],review['reviewer_id'],review['created_at'],'NO_EMERGENCY_INDICATOR',1,review['modified_pathway'] or review['original_pathway'],'REVIEWED',review['reason'],now(),b.review_id))
  c.execute('INSERT INTO member_history (event_id,member_id,event_type,event_date,source,details,created_at) VALUES(?,?,?,?,?,?,?)',
            (str(uuid.uuid4()), review['case_id'], 'INTERVENTION', review['created_at'], f'intervention_id:{iid}', json.dumps({'review_id':b.review_id,'decision':review['decision']}), now()))
 return {'intervention_id':iid,'status':'REVIEWED'}
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
   existing = c.execute('SELECT * FROM outcomes WHERE intervention_id=? AND anchor_type=?',(intervention_id, anchor_type)).fetchone()
   if existing:
    output[anchor_type] = {'outcome_id':existing['outcome_id'], 'anchor_date':existing['anchor_date'], 'repeat_ed':existing['repeat_ed'], 'outpatient_followup':existing['outpatient_followup'], 'inpatient_event':existing['inpatient_event']}
   else:
    result=outcome_for_anchor(e,str(i['member_id']),anchor_date,window_days); oid=str(uuid.uuid4())
    c.execute('INSERT INTO outcomes(outcome_id,intervention_id,anchor_type,anchor_date,window_days,repeat_ed,outpatient_followup,inpatient_event,calculated_at) VALUES(?,?,?,?,?,?,?,?,?)',(oid,intervention_id,anchor_type,anchor_date.isoformat(),window_days,result['repeat_ed'],result['outpatient_followup'],result['inpatient_event'],now()))
    c.execute('INSERT INTO member_history (event_id,member_id,event_type,event_date,source,details,created_at) VALUES(?,?,?,?,?,?,?)',
              (str(uuid.uuid4()), str(i['member_id']), 'OUTCOME', anchor_date.isoformat(), f'outcome_id:{oid}', json.dumps(result), now()))
    output[anchor_type]={'outcome_id':oid,'anchor_date':anchor_date.date().isoformat(),**result}
 return {'window_days':window_days,'outcomes':output,'notice':'Index outcomes measure subsequent utilization; post-intervention outcomes measure follow-up after the recorded intervention. Claims absence is not proof of success.'}
@app.post('/v1/providers/recommend',dependencies=[Depends(auth)])
def recommend_providers(b:ProviderRequest):
 with conn() as c:
  ps = c.execute('SELECT * FROM pathway_sessions WHERE pathway_session_id=?',(b.pathway_session_id,)).fetchone()
  if not ps: raise HTTPException(404,{'status':'SESSION_NOT_FOUND'})
  ds = c.execute('SELECT * FROM driver_sessions WHERE driver_session_id=?',(ps['driver_session_id'],)).fetchone()
  os_sess = c.execute('SELECT * FROM opportunity_sessions WHERE opportunity_id=?',(ds['opportunity_session_id'],)).fetchone()
  ss = c.execute('SELECT * FROM safety_sessions WHERE session_id=?',(os_sess['safety_session_id'],)).fetchone()
 
 if ss['safety_status'] != 'NO_EMERGENCY_INDICATOR':
  return {'human_review_required':True,'availability_status':'NOT_VERIFIED','network_status':'NOT_VERIFIED','provider_results':[],'reason':'Safety Gate explicitly blocked lower-acuity provider recommendation due to emergency indicator.'}
 
 pathway = ps['recommended_pathway']
 if pathway == 'NO_PATHWAY_RECOMMENDATION':
  return {'human_review_required':True,'availability_status':'NOT_VERIFIED','network_status':'NOT_VERIFIED','provider_results':[],'reason':'No specific lower-acuity pathway was recommended in Step 8.'}
 
 specialties={'PRIMARY_CARE':['GENERAL PRACTICE','FAMILY PRACTICE','INTERNAL MEDICINE','GERIATRIC MEDICINE'],'TELEHEALTH':['GENERAL PRACTICE','FAMILY PRACTICE','INTERNAL MEDICINE'],'CARE_MANAGEMENT':['CLINICAL SOCIAL WORKER','NURSE PRACTITIONER','GENERAL PRACTICE','INTERNAL MEDICINE'],'URGENT_CARE':['URGENT CARE FACILITY']}[pathway]
 where=['('+' OR '.join('UPPER(primary_specialty) LIKE ?' for _ in specialties)+')']; params=[f'%{x}%' for x in specialties]
 if b.state: where.append('UPPER(state)=?'); params.append(b.state.upper())
 if b.require_telehealth or pathway == 'TELEHEALTH': where.append("telehealth_available='YES'")
 params.append(b.limit)
 
 # Ranking: prioritize quality data available, then mips_score (if present in verified catalog), then facility count. No fabricated scores.
 sql=f"SELECT NPI as provider_id,first_name,last_name,primary_specialty as specialty,telehealth_available,city,state,zip,phone,affiliated_facility_types as facility_name FROM providers WHERE {' AND '.join(where)} ORDER BY CASE WHEN mips_score IS NULL THEN 1 ELSE 0 END,mips_score DESC,affiliated_facility_count DESC LIMIT ?"
 
 db_path = ROOT/'provider_catalog'/'provider_catalog.sqlite'
 if not db_path.exists(): raise HTTPException(500,{'status':'PROVIDER_DATABASE_MISSING'})
 
 pc = sqlite3.connect(db_path); pc.row_factory=sqlite3.Row
 rows = []
 for row in pc.execute(sql,params).fetchall():
  d = dict(row)
  name_parts = [p for p in (d.pop('first_name'), d.pop('last_name')) if p]
  d['provider_name'] = ' '.join(name_parts)
  prov_id = d.pop('provider_id')
  if pathway == 'URGENT_CARE':
      d['facility_id'] = prov_id
      d['provider_id'] = None
  else:
      d['facility_id'] = None
      d['provider_id'] = prov_id
  d['location'] = f"{d.pop('city')}, {d.pop('state')} {d.pop('zip')}"
  rows.append(d)
 pc.close()
 
 if not rows:
  return {'human_review_required':True,'availability_status':'NOT_VERIFIED','network_status':'NOT_VERIFIED','provider_results':[],'reason':'NO_PROVIDER_FOUND'}
  
 provider_session_id = str(uuid.uuid4())
 with conn() as c:
  c.execute("INSERT INTO provider_sessions VALUES(?,?,?,?,?,?)", (provider_session_id, b.pathway_session_id, ps['case_id'], pathway, json.dumps(rows), now()))
  
 return {
  'provider_session_id':provider_session_id,
  'pathway_session_id':b.pathway_session_id,
  'recommended_pathway':pathway,
  'provider_results':rows,
  'availability_status':'NOT_VERIFIED',
  'network_status':'NOT_VERIFIED',
  'source':'VERIFIED_PROVIDER_DATABASE',
  'human_review_required':True,
  'notice':'Directory options only; verify network, availability, accessibility and clinical fit. The generated provider_catalog.sqlite is synthetic prototype/demo data only. It must never be represented as real provider data, real availability, or real network participation.'
 }

@app.post('/v1/care-manager/review',dependencies=[Depends(auth)])
def create_review(b:CareManagerReviewRequest):
 if b.decision not in ('APPROVE','MODIFY','REJECT','ESCALATE'): raise HTTPException(422,{'status':'INVALID_DECISION'})
 with conn() as c:
  ps = c.execute('SELECT * FROM provider_sessions WHERE provider_session_id=?',(b.provider_session_id,)).fetchone()
  if not ps: raise HTTPException(404,{'status':'SESSION_NOT_FOUND'})
  
  # Session chain validation
  pws = c.execute('SELECT * FROM pathway_sessions WHERE pathway_session_id=?',(ps['pathway_session_id'],)).fetchone()
  ds = c.execute('SELECT * FROM driver_sessions WHERE driver_session_id=?',(pws['driver_session_id'],)).fetchone()
  os = c.execute('SELECT * FROM opportunity_sessions WHERE opportunity_id=?',(ds['opportunity_session_id'],)).fetchone()
  ss = c.execute('SELECT * FROM safety_sessions WHERE session_id=?',(os['safety_session_id'],)).fetchone()
  
  if ss['safety_status'] in ('POSSIBLE_EMERGENCY', 'INSUFFICIENT_INFORMATION'):
      raise HTTPException(403,{'status':'SAFETY_GATE_BLOCKED','message':'Cannot create a lower-acuity navigation intervention. The case may still be presented to the appropriate human/clinical reviewer for review and escalation.'})

  review_id = str(uuid.uuid4())
  c.execute('INSERT INTO care_manager_reviews VALUES(?,?,?,?,?,?,?,?,?,?,?)',
      (review_id, b.provider_session_id, ps['case_id'], b.reviewer_id, b.decision, ps['recommended_pathway'], None, b.modified_pathway, b.modified_provider_id, b.reason, now()))
 return {'review_id': review_id, 'status': b.decision}
 
@app.get('/v1/care-manager/context/{provider_session_id}',dependencies=[Depends(auth)])
def get_care_manager_context(provider_session_id:str):
 with conn() as c:
  ps = c.execute('SELECT * FROM provider_sessions WHERE provider_session_id=?',(provider_session_id,)).fetchone()
  if not ps: raise HTTPException(404,{'status':'SESSION_NOT_FOUND'})
  pws = c.execute('SELECT * FROM pathway_sessions WHERE pathway_session_id=?',(ps['pathway_session_id'],)).fetchone()
  ds = c.execute('SELECT * FROM driver_sessions WHERE driver_session_id=?',(pws['driver_session_id'],)).fetchone()
  os = c.execute('SELECT * FROM opportunity_sessions WHERE opportunity_id=?',(ds['opportunity_session_id'],)).fetchone()
  ss = c.execute('SELECT * FROM safety_sessions WHERE session_id=?',(os['safety_session_id'],)).fetchone()
 return {
    'case_id': ps['case_id'],
    'safety_status': ss['safety_status'],
    'navigation_opportunity': os['opportunity_level'],
    'drivers': json.loads(ds['drivers']),
    'recommended_pathway': ps['recommended_pathway'],
    'provider_options': json.loads(ps['providers']),
    'availability_status': 'NOT_VERIFIED',
    'network_status': 'NOT_VERIFIED',
    'human_review_required': True
 }
def rag(query:str):
 docs=json.loads((ROOT/'kg_rag'/'rag_document_index.json').read_text()); words=set(query.lower().split()); ranked=[]
 for d in docs:
  if d['approved_for_retrieval']: ranked.append({'document_id':d['document_id'],'score':len(words&set(d['text'].lower().split())),'text':d['text']})
 return {'documents':sorted(ranked,key=lambda x:x['score'],reverse=True),'notice':'Approved guidance only; no clinical determination.'}
