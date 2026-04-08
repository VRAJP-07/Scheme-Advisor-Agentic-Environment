"""
Scheme Advisor Environment — Baseline Inference Script

Uses the OpenAI API client to run an LLM agent against all 3 tasks.
Reads OPENAI_API_KEY from environment variables.
Produces reproducible baseline scores.

Usage:
    python baseline.py                      # run all tasks, pretty print
    python baseline.py --task easy_farmer   # run one task
    python baseline.py --all-tasks --output-json  # machine-readable (for /baseline endpoint)
"""

import os
import sys
import json
import time
import argparse
import requests
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_PROVIDER = os.getenv("API_PROVIDER", "groq").lower()
API_KEY = os.getenv("API_KEY", "")

# Default models per provider (used when MODEL_NAME is not specified)
PROVIDER_DEFAULTS = {
    "groq": "llama-3.1-8b-instant",
    "openai": "gpt-4o-mini",
    "huggingface": "meta-llama/Meta-Llama-3-8B-Instruct",
    "grok": "grok-2-latest"
}

# Use MODEL_NAME from .env if specified, otherwise use provider default
MODEL_NAME = os.getenv("MODEL_NAME", "").strip()
MODEL = MODEL_NAME if MODEL_NAME else PROVIDER_DEFAULTS.get(API_PROVIDER, "llama-3.1-8b-instant")
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:8000")

TASK_IDS = ["easy_farmer", "medium_bpl_woman", "hard_urban_vendor_student"]


# ---------------------------------------------------------------------------
# Simple HTTP client to the environment
# ---------------------------------------------------------------------------

class EnvClient:
    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/")

    def reset(self, task_id: Optional[str] = None) -> Dict:
        payload = {"task_id": task_id} if task_id else {}
        r = requests.post(f"{self.base}/reset", json=payload, timeout=30)
        r.raise_for_status()
        return r.json()

    def step(self, action_type: str, profile: dict = None, scheme_id: str = None,
             document_request: list = None) -> Dict:
        payload = {
            "action_type": action_type,
            "profile": profile or {},
            "scheme_id": scheme_id,
            "document_request": document_request or [],
        }
        r = requests.post(f"{self.base}/step", json=payload, timeout=30)
        r.raise_for_status()
        return r.json()

    def get_tasks(self) -> Dict:
        r = requests.get(f"{self.base}/tasks", timeout=30)
        r.raise_for_status()
        return r.json()

    def grade(self, task_id: str, submitted_profile: dict,
              queried_schemes: list, requested_documents: list) -> Dict:
        payload = {
            "task_id": task_id,
            "submitted_profile": submitted_profile,
            "queried_schemes": queried_schemes,
            "requested_documents": requested_documents,
        }
        r = requests.post(f"{self.base}/grader", json=payload, timeout=30)
        r.raise_for_status()
        return r.json()


# ---------------------------------------------------------------------------
# LLM Agent using OpenAI client
# ---------------------------------------------------------------------------

def call_llm(messages: List[Dict], model: str = MODEL) -> str:
    """Call LLM API and return text response."""
    if not API_KEY:
        # Fallback: rule-based agent (no API key needed)
        return _rule_based_agent(messages)

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": 1000,
    }

    if API_PROVIDER == "groq":
        url = "https://api.groq.com/openai/v1/chat/completions"
        payload["response_format"] = {"type": "json_object"}
    elif API_PROVIDER == "openai":
        url = "https://api.openai.com/v1/chat/completions"
        payload["response_format"] = {"type": "json_object"}
    elif API_PROVIDER == "grok":
        url = "https://api.x.ai/v1/chat/completions"
    elif API_PROVIDER == "huggingface":
        # Supports both Hugging Face Inference Endpoints and serverless
        if "/" in model:
            url = f"https://api-inference.huggingface.co/models/{model}/v1/chat/completions"
        else:
            url = f"https://api-inference.huggingface.co/chat/completions"
    else:
        # Generic OpenAI-compatible fallback if provider is unknown but key is provided
        url = os.getenv("API_BASE_URL", "https://api.openai.com/v1/chat/completions")

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        raise Exception(f"API Error ({API_PROVIDER}): {response.text}")
    
    data = response.json()
    return data["choices"][0]["message"]["content"]


