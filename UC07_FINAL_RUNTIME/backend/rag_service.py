"""Grounded care-manager copilot services.

The module deliberately keeps retrieval local and dependency-free for the prototype.
It uses term-frequency ranking over organization-approved policy cards. The provider
interface is isolated so it can later be replaced with pgvector or another vector DB.
"""
import json
import os
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

try:
    import requests
except ImportError:  # Local RAG fallback remains usable before optional HTTP deps are installed.
    requests = None


BASE_DIR = os.path.dirname(__file__)
POLICY_PATH = os.path.join(BASE_DIR, "knowledge", "care_navigation_policies.json")
AUDIT_DB_PATH = os.path.join(BASE_DIR, "data", "appointments.db")
MAX_CONTEXT_CHARS = 6000


def _tokens(value: str) -> List[str]:
    return re.findall(r"[a-z0-9_]+", value.lower())


def load_documents() -> List[Dict[str, Any]]:
    with open(POLICY_PATH, encoding="utf-8") as source:
        return json.load(source)


def retrieve(query: str, filters: List[str] | None = None, limit: int = 4) -> List[Dict[str, Any]]:
    """Retrieve approved policy cards with transparent lexical ranking."""
    query_terms = Counter(_tokens(query + " " + " ".join(filters or [])))
    ranked: List[Tuple[float, Dict[str, Any]]] = []
    for document in load_documents():
        haystack = " ".join([document["title"], document["content"], " ".join(document.get("tags", []))])
        document_terms = Counter(_tokens(haystack))
        score = sum(min(query_terms[term], document_terms[term]) for term in query_terms)
        if filters and any(item.lower() in [tag.lower() for tag in document.get("tags", [])] for item in filters):
            score += 3
        if score:
            ranked.append((score, document))
    ranked.sort(key=lambda item: (-item[0], item[1]["id"]))
    return [document for _, document in ranked[:limit]]


def build_case_graph(patient_id: str, encounter_id: str, evaluation: Dict[str, Any]) -> Dict[str, Any]:
    """Build a compact graph view from the case facts; no clinical facts are inferred."""
    step4 = evaluation.get("step4", {})
    step5 = evaluation.get("step5", {})
    step6 = evaluation.get("step6", {})
    step7 = evaluation.get("step7") or {}
    nodes = [
        {"id": f"patient:{patient_id}", "type": "Patient", "label": f"Patient {patient_id}"},
        {"id": f"encounter:{encounter_id}", "type": "Encounter", "label": f"Encounter {encounter_id}"},
        {"id": "risk", "type": "RiskAssessment", "label": f"Historical risk: {step4.get('band', 'UNKNOWN')}"},
        {"id": "safety", "type": "SafetyAssessment", "label": f"Safety: {step5.get('status', 'PENDING')}"},
        {"id": "pathway", "type": "CarePathway", "label": step6.get("Name", "Assessment required")},
    ]
    edges = [
        {"from": f"patient:{patient_id}", "to": f"encounter:{encounter_id}", "type": "HAS_ENCOUNTER"},
        {"from": f"encounter:{encounter_id}", "to": "risk", "type": "HAS_RISK_ASSESSMENT"},
        {"from": f"encounter:{encounter_id}", "to": "safety", "type": "HAS_SAFETY_ASSESSMENT"},
        {"from": "risk", "to": "pathway", "type": "INFORMS"},
        {"from": "safety", "to": "pathway", "type": "GOVERNS"},
    ]
    for index, driver in enumerate(step4.get("drivers", [])[:3]):
        node_id = f"driver:{index}"
        nodes.append({"id": node_id, "type": "RiskDriver", "label": str(driver)})
        edges.append({"from": "risk", "to": node_id, "type": "SUPPORTED_BY"})
    for index, provider in enumerate(step7.get("Options", [])[:3]):
        node_id = f"provider:{index}"
        nodes.append({"id": node_id, "type": "Provider", "label": provider.get("Name", "Provider")})
        edges.append({"from": "pathway", "to": node_id, "type": "MATCHED_TO"})
    return {"nodes": nodes, "edges": edges}


def _guardrail_summary(evaluation: Dict[str, Any]) -> str:
    status = (evaluation.get("step5") or {}).get("status", "PENDING")
    if status == "RED":
        return "Safety status is RED. Do not suggest routine scheduling or alternatives to emergency evaluation."
    if status == "YELLOW":
        return "Safety status is YELLOW. State that urgent human clinical review is required before routine navigation."
    if status == "PENDING":
        return "Safety assessment is incomplete. State that current clinical information is required; do not infer missing findings."
    return "Safety status is GREEN. This permits navigation discussion only; final decisions remain with the human care manager."


