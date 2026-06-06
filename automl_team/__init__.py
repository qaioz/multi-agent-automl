"""Multi-Agent AutoML Team — harness package.

Three LLM agents (Cleaner → Feature Engineer → Trainer) on one generic
function-calling loop. The harness provides tools + orchestration only;
every data-science decision is the LLM's (NO-HARDCODE), and every decision
lands in events.jsonl with its evidence (SHOW-WORK).
"""
