import os
import sys
import pandas as pd
import sqlite3

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../pipeline/step7_provider')))
from advanced_provider_matching_engine import AdvancedProviderMatchingEngine

DB_PATH = r"d:\cognizant-hackathon-main\UC07_FINAL_RUNTIME\backend\data\provider_index.db"

def get_real_providers_by_specialty(specialty: str) -> pd.DataFrame:
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(DB_PATH)
        # Using ONLY available columns: NPI, PAC_ID, Name, Specialty, Quality_Score
        query = """
            SELECT 
                d.NPI, 
                d.PAC_ID, 
                d.First_Name || ' ' || d.Last_Name AS Name, 
                d.Specialty,
                COALESCE(s.Quality_Score, 50) AS Norm_Quality
            FROM dac d
            LEFT JOIN scores s ON d.NPI = s.NPI
            WHERE d.Specialty LIKE ?
            LIMIT 500
        """
        df = pd.read_sql_query(query, conn, params=('%' + specialty + '%',))
        conn.close()
        return df
    except Exception as e:
        print(f"Provider DB Error: {e}")
        return pd.DataFrame()

def run_tests():
    print("Testing Advanced Provider Matching Engine")
    
    # Base real data
    df_providers = get_real_providers_by_specialty("Cardiology")
    if df_providers.empty:
        # Fallback to general practice if cardiology fails to load records in the sample DB
        df_providers = get_real_providers_by_specialty("GENERAL PRACTICE")
        req_spec = "GENERAL PRACTICE"
    else:
        req_spec = "Cardiology"

    engine = AdvancedProviderMatchingEngine(df_providers)
    
    # Test 1: RED -> BLOCKED
    print("\nTest 1: RED -> BLOCKED")
    res1 = engine.match({"Safety Status": "RED", "Required Specialty": req_spec})
    print(res1['Status'])
    assert res1['Status'] == "BLOCKED"

    # Test 2: YELLOW -> CONDITIONAL
    print("\nTest 2: YELLOW -> CONDITIONAL")
    res2 = engine.match({"Safety Status": "YELLOW", "Required Specialty": req_spec})
    print(res2['Status'])
    assert res2['Status'] == "CONDITIONAL"
    
    # Test 3: GREEN + Valid -> ranked
    print("\nTest 3: GREEN -> RANKED")
    res3 = engine.match({"Safety Status": "GREEN", "Required Specialty": req_spec, "Clinical Context": "needs routine checkup"})
    print(res3['Status'])
    assert res3['Status'] == "SUCCESS"
    for r in res3['Options']:
        print(r['Rank'], r['Name'], r['TOPSIS_Score'], r['Provenance'])
        assert r['NPI'] != 'UNKNOWN'
        
    # Test 4: Invalid Specialty
    print("\nTest 4: INVALID SPECIALTY")
    res4 = engine.match({"Safety Status": "GREEN", "Required Specialty": "PEDIATRIC NEUROSURGERY"})
    print(res4['Status'])
    assert res4['Status'] == "NO_MATCH"
    
    # Test 8 & 9: Deterministic Ranking
    print("\nTest 8 & 9: DETERMINISM")
    res5 = engine.match({"Safety Status": "GREEN", "Required Specialty": req_spec, "Clinical Context": "heart flutter"})
    res6 = engine.match({"Safety Status": "GREEN", "Required Specialty": req_spec, "Clinical Context": "heart flutter"})
    top1_5 = res5['Options'][0]['NPI'] if res5['Options'] else None
    top1_6 = res6['Options'][0]['NPI'] if res6['Options'] else None
    print("Run A Top NPI:", top1_5)
    print("Run B Top NPI:", top1_6)
    assert top1_5 == top1_6
    
    print("\nAll independent tests passed!")

if __name__ == "__main__":
    run_tests()
