# Scheme Advisor — Testing Guide

## Overview

The Scheme Advisor is a FastAPI-based RL environment where an AI agent advises Indian citizens on government welfare scheme eligibility. This guide covers environment setup, server startup, and step-by-step testing of every endpoint and feature.

---

## 1. Prerequisites

- Python 3.10 or higher
- pip

Install dependencies from the project root:

```bash
pip install fastapi uvicorn[standard] pydantic requests websockets python-multipart python-dotenv
```

> **Note:** `openenv-core` is **not** installed from PyPI. It is provided as a local stub package in the `openenv/` directory and is automatically importable when you run from the project root.

---

## 2. Configuration

Copy `.env.example` to `.env` and fill in your API key:

```bash
cp .env.example .env
```

Edit `.env`:

```env
API_PROVIDER=groq          # Options: groq, openai, huggingface, grok
API_KEY=your_api_key_here  # Your key for the chosen provider
ENV_BASE_URL=http://localhost:8000
```

> If `API_KEY` is left blank, the baseline agent automatically falls back to a deterministic rule-based agent (no LLM required). This is the easiest way to test without an API key.

---

## 3. Starting the Server

From the **project root directory** (where `models.py`, `schemes_db.py`, `openenv/` etc. live):

```bash
uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload
```

Expected output:

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

---

## 4. Testing All Endpoints

### 4.1 Health Check

Verify the server is running:

```bash
curl http://localhost:8000/health
```

**Expected response:**

```json
{ "status": "ok", "environment": "scheme_advisor" }
```

---

### 4.2 List All Tasks

```bash
curl http://localhost:8000/tasks
```

**Expected response:** A JSON object with a `tasks` array containing 3 tasks (`easy_farmer`, `medium_bpl_woman`, `hard_urban_vendor_student`), the `action_schema`, and `available_schemes`.

---

### 4.3 Reset — Start a New Episode

Start a random task:

```bash
curl -X POST http://localhost:8000/reset \
  -H "Content-Type: application/json" \
  -d '{}'
```

Start a specific task:

```bash
curl -X POST http://localhost:8000/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "easy_farmer"}'
```

**Expected response fields:**

| Field              | Description                                                     |
| ------------------ | --------------------------------------------------------------- |
| `task_id`          | Which task was selected                                         |
| `citizen_context`  | Narrative description of the citizen                            |
| `task_description` | Instructions for the agent                                      |
| `feedback`         | "Episode started. Read the citizen context and begin advising." |
| `done`             | `false`                                                         |
| `steps_taken`      | `0`                                                             |
| `max_steps`        | `10`                                                            |

---

### 4.4 Step — Execute Actions

All three action types can be tested in sequence. First reset to `easy_farmer` (above), then:

#### Action 1: `submit_profile`

```bash
curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "submit_profile",
    "profile": {
      "age": 45,
      "gender": "male",
      "location_type": "rural",
      "occupation": "farmer",
      "land_hectares": 1.5,
      "bpl_card": false,
      "annual_income_inr": 120000,
      "is_income_taxpayer": false,
      "is_government_employee": false,
      "has_epf": false,
      "sector": "unorganised"
    }
  }'
```

**Expected:** `feedback` reports covered fields and lists eligible schemes found so far (e.g. `PM_KISAN`, `MGNREGS`).

#### Action 2: `query_scheme`

```bash
curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "query_scheme",
    "scheme_id": "PM_KISAN"
  }'
```

**Expected:** `scheme_details` contains scheme name, ministry, benefit, eligibility summary, and `required_documents`. Eligibility note shows ✅ or ❌.

#### Action 3: `request_documents` (ends the episode)

```bash
curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "request_documents",
    "document_request": [
      "Aadhaar card",
      "Land ownership records (Khasra/Khatauni)",
      "Bank passbook",
      "Mobile number linked to Aadhaar"
    ]
  }'
```

**Expected:** `done: true`, `reward` between 0.0 and 1.0, `feedback` shows final score and breakdown.

---

### 4.5 Get Current State

