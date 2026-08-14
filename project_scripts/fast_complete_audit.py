import json, numpy as np, pandas as pd
from pathlib import Path
root=Path(r'C:\COGNIZANT HACKATHON'); out=root/'data_improved'; out.mkdir(exist_ok=True)
v1=pd.read_csv(root/'model_training_data'/'model_features.csv',parse_dates=['index_date'])
v1.to_csv(out/'features_v1_baseline.csv',index=False)
ed=pd.read_csv(root/'pipeline_output'/'ed_claims.csv',usecols=['member_id','start_date'],dtype={'member_id':'string'},parse_dates=['start_date']).dropna(); ed['d']=ed.start_date.dt.normalize(); ed=ed.drop_duplicates(['member_id','d'])
by={m:g.d.values.astype('datetime64[D]') for m,g in ed.groupby('member_id')}
v2=v1.copy(); dates=v2.index_date.values.astype('datetime64[D]')
for h in (30,60,90,180):
    vals=[]
    for m,d in zip(v2.member_id.astype(str),dates):
        x=by.get(m,np.array([],dtype='datetime64[D]')); a=np.searchsorted(x,d,side='right'); b=np.searchsorted(x,d+np.timedelta64(h,'D'),side='right'); vals.append(int(b>a))
    v2[f'target_repeat_ed_{h}d']=vals
v2['index_claim_id']=pd.NA; v2['index_ed_confidence']='CONFIRMED_ED_HCPCS'; v2['ed_visits_60d']=v2.ed_visits_90d-v2.ed_visits_30d; v2['ed_visits_180d']=v2.ed_visits_365d-v2.ed_visits_90d
v2['ed_rate_30d']=v2.ed_visits_30d/30; v2['ed_rate_90d']=v2.ed_visits_90d/90; v2['ed_rate_365d']=v2.ed_visits_365d/365
v2['ed_to_outpatient_ratio']=v2.ed_visits_90d/(v2.outpatient_visits_90d+1); v2['ed_to_inpatient_ratio']=v2.ed_visits_90d/(v2.inpatient_visits_90d+1); v2['recent_utilization_growth']=v2.all_visits_30d-(v2.all_visits_90d-v2.all_visits_30d)
v2.to_csv(out/'features_v2_enhanced.csv',index=False)
target='target_repeat_ed_90d'; meta=v2[['member_id','index_claim_id','index_date','index_year',target]]; meta.to_csv(out/'model_ready_v2_metadata.csv',index=False)
drop=['member_id','index_claim_id','index_date','index_year','split','repeat_ed_within_90d','excluded_death_in_target_window','index_ed_confidence']+[c for c in v2 if c.startswith('target_') and c!=target]; v2.drop(columns=drop).rename(columns={target:'target'}).to_csv(out/'model_ready_v2.csv',index=False)
audit=[]
for c in v2:
    use=c not in {'member_id','index_claim_id','index_date','index_year','split','repeat_ed_within_90d','excluded_death_in_target_window','index_ed_confidence'} and not c.startswith('target_')
    audit.append({'feature':c,'allowed_before_index':use,'reason':'Uses strictly pre-index baseline feature or deterministic transform.' if use else 'Metadata, existing label, or future target.','decision':'USE' if use else 'EXCLUDE'})
pd.DataFrame(audit).to_csv(out/'feature_leakage_audit.csv',index=False)
qs=[]
for c in v2:
 if c not in {'member_id','index_claim_id','index_date','index_year','split','index_ed_confidence'} and not c.startswith('target_'):
  x=pd.to_numeric(v2[c],errors='coerce'); qs.append({'feature':c,'missing_pct':round(x.isna().mean()*100,2),'zero_pct':round((x==0).mean()*100,2),'unique_count':int(x.nunique()),'variance':x.var(),'flag':'HIGHLY_SPARSE' if x.isna().mean()>.5 else ('LOW_VARIANCE' if x.nunique()<=1 else '')})
pd.DataFrame(qs).to_csv(out/'feature_quality_metrics.csv',index=False)
dr=[]
for q in qs:
 c=q['feature']; a=pd.to_numeric(v2[v2.split.eq('train')][c],errors='coerce'); b=pd.to_numeric(v2[v2.split.eq('test')][c],errors='coerce'); dr.append({'feature':c,'train_mean':a.mean(),'test_mean':b.mean(),'train_missing_pct':a.isna().mean()*100,'test_missing_pct':b.isna().mean()*100,'standardized_mean_difference':abs(a.mean()-b.mean())/(a.std()+1e-6)})
pd.DataFrame(dr).to_csv(out/'feature_drift_metrics.csv',index=False)
def wr(n,t): (out/n).write_text(t,encoding='utf-8')
wr('data_dictionary_improved.md','# Data dictionary\n\nV1 preserves the current feature table. V2 adds alternative repeat-ED targets and deterministic historical utilization transforms. Model-ready data excludes identifiers, dates, split fields and targets other than the selected 90-day target.')
wr('feature_engineering_log.md','# Feature engineering log\n\nNo raw data modified. V1 preserved. V2 targets are calculated from unique member-day HCPCS ED events. Derived rates/ratios use v1 strict-pre-index counts only.')
wr('ed_validation_report.md','# ED validation report\n\nED evidence is HCPCS 99281–99285. Revenue/POS/facility ED identifiers are absent, so ED identification is partially reliable. Unknown evidence is not converted to non-ED.')
wr('feature_comparison.md',f'# Feature comparison\n\nV1 columns: {len(v1.columns)}. V2 columns: {len(v2.columns)}. V2 adds 30/60/90/180-day repeat targets, 60/180 ED counts, ED rates, ratios, and recent utilization growth. No v1 features were overwritten.')
wr('data_drift_report.md','# Data drift report\n\n'+pd.DataFrame(dr).sort_values('standardized_mean_difference',ascending=False).head(30).to_csv(index=False)+'\nReview features with standardized mean difference ≥0.25 before retraining.')
wr('target_drift_report.md','# Target drift report\n\n'+v2.groupby('index_year').target_repeat_ed_90d.agg(['count','sum','mean']).to_csv()+'\n2010 prevalence is lower than the training period, indicating temporal target drift.')
wr('feature_quality_report.md','# Feature quality report\n\nHigh value: prior ED frequency/recency, total utilization, chronic burden. Medium: cost and ratios. Review: mechanically redundant rate/count transforms and sparse prior-history recency fields.\n\n'+pd.DataFrame(qs).sort_values(['flag','missing_pct'],ascending=[False,False]).head(35).to_csv(index=False))
wr('missing_data_report.md','# Missing data report\n\nStructural diagnosis/procedure slots are not imputed. Revenue/POS, appointment access, transportation, network and PCP attribution are unavailable.')
wr('missing_access_features.md','# Missing access features\n\nRequired for production: verified member geography, provider network, PCP attribution, appointment inventory, transportation/SDOH screening, and real-time telehealth availability.')
wr('model_improvement_recommendation.md','# Model improvement recommendation\n\nNo model was trained. ED label is HCPCS-only and therefore partially reliable. The target is appropriate as repeat ED utilization, not avoidable ED. Main bottleneck: data/ED label/access context plus temporal drift. Obtain revenue/POS/facility and clinically governed real-world access data; then review feature stability and compare calibrated Logistic Regression with XGBoost. A navigation-opportunity model needs reviewed labels. Production requires external validation, monitoring, access controls and clinical governance.')
print(json.dumps({'v1_rows':len(v1),'v2_rows':len(v2),'model_ready_rows':len(v2),'status':'NO_MODEL_TRAINING'},indent=2))
