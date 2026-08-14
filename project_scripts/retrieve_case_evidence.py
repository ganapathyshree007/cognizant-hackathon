"""Retrieve structured KG evidence plus approved RAG documents for a CMS case."""
from __future__ import annotations
import argparse, json, re, sqlite3
from pathlib import Path

def terms(text: str) -> set[str]:
    return set(re.findall(r"[a-z]{3,}", text.lower()))

def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument('--kg-dir',type=Path,required=True); p.add_argument('--case-id',required=True); p.add_argument('--query',required=True); args=p.parse_args()
    conn=sqlite3.connect(args.kg_dir/'evidence_graph.sqlite')
    case=conn.execute("SELECT attributes_json FROM nodes WHERE node_type='cms_case' AND node_id=?",(args.case_id,)).fetchone()
    drivers=conn.execute("SELECT target_id,evidence_text FROM edges WHERE source_type='cms_case' AND source_id=? AND relation='HAS_DRIVER'",(args.case_id,)).fetchall()
    conn.close()
    docs=json.loads((args.kg_dir/'rag_document_index.json').read_text(encoding='utf-8'))
    query_terms=terms(args.query)
    ranked=[]
    for doc in docs:
        if not doc['approved_for_retrieval']: continue
        score=len(query_terms & terms(doc['text']))
        ranked.append({'document_id':doc['document_id'],'score':score,'text':doc['text']})
    ranked.sort(key=lambda d:d['score'],reverse=True)
    print(json.dumps({'case_found':bool(case),'case':json.loads(case[0]) if case else None,'drivers':[{'driver_id':x[0],'evidence':x[1]} for x in drivers],'retrieved_approved_documents':ranked[:3],'notice':'Evidence retrieval supports care-manager review. It does not make a clinical determination or safety clearance.'},indent=2))
if __name__=='__main__': main()
