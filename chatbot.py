"""
chatbot.py — NeuroNest Automotive IVN & Diagnostic Engineering Copilot

Provides an interactive, RAG-grounded conversational assistant that helps users with:
1. In-Vehicle Networking (CAN, CAN-FD, LIN, Automotive Ethernet, FlexRay).
2. ISO standards (ISO 11898-1/2, ISO 14229 UDS, AUTOSAR).
3. Test failure root-cause explanations and physical troubleshooting checklists.
4. Active context queries regarding currently loaded IVN test reports.
"""

import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

from rag_engine import load_automotive_standards, load_historical_memory

# ---------------------------------------------------------------------------
# Environment & Client Setup
# ---------------------------------------------------------------------------

_curr = os.path.dirname(os.path.abspath(__file__))
for path_cand in [
    os.path.join(_curr, ".env.app"),
    os.path.join(_curr, ".env"),
    os.path.join(_curr, "..", ".env.app"),
    os.path.join(_curr, "..", ".env"),
]:
    if os.path.exists(path_cand):
        load_dotenv(path_cand)

LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL", "")
MODEL_NAME = os.getenv("MODEL_NAME") or os.getenv("model_name_llm", "neuroverse-Qwen/Qwen3.6-27B")

_client = None

def _get_chat_client():
    global _client
    if _client is None:
        if not LLM_API_KEY:
            raise RuntimeError("LLM_API_KEY is not set. Please check your .env or .env.app file.")
        _client = OpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL if LLM_BASE_URL else None,
        )
    return _client


# ---------------------------------------------------------------------------
# Automotive System Prompt & RAG Grounding
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are 'NeuroNest Copilot', an elite Automotive IVN (In-Vehicle Networking) & Diagnostic Engineering AI Assistant developed for Tata Motors and the automotive engineering community.

Your Core Expertise:
1. In-Vehicle Networking: High-Speed CAN (ISO 11898-2), CAN-FD, LIN, Automotive Ethernet (100BASE-T1/1000BASE-T1), FlexRay.
2. Standards & Protocols:
   - ISO 11898-1 (Data link layer & bit timing), ISO 11898-2:2016 (Physical layer & high-speed transceiver specifications).
   - ISO 14229 (UDS Diagnostics), ISO 15765 (DoCAN), AUTOSAR COM / CAN Interface stacks.
   - Tata Motors & Vector CANoe / vTESTstudio test specifications and DBC matrix mapping.
3. Physical Layer Validation Rules & Thresholds:
   - Rise Time (tr) & Fall Time (tf): Pass threshold is <= 200 ns. Fails if > 200 ns.
     * Physical Root Cause: Due to electrical noise and excessive bus capacitance, the transition edge is sluggish and the bit length may increase/expand. This shifts the sample point and causes receiver bit-decoding or bit-stuffing errors.
   - Bit Rate Tolerance: Nominal bit duration is 2000 ns @ 500 kbps. Strict Pass band is 1998 ns - 2002 ns (+/- 2 ns / 0.1%). Measurements outside this window or 0.00 ns indicate clock oscillator drift, incorrect CAN bit timing register configuration (BRP, TSEG1, TSEG2, SJW), or bus-off.
   - Termination: Dual 120-ohm resistors (nominal 60 ohms differential resistance).
   - Bus Load & Jitter: Normal bus load < 30%, warning > 50%, critical > 70%. Jitter must be <= 10% of nominal cycle time.
4. Active Report Context:
   - When report context is provided, quote specific ECU names, test case IDs (e.g. PHL_TC006, PHL_TC_014), measured values, and give customized engineering fixes.