```bash
curl http://localhost:8000/state
```

**Expected:** Full episode state including `submitted_profile`, `queried_schemes`, `requested_documents`, `score_breakdown`.

---

### 4.6 Grader — Grade an Episode Externally

This endpoint is stateless and can be called at any time:

```bash
curl -X POST http://localhost:8000/grader \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "easy_farmer",
    "submitted_profile": {
      "age": 45,
      "gender": "male",
      "location_type": "rural",
      "occupation": "farmer",
      "land_hectares": 1.5,
      "is_government_employee": false,
      "is_income_taxpayer": false
    },
    "queried_schemes": ["PM_KISAN", "MGNREGS"],
    "requested_documents": [
      "Aadhaar card",
      "Land ownership records (Khasra/Khatauni)",
      "Bank passbook",
      "Mobile number linked to Aadhaar",
      "Residential proof (village panchayat certificate)",
      "Bank passbook or post office account",
      "Passport-size photograph"
    ]
  }'
```

**Expected response:**

```json
{
  "task_id": "easy_farmer",
  "score": 0.85,
  "breakdown": {
    "profile_completeness": 1.0,
    "scheme_recall": 1.0,
    "scheme_precision": 1.0,
    "document_f1": 0.7
  },
  "ground_truth_eligible_schemes": ["PM_KISAN", "MGNREGS"],
  "agent_identified_schemes": ["PM_KISAN", "MGNREGS"]
}
```

> Exact score varies based on document overlap with ground truth.

---

### 4.7 Baseline — Run the Rule-Based Agent

This triggers `baseline.py` as a subprocess and returns scores for all 3 tasks:

```bash
curl -X POST http://localhost:8000/baseline
```

**Expected response:**

```json
{
  "model": "llama3-8b-8192",
  "tasks": {
    "easy_farmer":   {"score": 0.45, ...},
    "medium_bpl_woman": {"score": 0.2, ...},
    "hard_urban_vendor_student": {"score": 0.1, ...}
  },
  "average_score": 0.25
}
```

> Exact scores depend on whether an API key is set. Without one, the deterministic rule-based fallback runs.

---

### 4.8 WebSocket Interface

Use `wscat` or any WebSocket client. Install wscat with `npm install -g wscat`, then:

```bash
wscat -c ws://localhost:8000/ws
```

Once connected, send JSON commands:

**Reset:**

```json
{ "command": "reset", "task_id": "medium_bpl_woman" }
```

**Step:**

```json
{
  "command": "step",
  "action_type": "submit_profile",
  "profile": {
    "age": 32,
    "gender": "female",
    "location_type": "rural",
    "bpl_card": true,
    "annual_income_inr": 120000
  }
}
```

**Query scheme:**

```json
{
  "command": "step",
  "action_type": "query_scheme",
  "scheme_id": "AYUSHMAN_BHARAT"
}
```

**Get state:**

```json
{ "command": "state" }
```

---

## 5. Running the Baseline Agent Directly

From the project root:

```bash
# Run all 3 tasks with pretty output
python baseline.py

# Run a single task
python baseline.py --task easy_farmer

# Machine-readable JSON output
python baseline.py --all-tasks --output-json

# Use a different model
python baseline.py --model llama3-70b-8192
```

---

## 6. Task Reference

### Task 1: `easy_farmer` (Easy)

**Citizen:** Ramesh, 45-year-old male farmer in a rural village in Rajasthan. Owns 1.5 hectares. Annual income ₹1,20,000.

**Ground truth eligible schemes:** `PM_KISAN`, `MGNREGS`

**Key profile fields to submit:**

```json
{
  "age": 45,
  "gender": "male",
  "location_type": "rural",
  "occupation": "farmer",
  "land_hectares": 1.5,
  "is_government_employee": false,
  "is_income_taxpayer": false
}
```

---

### Task 2: `medium_bpl_woman` (Medium)

**Citizen:** Savitri, 32-year-old rural woman in Uttar Pradesh. BPL household. Kutcha house. No LPG. Daughter aged 4.