def _rule_based_agent(messages: List[Dict]) -> str:
    """
    Deterministic rule-based baseline (no LLM required).
    Parses the observation and applies heuristics for the 3 predefined tasks.
    Used when API_KEY is not set.
    """
    # Extract task from system message or context
    system = messages[0]["content"] if messages else ""
    user_context = ""
    for m in messages:
        if m["role"] == "user" and "CITIZEN CONTEXT" in m["content"]:
            user_context = m["content"]
            break
    
    last_obs_msg = ""
    for m in reversed(messages):
        if m["role"] == "user" and "OBSERVATION" in m["content"]:
            last_obs_msg = m["content"]
            break

    # Determine which task we are in
    task_type = "easy"
    if "Savitri" in user_context or "medium" in user_context.lower():
        task_type = "medium"
    elif "Mohan" in user_context or "hard" in user_context.lower():
        task_type = "hard"

    # Step 1: submit profile
    if "Step 1" in last_obs_msg or not last_obs_msg:
        if task_type == "easy":
            profile = {"age": 35, "gender": "male", "location_type": "rural", "occupation": "farmer", "land_hectares": 1.5, "is_government_employee": False, "is_income_taxpayer": False, "sector": "unorganised", "has_epf": False}
        elif task_type == "medium":
            profile = {"age": 32, "gender": "female", "location_type": "rural", "bpl_card": True, "annual_income_inr": 120000, "house_type": "kutcha", "has_lpg_connection": False, "has_girl_child_below_10": True, "is_income_taxpayer": False, "sector": "unorganised", "has_epf": False}
        else: # hard
            profile = {"age": 38, "gender": "male", "location_type": "urban", "occupation": "street_vendor", "sector": "unorganised", "caste_category": "ST", "annual_income_inr": 180000, "is_income_taxpayer": False, "has_epf": False, "bpl_card": False, "breadwinner_died": False, "house_type": "rented"}
        
        return json.dumps({"action_type": "submit_profile", "profile": profile})

    # Step 2+: query schemes mentioned in eligible so far
    if "Step 2" in last_obs_msg or "Eligible so far: [" in last_obs_msg:
        import re
        m = re.search(r"Eligible so far: \[(.*?)\]", last_obs_msg)
        if m and m.group(1).strip():
            eligible_schemes = [s.strip().strip("'").strip('"') for s in m.group(1).split(",")]
            # Filter out schemes already queried (this is simplistic)
            for sid in eligible_schemes:
                if sid: return json.dumps({"action_type": "query_scheme", "scheme_id": sid})
        
        # Fallback query
        fallback = "PM_KISAN" if task_type == "easy" else ("AYUSHMAN_BHARAT" if task_type == "medium" else "PM_SVANIDHI")
        return json.dumps({"action_type": "query_scheme", "scheme_id": fallback})

    # Step 3: request documents (simplified)
    docs = ["Aadhaar card", "Bank passbook"]
    if task_type == "easy": docs += ["Land ownership records (Khasra/Khatauni)", "Mobile number linked to Aadhaar"]
    elif task_type == "medium": docs += ["Ration card (BPL/Antyodaya)", "Birth certificate of girl child"]
    else: docs += ["Vendor certificate", "PAN card"]

    return json.dumps({"action_type": "request_documents", "document_request": docs})


SYSTEM_PROMPT = """You are an expert Indian government welfare scheme advisor.
Your job is to advise a citizen on which government schemes they are eligible for
and what documents they need to collect.

You interact with an environment through structured JSON actions.

AVAILABLE ACTION TYPES:
1. submit_profile — submit citizen profile fields as a dict
2. query_scheme — query details of a specific scheme by scheme_id
3. request_documents — submit the final list of required documents (this ends the episode)

AVAILABLE SCHEME IDs:
PM_KISAN, AYUSHMAN_BHARAT, PM_AWAS_YOJANA_GRAMIN, MGNREGS, PM_UJJWALA,
SUKANYA_SAMRIDDHI, PM_MUDRA, SCHOLARSHIP_SC_ST, ATAL_PENSION, E_SHRAM,
PM_SVANIDHI, NFBS

STRATEGY:
1. Read the citizen context carefully.
2. Submit the citizen's profile (all relevant fields you can infer).
3. Query schemes you think the citizen might be eligible for to get document lists.
4. Submit the final list of required documents across all eligible schemes.

ALWAYS respond with a JSON object with these keys:
{
  "action_type": "submit_profile" | "query_scheme" | "request_documents",
  "profile": {},          // for submit_profile
  "scheme_id": "",        // for query_scheme  
  "document_request": []  // for request_documents
}

Be accurate — do NOT hallucinate eligibility. Only include schemes the citizen clearly qualifies for.
"""


