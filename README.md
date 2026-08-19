# AURA UC07 - Care Manager Orchestration Engine

## Overview
**AURA UC07** is a comprehensive, end-to-end Care Manager Orchestration system built to seamlessly process patient data, assess risk, enforce clinical safety rules, determine care pathways, and dynamically match patients with the optimal healthcare providers.

The engine replaces manual, fragmented patient intake systems with a streamlined, multi-step pipeline powered by machine learning and multi-criteria decision algorithms.

## Architecture

The orchestration engine follows a rigorous, multi-step pipeline to guarantee safety, determinism, and explainability:

### Step 4: Historical Risk Stratification
- Evaluates a patient's historical medical context (diagnoses, claims, past encounters).
- Uses a machine learning model (`joblib`) trained on Synthea data to predict a comprehensive Risk Band.

### Step 5: Clinical Safety Gate
- Assesses the patient's immediate, current context (e.g., live symptoms).
- Enforces hard safety filters, yielding a definitive status:
  - `GREEN` (Safe to proceed)
  - `YELLOW` (Requires conditional clinician clearance)
  - `RED` (Emergency intervention block)

### Step 6: Care Pathway Decision Matrix
- If cleared by the Safety Gate, patients are dynamically routed to specific clinical pathways (e.g., P1, P2, ... P5).
- Ensures that patients are only funneled to appropriate clinical programs matching their symptoms and historical risk.

### Step 7: Advanced Provider Matching
- **Hybrid Retrieval + Semantic Similarity + TOPSIS Ranking**
- Retrieves verified providers from the Cognizant Provider Master dataset.
- Evaluates **Semantic Compatibility** (mapping patient clinical needs via TF-IDF cosine similarity to provider specialties).
- Uses **TOPSIS (Technique for Order of Preference by Similarity to Ideal Solution)** to dynamically rank providers based on MIPS Quality Scores and Semantic scores, ensuring no hallucinated criteria are used.

## Directory Structure
- `/backend/`: The FastAPI backend containing active machine learning models, local SQLite databases, safety logic, and API endpoints.
- `/frontend/`: The production frontend application built with TanStack Start, React, and Vite.
- `/pipeline/`: The independent modules defining logic for Steps 4, 5, 6, and 7.
- `/scripts/`: Automated build, test, verification, and data-transformation scripts.
- `/tests/`: Standalone end-to-end and component tests for the various engines.
- `/reports/`: Comprehensive audits, implementation plans, and feasibility analyses documenting the complete data lineage and architectural decisions.

## Setup & Execution

### Prerequisites
- Python 3.9+
- See `backend/requirements.txt` for exact library dependencies.

### Running the API
```bash
cd backend
python api.py
```
*This launches the FastAPI application, bridging the orchestration pipeline with the frontend or external API gateways.*

## Data Provenance & Safety
- **No Hallucination**: The system utilizes rigid, deterministic fallbacks and does NOT train supervised models on fake outcome data. 
- **Real Provider Data**: The `provider_index.db` relies strictly on genuine, validated Cognizant/CMS source files for specialties, PAC IDs, NPIs, and MIPS quality metrics.

*(Disclaimer: This is a prototype engine. Final clinical and provider assignment decisions must remain with a human Care Manager.)*
