# Scheme Advisor — Detailed API Guide

This document provides a comprehensive guide to the Scheme Advisor API, explaining each endpoint, the corresponding `curl` command, and the importance of each action in the advice-giving workflow.

---

## 1. Health Check
Checks if the API server is up and running.

**Curl Command:**
```bash
curl http://localhost:8000/health
```

**What it does:** Returns a simple JSON response confirming the server's status and version.
**Importance:** Essential for initial connectivity testing and liveness probes in automated environments.

---

## 2. List All Tasks
Retrieves a list of all advising scenarios (tasks) available in the environment.

**Curl Command:**
```bash
curl http://localhost:8000/tasks
```

**What it does:** Lists all tasks (Easy, Medium, Hard) along with their difficulty, the context of the citizen, and the fields required to determine eligibility.
**Importance:** Helps the agent understand what tasks are available and what the action schema (structured input format) looks like.

---

## 3. Reset — Initializing an Episode
Starts a new advising session for a specific task or a random one.

**Curl Command (Specific Task):**
```bash
curl -X POST http://localhost:8000/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "easy_farmer"}'
```

**What it does:** Resets the environment state, selects the task, and returns the initial observation (citizen context).
**Importance:** **This is the mandatory first step.** Every advising session must start with a reset to clear previous state and prepare for a new citizen.

---

## 4. Step — Executing Actions
The `/step` endpoint is the core of the interaction. It accepts three types of actions.

### 4.1 Submit Profile
Submits fields of the citizen's profile to the environment.

**Curl Command:**
```bash
curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "submit_profile",
    "profile": {
      "age": 35,
      "gender": "male",
      "location_type": "rural",
      "occupation": "farmer",
      "land_hectares": 1.5,
      "is_government_employee": false,
      "is_income_taxpayer": false,
      "has_epf": false,
      "sector": "unorganised"
    }
  }'
```

**What it does:** Updates the internal profile of the citizen. The environment responds with feedback on how many required fields were covered and which schemes the citizen currently qualifies for.
**Importance:** Crucial for accurately determining eligibility. Without a complete profile, the advisor cannot correctly identify the right schemes.

### 4.2 Query Scheme
Retrieves detailed information and document requirements for a specific scheme.

**Curl Command:**
```bash
curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "query_scheme",
    "scheme_id": "PM_KISAN"
  }'
```

**What it does:** Provides the full details of a scheme (Ministry, Benefit, Detailed Eligibility, and **Required Documents**).
**Importance:** Allows the advisor to learn what documents are needed for each eligible scheme. It also confirms if the citizen appears eligible based on the submitted profile.

### 4.3 Request Documents
Submits the final list of documents the citizen needs to collect. **This action terminates the episode.**

**Curl Command:**
```bash
curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "request_documents",
    "document_request": ["Aadhaar card", "Bank passbook"]
  }'
```

**What it does:** Finalizes the advice. The environment grades the entire interaction (profile quality + scheme identification + document accuracy).
**Importance:** This is the terminal action. It represents the "final advice" given to the citizen.

---

## 5. Get Current State
Retrieves the full internal state of the current episode.

**Curl Command:**
```bash
curl http://localhost:8000/state
```

**What it does:** Shows the accumulated profile, queried schemes, and requested documents so far.
**Importance:** Extremely useful for debugging or for agents/users to remind themselves of what has been done without looking through a long transcript.

---

## 6. Grader
An external, stateless grading endpoint.

**Curl Command:**
```bash
curl -X POST http://localhost:8000/grader \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "easy_farmer",
    "submitted_profile": {...},
    "queried_schemes": [...],
    "requested_documents": [...]
  }'
```

**What it does:** Takes a full set of results and returns a score breakdown (0.0 to 1.0) without needing an active session.
**Importance:** Allows for external validation and offline scoring of advising transcripts.

---

## 7. Baseline
Runs a built-in agent to generate a performance baseline.

**Curl Command:**
```bash
curl -X POST http://localhost:8000/baseline
```

**What it does:** Triggers a rule-based agent that attempts to solve all 3 tasks and returns their scores.
**Importance:** Provides a point of comparison ("baseline") to see how much an LLM-based agent improves over a simple deterministic logic.
