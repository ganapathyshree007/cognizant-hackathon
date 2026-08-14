import json
from pathlib import Path
import pandas as pd

root=Path(r'C:\COGNIZANT HACKATHON')
cases=pd.read_csv(root/'kg_rag'/'cms_case_evidence.csv')
def decide(row):
    # CMS claims lack current clinical evidence, therefore no automated clearance.
    return pd.Series({'safety_status':'INSUFFICIENT_CURRENT_CLINICAL_DATA','pathway_status':'CLINICAL_REVIEW_REQUIRED','suggested_pathway':None,'reason':'Obtain current clinical assessment and care-manager/clinician review before navigation.'})
out=cases.join(cases.apply(decide,axis=1))
out.to_csv(root/'care_management'/'pathway_recommendations.csv',index=False)
print({'rows':len(out),'clinical_review_required':int(out.pathway_status.eq('CLINICAL_REVIEW_REQUIRED').sum())})
