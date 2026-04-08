"""
Scheme Advisor Environment — FastAPI Server

Exposes:
  POST /reset        — start a new episode (accepts optional task_id)
  POST /step         — execute one action
  GET  /state        — current episode state
  GET  /health       — liveness probe
  GET  /tasks        — list all tasks with action schema
  POST /grader       — grade a completed episode
  POST /baseline     — run baseline inference script and return scores
  WebSocket /ws      — persistent WebSocket interface (via OpenEnv core)
"""

import os
import sys
import json
import asyncio
import dataclasses
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import SchemeAdvisorAction, SchemeAdvisorObservation, SchemeAdvisorState
from schemes_db import SCHEMES, TASKS, get_all_scheme_ids, get_all_task_ids
from environment import SchemeAdvisorEnvironment


# ---------------------------------------------------------------------------
# App & global env registry (one env per WebSocket session)
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Scheme Advisor OpenEnv",
    description=(
        "An RL environment where AI agents learn to advise Indian citizens "
        "on government welfare scheme eligibility and required documents."
    ),
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Single shared environment for HTTP endpoints (demo / baseline use)
_http_env = SchemeAdvisorEnvironment()



# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------

class ResetRequest(BaseModel):
    task_id: Optional[str] = None


class StepRequest(BaseModel):
    action_type: str = "submit_profile"
    profile: dict = {}
    scheme_id: Optional[str] = None
    document_request: list = []


class GraderRequest(BaseModel):
    task_id: str
    submitted_profile: dict
    queried_schemes: list
    requested_documents: list


# ---------------------------------------------------------------------------
# Core HTTP endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {
        "status": "running",
        "environment": "scheme_advisor",
        "version": "1.0.0",
        "message": "Scheme Advisor OpenEnv Server",
        "endpoints": [
            "/health",
            "/reset (POST)",
            "/step (POST)",
            "/state",
            "/tasks",
            "/grader (POST)",
            "/baseline (POST)",
            "/ws (WebSocket)"
        ],
        "docs": "/docs"
    }

@app.get("/health")
def health():
    return {"status": "ok", "environment": "scheme_advisor", "version": "1.0.0"}

@app.post("/reset")
def reset(req: ResetRequest = ResetRequest()):
    global _http_env
    _http_env = SchemeAdvisorEnvironment(task_id=req.task_id)
    obs = _http_env.reset(task_id=req.task_id)
    logger.info(f"Reset with task_id: {req.task_id}")
    return JSONResponse(obs.model_dump())

@app.post("/step")
def step(req: StepRequest):
    # Check if environment is initialized
    if _http_env._task is None:
        raise HTTPException(status_code=400, detail="Call /reset before /step")

    action = SchemeAdvisorAction(
        action_type=req.action_type,
        profile=req.profile,
        scheme_id=req.scheme_id,
        document_request=req.document_request,
    )
    obs = _http_env.step(action)
    return JSONResponse(obs.model_dump())

@app.get("/state")
def state():
    # Check if environment is initialized
    if _http_env._task is None:
        raise HTTPException(status_code=400, detail="Call /reset before /state")

    return JSONResponse(_http_env.state.model_dump())

# ---------------------------------------------------------------------------
# Required hackathon endpoints
# ---------------------------------------------------------------------------

@app.get("/tasks")
def list_tasks():
    """Returns all tasks with action schema."""
    tasks_info = []
    for tid, task in TASKS.items():
        tasks_info.append({
            "task_id": tid,
            "difficulty": task["difficulty"],
            "citizen_context": task["citizen_context"],
            "required_profile_fields": task["required_profile_fields"],
            "ground_truth_eligible_schemes": task["ground_truth_eligible_schemes"],
        })

    return {
        "tasks": tasks_info,
        "action_schema": {
            "action_type": {
                "type": "string",
                "enum": ["submit_profile", "query_scheme", "request_documents"],
                "description": "Which action to take",
            },
            "profile": {
                "type": "object",
                "description": (
                    "Dict of citizen profile fields. Used with action_type='submit_profile'. "
                    "Keys: age, gender, location_type (rural/urban), occupation, land_hectares, "
                    "bpl_card, annual_income_inr, house_type (kutcha/pucca/rented/none), "
                    "has_lpg_connection, has_girl_child_below_10, is_government_employee, "
                    "is_income_taxpayer, sector (organised/unorganised), has_epf, "
                    "caste_category (GEN/OBC/SC/ST), is_student, breadwinner_died, "
                    "street_vendor_before_march_2020."
                ),
            },
            "scheme_id": {
                "type": "string",
                "enum": get_all_scheme_ids(),
                "description": "Scheme to query details about. Used with action_type='query_scheme'.",
            },
            "document_request": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "List of documents required for all eligible schemes. "
                    "Used with action_type='request_documents'. This finalises the episode."
                ),
            },
        },
        "available_schemes": list(SCHEMES.keys()),
    }

