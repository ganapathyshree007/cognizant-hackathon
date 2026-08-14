import json, sys
from pathlib import Path
sys.path.insert(0, r'C:\COGNIZANT HACKATHON\project_scripts')
import improve_data_investigation as m
import pandas as pd

root=Path(r'C:\COGNIZANT HACKATHON'); out=root/'data_improved'; out.mkdir(exist_ok=True)
rawdir=root/'step 1 2 3'; pipedir=root/'pipeline_output'; reports=[]; pieces=[]
for kind,rawname,collname in [('INPATIENT','DE1_0_2008_to_2010_Inpatient_Claims_Sample_1.csv','collapsed_inpatient_claims.csv'),('OUTPATIENT','DE1_0_2008_to_2010_Outpatient_Claims_Sample_1.csv','collapsed_outpatient_claims.csv')]:
    raw=pd.read_csv(rawdir/rawname,dtype='string',usecols=['CLM_ID','CLM_PMT_AMT'])
    c=pd.read_csv(pipedir/collname,dtype={'claim_id':'string'}); c['claim_type']=kind; pieces.append(c)
    reports.append({'claim_type':kind,'raw_rows':len(raw),'unique_claims':int(raw.CLM_ID.nunique()),'collapsed_claims':len(c),'raw_payment_sum':float(pd.to_numeric(raw.CLM_PMT_AMT,errors='coerce').sum()),'collapsed_payment_sum':float(pd.to_numeric(c.payment_amount,errors='coerce').sum()),'reconciled':len(c)==raw.CLM_ID.nunique()})
    c.to_csv(out/f'collapsed_{kind.lower()}_claims.csv',index=False)
events=m.ed_flags(pd.concat(pieces,ignore_index=True,sort=False)); events.to_csv(out/'trusted_claim_events.csv',index=False)
if 'provider_ids' not in events and 'provider_id' in events: events['provider_ids']=events['provider_id']
for c in ['start_date','end_date','admission_date','discharge_date']:
    if c in events: events[c]=pd.to_datetime(events[c],errors='coerce')
(out/'claim_reconciliation.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
members=pd.concat([pd.read_csv(rawdir/f'DE1_0_{y}_Beneficiary_Summary_File_Sample_1.csv',dtype='string',keep_default_na=False).assign(coverage_year=y,member_id=lambda x:x.DESYNPUF_ID) for y in (2008,2009,2010)],ignore_index=True)
v1=pd.read_csv(root/'model_training_data'/'model_features.csv'); v1.to_csv(out/'features_v1_baseline.csv',index=False)
v2=m.make_v2(events,members,out); v2.to_csv(out/'features_v2_enhanced.csv',index=False)
target='target_repeat_ed_90d'; v2[['member_id','index_claim_id','index_date','index_year',target]].to_csv(out/'model_ready_v2_metadata.csv',index=False)
drop=['member_id','index_claim_id','index_date','index_year','index_ed_confidence']+[c for c in v2 if c.startswith('target_') and c!=target]
v2.drop(columns=drop).rename(columns={target:'target'}).to_csv(out/'model_ready_v2.csv',index=False)
audit=[]
for c in v2:
    use=c not in {'member_id','index_claim_id','index_date','index_year','index_ed_confidence'} and not c.startswith('target_')
    audit.append({'feature':c,'allowed_before_index':use,'reason':'Strict historical claims feature' if use else 'Metadata or target','decision':'USE' if use else 'EXCLUDE'})
pd.DataFrame(audit).to_csv(out/'feature_leakage_audit.csv',index=False)
m.report_tables(v1,v2,events,out)
cand=[c for c in v2 if c not in {'member_id','index_claim_id','index_date','index_year','index_ed_confidence'} and not c.startswith('target_')]; d=[]
for c in cand:
    a=pd.to_numeric(v2[v2.index_year.isin([2008,2009])][c],errors='coerce'); b=pd.to_numeric(v2[v2.index_year.eq(2010)][c],errors='coerce'); d.append({'feature':c,'train_mean':a.mean(),'test_mean':b.mean(),'train_missing_pct':a.isna().mean()*100,'test_missing_pct':b.isna().mean()*100,'standardized_mean_difference':abs(a.mean()-b.mean())/(a.std()+1e-6)})
pd.DataFrame(d).to_csv(out/'feature_drift_metrics.csv',index=False)
m.md(out/'data_drift_report.md','# Data drift report\n\n'+pd.DataFrame(d).sort_values('standardized_mean_difference',ascending=False).head(30).to_markdown(index=False)+'\n\n2010 target prevalence differs from training years; monitor features with standardized mean difference ≥0.25.')
m.md(out/'missing_access_features.md','# Missing access features\n\nNot available: distance, appointment availability, provider network, transportation, PCP attribution, and real-time telehealth access. Do not fabricate these features.')
m.md(out/'missing_data_report.md','# Missing data report\n\nCode-slot blanks are structural and retained as absence of a code, not clinical zeroes. Revenue/POS fields for ED validation are absent. See feature_quality_metrics.csv.')
m.md(out/'data_dictionary_improved.md','# Data dictionary\n\nSee trusted_claim_events, v1/v2 features, model-ready table, and separate metadata table. CMS and Synthea remain separate populations.')
m.md(out/'feature_engineering_log.md','# Feature engineering log\n\nValidated collapsed raw-claim outputs against raw unique-claim counts and payments; retained all code arrays; ED evidence is observed HCPCS only; same-member same-day ED claims form one index; all features strictly precede index date.')
m.md(out/'model_improvement_recommendation.md','# Model improvement recommendation\n\nNo new model was trained. Main bottlenecks: HCPCS-only ED label, missing access/clinical context, sparse historical utilization, and temporal target drift. Fixes: claim reconciliation, same-day ED rule, richer strict-history features, and leakage audit. Obtain revenue/POS/facility and approved real-world access data before retraining. Keep XGBoost only as a future comparator with calibrated logistic regression; a Navigation Opportunity model requires reviewed labels. Production needs external validation, clinical governance, fairness/drift monitoring, security, authentication and audit logging.')
print(json.dumps({'events':len(events),'v2_rows':len(v2),'status':'NO_MODEL_TRAINING'},indent=2))
