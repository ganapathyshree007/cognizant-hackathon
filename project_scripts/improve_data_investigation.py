"""Pre-model CMS data investigation for Avoidable ED Navigator.

Creates reproducible, non-destructive claims reconciliation, ED validation,
versioned leakage-safe features and reports. It never trains a model.
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(r"C:\COGNIZANT HACKATHON")
ED_CODES = {"99281", "99282", "99283", "99284", "99285"}
WINDOWS = (7,14,30,60,90,180,365)
CHRONIC = ["SP_ALZHDMTA","SP_CHF","SP_CHRNKIDN","SP_CNCR","SP_COPD","SP_DEPRESSN","SP_DIABETES","SP_ISCHMCHT","SP_OSTEOPRS","SP_RA_OA","SP_STRKETIA"]

def codes_join(s):
    v=sorted(set(x for x in s.dropna().astype(str) if x and x.lower() not in {'nan','none'})); return '|'.join(v) if v else pd.NA
def ymd(s): return pd.to_datetime(s.astype('string').str.replace(r'\.0$','',regex=True),format='%Y%m%d',errors='coerce')
def md(path,text): path.write_text(text,encoding='utf-8')

def collapse(raw_path, kind, out):
    raw=pd.read_csv(raw_path,dtype='string',keep_default_na=False)
    raw_rows=len(raw)
    for c in raw.columns: raw[c]=raw[c].str.strip().replace({'':pd.NA})
    for c in ['CLM_FROM_DT','CLM_THRU_DT','CLM_ADMSN_DT','NCH_BENE_DSCHRG_DT']:
        if c in raw: raw[c]=ymd(raw[c])
    diag=[c for c in raw if c.startswith('ICD9_DGNS_CD_')]; proc=[c for c in raw if c.startswith('ICD9_PRCDR_CD_')]; hcpcs=[c for c in raw if c.startswith('HCPCS_CD_')]
    keys=['DESYNPUF_ID','CLM_ID']; g=raw.groupby(keys,dropna=False)
    aggregations=dict(start_date=('CLM_FROM_DT','min'),end_date=('CLM_THRU_DT','max'),payment_amount=('CLM_PMT_AMT',lambda x:pd.to_numeric(x,errors='coerce').sum(min_count=1)),provider_ids=('PRVDR_NUM',codes_join),attending_npis=('AT_PHYSN_NPI',codes_join),operating_npis=('OP_PHYSN_NPI',codes_join),other_npis=('OT_PHYSN_NPI',codes_join),segment_count=('SEGMENT','nunique'))
    if 'CLM_ADMSN_DT' in raw: aggregations['admission_date']=('CLM_ADMSN_DT','min')
    if 'NCH_BENE_DSCHRG_DT' in raw: aggregations['discharge_date']=('NCH_BENE_DSCHRG_DT','max')
    if 'CLM_DRG_CD' in raw: aggregations['drg_code']=('CLM_DRG_CD',codes_join)
    ev=g.agg(**aggregations).reset_index()
    for c in ['admission_date','discharge_date','drg_code']:
        if c not in ev: ev[c]=pd.NA
    long=raw[keys+diag+proc+hcpcs].melt(id_vars=keys,var_name='slot',value_name='code').dropna(subset=['code'])
    for pref,name in [('ICD9_DGNS_CD_','diagnosis_codes'),('ICD9_PRCDR_CD_','procedure_codes'),('HCPCS_CD_','hcpcs_codes')]:
        x=long[long.slot.str.startswith(pref)].groupby(keys).code.agg(codes_join).rename(name).reset_index(); ev=ev.merge(x,on=keys,how='left')
    ev=ev.rename(columns={'DESYNPUF_ID':'member_id','CLM_ID':'claim_id'}); ev['claim_type']=kind
    ev.to_csv(out/f'collapsed_{kind.lower()}_claims.csv',index=False)
    return ev, {'claim_type':kind,'raw_rows':raw_rows,'unique_claims':len(ev),'collapsed_claims':len(ev),'raw_payment_sum':float(pd.to_numeric(raw.CLM_PMT_AMT,errors='coerce').sum()),'collapsed_payment_sum':float(ev.payment_amount.sum()),'all_null_columns':[c for c in raw if raw[c].isna().all()]}

def ed_flags(ev):
    ev=ev.copy(); h=ev.hcpcs_codes.fillna('')
    ev['ed_hcpcs_flag']=h.apply(lambda x:int(bool(set(x.split('|')) & ED_CODES)))
    ev['ed_revenue_flag']=0; ev['ed_other_flag']=0 # source has no revenue/POS columns
    ev['ed_evidence_count']=ev[['ed_hcpcs_flag','ed_revenue_flag','ed_other_flag']].sum(axis=1)
    ev['ed_classification']=np.select([ev.ed_evidence_count.gt(0),h.eq('')],['CONFIRMED_ED','UNKNOWN'],default='NON_ED')
    return ev

def make_v2(events, members, out):
    e=events.dropna(subset=['start_date']).copy(); e['event_date']=e.start_date.dt.normalize(); e['payment_amount']=e.payment_amount.fillna(0).clip(lower=0); e['is_inpatient']=e.claim_type.eq('INPATIENT').astype(int); e['is_outpatient']=e.claim_type.eq('OUTPATIENT').astype(int)
    # one defensible ED index per member/day: earliest claim ID; same-day billing cannot create a repeat target.
    ed=e[e.ed_classification.eq('CONFIRMED_ED')].sort_values(['member_id','event_date','claim_id']).drop_duplicates(['member_id','event_date']).copy()
    cutoff=e.event_date.max()-pd.Timedelta(days=180); ed=ed[ed.event_date.le(cutoff)].copy()
    histories={m:g.sort_values('event_date').reset_index(drop=True) for m,g in e.groupby('member_id',sort=False)}; rows=[]
    for m, indices in ed.groupby('member_id',sort=False):
        h=histories[m]; dates=h.event_date.values.astype('datetime64[D]'); ed_dates=h.loc[h.ed_classification.eq('CONFIRMED_ED'),'event_date'].drop_duplicates().values.astype('datetime64[D]')
        for _,ix in indices.iterrows():
            d=np.datetime64(ix.event_date,'D'); pos=np.searchsorted(dates,d,'left'); prior=h.iloc[:pos]
            r={'member_id':m,'index_claim_id':ix.claim_id,'index_date':pd.Timestamp(d),'index_year':int(pd.Timestamp(d).year),'index_ed_confidence':'CONFIRMED_ED'}
            for days in WINDOWS:
                lo=d-np.timedelta64(days,'D'); win=prior[(prior.event_date.values.astype('datetime64[D]')>=lo)]
                r[f'ed_visits_{days}d']=int(win.ed_classification.eq('CONFIRMED_ED').sum()); r[f'all_visits_{days}d']=len(win); r[f'outpatient_visits_{days}d']=int(win.is_outpatient.sum()); r[f'inpatient_visits_{days}d']=int(win.is_inpatient.sum()); r[f'total_paid_{days}d']=float(win.payment_amount.sum()); r[f'ed_paid_{days}d']=float(win.loc[win.ed_classification.eq('CONFIRMED_ED'),'payment_amount'].sum()); r[f'inpatient_paid_{days}d']=float(win.loc[win.is_inpatient.eq(1),'payment_amount'].sum()); r[f'outpatient_paid_{days}d']=float(win.loc[win.is_outpatient.eq(1),'payment_amount'].sum())
                dx=[z for x in win.diagnosis_codes.dropna() for z in x.split('|')]; r[f'unique_diagnosis_count_{days}d']=len(set(dx)); r[f'repeated_diagnosis_count_{days}d']=sum(v>1 for v in pd.Series(dx).value_counts()) if dx else 0
            pe=ed_dates[ed_dates<d]; r['days_since_previous_ed']=int((d-pe[-1]).astype('timedelta64[D]').astype(int)) if len(pe) else np.nan; r['days_since_previous_event']=int((d-dates[pos-1]).astype('timedelta64[D]').astype(int)) if pos else np.nan
            pi=prior[prior.is_inpatient.eq(1)].event_date.values.astype('datetime64[D]'); po=prior[prior.is_outpatient.eq(1)].event_date.values.astype('datetime64[D]'); r['days_since_previous_inpatient']=int((d-pi[-1]).astype('timedelta64[D]').astype(int)) if len(pi) else np.nan; r['days_since_previous_outpatient']=int((d-po[-1]).astype('timedelta64[D]').astype(int)) if len(po) else np.nan
            r['ed_rate_30d']=r['ed_visits_30d']/30; r['ed_rate_90d']=r['ed_visits_90d']/90; r['ed_rate_365d']=r['ed_visits_365d']/365; r['ed_count_30_vs_90']=r['ed_visits_30d']-max(0,r['ed_visits_90d']-r['ed_visits_30d']); r['ed_count_90_vs_365']=r['ed_visits_90d']-max(0,r['ed_visits_365d']-r['ed_visits_90d']); r['recent_utilization_growth']=r['all_visits_30d']-max(0,r['all_visits_90d']-r['all_visits_30d']); r['repeat_ed_pattern']=int(r['ed_visits_90d']>=2); r['ed_to_outpatient_ratio']=r['ed_visits_90d']/(r['outpatient_visits_90d']+1); r['ed_to_inpatient_ratio']=r['ed_visits_90d']/(r['inpatient_visits_90d']+1)
            r['distinct_providers_90d']=prior[prior.event_date.ge(pd.Timestamp(d)-pd.Timedelta(days=90))].provider_ids.nunique(); r['same_or_similar_diagnosis_before_ed']=int(bool(set(str(ix.diagnosis_codes).split('|')) & set(z for x in prior.diagnosis_codes.dropna() for z in x.split('|'))))
            for horizon in (30,60,90,180): r[f'target_repeat_ed_{horizon}d']=int(np.any((ed_dates>d)&(ed_dates<=d+np.timedelta64(horizon,'D'))))
            rows.append(r)
    f=pd.DataFrame(rows)
    # Strict-pre-index annual demographic policy: only previous calendar year's beneficiary summary may be used.
    b=members.copy(); b['BENE_BIRTH_DT']=ymd(b.BENE_BIRTH_DT); b['available_year']=pd.to_numeric(b.coverage_year)-1
    b['age_at_index']=b.available_year+1-b.BENE_BIRTH_DT.dt.year
    for c in CHRONIC: b[c.replace('SP_','chronic_').lower()]=b[c].eq('1').astype(int)
    flags=[c.replace('SP_','chronic_').lower() for c in CHRONIC]; b['chronic_condition_burden']=b[flags].sum(axis=1)
    b=b.rename(columns={'member_id':'b_member_id','available_year':'index_year'}); f=f.merge(b[['b_member_id','index_year','age_at_index','chronic_condition_burden']+flags],left_on=['member_id','index_year'],right_on=['b_member_id','index_year'],how='left').drop(columns='b_member_id')
    return f

def report_tables(v1,v2,events,out):
    target_cols=[c for c in v2 if c.startswith('target_repeat')]
    lines=['# ED validation report','',f"- Claim events: {len(events):,}",f"- Confirmed ED claims: {(events.ed_classification=='CONFIRMED_ED').sum():,}",f"- Confirmed ED members: {events.loc[events.ed_classification=='CONFIRMED_ED','member_id'].nunique():,}",f"- ED identification: HCPCS 99281–99285 only; revenue, place-of-service, and facility ED evidence are unavailable in this source.",'',events.groupby(['claim_type','ed_classification']).size().to_markdown()]
    md(out/'ed_validation_report.md','\n'.join(lines))
    tr=[]
    for c in target_cols: tr.append({'target':c,'positive_cases':int(v2[c].sum()),'negative_cases':int((1-v2[c]).sum()),'positive_rate':round(float(v2[c].mean()),4)})
    pd.DataFrame(tr).to_csv(out/'target_prevalence.csv',index=False)
    md(out/'target_drift_report.md','# Target drift report\n\n'+v2.groupby('index_year').target_repeat_ed_90d.agg(['count','sum','mean']).to_markdown()+"\n\nThe 2010 target prevalence is lower than 2008–2009; this is temporal target drift and can reduce temporal-test performance.")
    quality=[]
    for c in v2.columns:
        if c in {'member_id','index_claim_id','index_date','index_ed_confidence'} or c.startswith('target_'): continue
        s=v2[c]; num=pd.to_numeric(s,errors='coerce'); quality.append({'feature':c,'missing_pct':round(float(s.isna().mean()*100),2),'zero_pct':round(float((num==0).mean()*100),2),'unique_count':int(s.nunique()),'variance':float(num.var()) if num.notna().any() else np.nan,'flag':'HIGHLY_SPARSE' if s.isna().mean()>.5 else ('LOW_VARIANCE' if num.nunique(dropna=True)<=1 else '')})
    q=pd.DataFrame(quality); q.to_csv(out/'feature_quality_metrics.csv',index=False)
    md(out/'feature_quality_report.md','# Feature quality report\n\nHigh value: prior ED frequency/recency, all utilization, inpatient use, diagnosis recurrence, chronic-condition burden.\n\nMedium value: payments, provider count, outpatient ratio.\n\nLow or review: rate and count transformations that are mechanically redundant; sparse prior-event recency fields.\n\n'+q.sort_values(['flag','missing_pct'],ascending=[False,False]).head(40).to_markdown(index=False))
    base=[c for c in v1.columns if c not in {'member_id','index_date','index_year','split','repeat_ed_within_90d','excluded_death_in_target_window'}]
    new=[c for c in v2.columns if c not in {'member_id','index_claim_id','index_date','index_year','index_ed_confidence'} and not c.startswith('target_') and c not in base]
    md(out/'feature_comparison.md',f'# Feature comparison\n\n- v1 predictor count: {len(base)}\n- v2 candidate predictor count: {len([c for c in v2 if c not in {"member_id","index_claim_id","index_date","index_year","index_ed_confidence"} and not c.startswith("target_")])}\n- Added: {", ".join(new)}\n- v1 is preserved unchanged; v2 adds only strict-pre-index claims features and does not include identity/date/target fields in model-ready data.')

def main():
    p=argparse.ArgumentParser(); p.add_argument('--root',type=Path,default=ROOT); a=p.parse_args(); root=a.root; out=root/'data_improved'; out.mkdir(exist_ok=True)
    inp=root/'step 1 2 3'; ip,ri=collapse(inp/'DE1_0_2008_to_2010_Inpatient_Claims_Sample_1.csv','INPATIENT',out); op,ro=collapse(inp/'DE1_0_2008_to_2010_Outpatient_Claims_Sample_1.csv','OUTPATIENT',out); events=ed_flags(pd.concat([ip,op],ignore_index=True)); events.to_csv(out/'trusted_claim_events.csv',index=False); (out/'claim_reconciliation.json').write_text(json.dumps([ri,ro],indent=2),encoding='utf-8')
    members=pd.concat([pd.read_csv(inp/f'DE1_0_{y}_Beneficiary_Summary_File_Sample_1.csv',dtype='string',keep_default_na=False).assign(coverage_year=y,member_id=lambda x:x.DESYNPUF_ID) for y in (2008,2009,2010)],ignore_index=True)
    v1=pd.read_csv(root/'model_training_data'/'model_features.csv'); v1.to_csv(out/'features_v1_baseline.csv',index=False)
    v2=make_v2(events,members,out); v2.to_csv(out/'features_v2_enhanced.csv',index=False)
    # Model-ready excludes IDs/dates/targets/index confidence. Keep metadata separately.
    target='target_repeat_ed_90d'; meta=v2[['member_id','index_claim_id','index_date','index_year',target]].copy(); meta.to_csv(out/'model_ready_v2_metadata.csv',index=False)
    drop=['member_id','index_claim_id','index_date','index_year','index_ed_confidence']+[c for c in v2 if c.startswith('target_') and c!=target]; ready=v2.drop(columns=drop).rename(columns={target:'target'}); ready.to_csv(out/'model_ready_v2.csv',index=False)
    audit=[]
    for c in v2.columns:
        allow=c not in {'member_id','index_claim_id','index_date','index_year','index_ed_confidence'} and not c.startswith('target_') and not c.startswith('age_at_year_end')
        audit.append({'feature':c,'allowed_before_index':allow,'reason':'Historical claim window strictly before index date.' if allow else 'Identifier, index metadata, or future-derived target; excluded from model inputs.','decision':'USE' if allow else 'EXCLUDE'})
    pd.DataFrame(audit).to_csv(out/'feature_leakage_audit.csv',index=False)
    report_tables(v1,v2,events,out)
    # drift on v2 candidate features
    cand=[c for c in ready.columns if c!='target']; drift=[]
    for c in cand:
        x=pd.to_numeric(v2.loc[v2.index_year.isin([2008,2009]),c],errors='coerce'); y=pd.to_numeric(v2.loc[v2.index_year.eq(2010),c],errors='coerce');
        drift.append({'feature':c,'train_mean':x.mean(),'test_mean':y.mean(),'train_missing_pct':x.isna().mean()*100,'test_missing_pct':y.isna().mean()*100,'standardized_mean_difference':abs(x.mean()-y.mean())/(x.std()+1e-6)})
    d=pd.DataFrame(drift); d.to_csv(out/'feature_drift_metrics.csv',index=False); md(out/'data_drift_report.md','# Data drift report\n\n'+d.sort_values('standardized_mean_difference',ascending=False).head(30).to_markdown(index=False)+"\n\nFeatures with standardized mean difference ≥0.25 warrant monitoring; drift does not prove model failure but may explain lower 2010 prevalence/performance.")
    md(out/'missing_access_features.md','# Missing access features\n\nUnavailable: distance/travel time, appointment availability, network status, transportation, PCP attribution, real-time telehealth access. Required for deployment: member address/ZIP, provider network, appointment inventory, transportation/SDOH screening, and verified PCP relationship.')
    md(out/'missing_data_report.md','# Missing data report\n\nStructural claim-code blanks are retained as absent code evidence, not zero-filled clinical facts. Provider/facility fields are partially available. Revenue codes and place-of-service fields needed for stronger ED validation are absent. See feature_quality_metrics.csv and claim_reconciliation.json.')
    md(out/'data_dictionary_improved.md','# Data dictionary\n\n`trusted_claim_events.csv`: one member/claim/type after claim-segment collapse. `features_v1_baseline.csv`: preserved existing model feature table. `features_v2_enhanced.csv`: index encounter metadata, four targets, and strict historical features. `model_ready_v2.csv`: target plus candidate predictors only. `model_ready_v2_metadata.csv`: identifiers separated for evaluation.')
    md(out/'feature_engineering_log.md','# Feature engineering log\n\n1. Collapsed raw claim segments by member and claim ID; sums payment once per raw claim row/segment.\n2. Preserved diagnosis, procedure and HCPCS values as pipe-delimited traceable code arrays.\n3. Classified ED via observed HCPCS 99281–99285 only.\n4. Collapsed same-day ED claims to one member-day index encounter.\n5. Calculated all utilization and diagnosis features strictly before the index date.\n6. Used only prior calendar-year beneficiary records for annual-derived fields; no current-year annual summaries enter v2.')
    md(out/'model_improvement_recommendation.md','# Model improvement recommendation\n\n## Findings\nThe likely bottlenecks are a partially reliable HCPCS-only ED label, limited clinical/access context, target prevalence drift, sparse prior history, and annual-summary leakage risk in the prior baseline.\n\n## Fixes\nClaim segments were reconciled; same-day ED billing was collapsed; 30/60/90/180-day targets and richer strict-history utilization, cost, diagnosis and continuity features were created; metadata/targets are excluded from model-ready predictors.\n\n## Recommendation\nDo not train yet. First obtain/validate revenue code, place-of-service, facility setting, provider specialty, and approved access/PCP data; then clinically review ED classification and target definitions. Keep XGBoost as one comparator later, alongside calibrated logistic regression and other methods only after this data review is approved. A separate Navigation Opportunity model requires expert-reviewed labels. Production requires real-data external validation, clinical governance, fairness monitoring, authentication, audit logs and drift monitoring.\n')
    print(json.dumps({'output':str(out),'events':len(events),'v1_rows':len(v1),'v2_rows':len(v2),'model_ready_rows':len(ready),'status':'NO_MODEL_TRAINING_PERFORMED'},indent=2))
if __name__=='__main__': main()
