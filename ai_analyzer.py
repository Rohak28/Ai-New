"""
ai_analyzer.py — NeuroNest IVN AI Analysis Module (Phase 3)

Connects to the NeuroVerse Qwen LLM to provide root-cause diagnosis
for failed IVN test cases. Implements the 90/10 smart filtering rule:
  - PASS test cases: skip AI, store directly
  - FAIL test cases: send measurements + context to Qwen for diagnosis
"""

import os
import json
import time
from openai import OpenAI
from dotenv import load_dotenv

from rag_engine import retrieve_rag_context, save_historical_failure

# ---------------------------------------------------------------------------
# 1. Load environment and initialize Qwen client
# ---------------------------------------------------------------------------

# Search for .env or .env.app in current dir, parent, and project root
_curr = os.path.dirname(os.path.abspath(__file__))
for path_cand in [
    os.path.join(_curr, ".env.app"),
    os.path.join(_curr, ".env"),
    os.path.join(_curr, "..", ".env.app"),
    os.path.join(_curr, "..", ".env"),
    os.path.join(_curr, "..", "..", ".env.app"),
    os.path.join(_curr, "..", "..", ".env"),
]:
    if os.path.exists(path_cand):
        load_dotenv(path_cand)

LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL", "")
MODEL_NAME = os.getenv("MODEL_NAME") or os.getenv("model_name_llm", "neuroverse-Qwen/Qwen3.6-27B")

_client = None  # singleton


def _get_client():
    """Lazy-initialize the OpenAI-compatible Qwen client."""
    global _client
    if _client is None:
        if not LLM_API_KEY:
            raise RuntimeError(
                "LLM_API_KEY is not set. Please configure your .env file."
            )
        _client = OpenAI(
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL if LLM_BASE_URL else None,
        )
        print(f"[AI Analyzer] Connected to model: {MODEL_NAME}")
    return _client


# ---------------------------------------------------------------------------
# 2. Prompt builder for a single failed test case
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are an expert automotive IVN (In-Vehicle Networking) Test Report Analyzer AI "
    "specializing in CAN bus physical layer diagnostics per ISO 11898. "
    "When given a failed test case with its measurement data, provide a structured "
    "diagnosis in EXACTLY this JSON format (no markdown, no code fences, just raw JSON):\n"
    '{\n'
    '  "root_cause": "A clear 2-3 sentence explanation of WHY the test failed",\n'
    '  "iso_reference": "The specific ISO standard section that defines the pass/fail criteria",\n'
    '  "severity": "CRITICAL or HIGH or MEDIUM or LOW",\n'
    '  "recommended_fix": "Numbered list of engineering steps to resolve the failure"\n'
    '}\n\n'
    "Base your severity on:\n"
    "- CRITICAL: Node is offline, bus-off, or zero readings (safety risk)\n"
    "- HIGH: Values exceed ISO limits significantly (>20% deviation)\n"
    "- MEDIUM: Values are borderline or intermittent failures\n"
    "- LOW: Minor deviations, likely measurement noise\n"
)


def _build_failure_prompt(test_case, iso_context=""):
    """
    Build a structured user prompt for a single failed test case.

    Args:
        test_case: dict with keys tc_id, name, verdict, measurements, images
        iso_context: optional string of relevant ISO standards from Milvus RAG
    """
    tc_id = test_case.get("tc_id", "Unknown")
    tc_name = test_case.get("name", "Unknown")
    measurements = test_case.get("measurements", [])

    # Filter out junk measurements (footer rows, empty headers)
    valid_measurements = []
    for m in measurements:
        # Skip rows where most keys are empty or contain footer text
        values = list(m.values())
        non_empty = [v for v in values if v and v.strip() and v.strip() != "-"]
        keys = list(m.keys())
        # Skip if keys contain footer text like "TITLE:", "Test Report No:"
        if any("TITLE" in k or "Test Report No" in k for k in keys):
            continue
        # Skip if keys are mostly empty strings
        if all(k.strip() == "" for k in keys):
            continue
        # Skip rows with "IVN Test Report" as a key (footer artifact)
        if any("IVN Test Report" in k for k in keys):
            continue
        if len(non_empty) >= 2:
            valid_measurements.append(m)

    # Format measurements as a readable table
    measurement_text = ""
    if valid_measurements:
        measurement_text = "\nMeasurement Data:\n"
        for i, row in enumerate(valid_measurements[:30]):  # Cap at 30 rows to avoid token overflow
            row_str = " | ".join(f"{k}: {v}" for k, v in row.items() if k.strip())
            measurement_text += f"  Row {i+1}: {row_str}\n"
    else:
        measurement_text = "\nNo valid measurement data available.\n"

    # Build the image context (paths for reference, not actual image data)
    image_info = ""
    images = test_case.get("images", [])
    if images:
        image_info = f"\nWaveform Images Available: {len(images)} oscilloscope trace(s) captured.\n"

    # ISO context from Milvus RAG (if available)
    iso_section = ""
    if iso_context:
        iso_section = f"\nRelevant ISO Standards Context:\n{iso_context}\n"

    prompt = (
        f"Analyze this FAILED IVN test case:\n\n"
        f"Test Case ID: {tc_id}\n"
        f"Test Case Name: {tc_name}\n"
        f"Verdict: FAIL\n"
        f"{measurement_text}"
        f"{image_info}"
        f"{iso_section}"
        f"\nProvide your diagnosis as a JSON object."
    )

    return prompt


