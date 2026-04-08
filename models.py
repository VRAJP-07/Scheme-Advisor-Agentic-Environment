"""
Scheme Advisor Environment — Models
Typed Action, Observation, and State definitions.
"""

from typing import List, Optional, Dict, Any

from pydantic import BaseModel
from openenv.core.env_server import Action, Observation, State


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------

class SchemeAdvisorAction(Action):
    """
    An action the agent can take:
      - action_type: one of "submit_profile" | "query_scheme" | "request_documents"
      - profile: citizen profile fields (used when action_type == "submit_profile")
      - scheme_id: ID of scheme to query details about
      - document_request: list of document names to confirm availability

    On each step the agent should move toward:
      1. Submitting a complete citizen profile
      2. Identifying all eligible schemes
      3. Requesting the right documents for each eligible scheme
    """
    action_type: str = "submit_profile"       # "submit_profile" | "query_scheme" | "request_documents"
    profile: Dict[str, Any] = {}
    scheme_id: Optional[str] = None
    document_request: List[str] = []


# ---------------------------------------------------------------------------
# Observation
# ---------------------------------------------------------------------------

class SchemeAdvisorObservation(Observation):
    """
    What the agent sees after each step.
    """
    done: bool = False
    reward: Optional[float] = None

    # Current task context
    task_id: str = ""
    task_description: str = ""
    citizen_context: str = ""          # Narrative description of the citizen

    # Feedback from the last action
    feedback: str = ""
    submitted_profile: Dict[str, Any] = {}
    eligible_schemes: List[Dict[str, Any]] = []
    scheme_details: Optional[Dict[str, Any]] = None
    missing_profile_fields: List[str] = []
    required_documents: List[str] = []

    # Progress tracking
    steps_taken: int = 0
    max_steps: int = 10
    partial_score: float = 0.0


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class SchemeAdvisorState(State):
    """
    Full episode state (returned by state() endpoint).
    """
    episode_id: Optional[str] = None
    step_count: int = 0
    task_id: str = ""
    submitted_profile: Dict[str, Any] = {}
    queried_schemes: List[str] = []
    requested_documents: List[str] = []
    ground_truth_eligible_schemes: List[str] = []
    ground_truth_documents: Dict[str, List[str]] = {}
    score_breakdown: Dict[str, float] = {}