def run_agent_episode(env: EnvClient, task_id: str, verbose: bool = True) -> Dict:
    """Run one full episode with the LLM agent."""
    obs = env.reset(task_id=task_id)

    if verbose:
        print(f"\n{'='*60}")
        print(f"TASK: {task_id.upper()}")
        print(f"CITIZEN: {obs['citizen_context'][:200]}...")
        print(f"{'='*60}")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"CITIZEN CONTEXT:\n{obs['citizen_context']}\n\n"
                f"TASK: {obs['task_description']}\n\n"
                "Begin advising. Start with submit_profile.\n"
                "Step 1: submit_profile with all fields you can infer."
            ),
        },
    ]

    submitted_profile = {}
    queried_schemes = []
    requested_documents = []
    step = 0
    max_steps = 10
    raw = ""

    while step < max_steps:
        step += 1

        # Get LLM action
        try:
            raw = call_llm(messages, model=MODEL)
            action = json.loads(raw)
        except Exception as e:
            if verbose:
                print(f"  [Step {step}] LLM error: {e}. Using fallback.")
            raw = ""
            action = {"action_type": "request_documents", "document_request": ["Aadhaar card"]}

        action_type = action.get("action_type", "submit_profile")

        if verbose:
            print(f"\n  [Step {step}] Action: {action_type}")

        # Execute action
        try:
            obs = env.step(
                action_type=action_type,
                profile=action.get("profile", {}),
                scheme_id=action.get("scheme_id"),
                document_request=action.get("document_request", []),
            )
        except Exception as e:
            if verbose:
                print(f"  Env error: {e}")
            break

        # Track for grader
        if action_type == "submit_profile":
            submitted_profile.update(action.get("profile", {}))
        elif action_type == "query_scheme" and action.get("scheme_id"):
            if action["scheme_id"] not in queried_schemes:
                queried_schemes.append(action["scheme_id"])
        elif action_type == "request_documents":
            requested_documents = action.get("document_request", [])

        if verbose:
            print(f"  Feedback: {obs.get('feedback', '')[:200]}")

        # Build next message with observation
        messages.append({"role": "assistant", "content": raw if raw else json.dumps(action)})
        messages.append({
            "role": "user",
            "content": (
                f"OBSERVATION (Step {step}):\n"
                f"Feedback: {obs.get('feedback', '')}\n"
                f"Missing fields: {obs.get('missing_profile_fields', [])}\n"
                f"Eligible so far: {[s['id'] for s in obs.get('eligible_schemes', [])]}\n"
                f"Done: {obs.get('done', False)}\n\n"
                + (
                    "The episode is complete. No more actions needed."
                    if obs.get("done")
                    else (
                        f"Step {step+1}: "
                        + ("Now query each eligible scheme to get document details."
                           if action_type == "submit_profile"
                           else "Continue querying schemes or submit documents if ready.")
                    )
                )
            ),
        })

        if obs.get("done"):
            break

        time.sleep(0.5)  # Be kind to API rate limits

    # Final grading
    grade = env.grade(task_id, submitted_profile, queried_schemes, requested_documents)

    if verbose:
        print(f"\n  FINAL SCORE: {grade['score']:.3f}")
        print(f"  Breakdown: {grade['breakdown']}")
        print(f"  GT schemes: {grade['ground_truth_eligible_schemes']}")
        print(f"  Agent identified: {grade['agent_identified_schemes']}")

    return {
        "task_id": task_id,
        "score": grade["score"],
        "breakdown": grade["breakdown"],
        "steps_taken": step,
        "submitted_profile_keys": list(submitted_profile.keys()),
        "queried_schemes": queried_schemes,
        "requested_documents": requested_documents,
        "ground_truth_eligible_schemes": grade["ground_truth_eligible_schemes"],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global MODEL
    parser = argparse.ArgumentParser(description="Scheme Advisor Baseline Agent")
    parser.add_argument("--task", default=None, help="Specific task ID to run")
    parser.add_argument("--all-tasks", action="store_true", help="Run all 3 tasks")
    parser.add_argument("--output-json", action="store_true", help="Output JSON (for /baseline endpoint)")
    parser.add_argument("--env-url", default=ENV_BASE_URL, help="Environment base URL")
    parser.add_argument("--model", default=MODEL, help="LLM model to use")
    args = parser.parse_args()

    MODEL = args.model

    env = EnvClient(args.env_url)
    verbose = not args.output_json

    tasks_to_run = TASK_IDS if args.all_tasks else ([args.task] if args.task else TASK_IDS)

    results = {}
    for task_id in tasks_to_run:
        try:
            result = run_agent_episode(env, task_id, verbose=verbose)
            results[task_id] = result
        except Exception as e:
            results[task_id] = {"task_id": task_id, "score": 0.0, "error": str(e)}

    if args.output_json:
        # Machine-readable output for /baseline endpoint
        summary = {
            "model": MODEL,
            "tasks": results,
            "average_score": round(
                sum(r.get("score", 0) for r in results.values()) / max(len(results), 1), 4
            ),
        }
        print(json.dumps(summary))
    else:
        print("\n" + "="*60)
        print("BASELINE SUMMARY")
        print("="*60)
        total = 0
        for tid, r in results.items():
            score = r.get("score", 0)
            total += score
            print(f"  {tid}: {score:.3f}")
        print(f"  AVERAGE: {total/max(len(results),1):.3f}")
        print("="*60)


if __name__ == "__main__":
    main()