**Ground truth eligible schemes:** `AYUSHMAN_BHARAT`, `PM_AWAS_YOJANA_GRAMIN`, `PM_UJJWALA`, `SUKANYA_SAMRIDDHI`, `E_SHRAM`, `ATAL_PENSION`, `MGNREGS`

**Key profile fields to submit:**

```json
{
  "age": 32,
  "gender": "female",
  "location_type": "rural",
  "bpl_card": true,
  "annual_income_inr": 120000,
  "house_type": "kutcha",
  "has_lpg_connection": false,
  "has_girl_child_below_10": true,
  "is_income_taxpayer": false
}
```

---

### Task 3: `hard_urban_vendor_student` (Hard)

**Citizen:** Mohan, 38-year-old male ST urban street vendor in Pune. Annual income ₹1,80,000. No BPL card. Rented house.

**Ground truth eligible schemes:** `PM_SVANIDHI`, `PM_MUDRA`, `E_SHRAM`, `ATAL_PENSION`

**Key profile fields to submit:**

```json
{
  "age": 38,
  "gender": "male",
  "location_type": "urban",
  "occupation": "street_vendor",
  "sector": "unorganised",
  "caste_category": "ST",
  "annual_income_inr": 180000,
  "is_income_taxpayer": false,
  "has_epf": false,
  "bpl_card": false,
  "breadwinner_died": false,
  "house_type": "rented"
}
```

---

## 7. Scoring Breakdown

Each episode is scored 0.0–1.0 across four components:

| Component            | Weight | Description                                                       |
| -------------------- | ------ | ----------------------------------------------------------------- |
| Profile Completeness | 30%    | Fraction of required profile fields submitted with correct values |
| Scheme Recall        | 30%    | Fraction of truly eligible schemes that were queried              |
| Scheme Precision     | 20%    | Penalty for querying schemes the citizen isn't eligible for       |
| Document F1          | 20%    | F1 score of submitted documents vs ground truth documents         |

**Formula:**

```
score = 0.30 × profile_completeness
      + 0.30 × scheme_recall
      + 0.20 × scheme_precision
      + 0.20 × document_f1
```

A perfect score of **1.0** requires:

1. All required profile fields submitted with exact correct values
2. All eligible schemes queried (and no ineligible ones)
3. All required documents submitted (no extras, no missing)

---

## 8. Available Scheme IDs

```
PM_KISAN             PM-KISAN (farmer income support)
AYUSHMAN_BHARAT      Health cover ₹5 lakh/year
PM_AWAS_YOJANA_GRAMIN  Rural housing assistance
MGNREGS              100 days guaranteed employment
PM_UJJWALA           Free LPG connection for BPL women
SUKANYA_SAMRIDDHI    Girl child savings scheme
PM_MUDRA             Micro-enterprise loans
SCHOLARSHIP_SC_ST    Education scholarship for SC/ST
ATAL_PENSION         Pension scheme for unorganised workers
E_SHRAM              Unorganised worker registration
PM_SVANIDHI          Street vendor micro-credit
NFBS                 National Family Benefit Scheme
```

---

## 9. Error Cases to Test

| Test                                     | Expected behaviour                                           |
| ---------------------------------------- | ------------------------------------------------------------ |
| `POST /step` before `POST /reset`        | Returns `{"feedback": "ERROR: Call reset() before step()."}` |
| `query_scheme` with invalid `scheme_id`  | Returns feedback listing all valid scheme IDs                |
| `submit_profile` with empty profile `{}` | Returns feedback asking for a non-empty profile dict         |
| `request_documents` with empty list      | Returns feedback asking for a non-empty document list        |
| `POST /grader` with unknown `task_id`    | Returns HTTP 404 with detail message                         |
| `/reset` with unknown `task_id`          | Falls back to a random valid task                            |

---

## 10. Docker (Optional)

```bash
cd server
docker build -t scheme-advisor .
docker run -p 8000:8000 --env-file ../.env scheme-advisor
```

Then test against `http://localhost:8000` as above.
