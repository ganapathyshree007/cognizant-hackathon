"""Complete, chronological benchmark for CatBoost, XGBoost, and FT-Transformer.

Reads the leakage-safe feature table created by train_step4_models.py.  The
evaluation intentionally does not use TabPFN until its external model license
has been accepted.  All outputs are written to step4_ml_output/evaluation.
"""
from __future__ import annotations
import json, random
from pathlib import Path
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (accuracy_score, average_precision_score, brier_score_loss,
                             confusion_matrix, precision_recall_fscore_support,
                             roc_auc_score)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBClassifier

SEED = 42
OUT = Path("step4_ml_output/evaluation")

def get_columns(d):
    excluded={"index_encounter_id","patient_id","index_date","repeat_ed_within_90d","split"}
    cols=[c for c in d if c not in excluded]
    cats=[c for c in cols if str(d[c].dtype) in ("string","object")]
    return cols,cats,[c for c in cols if c not in cats]

def score(y, p, threshold=.5):
    pred=(p>=threshold).astype(int); tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
    precision,recall,f1,_=precision_recall_fscore_support(y,pred,average="binary",zero_division=0)
    return {"sample_count":int(len(y)),"positive_count":int(y.sum()),"threshold":threshold,
            "roc_auc":round(float(roc_auc_score(y,p)),5) if y.nunique()==2 else None,
            "pr_auc":round(float(average_precision_score(y,p)),5) if y.nunique()==2 else None,
            "precision":round(float(precision),5),"recall":round(float(recall),5),"f1":round(float(f1),5),
            "brier_score":round(float(brier_score_loss(y,p)),5),"accuracy":round(float(accuracy_score(y,pred)),5),
            "specificity":round(float(tn/(tn+fp)),5) if tn+fp else None,"tp":int(tp),"tn":int(tn),"fp":int(fp),"fn":int(fn)}

def benchmark_catboost(train,val,test,cols,cats):
    def prep(x):
        x=x[cols].copy()
        for c in cats: x[c]=x[c].fillna("__MISSING__").astype(str)
        return x
    m=CatBoostClassifier(iterations=500,depth=6,learning_rate=.04,loss_function="Logloss",eval_metric="PRAUC",random_seed=SEED,verbose=False,auto_class_weights="Balanced",allow_writing_files=False)
    m.fit(prep(train),train.repeat_ed_within_90d,cat_features=cats,eval_set=(prep(val),val.repeat_ed_within_90d),early_stopping_rounds=50,verbose=False)
    probs={name:m.predict_proba(prep(frame))[:,1] for name,frame in (("train",train),("validation",val),("test",test))}
    imp=pd.DataFrame({"feature":cols,"importance":m.get_feature_importance()}).sort_values("importance",ascending=False)
    return probs,imp

def benchmark_xgboost(train,val,test,cols,cats,nums):
    pre=ColumnTransformer([("numeric",SimpleImputer(strategy="median"),nums),("categorical",Pipeline([("impute",SimpleImputer(strategy="most_frequent")),("encode",OneHotEncoder(handle_unknown="ignore"))]),cats)])
    def prep(d):
        x=d[cols].copy()
        for c in cats: x[c]=x[c].astype("string").fillna("__MISSING__").astype(object)
        for c in nums: x[c]=pd.to_numeric(x[c],errors="coerce")
        return x
    xtr=pre.fit_transform(prep(train)); xv=pre.transform(prep(val)); xt=pre.transform(prep(test))
    scale=(len(train)-train.repeat_ed_within_90d.sum())/max(train.repeat_ed_within_90d.sum(),1)
    m=XGBClassifier(n_estimators=500,max_depth=4,learning_rate=.03,subsample=.85,colsample_bytree=.85,eval_metric="logloss",random_state=SEED,n_jobs=4,scale_pos_weight=scale,early_stopping_rounds=50)
    m.fit(xtr,train.repeat_ed_within_90d,eval_set=[(xv,val.repeat_ed_within_90d)],verbose=False)
    probs={"train":m.predict_proba(xtr)[:,1],"validation":m.predict_proba(xv)[:,1],"test":m.predict_proba(xt)[:,1]}
    names=pre.get_feature_names_out(); imp=pd.DataFrame({"feature":names,"importance":m.feature_importances_}).sort_values("importance",ascending=False)
    return probs,imp