# ---------------------------------------------------------------------------
# 3. Single test case analysis
# ---------------------------------------------------------------------------

def analyze_failed_test_case(test_case, iso_context=""):
    """
    Send a single failed test case to Qwen for root-cause diagnosis.
    Grounds diagnosis in ISO standards & historical failure memory (RAG).

    Returns:
        dict with keys: root_cause, iso_reference, severity, recommended_fix
        OR a fallback dict if the AI call fails
    """
    client = _get_client()

    # Automatically retrieve grounded ISO standards and historical fixes if not provided
    if not iso_context:
        iso_context = retrieve_rag_context(test_case)

    prompt = _build_failure_prompt(test_case, iso_context)

    tc_id = test_case.get("tc_id", "Unknown")
    print(f"[AI Analyzer] Analyzing failed TC: {tc_id} with RAG grounding...")

    max_attempts = 3
    base_delay = 2.0

    for attempt in range(max_attempts):
        try:
            # 8192 max_tokens ensures zero cutoffs; 120s timeout prevents gateway drops
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=8192,
                temperature=0.3,
                timeout=120.0,
            )

            # Robust output extraction: checks content and reasoning_content
            raw_content = response.choices[0].message.content
            if not raw_content:
                raw_content = getattr(response.choices[0].message, "reasoning_content", "")
            
            if not raw_content:
                raise ValueError("API returned an empty response (content is None)")
            
            reply = raw_content.strip()

            # Strip <think> tags if model uses chain-of-thought formatting
            if "<think>" in reply and "</think>" in reply:
                reply = reply.split("</think>")[-1].strip()

            # Clean JSON markdown formatting artifacts
            if "```" in reply:
                lines = reply.split("\n")
                json_lines = []
                in_block = False
                for line in lines:
                    if line.strip().startswith("```"):
                        in_block = not in_block
                        continue
                    if in_block or not line.strip().startswith("```"):
                        json_lines.append(line)
                reply = "\n".join(json_lines).strip()

            # Extract first valid JSON object in case of conversational prefix
            if "{" in reply and "}" in reply:
                start_idx = reply.find("{")
                end_idx = reply.rfind("}") + 1
                reply = reply[start_idx:end_idx]

            # Parse JSON
            diagnosis = json.loads(reply)
            
            expected_keys = ["root_cause", "iso_reference", "severity", "recommended_fix"]
            for key in expected_keys:
                if key not in diagnosis:
                    diagnosis[key] = "Not provided by AI"

            print(f"[AI Analyzer] TC {tc_id}: Severity = {diagnosis.get('severity', 'N/A')} (Attempt {attempt+1}/{max_attempts})")
            return diagnosis

        except json.JSONDecodeError:
            print(f"[AI Analyzer] TC {tc_id}: Response was not valid JSON, returning structured fallback.")
            return {
                "root_cause": reply if reply else "AI completed analysis but formatting was text-based.",
                "iso_reference": "ISO 11898-2 CAN Physical Layer Specification",
                "severity": "HIGH",
                "recommended_fix": "Verify bus termination (60 ohms total) and check wiring stub length.",
            }
            
        except Exception as e:
            print(f"[AI Analyzer] WARNING: Attempt {attempt+1}/{max_attempts} failed for TC {tc_id}: {str(e)}")
            if attempt < max_attempts - 1:
                sleep_time = base_delay * (2 ** attempt) # Exponential backoff: 2s, 4s
                print(f"[AI Analyzer] Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                print(f"[AI Analyzer] ERROR: All {max_attempts} attempts failed for TC {tc_id}.")
                return {
                    "root_cause": f"AI analysis completely failed after {max_attempts} retries: {str(e)}",
                    "iso_reference": "N/A",
                    "severity": "UNKNOWN",
                    "recommended_fix": "The external AI Provider is currently down or heavily overloaded. Please wait a few minutes and run the analysis again.",
                }


# ---------------------------------------------------------------------------
# 4. Full report analysis with 90/10 smart filtering
# ---------------------------------------------------------------------------

def analyze_full_report(report_data):
    """
    Apply the 90/10 smart filter to an entire extracted report.

    - PASS test cases: Skip AI call, mark with simple status
    - FAIL test cases: Send to Qwen for root-cause diagnosis

    Args:
        report_data: dict with keys 'metadata' and 'test_cases'

    Returns:
        The same report_data dict, enriched with 'ai_analysis' on each test case
        and a top-level 'analysis_summary' field.
    """
    test_cases = report_data.get("test_cases", [])
    total = len(test_cases)
    passed = 0
    failed = 0
    analyzed = 0

    print(f"\n[AI Analyzer] Starting 90/10 analysis on {total} test cases...")
    start_time = time.time()

    for tc in test_cases:
        verdict = tc.get("verdict", "unknown").lower()

        if verdict == "pass":
            # 90% path: Skip AI, just tag it
            tc["ai_analysis"] = {
                "status": "PASS",
                "message": "Test passed — no AI analysis needed."
            }
            # Storage Optimization (Smart Summary): Drop heavy tables for passed cases
            tc["measurements"] = []
            passed += 1

        elif verdict == "fail":
            # 10% path: Full AI diagnosis
            diagnosis = analyze_failed_test_case(tc)
            tc["ai_analysis"] = diagnosis
            failed += 1
            analyzed += 1

            # Continuous Learning Memory: Store failure pattern & verified fix
            try:
                report_no = report_data.get("metadata", {}).get("report_no", "Report")
                save_historical_failure({
                    "tc_id": tc.get("tc_id"),
                    "name": tc.get("name"),
                    "report_no": report_no,
                    "ecu": report_data.get("metadata", {}).get("project_name", "ECU Node"),
                    "root_cause": diagnosis.get("root_cause"),
                    "verified_fix": diagnosis.get("recommended_fix"),
                    "severity": diagnosis.get("severity")
                })
            except Exception as e:
                print(f"[AI Analyzer] Warning: Could not save historical memory: {e}")

        else:
            # Unknown/inconclusive verdict
            tc["ai_analysis"] = {
                "status": "UNKNOWN",
                "message": f"Verdict '{verdict}' is not pass/fail. Manual review recommended."
            }

    elapsed = time.time() - start_time

    # Add top-level analysis summary
    report_data["analysis_summary"] = {
        "total_test_cases": total,
        "passed": passed,
        "failed": failed,
        "ai_analyzed": analyzed,
        "analysis_time_seconds": round(elapsed, 2),
        "model_used": MODEL_NAME,
    }

    print(f"[AI Analyzer] Complete! {passed} passed, {failed} failed, "
          f"{analyzed} AI-analyzed in {elapsed:.1f}s")

    return report_data


# ---------------------------------------------------------------------------
# 5. Standalone test entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    """
    Run standalone to test AI analysis on the sample PDF.
    Usage: python ai_analyzer.py
    """
    from PDF_extraction import IVNReportParser

    pdf_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "IVN_Test_Report(15_57_18).pdf"
    )

    if not os.path.exists(pdf_path):
        print(f"[ERROR] Sample PDF not found at: {pdf_path}")
        exit(1)

    print("=" * 60)
    print("  NeuroNest AI Analyzer — Standalone Test")
    print("=" * 60)

    # Phase 1: Extract
    parser = IVNReportParser(pdf_path, output_dir="static/reports")
    report_data = parser.parse_report()
    print(f"\nExtracted {len(report_data['test_cases'])} test cases.")

    # Phase 3: Analyze
    enriched = analyze_full_report(report_data)

    # Print results
    print("\n" + "=" * 60)
    print("  ANALYSIS RESULTS")
    print("=" * 60)
    print(json.dumps(enriched["analysis_summary"], indent=2))

    for tc in enriched["test_cases"]:
        print(f"\n--- {tc['tc_id']}: {tc['name']} [{tc['verdict'].upper()}] ---")
        ai = tc.get("ai_analysis", {})
        if isinstance(ai, dict) and "root_cause" in ai:
            print(f"  Root Cause: {ai['root_cause']}")
            print(f"  ISO Ref:    {ai['iso_reference']}")
            print(f"  Severity:   {ai['severity']}")
            print(f"  Fix:        {ai['recommended_fix']}")
        else:
            print(f"  Status: {ai.get('message', ai.get('status', 'N/A'))}")
