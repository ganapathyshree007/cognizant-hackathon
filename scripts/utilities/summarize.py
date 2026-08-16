import json

with open("c:\\COGNIZANT HACKATHON\\audit_results.json", "r") as f:
    results = json.load(f)

summary = []

summary.append("=== INVENTORY & QUALITY SUMMARY ===")
for name, inv in results["inventory"].items():
    qual = results["quality"][name]
    summary.append(f"File: {name} ({inv['file_size_bytes']} bytes)")
    summary.append(f"Rows: {inv['rows']}, Cols: {inv['columns']}")
    summary.append(f"Duplicates: {qual['duplicate_rows']}")
    
    # summarize missingness
    high_missing = [c for c, m in qual['missing_pct'].items() if m > 0]
    summary.append(f"Columns with missing values: {len(high_missing)}")
    
    # Check key columns
    cols = inv['column_names']
    key_cols = [c for c in cols if 'ID' in c.upper() or 'DT' in c.upper() or 'DATE' in c.upper() or 'CD' in c.upper() or 'AMT' in c.upper()]
    summary.append(f"Key Columns (sample): {key_cols[:20]}")
    summary.append("")

summary.append("=== CMS JOINS ===")
summary.append(str(results.get("cms_validation", {})))
summary.append("")

summary.append("=== SYNTHEA JOINS ===")
for j, v in results.get("synthea_joins", {}).items():
    summary.append(f"{v['parent']} -> {v['child']} on {v['join_col']}: Match Rate {v['match_rate']:.2f}%, Child Records: {v['child_total_records']}")
summary.append("")

summary.append("=== CROSS JOINS ===")
summary.append(str(results.get("cross_join", {})))

with open("c:\\COGNIZANT HACKATHON\\audit_summary.txt", "w") as f:
    f.write("\n".join(summary))