Guidelines:
- Provide authoritative, concise, and structured answers.
- Use bullet points, bold technical terms, and numbered step-by-step remediation checklists for hardware/software fixes.
- If asked general automotive or IVN questions, explain the engineering principles clearly.
"""


def _retrieve_kb_context(query: str) -> str:
    """Retrieve matching automotive standards and historical failures for the user query."""
    q_upper = query.upper()
    standards = load_automotive_standards()
    matched_snippets = []

    for std in standards:
        param = std.get("parameter", "").upper()
        sid = std.get("id", "").upper()
        desc = std.get("description", "").upper()
        if any(word in q_upper for word in ["RISE", "FALL", "SLEW", "200"]) and ("RISE" in param or "FALL" in param):
            matched_snippets.append(
                f"- Standard {std.get('standard')}: {std.get('parameter')} (Limit: {std.get('limit')})\n"
                f"  Explanation: {std.get('root_cause_diagnosis')}"
            )
        elif any(word in q_upper for word in ["BIT TIME", "BIT RATE", "TOLERANCE", "2000", "1998", "2002"]) and "BIT" in param:
            matched_snippets.append(
                f"- Standard {std.get('standard')}: {std.get('parameter')} (Limit: {std.get('limit')})\n"
                f"  Explanation: {std.get('root_cause_diagnosis')}"
            )
        elif any(word in q_upper for word in ["JITTER", "LOAD", "PERIODICITY", "DBC"]) and ("JITTER" in param or "LOAD" in param):
            matched_snippets.append(
                f"- Standard {std.get('standard')}: {std.get('parameter')} (Limit: {std.get('limit')})\n"
                f"  Explanation: {std.get('root_cause_diagnosis')}"
            )

    history = load_historical_memory()
    for h in history[-2:]:
        tc_id = h.get("tc_id", "").upper()
        if tc_id in q_upper:
            matched_snippets.append(
                f"- Historical Case {h.get('tc_id')} (Report {h.get('report_no')}, ECU {h.get('ecu')}):\n"
                f"  Root Cause: {h.get('root_cause')}\n"
                f"  Fix: {h.get('verified_fix')}"
            )

    if matched_snippets:
        return "\n\nRelevant Engineering Knowledge Base:\n" + "\n".join(matched_snippets)
    return ""


def ask_ivn_copilot(
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
    report_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Process an interactive question from the user with full context and RAG memory.
    """
    client = _get_chat_client()
    history = history or []

    # 1. Build context
    kb_context = _retrieve_kb_context(message)
    
    report_snippet = ""
    if report_context:
        meta = report_context.get("metadata", {})
        summary = report_context.get("analysis_summary", {})
        test_cases = report_context.get("test_cases", [])
        
        tc_summary = []
        for tc in test_cases[:6]:
            tc_summary.append(f"  * {tc.get('tc_id')}: {tc.get('name')} -> Verdict: {tc.get('verdict', '').upper()}")
        
        report_snippet = (
            f"\n\nCurrently Active Report Context:\n"
            f"- Report No: {meta.get('report_no', 'N/A')}\n"
            f"- Project: {meta.get('project_name', 'N/A')} (DR Stage: {meta.get('dr_stage', 'N/A')})\n"
            f"- Overall Summary: Total {summary.get('total_test_cases', len(test_cases))} cases "
            f"({summary.get('passed', 0)} Pass, {summary.get('failed', 0)} Fail)\n"
            f"- Extracted Test Cases:\n" + "\n".join(tc_summary)
        )

    # 2. Build messages array
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + kb_context + report_snippet}
    ]

    # Append recent chat history (limit to last 6 turns to keep context fast)
    for turn in history[-6:]:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if role in ["user", "assistant"] and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": message})

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=4096,
            temperature=0.4,
            timeout=90.0,
        )

        raw_content = response.choices[0].message.content
        if not raw_content:
            raw_content = getattr(response.choices[0].message, "reasoning_content", "")
        
        if not raw_content:
            raw_content = "I could not generate an answer at this moment. Please check network connectivity to the AI provider."

        reply = raw_content.strip()

        # Clean <think> tags if present
        if "<think>" in reply and "</think>" in reply:
            reply = reply.split("</think>")[-1].strip()

        # Dynamic suggested follow-up questions
        suggested = [
            "Why does rise time > 200 ns cause bit length expansion?",
            "What is the pass criteria for Bit Rate Tolerance?",
            "How do I fix a CAN Bus-Off state on an ECU?",
            "What causes network jitter in Vector CANoe reports?"
        ]

        return {
            "reply": reply,
            "suggested_questions": suggested
        }

    except Exception as e:
        print(f"[Chatbot] Error in ask_ivn_copilot: {e}")
        return {
            "reply": (
                f"**Error reaching AI Copilot:** {str(e)}\n\n"
                "*Tip:* Verify that the backend has access to the Neuroverse API URL and that LLM_API_KEY is configured."
            ),
            "suggested_questions": [
                "What is the standard CAN differential termination resistance?",
                "What are the ISO 11898-2 voltage limits?"
            ]
        }
