import os
import csv
import glob
from pathlib import Path

def categorize_file(rel_path):
    rel_path_str = str(rel_path).replace("\\", "/")
    
    # EXACT RUNTIME MATCHES
    if rel_path_str == "UC07_SYNTHEA_STEP4_BEST_MODEL.joblib":
        return "REQUIRED_MODEL"
    elif rel_path_str == "patient_features.db" or rel_path_str == "provider_index.db":
        return "REQUIRED_DATA"
    elif rel_path_str.startswith("care_manager_app/backend/"):
        return "REQUIRED_BACKEND"
    elif rel_path_str.startswith("care_manager_app/frontend/"):
        if "node_modules" in rel_path_str:
            return "SAFE_TO_EXCLUDE"
        return "REQUIRED_FRONTEND"
    elif rel_path_str == "safety_gate_engine.py":
        return "REQUIRED_RUNTIME"
    elif rel_path_str == "provider_matching_engine.py":
        return "REQUIRED_RUNTIME"
    elif rel_path_str == "UC07_CARE_MANAGER_AUDIT_TRAIL.csv":
        return "REQUIRED_DATA"
    
    # UNKNOWN - DO NOT DELETE
    if rel_path_str.startswith("sources/") or rel_path_str.startswith("step4_raw/"):
        return "UNKNOWN — MUST NOT DELETE"
        
    # DOCUMENTATION
    if rel_path_str.endswith(".md"):
        return "DOCUMENTATION_ONLY"
        
    # SCRIPTS
    if rel_path_str.startswith("project_scripts/") or rel_path_str.startswith("kg_rag/") or rel_path_str.startswith("powerbi_dashboard/"):
        return "DEVELOPMENT_SCRIPT"
        
    if rel_path_str.endswith(".py"):
        if rel_path_str.startswith("test_") or "audit_" in rel_path_str or "verify_" in rel_path_str:
            return "REQUIRED_TEST"
        if "experiment" in rel_path_str or "benchmark" in rel_path_str or "tuning" in rel_path_str:
            return "EXPERIMENT_ONLY"
        if "build_" in rel_path_str or "clean_" in rel_path_str or "run_" in rel_path_str:
            return "DEVELOPMENT_SCRIPT"
            
    if rel_path_str.endswith(".joblib") or rel_path_str.endswith(".json") or rel_path_str.endswith(".csv") or rel_path_str.endswith(".txt"):
        if "experiment" in rel_path_str or "benchmark" in rel_path_str or "stage" in rel_path_str:
            return "EXPERIMENT_ONLY"
        if "RESULTS" in rel_path_str.upper() or "REPORT" in rel_path_str.upper() or "AUDIT" in rel_path_str.upper():
            return "DOCUMENTATION_ONLY"
        if rel_path_str.startswith("UC07_final_"):
            return "INTERMEDIATE_ARTIFACT"
        if "HISTORICAL_FEATURES" in rel_path_str:
            # We found DB is enough, so CSV is intermediate artifact or not strictly required at runtime
            return "INTERMEDIATE_ARTIFACT"
        if "matrix" in rel_path_str.lower():
            # e.g., UC07_STEP6_CARE_PATHWAY_DECISION_MATRIX.csv
            return "REQUIRED_DATA"
            
    if ".git" in rel_path_str or "__pycache__" in rel_path_str or "catboost_info" in rel_path_str:
        return "SAFE_TO_EXCLUDE"
        
    return "UNKNOWN — MUST NOT DELETE"

def main():
    root_dir = Path("D:/cognizant-hackathon-main")
    
    rows = []
    
    for dp, dn, filenames in os.walk(root_dir):
        # skip git entirely to speed up and reduce clutter
        if ".git" in dp:
            continue
        
        for f in filenames:
            full_path = Path(dp) / f
            rel_path = full_path.relative_to(root_dir)
            cat = categorize_file(rel_path)
            rows.append({
                "File Path": str(rel_path).replace("\\", "/"),
                "Category": cat
            })
            
    with open(root_dir / "UC07_RUNTIME_FILE_MANIFEST.csv", "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["File Path", "Category"])
        writer.writeheader()
        writer.writerows(rows)
        
    print(f"Manifest written to UC07_RUNTIME_FILE_MANIFEST.csv with {len(rows)} entries.")

if __name__ == "__main__":
    main()
