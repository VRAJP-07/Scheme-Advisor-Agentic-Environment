"""
Scheme Advisor Environment — Server-side Environment Logic

Implements the OpenEnv Environment base class:
  - reset()  → starts a new episode
  - step()   → processes one agent action
  - state    → returns current episode state

Reward design:
  - Partial credit for submitting relevant profile fields
  - Reward for identifying correct eligible schemes
  - Reward for correctly requesting required documents
  - Penalty for hallucinating schemes the citizen isn't eligible for
  - Bonus for completing all objectives

Fixes applied:
  - BUG FIX: __init__ now initialises _task, _state, _submitted_profile,
    _queried_schemes, _requested_documents so that step() / state accesses
    before reset() return a clear error rather than AttributeError.
"""

import uuid
import random
from typing import Optional

from openenv.core.env_server import Environment

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import SchemeAdvisorAction, SchemeAdvisorObservation, SchemeAdvisorState
from schemes_db import SCHEMES, TASKS, check_eligibility


MAX_STEPS = 10


class SchemeAdvisorEnvironment(Environment):
    def __init__(
        self,
        episode_id=None,
        step_count=0,
        task_id=None,
        submitted_profile=None,
        queried_schemes=None,
        requested_documents=None,
        ground_truth_eligible_schemes=None,
        ground_truth_documents=None,
        score_breakdown=None,
    ):
        self.episode_id = episode_id
        self.step_count = step_count
        self.task_id = task_id

        self.submitted_profile = submitted_profile or {}
        self.queried_schemes = queried_schemes or []
        self.requested_documents = requested_documents or []

        self.ground_truth_eligible_schemes = ground_truth_eligible_schemes or []
        self.ground_truth_documents = ground_truth_documents or []

        self.score_breakdown = score_breakdown or {}

        # FIX: initialise private attributes so step()/state work before reset()
        self._task = None
        self._task_id = task_id
        self._submitted_profile = submitted_profile or {}
        self._queried_schemes = queried_schemes or []
        self._requested_documents = requested_documents or []
        self._state = SchemeAdvisorState(
            episode_id=episode_id,
            step_count=step_count,
            task_id=task_id or "",
            submitted_profile=self._submitted_profile,
            queried_schemes=self._queried_schemes,
            requested_documents=self._requested_documents,
            ground_truth_eligible_schemes=ground_truth_eligible_schemes or [],
            ground_truth_documents=ground_truth_documents or {},
            score_breakdown=score_breakdown or {},
        )

    # ------------------------------------------------------------------
    # reset
    # ------------------------------------------------------------------

    def reset(self, task_id: Optional[str] = None) -> SchemeAdvisorObservation:
        task_ids = list(TASKS.keys())

        # If task_id is None, try to use the one from __init__
        if task_id is None:
            task_id = self._task_id
        
        # If still None, pick a random task
        if task_id is None:
            task_id = random.choice(task_ids)

        self._task_id = task_id
        if task_id not in TASKS:
             # Try case-insensitive match
             found = False
             for tid in TASKS:
                 if tid.lower() == task_id.lower():
                     task_id = tid
                     self._task_id = tid
                     found = True
                     break
             
             if not found:
                 return self._error_obs(f"Unknown task_id '{task_id}'. Available: {list(TASKS.keys())}")

        self._task = TASKS[task_id]

        self._submitted_profile = {}
        self._queried_schemes = []
        self._requested_documents = []

        self._state = SchemeAdvisorState(
            episode_id=str(uuid.uuid4()),
            step_count=0,
            task_id=task_id,
            submitted_profile={},
            queried_schemes=[],
            requested_documents=[],
            ground_truth_eligible_schemes=self._task["ground_truth_eligible_schemes"],
            ground_truth_documents=self._task["ground_truth_documents"],
            score_breakdown={},
        )

        return SchemeAdvisorObservation(
            done=False,
            reward=None,
            task_id=task_id,
            task_description=(
                f"[{self._task['difficulty'].upper()} TASK] "
                "You are a government scheme advisor. Read the citizen's context carefully. "
                "Then:\n"
                "  1. Use action_type='submit_profile' to submit relevant profile fields.\n"
                "  2. Use action_type='query_scheme' with scheme_id to learn about a specific scheme.\n"
                "  3. Use action_type='request_documents' with document_request list to specify "
                "required documents for eligible schemes.\n"
                "Your goal: identify ALL eligible schemes accurately (no hallucinations) and "
                "specify correct documents for each. You have up to 10 steps."
            ),
            citizen_context=self._task["citizen_context"],
            feedback="Episode started. Read the citizen context and begin advising.",
            eligible_schemes=[],
            scheme_details=None,
            missing_profile_fields=self._task["required_profile_fields"],
            required_documents=[],
            steps_taken=0,
            max_steps=MAX_STEPS,
            partial_score=0.0,
        )

    # ------------------------------------------------------------------
    # step
    # ------------------------------------------------------------------

    def step(self, action: SchemeAdvisorAction) -> SchemeAdvisorObservation:
        # FIX: guard against step() called before reset() — _task is None until reset()
        if self._task is None:
            return self._error_obs("Call reset() before step().")

        self._state.step_count += 1
        steps = self._state.step_count

        action_type = action.action_type.strip().lower()

        # ---- submit_profile ----
        if action_type == "submit_profile":
            return self._handle_submit_profile(action, steps)

        # ---- query_scheme ----
        elif action_type == "query_scheme":
            return self._handle_query_scheme(action, steps)

        # ---- request_documents ----
        elif action_type == "request_documents":
            return self._handle_request_documents(action, steps)

        else:
            return self._make_obs(
                feedback=f"Unknown action_type '{action.action_type}'. "
                         "Use 'submit_profile', 'query_scheme', or 'request_documents'.",
                steps=steps,
            )

    # ------------------------------------------------------------------
    # state property
    # ------------------------------------------------------------------

    @property
    def state(self) -> SchemeAdvisorState:
        return self._state

    # ------------------------------------------------------------------
    # Internal handlers
    # ------------------------------------------------------------------

    def _handle_submit_profile(self, action: SchemeAdvisorAction, steps: int) -> SchemeAdvisorObservation:
        if not action.profile:
            return self._make_obs(
                feedback="'submit_profile' action requires a non-empty 'profile' dict.",
                steps=steps,
            )

        # Basic normalization for common field types
        normalized_profile = {}
        for k, v in action.profile.items():
            if isinstance(v, str):
                v_strip = v.strip().lower()
                if v_strip in ["true", "yes"]:
                    normalized_profile[k] = True
                elif v_strip in ["false", "no"]:
                    normalized_profile[k] = False
                else:
                    try:
                        # Try numeric conversion
                        if "." in v:
                            normalized_profile[k] = float(v)
                        else:
                            normalized_profile[k] = int(v)
                    except ValueError:
                        normalized_profile[k] = v
            else:
                normalized_profile[k] = v

        # Merge into accumulated profile
        self._submitted_profile.update(normalized_profile)
        self._state.submitted_profile = self._submitted_profile

        required_fields = self._task["required_profile_fields"]

        # Which required fields are now covered?
        covered = [f for f in required_fields if f in self._submitted_profile]
        missing = [f for f in required_fields if f not in self._submitted_profile]

        # Compute which schemes are eligible given submitted profile so far
        eligible_now = []
        for sid, scheme in SCHEMES.items():
            try:
                if scheme["eligibility_fn"](self._submitted_profile):
                    eligible_now.append({
                        "id": sid,
                        "name": scheme["name"],
                        "benefit": scheme["benefit"],
                        "eligibility_summary": scheme["eligibility_summary"],
                    })
            except Exception:
                pass

        # Partial reward: field coverage
        field_score = len(covered) / len(required_fields) if required_fields else 1.0

        # Check if done (agent submitted everything and at max steps)
        done = len(missing) == 0 and steps >= MAX_STEPS

        feedback = (
            f"Profile updated. Covered {len(covered)}/{len(required_fields)} required fields. "
            f"Missing: {missing if missing else 'None — profile complete!'}. "
            f"Eligible schemes based on current profile: "
            f"{[s['id'] for s in eligible_now] if eligible_now else 'None yet — submit more fields.'}."
        )

        return self._make_obs(
            feedback=feedback,
            eligible_schemes=eligible_now,
            missing_profile_fields=missing,
            steps=steps,
            partial_score=field_score * 0.3,  # 30% of final score is profile quality
        )

    def _handle_query_scheme(self, action: SchemeAdvisorAction, steps: int) -> SchemeAdvisorObservation:
        scheme_id = (action.scheme_id or "").strip().upper()
        scheme = SCHEMES.get(scheme_id)

        if not scheme:
            return self._make_obs(
                feedback=f"Unknown scheme_id '{action.scheme_id}'. "
                         f"Available: {list(SCHEMES.keys())}",
                steps=steps,
            )

        if scheme_id not in self._queried_schemes:
            self._queried_schemes.append(scheme_id)
            self._state.queried_schemes = self._queried_schemes

        is_eligible = check_eligibility(scheme_id, self._submitted_profile)
        eligibility_note = (
            "✅ Citizen appears ELIGIBLE based on submitted profile."
            if is_eligible
            else "❌ Citizen does NOT appear eligible based on submitted profile (profile may be incomplete)."
        )

        return self._make_obs(
            feedback=f"Scheme details retrieved for '{scheme_id}'. {eligibility_note}",
            scheme_details={
                "id": scheme["id"],
                "name": scheme["name"],
                "ministry": scheme["ministry"],
                "benefit": scheme["benefit"],
                "eligibility_summary": scheme["eligibility_summary"],
                "required_documents": scheme["required_documents"],
            },
            steps=steps,
        )

    def _handle_request_documents(self, action: SchemeAdvisorAction, steps: int) -> SchemeAdvisorObservation:
        """
        Agent submits a flat list of documents it believes are required.
        We grade against ground truth and compute final episode score.
        """
        submitted_docs = [d.strip() for d in action.document_request if d.strip()]

        if not submitted_docs:
            return self._make_obs(
                feedback="'request_documents' requires a non-empty 'document_request' list.",
                steps=steps,
            )

        self._requested_documents = submitted_docs
        self._state.requested_documents = submitted_docs

        # Compute final score
        score, breakdown = self._compute_final_score()
        self._state.score_breakdown = breakdown

        done = True  # Document submission finalizes the episode

        feedback = (
            f"Documents submitted. Episode complete. "
            f"Final score: {score:.3f}. "
            f"Breakdown: {breakdown}"
        )

        return SchemeAdvisorObservation(
            done=done,
            reward=score,
            task_id=self._state.task_id,
            task_description="Episode complete.",
            citizen_context=self._task["citizen_context"],
            feedback=feedback,
            eligible_schemes=[],
            scheme_details=None,
            missing_profile_fields=[],
            required_documents=submitted_docs,
            steps_taken=steps,
            max_steps=MAX_STEPS,
            partial_score=score,
        )

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _compute_final_score(self) -> tuple:
        """
        Returns (total_score: float 0.0–1.0, breakdown: dict)

        Scoring components:
          A. Profile completeness (30%): fraction of required fields submitted correctly
          B. Scheme recall (30%): fraction of true eligible schemes correctly identified
          C. Scheme precision (20%): penalty for hallucinated (incorrect) schemes
          D. Document accuracy (20%): fraction of correct documents across eligible schemes
        """
        if not self._task:
            return 0.0, {}

        gt_eligible = set(self._task["ground_truth_eligible_schemes"])
        gt_profile = self._task["ground_truth_profile"]
        required_fields = self._task["required_profile_fields"]
        gt_docs = self._task["ground_truth_documents"]

        def normalize_val(v):
            if isinstance(v, str):
                v_lower = v.strip().lower()
                if v_lower in ["true", "yes"]: return True
                if v_lower in ["false", "no"]: return False
                return v.strip()
            return v

        # A. Profile completeness (with normalization)
        covered = 0
        for f in required_fields:
            if f in self._submitted_profile:
                s_val = normalize_val(self._submitted_profile[f])
                g_val = normalize_val(gt_profile.get(f))
                if s_val == g_val:
                    covered += 1
        
        profile_score = covered / len(required_fields) if required_fields else 1.0

        # B & C. Scheme identification
        identified_schemes = {s.strip().upper() for s in self._queried_schemes}
        true_positives = identified_schemes & gt_eligible
        false_positives = identified_schemes - gt_eligible

        recall = len(true_positives) / len(gt_eligible) if gt_eligible else 1.0
        precision = 1.0 - (len(false_positives) / max(len(identified_schemes), 1))

        # D. Document accuracy (case-insensitive)
        all_gt_docs = set()
        for sid in gt_eligible:
            for d in gt_docs.get(sid, []):
                all_gt_docs.add(d.strip().lower())

        submitted_norm = {d.strip().lower() for d in self._requested_documents}
        doc_tp = len(submitted_norm & all_gt_docs)
        doc_precision = doc_tp / len(submitted_norm) if submitted_norm else 0.0
        doc_recall = doc_tp / len(all_gt_docs) if all_gt_docs else 1.0
        doc_f1 = (
            2 * doc_precision * doc_recall / (doc_precision + doc_recall)
            if (doc_precision + doc_recall) > 0
            else 0.0
        )

        total = (
            0.30 * profile_score
            + 0.30 * recall
            + 0.20 * precision
            + 0.20 * doc_f1
        )

        breakdown = {
            "profile_completeness": round(profile_score, 3),
            "scheme_recall": round(recall, 3),
            "scheme_precision": round(precision, 3),
            "document_f1": round(doc_f1, 3),
            "total": round(total, 3),
        }

        return round(total, 4), breakdown

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_obs(
        self,
        feedback: str,
        eligible_schemes=None,
        scheme_details=None,
        missing_profile_fields=None,
        required_documents=None,
        steps: int = 0,
        partial_score: float = 0.0,
        done: bool = False,
    ) -> SchemeAdvisorObservation:
        if missing_profile_fields is None:
            required_fields = self._task["required_profile_fields"] if self._task else []
            missing_profile_fields = [f for f in required_fields if f not in self._submitted_profile]

        # Auto-terminate if steps exhausted
        if steps >= MAX_STEPS and not done:
            done = True
            score, breakdown = self._compute_final_score()
            self._state.score_breakdown = breakdown
            partial_score = score
            feedback += f" [MAX STEPS REACHED] Final score: {score:.3f}. Breakdown: {breakdown}"

        return SchemeAdvisorObservation(
            done=done,
            reward=partial_score if done else None,
            task_id=self._state.task_id if self._state else "",
            task_description=(
                f"[{self._task['difficulty'].upper()} TASK] "
                "Submit profile → Query schemes → Request documents."
                if self._task else ""
            ),
            citizen_context=self._task["citizen_context"] if self._task else "",
            feedback=feedback,
            submitted_profile=self._submitted_profile,
            eligible_schemes=eligible_schemes or [],
            scheme_details=scheme_details,
            missing_profile_fields=missing_profile_fields,
            required_documents=required_documents or [],
            steps_taken=steps,
            max_steps=MAX_STEPS,
            partial_score=partial_score,
        )

    def _error_obs(self, msg: str) -> SchemeAdvisorObservation:
        return SchemeAdvisorObservation(
            done=False,
            reward=None,
            task_id="",
            task_description="",
            citizen_context="",
            feedback=f"ERROR: {msg}",
            submitted_profile=self._submitted_profile,
            eligible_schemes=[],
            max_steps=MAX_STEPS,
            partial_score=0.0,
        )