def _fallback_answer(evaluation: Dict[str, Any], sources: List[Dict[str, Any]], question: str | None = None) -> str:
    step4, step5, step6 = evaluation.get("step4", {}), evaluation.get("step5", {}), evaluation.get("step6", {})
    lines = [
        "Grounded care-manager summary (LLM unavailable; generated from structured results and approved policy).",
        f"Historical utilization risk: {step4.get('band', 'UNKNOWN')} (score {step4.get('score', 'not available')}).",
        f"Safety status: {step5.get('status', 'PENDING')}. {step5.get('report', '')}",
        f"Current pathway: {step6.get('Pathway', 'Assessment Required')} — {step6.get('Name', 'Assessment Required')}.",
        _guardrail_summary(evaluation),
    ]
    if question:
        lines.append(f"Question received: {question}. Review the cited approved policies below; no unsupported patient facts were added.")
    lines.append("Sources: " + "; ".join(f"[{source['id']}] {source['title']}" for source in sources))
    return "\n\n".join(lines)


def _external_llm_enabled() -> bool:
    return requests is not None and os.getenv("ENABLE_EXTERNAL_LLM", "false").lower() == "true" and bool(
        os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    )


def generate_grounded_answer(evaluation: Dict[str, Any], question: str | None = None) -> Dict[str, Any]:
    """Return a cited answer. External LLM use is opt-in to protect patient data."""
    case_terms = [
        str((evaluation.get("step4") or {}).get("band", "")),
        str((evaluation.get("step5") or {}).get("status", "")),
        str((evaluation.get("step6") or {}).get("Pathway", "")),
    ]
    sources = retrieve(question or "care navigation summary", case_terms)
    if not _external_llm_enabled():
        return {"answer": _fallback_answer(evaluation, sources, question), "sources": sources, "mode": "grounded_fallback"}

    source_text = "\n\n".join(f"[{item['id']}] {item['title']}: {item['content']}" for item in sources)
    case_json = json.dumps(evaluation, ensure_ascii=False)[:MAX_CONTEXT_CHARS]
    system_prompt = """You are a care-manager documentation copilot. Explain only the supplied structured case and approved policy excerpts. Never diagnose, prescribe, alter risk/safety/pathway/provider results, or state that an ED visit was avoidable. RED blocks routine scheduling; YELLOW requires urgent human clinical review; PENDING requires more information. State uncertainty when information is absent. Give concise, operational next steps and cite sources using their bracketed IDs. Human approval is required for every action."""
    user_prompt = f"Structured case (authoritative):\n{case_json}\n\nApproved policy excerpts:\n{source_text}\n\nCare manager question: {question or 'Provide a concise case explanation and next steps.'}"
    try:
        if os.getenv("OPENAI_API_KEY"):
            url, token, model = "https://api.openai.com/v1/chat/completions", os.getenv("OPENAI_API_KEY"), os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        else:
            url, token, model = "https://openrouter.ai/api/v1/chat/completions", os.getenv("OPENROUTER_API_KEY"), os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        response = requests.post(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json={"model": model, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], "temperature": 0.1}, timeout=20)
        response.raise_for_status()
        answer = response.json()["choices"][0]["message"]["content"].strip()
        return {"answer": answer, "sources": sources, "mode": "external_grounded_llm"}
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return {"answer": _fallback_answer(evaluation, sources, question), "sources": sources, "mode": "grounded_fallback"}


def log_copilot_event(user_id: str, patient_id: str, encounter_id: str, question: str | None, result: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(AUDIT_DB_PATH), exist_ok=True)
    connection = sqlite3.connect(AUDIT_DB_PATH)
    try:
        connection.execute("""CREATE TABLE IF NOT EXISTS copilot_audit (
            id TEXT PRIMARY KEY, created_at TEXT NOT NULL, user_id TEXT NOT NULL,
            patient_id TEXT NOT NULL, encounter_id TEXT NOT NULL, question TEXT,
            mode TEXT NOT NULL, source_ids TEXT NOT NULL
        )""")
        connection.execute("INSERT INTO copilot_audit VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
            __import__("uuid").uuid4().hex, datetime.now(timezone.utc).isoformat(), user_id, patient_id,
            encounter_id, question, result["mode"], json.dumps([item["id"] for item in result["sources"]]),
        ))
        connection.commit()
    finally:
        connection.close()
