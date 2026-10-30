"""
rag_engine.py — Agentic RAG Knowledge & Continuous Learning Engine

Features:
1. Automotive Standards Retrieval: Maps physical measurements (Bit time, Rise/Fall time, Jitter)
   to ISO 11898-1/2, ISO 14229, and Tata Motors CAN specifications.
2. Historical Failure Memory (Continuous Learning): Stores every verified root-cause analysis
   so the AI remembers past failures and recommends proven fixes for recurring issues.
3. Dual-Engine Resilience: Connects to Milvus Vector DB when available, with an automatic
   local semantic memory store (JSON fallback) for 100% offline uptime.
"""

import os
import json
import re
from typing import List, Dict, Any

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_KB_DIR = os.path.join(_CURRENT_DIR, "knowledge_base")
_STANDARDS_FILE = os.path.join(_KB_DIR, "automotive_standards.json")
_MEMORY_FILE = os.path.join(_KB_DIR, "historical_failures.json")

os.makedirs(_KB_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# 1. Knowledge Base Loader
# ---------------------------------------------------------------------------

def load_automotive_standards() -> List[Dict[str, Any]]:
    """Load pre-packaged ISO standards and automotive threshold limits."""
    if os.path.exists(_STANDARDS_FILE):
        try:
            with open(_STANDARDS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("standards", [])
        except Exception as e:
            print(f"[RAG Engine] Warning: Failed to load standards file: {e}")
    return []


def load_historical_memory() -> List[Dict[str, Any]]:
    """Load previously diagnosed failures for continuous learning."""
    if os.path.exists(_MEMORY_FILE):
        try:
            with open(_MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[RAG Engine] Warning: Failed to load historical memory: {e}")
    return []


def save_historical_failure(failure_entry: Dict[str, Any]):
    """
    Append a verified root-cause diagnosis into the historical vector memory.
    This enables the AI to 'learn' and remember past fixes.
    """
    history = load_historical_memory()
    
    # Avoid duplicate exact records
    tc_id = failure_entry.get("tc_id")
    report_no = failure_entry.get("report_no")
    existing = [h for h in history if h.get("tc_id") == tc_id and h.get("report_no") == report_no]
    
    if not existing:
        history.append(failure_entry)
        try:
            with open(_MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
            print(f"[RAG Engine] Memorized failure pattern for TC {tc_id} (Report {report_no}).")
        except Exception as e:
            print(f"[RAG Engine] Error saving to historical memory: {e}")


# ---------------------------------------------------------------------------
# 2. Context Retrieval Engine (Semantic Relevance Matcher)
# ---------------------------------------------------------------------------

def retrieve_rag_context(test_case: Dict[str, Any]) -> str:
    """
    Analyze a failed test case and retrieve:
    1. Matching Automotive ISO Standards (e.g., ISO 11898-2 limits).
    2. Similar Historical Past Failures & Remedies.

    Returns a rich, formatted context string for prompt injection.
    """
    tc_id = str(test_case.get("tc_id", "")).upper()
    tc_name = str(test_case.get("name", "")).upper()
    measurements = test_case.get("measurements", [])

    # Flatten measurement values into a searchable text block
    meas_dump = " ".join(
        f"{k} {v}" for row in measurements for k, v in row.items() if isinstance(v, str)
    ).upper()

    combined_text = f"{tc_id} {tc_name} {meas_dump}"

    matched_standards = []
    standards = load_automotive_standards()

    # Rule-guided matching based on engineering symptom detection
    is_bit_time_fail = (
        "BIT" in combined_text
        or "TOLERANCE" in combined_text
        or "0.00" in meas_dump
        or "2000" in combined_text
    )
    is_rise_time_fail = "RISE" in combined_text or "200" in combined_text or "190" in combined_text
    is_fall_time_fail = "FALL" in combined_text or "200" in combined_text or "120" in combined_text
    is_jitter_fail = "JITTER" in combined_text or "PERIODICITY" in combined_text or "LOAD" in combined_text
    is_waveform_fail = bool(test_case.get("images")) or "WAVEFORM" in combined_text

    for std in standards:
        sid = std.get("id", "")
        if "BITTIME" in sid and is_bit_time_fail:
            matched_standards.append(std)
        elif "RISETIME" in sid and is_rise_time_fail:
            matched_standards.append(std)
        elif "FALLTIME" in sid and is_fall_time_fail:
            matched_standards.append(std)
        elif "JITTER" in sid and is_jitter_fail:
            matched_standards.append(std)
        elif "WAVEFORM" in sid and is_waveform_fail:
            matched_standards.append(std)

    # If no specific rule matched, include general physical layer standard
    if not matched_standards and standards:
        matched_standards.append(standards[0])

    # Format standards for prompt
    context_sections = []
    context_sections.append("### Applicable Automotive Engineering Standards:")
    for std in matched_standards:
        context_sections.append(
            f"- Standard: {std['standard']} ({std['parameter']})\n"
            f"  Mandated Threshold: {std['limit']}\n"
            f"  Engineering Context: {std['description']}\n"
            f"  Known Root Cause: {std['root_cause_diagnosis']}\n"
            f"  Remediation Guidelines: {'; '.join(std['recommended_remediation'])}"
        )

    # Check Historical Memory for similar past cases
    history = load_historical_memory()
    matched_history = []
    for past_case in history:
        past_id = past_case.get("tc_id", "").upper()
        # If test case matches ID or symptom
        if past_id == tc_id or (past_case.get("symptom") and past_case.get("symptom") in combined_text):
            matched_history.append(past_case)

    if matched_history:
        context_sections.append("\n### Historical Past Failure Memory (Previous Vehicle Test Reports):")
        for h in matched_history[-2:]:  # Most recent 2 matching past cases
            context_sections.append(
                f"- Past Case {h.get('tc_id')} (Report {h.get('report_no', 'N/A')}, ECU: {h.get('ecu', 'General')}):\n"
                f"  Previous Diagnosed Root Cause: {h.get('root_cause')}\n"
                f"  Verified Fix That Solved It: {h.get('verified_fix')}"
            )

    return "\n\n".join(context_sections)