def benchmark_ft(train,val,test,cols,cats,nums):
    import torch
    from torch import nn
    torch.manual_seed(SEED); np.random.seed(SEED); random.seed(SEED)
    med=train[nums].median(); mean=train[nums].fillna(med).mean(); std=train[nums].fillna(med).std().replace(0,1)
    vocab={c:{v:i+1 for i,v in enumerate(train[c].fillna("__MISSING__").astype(str).unique())} for c in cats}
    def enc(d):
        a=torch.tensor(((d[nums].fillna(med)-mean)/std).to_numpy(np.float32)); b=np.column_stack([d[c].fillna("__MISSING__").astype(str).map(vocab[c]).fillna(0).astype(int) for c in cats]); return a,torch.tensor(b),torch.tensor(d.repeat_ed_within_90d.to_numpy(np.float32))
    class FT(nn.Module):
        def __init__(self):
            super().__init__(); z=32; self.w=nn.Parameter(torch.randn(len(nums),z)*.02); self.b=nn.Parameter(torch.zeros(len(nums),z)); self.e=nn.ModuleList([nn.Embedding(len(vocab[c])+1,z) for c in cats]); self.cls=nn.Parameter(torch.zeros(1,1,z)); self.t=nn.TransformerEncoder(nn.TransformerEncoderLayer(z,4,64,batch_first=True,dropout=.1),2); self.h=nn.Sequential(nn.LayerNorm(z),nn.Linear(z,1))
        def forward(self,a,b):
            q=[self.cls.expand(len(a),-1,-1),a.unsqueeze(-1)*self.w+self.b]+[e(b[:,i]).unsqueeze(1) for i,e in enumerate(self.e)]
            return self.h(self.t(torch.cat(q,1))[:,0]).squeeze(1)
    m=FT(); opt=torch.optim.AdamW(m.parameters(),lr=.001,weight_decay=1e-5); wt=torch.tensor([(len(train)-train.repeat_ed_within_90d.sum())/max(train.repeat_ed_within_90d.sum(),1)]); loss=nn.BCEWithLogitsLoss(pos_weight=wt); a,b,y=enc(train); av,bv,yv=enc(val); best=float("inf"); state=None; patience=0
    for _ in range(80):
        m.train(); opt.zero_grad(); z=loss(m(a,b),y); z.backward(); opt.step(); m.eval()
        with torch.no_grad(): v=float(loss(m(av,bv),yv))
        if v<best: best=v; state={k:x.detach().clone() for k,x in m.state_dict().items()}; patience=0
        else: patience+=1
        if patience==12: break
    m.load_state_dict(state); m.eval(); result={}
    for name,d in (("train",train),("validation",val),("test",test)):
        a,b,_=enc(d)
        with torch.no_grad(): result[name]=torch.sigmoid(m(a,b)).numpy()
    # Permutation importance on the test set keeps explanations tied to model behaviour.
    base=average_precision_score(test.repeat_ed_within_90d,result["test"]); values=[]
    for c in cols:
        altered=test.copy(); altered[c]=np.random.default_rng(SEED).permutation(altered[c].to_numpy()); a,b,_=enc(altered)
        with torch.no_grad(): p=torch.sigmoid(m(a,b)).numpy()
        values.append({"feature":c,"importance":round(float(base-average_precision_score(test.repeat_ed_within_90d,p)),6)})
    return result,pd.DataFrame(values).sort_values("importance",ascending=False)

def audit(d):
    splits={n:d[d.split==n] for n in ("train","validation","test")}
    patient_sets={n:set(x.patient_id) for n,x in splits.items()}
    overlaps={f"{a}_{b}":len(patient_sets[a]&patient_sets[b]) for a,b in (("train","validation"),("train","test"),("validation","test"))}
    return {"split_strategy":"chronological: final observed index year=test; prior year=validation", "index_date_ranges":{n:[str(x.index_date.min().date()),str(x.index_date.max().date())] for n,x in splits.items()},"patient_counts":{n:len(patient_sets[n]) for n in splits},"patient_overlaps":overlaps,"patient_level_separation":False,"interpretation":"Patients may appear in later time splits; this reflects real repeat-utilisation scoring. Features are strictly pre-index, so later encounters are never included. Do not claim a patient-disjoint generalisation result from this experiment.","class_distribution":{n:{"rows":len(x),"positives":int(x.repeat_ed_within_90d.sum()),"positive_rate":round(float(x.repeat_ed_within_90d.mean()),5)} for n,x in splits.items()}}

