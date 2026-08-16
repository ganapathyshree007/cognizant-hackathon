import os
import pandas as pd
import json

datasets = {
    "CMS": [
        r"d:\cognizant-hackathon-main\step 1 2 3\DE1_0_2008_to_2010_Inpatient_Claims_Sample_1.csv",
        r"d:\cognizant-hackathon-main\step 1 2 3\DE1_0_2008_to_2010_Outpatient_Claims_Sample_1.csv",
        r"d:\cognizant-hackathon-main\step 1 2 3\DE1_0_2008_Beneficiary_Summary_File_Sample_1.csv"
    ],
    "Synthea": [
        r"d:\cognizant-hackathon-main\step4_raw\patients.csv",
        r"d:\cognizant-hackathon-main\step4_raw\encounters.csv",
        r"d:\cognizant-hackathon-main\step4_raw\observations.csv",
        r"d:\cognizant-hackathon-main\step4_raw\medications.csv"
    ],
    "Cognizant": [
        r"d:\cognizant-hackathon-main\sources\DAC_NationalDownloadableFile.csv",
        r"d:\cognizant-hackathon-main\sources\Facility_Affiliation.csv"
    ]
}

out = {}

for ds_name, files in datasets.items():
    out[ds_name] = {}
    for f in files:
        if not os.path.exists(f): continue
        try:
            # Read just 5 rows to get schema
            df = pd.read_csv(f, nrows=5, dtype=str)
            # Count rows roughly (this might take long for huge files, so skip full row count for gigabyte files, or just use chunks)
            # For speed, we just get columns
            out[ds_name][os.path.basename(f)] = {
                "columns": list(df.columns),
            }
        except Exception as e:
            out[ds_name][os.path.basename(f)] = {"error": str(e)}

with open('dataset_schemas.json', 'w') as outf:
    json.dump(out, outf, indent=2)
