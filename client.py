"""
Scheme Advisor Environment — Client

Provides SchemeAdvisorEnv, a typed HTTP client for the Scheme Advisor environment.
Compatible with both async and sync (via .sync()) usage patterns.

Usage:
    # Async
    async with SchemeAdvisorEnv(base_url="http://localhost:8000") as env:
        obs = await env.reset()
        obs = await env.step(SchemeAdvisorAction(action_type="submit_profile", profile={...}))

    # Sync
    with SchemeAdvisorEnv(base_url="http://localhost:8000").sync() as env:
        obs = env.reset()
        obs = env.step(SchemeAdvisorAction(action_type="submit_profile", profile={...}))
"""

import dataclasses
from typing import Optional

from openenv.core import GenericEnvClient

from models import SchemeAdvisorAction, SchemeAdvisorObservation, SchemeAdvisorState


def _safe_list(val, default=None):
    if val is None:
        return default if default is not None else []
    return val


class SchemeAdvisorEnv(GenericEnvClient):
    """
    Typed HTTP client for the Scheme Advisor OpenEnv environment.
    """

    def _step_payload(self, action: SchemeAdvisorAction) -> dict:
        return {
            "action_type": action.action_type,
            "profile": action.profile or {},
            "scheme_id": action.scheme_id,
            "document_request": action.document_request or [],
        }

    def _parse_result(self, payload: dict):
        obs = SchemeAdvisorObservation(
            done=payload.get("done", False),
            reward=payload.get("reward"),
            task_id=payload.get("task_id", ""),
            task_description=payload.get("task_description", ""),
            citizen_context=payload.get("citizen_context", ""),
            feedback=payload.get("feedback", ""),
            eligible_schemes=_safe_list(payload.get("eligible_schemes")),
            scheme_details=payload.get("scheme_details"),
            missing_profile_fields=_safe_list(payload.get("missing_profile_fields")),
            required_documents=_safe_list(payload.get("required_documents")),
            steps_taken=payload.get("steps_taken", 0),
            max_steps=payload.get("max_steps", 10),
            partial_score=payload.get("partial_score", 0.0),
        )
        return obs

    def _parse_state(self, payload: dict) -> SchemeAdvisorState:
        return SchemeAdvisorState(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
            task_id=payload.get("task_id", ""),
            submitted_profile=payload.get("submitted_profile", {}),
            queried_schemes=_safe_list(payload.get("queried_schemes")),
            requested_documents=_safe_list(payload.get("requested_documents")),
            ground_truth_eligible_schemes=_safe_list(payload.get("ground_truth_eligible_schemes")),
            ground_truth_documents=payload.get("ground_truth_documents", {}),
            score_breakdown=payload.get("score_breakdown", {}),
        )