def main():
    OUT.mkdir(parents=True,exist_ok=True); d=pd.read_parquet("step4_ml_output/repeat_ed_features.parquet"); cols,cats,nums=get_columns(d); train,val,test=(d[d.split==n].copy() for n in ("train","validation","test")); models={}
    for name,fn in (("CatBoost",benchmark_catboost),("XGBoost",benchmark_xgboost),("FT-Transformer",benchmark_ft)):
        probs,importance=fn(train,val,test,cols,cats) if name=="CatBoost" else fn(train,val,test,cols,cats,nums)
        models[name]=probs; importance.to_csv(OUT/f"{name.lower().replace('-','_')}_feature_importance.csv",index=False)
    # Repeated rolling-origin validation: each evaluation year is strictly later
    # than both the fitting and tuning years.  It is temporal validation, not a
    # patient-disjoint cross-validation experiment.
    rolling=[]
    for year in (2019, 2020, 2021):
        fit=d[d.index_date.dt.year < year-1].copy(); tune=d[d.index_date.dt.year == year-1].copy(); hold=d[d.index_date.dt.year == year].copy()
        if min(len(fit),len(tune),len(hold)) == 0 or min(tune.repeat_ed_within_90d.sum(),hold.repeat_ed_within_90d.sum()) == 0: continue
        for name,fn in (("CatBoost",benchmark_catboost),("XGBoost",benchmark_xgboost),("FT-Transformer",benchmark_ft)):
            p,_=fn(fit,tune,hold,cols,cats) if name=="CatBoost" else fn(fit,tune,hold,cols,cats,nums)
            rolling.append({"model":name,"evaluation_year":year,"fit_through_year":year-2,**score(hold.repeat_ed_within_90d,p["test"])})
    pd.DataFrame(rolling).to_csv(OUT/"rolling_temporal_validation.csv",index=False)
    rows=[]; thresholds=[]; calibration=[]; subgroup=[]
    for name,prob in models.items():
        for split,frame in (("train",train),("validation",val),("test",test)):
            row={"model":name,"split":split,**score(frame.repeat_ed_within_90d,prob[split])}; rows.append(row)
        for t in (.1,.2,.3,.4,.5,.6,.7,.8): thresholds.append({"model":name,"split":"test",**score(test.repeat_ed_within_90d,prob["test"],t)})
        frac,mean=calibration_curve(test.repeat_ed_within_90d,prob["test"],n_bins=8,strategy="quantile")
        calibration += [{"model":name,"bin":i+1,"mean_predicted_probability":round(float(p),5),"observed_positive_rate":round(float(o),5)} for i,(p,o) in enumerate(zip(mean,frac))]
        for field in ("gender","race","ethnicity"):
            for value,part in test.groupby(field,dropna=False):
                if len(part)>=10 and part.repeat_ed_within_90d.nunique()==2: subgroup.append({"model":name,"field":field,"group":str(value),**score(part.repeat_ed_within_90d,prob["test"][part.index.to_numpy()-test.index.min()])})
    pd.DataFrame(rows).to_csv(OUT/"full_metrics_by_split.csv",index=False); pd.DataFrame(thresholds).to_csv(OUT/"threshold_analysis_test.csv",index=False); pd.DataFrame(calibration).to_csv(OUT/"calibration_test.csv",index=False); pd.DataFrame(subgroup).to_csv(OUT/"subgroup_fairness_test.csv",index=False)
    report={"scope":"Repeat ED use within 90 days; prioritisation only, not triage.","models_evaluated":list(models),"audit":audit(d),"notes":["Threshold 0.5 is reported for comparison only; choose the operating threshold from validation data with Care Manager capacity and acceptable false-negative risk.","Synthetic Synthea data and a small 87-row test set limit real-world generalisation and fairness conclusions.","Rolling validation is chronological and repeatable; it is not patient-disjoint cross-validation.","TabPFN-3 is excluded only pending one-time external license acceptance."],"outputs":[p.name for p in OUT.iterdir()]}
    (OUT/"evaluation_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(pd.DataFrame(rows).query("split == 'test'").to_string(index=False)); print(json.dumps(audit(d),indent=2))
if __name__=="__main__": main()
