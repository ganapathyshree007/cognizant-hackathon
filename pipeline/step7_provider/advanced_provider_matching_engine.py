import pandas as pd
import numpy as np
import json
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import sqlite3

class AdvancedProviderMatchingEngine:
    def __init__(self, providers_df, config_path=None):
        """
        Advanced Provider Matching Engine using Semantic Compatibility and TOPSIS.
        Requires providers_df with: NPI, PAC_ID, Name, Specialty, Norm_Quality.
        """
        self.providers = providers_df.copy()
        
        # Load config
        if config_path is None:
            config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../config/UC07_STEP7_ADVANCED_MATCHING_CONFIG.json'))
        
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        except Exception as e:
            # Fallback safe config
            self.config = {
                "weights": {"semantic_compatibility": 0.50, "quality_score": 0.50},
                "criteria_metadata": {
                    "semantic_compatibility": {"type": "BENEFIT", "available": True},
                    "quality_score": {"type": "BENEFIT", "available": True}
                },
                "limitations": ["Fallback configuration loaded."]
            }

    def _calculate_semantic_compatibility(self, patient_state, providers):
        """
        Calculate cosine similarity between patient's clinical need and provider's specialty.
        """
        patient_text = f"{patient_state.get('Required Specialty', '')} {patient_state.get('Care Pathway', '')} {str(patient_state.get('Clinical Context', ''))} {patient_state.get('Conditions', '')}"
        
        # We fill missing specialties with empty string just in case
        provider_texts = providers['Specialty'].fillna('').tolist()
        
        # If there are no provider texts or patient text is empty
        if not provider_texts or not patient_text.strip():
            return np.zeros(len(providers))
            
        vectorizer = TfidfVectorizer(stop_words='english')
        
        # Fit on all texts (patient + providers) to share vocabulary
        all_texts = [patient_text] + provider_texts
        try:
            tfidf_matrix = vectorizer.fit_transform(all_texts)
            
            patient_vector = tfidf_matrix[0:1]
            provider_vectors = tfidf_matrix[1:]
            
            similarities = cosine_similarity(patient_vector, provider_vectors)[0]
            
            # Normalize to 0-100 scale for TOPSIS
            if similarities.max() > 0:
                similarities = (similarities / similarities.max()) * 100.0
            return similarities
        except ValueError:
            # In case TF-IDF fails (e.g. only stop words)
            return np.zeros(len(providers))
            

    def _calculate_topsis(self, df):
        """
        Multi-objective ranking using TOPSIS on available criteria.
        Expects df to have 'Semantic_Score' and 'Norm_Quality'.
        """
        criteria = ['Semantic_Score', 'Norm_Quality']
        weights = [self.config['weights']['semantic_compatibility'], self.config['weights']['quality_score']]
        
        # 1. Extract matrix
        mat = df[criteria].values.astype(float)
        
        # 2. Normalize matrix
        # Avoid division by zero
        norm_div = np.sqrt((mat**2).sum(axis=0))
        norm_div[norm_div == 0] = 1.0
        norm_mat = mat / norm_div
        
        # 3. Apply weights
        weighted_mat = norm_mat * weights
        
        # 4. Ideal and Anti-Ideal solutions (both are BENEFIT criteria)
        ideal = np.max(weighted_mat, axis=0)
        anti_ideal = np.min(weighted_mat, axis=0)
        
        # 5. Distances
        dist_ideal = np.sqrt(np.sum((weighted_mat - ideal)**2, axis=1))
        dist_anti_ideal = np.sqrt(np.sum((weighted_mat - anti_ideal)**2, axis=1))
        
        # 6. Closeness coefficient
        denom = dist_ideal + dist_anti_ideal
        # Avoid division by zero
        denom[denom == 0] = 1.0
        closeness = dist_anti_ideal / denom
        
        # Return scaled 0-100
        return closeness * 100.0


    def match(self, patient_state, db_path=None):
        # 1. Hard Eligibility Filters
        safety = patient_state.get('Safety Status')
        req_specialty = patient_state.get('Required Specialty')
        
        if safety == 'RED':
            return {"Status": "BLOCKED", "Reason": "Emergency escalation bypasses provider matching. (RED safety status overrides all)", "Options": []}
        
        if safety == 'YELLOW' and not patient_state.get('Clinician Cleared', False):
            return {"Status": "CONDITIONAL", "Reason": "Clinician clearance required for YELLOW safety status.", "Options": []}

        # Filter by required specialty (Hard Constraint)
        eligible = self.providers[self.providers['Specialty'].str.contains(req_specialty, case=False, na=False)].copy()
        
        if len(eligible) == 0:
            return {"Status": "NO_MATCH", "Reason": f"No eligible providers found for required specialty: {req_specialty}.", "Options": []}
            
        # 2. Semantic Compatibility
        eligible['Semantic_Score'] = self._calculate_semantic_compatibility(patient_state, eligible)
        
        # Fill missing quality with 50 (average) if needed, though real data query uses COALESCE
        if 'Norm_Quality' not in eligible.columns:
            eligible['Norm_Quality'] = 50.0
            
        # 3. TOPSIS Multi-Objective Ranking
        eligible['TOPSIS_Score'] = self._calculate_topsis(eligible)
        
        # Sort by TOPSIS
        eligible = eligible.sort_values(by='TOPSIS_Score', ascending=False)
        top5 = eligible.head(5)
        
        options = []
        for rank, (_, row) in enumerate(top5.iterrows(), 1):
            npi = row.get('NPI', 'UNKNOWN')
            
            # Fetch supporting information from DB if path is provided
            facilities_list = []
            utilization_list = []
            
            if db_path and os.path.exists(db_path) and str(npi).isdigit():
                try:
                    conn = sqlite3.connect(db_path)
                    
                    # Get facilities (CCNs)
                    fac_df = pd.read_sql_query("SELECT CCN FROM facilities WHERE NPI = ?", conn, params=(int(npi),))
                    if not fac_df.empty:
                        facilities_list = fac_df['CCN'].dropna().unique().tolist()
                        
                    # Get Utilization (Categories and Counts)
                    util_df = pd.read_sql_query("SELECT Procedure_Category, Ordinal_Count FROM utilization WHERE NPI = ?", conn, params=(int(npi),))
                    if not util_df.empty:
                        utilization_list = [f"{r['Procedure_Category']}: {r['Ordinal_Count']}" for _, r in util_df.iterrows()]
                        
                    conn.close()
                except Exception as e:
                    print(f"Error fetching supporting info for {npi}: {e}")
            
            options.append({
                "Rank": rank,
                "NPI": npi,
                "PAC_ID": row.get('PAC_ID', 'UNKNOWN'),
                "Name": row.get('Name', 'UNKNOWN'),
                "Specialty": row.get('Specialty', 'UNKNOWN'),
                "Procedure_Volumes": utilization_list if utilization_list else ["No procedure volume data available"],
                "Quality_Score": round(row.get('Norm_Quality', 0), 2),
                "Facilities_CCN": facilities_list if facilities_list else ["No facility affiliation data available"],
                "Semantic_Compatibility": round(row['Semantic_Score'], 2),
                "TOPSIS_Score": round(row['TOPSIS_Score'], 2),
                "Criteria_Used": ["Semantic Compatibility (50%)", "Quality Score (50%)"],
                "Score_Breakdown": f"Semantic:{round(row['Semantic_Score'], 2)} | Quality:{round(row.get('Norm_Quality', 0), 2)}",
                "Limitations": self.config.get('limitations', []),
                "Human_Review_Required": "REQUIRED",
                "Provenance": f"REAL DATA: NPI={npi}, PAC_ID={row.get('PAC_ID', 'UNKNOWN')}, Source=Cognizant Provider Dataset"
            })
            
        return {"Status": "SUCCESS", "Reason": "Advanced TOPSIS ranking applied successfully.", "Options": options}
