# UC07 Cognizant Provider Dataset Cleaning Report

## Cleaning & Validation Operations
This was a strictly READ-ONLY execution. No source data was modified.
The script validated 9 files via chunked streaming to avoid OOM errors while extracting precise row counts and key sets.

### Duplicates & Keys
- **DAC_NationalDownloadableFile.csv**: 3387942 rows. Likely PK: NPI. Approximate duplicates on PK: 1771376.
- **ec_public_reporting.csv**: 539928 rows. Likely PK: NPI. Approximate duplicates on PK: 503259.
- **ec_score_file.csv**: 541334 rows. Likely PK: NPI. Approximate duplicates on PK: 63747.
- **Facility_Affiliation.csv**: 2260193 rows. Likely PK: NPI. Approximate duplicates on PK: 1319843.
- **FY_2026_Hospital_Readmissions_Reduction_Program_Hospital.csv**: 18330 rows. Likely PK: Facility ID. Approximate duplicates on PK: 0.
- **grp_public_reporting.csv**: 199228 rows. Likely PK: None. Approximate duplicates on PK: 0.
- **grp_public_reporting_cahps.csv**: 560 rows. Likely PK: None. Approximate duplicates on PK: 0.
- **Utilization.csv**: 319746 rows. Likely PK: NPI. Approximate duplicates on PK: 134930.
- **vg_public_reporting.csv**: 0 rows. Likely PK: None. Approximate duplicates on PK: 0.

### Orphan Records
- Cross-referencing `Facility_Affiliation.csv` to `DAC_NationalDownloadableFile.csv` via PAC_ID revealed 29 orphan affiliation records (PAC_IDs in the affiliation file that do not exist in the master provider file).

### Data Quality Issues Detected (Sample-based)
- The coordinate columns (`lat`, `lon`) were checked for domain validity.
- Many quality and utilization tables possess dense missingness in granular sub-score fields, typical for Medicare reporting files.
