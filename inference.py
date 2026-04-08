"""
inference.py — SchemeAdvisor OpenEnv agent

Connects to the already-running environment server via its HTTP REST API
(POST /reset, POST /step). No Docker required — the platform starts the
server before running this script.

Environment variables:
  OPENENV_ENV_URL  — base URL of the running server (default: http://localhost:7860)
  ENV_URL          — fallback alias for OPENENV_ENV_URL
  API_BASE_URL     — OpenAI-compatible API base URL
  MODEL_NAME       — model name to use
  API_KEY / HF_TOKEN — API key
"""

import asyncio
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

import requests
from openai import OpenAI
from pydantic import BaseModel

# ── Configuration ──────────────────────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "gpt-3.5-turbo")
HF_TOKEN     = os.getenv("HF_TOKEN",     "")
API_KEY      = os.getenv("API_KEY", HF_TOKEN) or "dummy-key"

# URL of the already-running environment server (set by the platform)
ENV_BASE_URL = os.getenv(
    "OPENENV_ENV_URL",
    os.getenv("ENV_URL", "http://localhost:7860"),
).rstrip("/")

TASK_NAME               = "scheme_advisor"
BENCHMARK               = "scheme-advisor-env"
MAX_STEPS               = 10
MAX_TOTAL_REWARD        = 1.0
SUCCESS_SCORE_THRESHOLD = 0.6
HTTP_TIMEOUT            = 30   # seconds per request


# ── Action model (matches server's StepRequest) ───────────────────────────
class SchemeAdvisorAction(BaseModel):
    action_type: str
    profile: Optional[Dict[str, Any]] = None
    scheme_id: Optional[str] = None
    document_request: Optional[List[str]] = None


# ── Logging ───────────────────────────────────────────────────────────────
def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float,
             done: bool, error: Optional[str] = None) -> None:
    err = f" error={error!r}" if error else ""
    print(
        f"[STEP] step={step} action={action!r} "
        f"reward={reward:.4f} done={done}{err}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float,
            rewards: List[float]) -> None:
    rw = " ".join(f"{r:.4f}" for r in rewards)
    print(
        f"[END] success={success} steps={steps} "
        f"score={score:.4f} rewards=[{rw}]",
        flush=True,
    )


# ── HTTP helpers ───────────────────────────────────────────────────────────
def wait_for_server(base_url: str, retries: int = 10, delay: float = 2.0) -> None:
    """Wait until the environment server is responding on /health."""
    for attempt in range(retries):
        try:
            r = requests.get(f"{base_url}/health", timeout=5)
            if r.status_code == 200:
                print(f"[INFO] Server ready at {base_url}", flush=True)
                return
        except requests.RequestException:
            pass
        print(f"[INFO] Waiting for server ({attempt + 1}/{retries})…", flush=True)
        time.sleep(delay)
    raise RuntimeError(f"Server at {base_url} did not become ready after {retries} attempts")


def http_reset(base_url: str, task_id: Optional[str] = None) -> Dict[str, Any]:
    """POST /reset and return the observation dict."""
    payload = {"task_id": task_id} if task_id else {}
    r = requests.post(f"{base_url}/reset", json=payload, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    return r.json()


def http_step(base_url: str, action: SchemeAdvisorAction) -> Dict[str, Any]:
    """POST /step and return the observation dict."""
    payload = {
        "action_type": action.action_type,
        "profile": action.profile or {},
        "scheme_id": action.scheme_id,
        "document_request": action.document_request or [],
    }
    r = requests.post(f"{base_url}/step", json=payload, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    return r.json()


# ── LLM helper ────────────────────────────────────────────────────────────
def get_action_from_model(
    client: OpenAI,
    step: int,
    last_observation: str,
    last_reward: float,
    history: List[str],
) -> SchemeAdvisorAction:
    """Call the LLM and parse its JSON response into a SchemeAdvisorAction."""

    system_prompt = (
        "You are a government welfare scheme advisor in India.\n"
        "Respond ONLY with a single valid JSON object — no markdown, no extra text.\n"
        "Required field:\n"
        '  "action_type": one of "submit_profile", "query_scheme", "request_documents"\n'
        "Optional fields (include only when relevant):\n"
        '  "profile": object — citizen profile key-value pairs '
        '(e.g. age, income, gender, caste, state, occupation)\n'
        '  "scheme_id": string — government scheme identifier\n'
        '  "document_request": array of strings — required document names\n\n'
        "Strategy:\n"
        "1. Start by submitting a detailed citizen profile.\n"
        "2. Then query schemes the citizen is eligible for.\n"
        "3. Finally request documents for the best matching scheme.\n"
    )

    history_text = "\n".join(history) if history else "None yet."
    user_prompt = (
        f"Step {step}/{MAX_STEPS}  |  Last reward: {last_reward:.2f}\n\n"
        f"Observation:\n{last_observation}\n\n"
        f"History:\n{history_text}"
    )

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=512,
            temperature=0.2,
        )
        raw = (response.choices[0].message.content or "").strip()

        # Strip markdown fences if present
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1] if len(parts) > 1 else raw
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        data = json.loads(raw)
        return SchemeAdvisorAction(**data)

    except Exception as exc:
        print(f"[WARN] LLM/parse error at step {step}: {exc}", flush=True)
        # Fallback: first try profile submission, then query, then docs
        if step <= 3:
            return SchemeAdvisorAction(
                action_type="submit_profile",
                profile={
                    "age": 35, "gender": "female", "income": 15000,
                    "caste": "SC", "state": "Uttar Pradesh",
                    "occupation": "farmer", "bpl": True,
                    "land_owned_acres": 1.5,
                },
            )
        elif step <= 6:
            return SchemeAdvisorAction(action_type="query_scheme", scheme_id="PM-KISAN")
        else:
            return SchemeAdvisorAction(
                action_type="request_documents",
                document_request=["Aadhaar card", "land records", "bank passbook"],
            )


# ── Main ──────────────────────────────────────────────────────────────────
def main() -> None:
    print(f"[INFO] Environment server: {ENV_BASE_URL}", flush=True)

    # Wait for server to be ready
    wait_for_server(ENV_BASE_URL)

    llm_client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

    try:
        # Reset environment
        obs_data = http_reset(ENV_BASE_URL)
        last_observation = json.dumps(obs_data, ensure_ascii=False)
        last_reward = 0.0
        done = obs_data.get("done", False)

        for step in range(1, MAX_STEPS + 1):
            if done:
                break

            action = get_action_from_model(
                llm_client, step, last_observation, last_reward, history
            )
            action_str = action.model_dump_json()

            try:
                obs_data = http_step(ENV_BASE_URL, action)
                reward = float(obs_data.get("reward") or 0.0)
                done = bool(obs_data.get("done", False))
                last_observation = json.dumps(obs_data, ensure_ascii=False)
                error = None
            except Exception as exc:
                print(f"[WARN] http_step error at step {step}: {exc}", flush=True)
                reward = 0.0
                done = True
                error = str(exc)

            rewards.append(reward)
            steps_taken = step
            last_reward = reward

            log_step(step=step, action=action_str, reward=reward,
                     done=done, error=error)
            history.append(f"Step {step}: {action.action_type} -> reward {reward:+.2f}")

            if done:
                break

        score = sum(rewards) / MAX_TOTAL_REWARD if MAX_TOTAL_REWARD > 0 else 0.0
        score = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as exc:
        print(f"[ERROR] Episode failed: {exc}", flush=True)
        # Do NOT re-raise — log_end must always run and exit 0

    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


if __name__ == "__main__":
    main()
