---
title: Scheme Advisor OpenEnv
emoji: 🏛️
colorFrom: blue
colorTo: green
sdk: docker
app_file: app.py
pinned: false
tags:
  - openenv
  - reinforcement-learning
  - government
  - welfare
  - india
---

# Scheme Advisor Agentic Environment

## Overview

Scheme Advisor is a high-fidelity agentic environment designed for AI agents to learn the task of **Government Welfare Scheme Counseling**. In this environment, an agent takes on the role of a social worker or CSC (Common Service Centre) operator in India, helping citizens identify which government welfare schemes they are eligible for and what documents they need to collect.

## How it Works

The environment is structured as a multi-step reinforcement learning episode (open-loop or closed-loop).

1.  **Context**: Each episode starts with a **Citizen Context** (a narrative description of a citizen's life, occupation, income, and needs).
2.  **Profiling**: The agent must intelligently extract and submit the citizen's profile using `submit_profile`.
3.  **Discovery**: Based on the profile, the environment suggests potentially eligible schemes.
4.  **Inquiry**: The agent queries specific schemes (`query_scheme`) to understand their benefits and document requirements.
5.  **Advice**: The agent concludes the session by requesting the final set of required documents (`request_documents`).

## Key Components

- **Knowledge Base (`schemes_db.py`)**: A structured database of major Indian welfare schemes (PM-KISAN, Ayushman Bharat, etc.) with deterministic eligibility rules.
- **Environment Engine (`server/environment.py`)**: Handles the state transitions, action processing, and rewards.
- **Scoring System**: Graded reward based on:
  - **Profile Accuracy (30%)**: Correctly extracting information from the narrative.
  - **Scheme Recall (30%)**: Finding all truly eligible schemes.
  - **Scheme Precision (20%)**: Avoiding "hallucinating" eligibility for schemes the citizen doesn't qualify for.
  - **Document Accuracy (20%)**: Specifying the exact documents needed.

## Getting Started

### Prerequisites

- Python 3.10+
- FastAPI & Uvicorn

### Installation

```bash
pip install -r server/requirements.txt
```

### Running the Server

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

### Running the Baseline Agent

You can test the environment using the built-in baseline script:

```bash
python baseline.py
```

## Documentation

- [API_GUIDE.md](./API_GUIDE.md): Detailed explanation of all API endpoints and CURL commands.
- [TESTING_GUIDE.md](./TESTING_GUIDE.md): Step-by-step instructions for manual and automated testing.

## Technology Stack

- **Backend**: FastAPI (Python)
- **Architecture**: OpenEnv (Agentic Environment Standard)
- **Models**: Pydantic v2
- **Deployment**: Hugging Face Spaces Docker Runtime