@app.post("/grader")
def grader(request: Request, req: GraderRequest):
    """
    Grade a completed episode externally (stateless).
    Accepts submitted_profile, queried_schemes, requested_documents.
    Returns score 0.0–1.0 with breakdown.
    """
    # Validate Content-Type
    if not "application/json" in request.headers.get("content-type", "").lower():
        raise HTTPException(status_code=400, detail="Content-Type must be application/json")

    task = TASKS.get(req.task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Unknown task_id: {req.task_id}")

    # Validate required fields
    if not req.submitted_profile:
        raise HTTPException(status_code=400, detail="submitted_profile is required")
    if not req.queried_schemes:
        raise HTTPException(status_code=400, detail="queried_schemes is required")
    if not req.requested_documents:
        raise HTTPException(status_code=400, detail="requested_documents is required")
    # Use environment's own grading logic for consistency
    temp_env = SchemeAdvisorEnvironment()
    temp_env._task = task
    temp_env._submitted_profile = req.submitted_profile
    temp_env._queried_schemes = req.queried_schemes
    temp_env._requested_documents = req.requested_documents
    
    score, breakdown = temp_env._compute_final_score()

    return {
        "task_id": req.task_id,
        "score": score,
        "breakdown": breakdown,
        "ground_truth_eligible_schemes": list(task["ground_truth_eligible_schemes"]),
        "agent_identified_schemes": list(req.queried_schemes),
    }


@app.post("/baseline")
def baseline(request: Request):
    """
    Trigger the baseline inference script and return scores for all 3 tasks.
    Uses a simple rule-based agent (no LLM call) for reproducibility.
    """
    # Validate Content-Type
    if not "application/json" in request.headers.get("content-type", "").lower():
        raise HTTPException(status_code=400, detail="Content-Type must be application/json")

    # Import baseline functions directly to avoid subprocess issues
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    try:
        from baseline import run_agent_episode, TASK_IDS

        logger.info("Running baseline agent...")
        # Create a simple client that uses the current server instance
        class LocalEnvClient:
            def __init__(self):
                self.env = SchemeAdvisorEnvironment()
            
            def reset(self, task_id=None):
                self.env = SchemeAdvisorEnvironment(task_id=task_id)
                return self.env.reset().model_dump()
            
            def step(self, action_type, profile=None, scheme_id=None, document_request=None):
                from models import SchemeAdvisorAction
                action = SchemeAdvisorAction(
                    action_type=action_type,
                    profile=profile or {},
                    scheme_id=scheme_id,
                    document_request=document_request or [],
                )
                return self.env.step(action).model_dump()
            
            def grade(self, task_id, submitted_profile, queried_schemes, requested_documents):
                from fastapi import HTTPException
                # Use environment's own grading logic for consistency
                temp_env = SchemeAdvisorEnvironment()
                temp_env._task = TASKS.get(task_id)
                if not temp_env._task:
                    raise HTTPException(status_code=404, detail=f"Unknown task_id: {task_id}")
                
                temp_env._submitted_profile = submitted_profile
                temp_env._queried_schemes = queried_schemes
                temp_env._requested_documents = requested_documents
                
                score, breakdown = temp_env._compute_final_score()
                return {
                    "task_id": task_id,
                    "score": score,
                    "breakdown": breakdown,
                    "ground_truth_eligible_schemes": list(temp_env._task["ground_truth_eligible_schemes"]),
                    "agent_identified_schemes": list(queried_schemes),
                }
        
        # Run baseline for all tasks
        env = LocalEnvClient()
        results = {}
        for task_id in TASK_IDS:
            try:
                result = run_agent_episode(env, task_id, verbose=False)
                results[task_id] = result
            except Exception as e:
                results[task_id] = {"task_id": task_id, "score": 0.0, "error": str(e)}

        # Calculate average score
        average_score = round(
            sum(r.get("score", 0) for r in results.values()) / max(len(results), 1), 4
        )
        
        return {
            "model": "rule-based",
            "tasks": results,
            "average_score": average_score,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Baseline failed: {str(e)}")


# ---------------------------------------------------------------------------
# WebSocket endpoint (OpenEnv standard)
# ---------------------------------------------------------------------------

class _WSSession:
    def __init__(self):
        self.env = SchemeAdvisorEnvironment()
        self.obs = None


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    session = _WSSession()
    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            cmd = msg.get("command", "")

            if cmd == "reset":
                task_id = msg.get("task_id", None)
                session.env = SchemeAdvisorEnvironment(task_id=task_id)
                obs = session.env.reset()
                session.obs = obs
                await ws.send_text(json.dumps({"type": "observation", "data": obs.model_dump()}))

            elif cmd == "step":
                action = SchemeAdvisorAction(
                    action_type=msg.get("action_type", "submit_profile"),
                    profile=msg.get("profile", {}),
                    scheme_id=msg.get("scheme_id"),
                    document_request=msg.get("document_request", []),
                )
                obs = session.env.step(action)
                session.obs = obs
                await ws.send_text(json.dumps({"type": "observation", "data": obs.model_dump()}))

            elif cmd == "state":
                await ws.send_text(json.dumps({"type": "state", "data": session.env.state.model_dump()}))

            else:
                await ws.send_text(json.dumps({"type": "error", "message": f"Unknown command: {cmd}"}))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass


def main():
    """Main entry point for OpenEnv server"""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860, workers=1)


if __name__ == "__main__":
    main()
