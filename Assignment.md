# Assignment 2: The Multi-Agent AutoML Team

## Overview

Develop an **autonomous AI Data Science Team** consisting of three distinct LLM agents that collaborate to process a dataset. Unlike traditional AutoML (which uses fixed grid searches), these agents must perform semantic reasoning, make independent decisions based on data inspection, and generate/execute their own code.

---

## The Architecture: Sequential Pipeline

The system follows a sequential handoff workflow where information is passed between agents via **Structured Reports** (a combination of a processed CSV file and a descriptive text summary).

### Agent 1: The Data Cleaner ("The Auditor")

* **Goal:** Ensure the dataset is technically sound and ready for logic operations.
* **Behavior:** Inspects raw data, identifies quality issues (missing values, types, cardinality).
* **Tools:** `inspect_metadata()`, `get_column_stats()`, `impute_missing()`, `drop_column()`.
* **Handoff:** `clean_data.csv` + Summary Report (e.g., "Dropped ID due to high cardinality, imputed Age with median").

### Agent 2: The Feature Engineer ("The Architect")

* **Goal:** Maximize information density and predictive power.
* **Behavior:** Performs domain logic to create new features and executes feature selection.
* **Tools:** `create_interaction()`, `encode_categorical()`, `correlation_analysis()`, `select_top_features()`.
* **Handoff:** `engineered_data.csv` + Strategy Summary (e.g., "Created income_per_age feature and removed collinear variables").

### Agent 3: The Model Trainer ("The Coder")

* **Goal:** Train and optimize an XGBoost model.
* **Behavior:** Generates executable Python code, executes it, and evaluates performance.
* **Feedback Loop (Required):** 1. Generate baseline code.
2. Execute and capture metrics.
3. **Decision Step:** If metrics are insufficient, iterate (adjust hyperparameters); if sufficient, terminate.
* **Tools:** `execute_python_code(code_string)`.

---

## Core Requirements & Constraints

### 1. Creative Control (LLM Logic)

* **No Hardcoding:** The agents must not use static, predefined logic (e.g., "Always use mean imputation").
* **Reasoning-Based Decisions:** Agents must utilize their provided tools to inspect the data and make context-specific decisions.

### 2. Execution Loop

The Model Trainer must demonstrate a self-correcting cycle where it interprets the `stdout/stderr` of its own code to inform subsequent attempts.

---

## Deliverables

1. **System Code:** Python implementation of the three-agent flow.
2. **Execution Logs:** Transcripts of the agents' "thought processes" and reasoning.
3. **Final Report:** A generated Markdown file summarizing the full pipeline: *Raw Data → Transformations → Model Metrics.*

---

## Technical Checklist

* [ ] **Agent 1:** Successfully cleans data and passes state to Agent 2.
* [ ] **Agent 2:** Adds $\geq 1$ feature based on domain-logic analysis.
* [ ] **Agent 3:** Generates/Executes Python code for XGBoost training.
* [ ] **Agent 3:** Implements a reactive feedback loop based on evaluation metrics.

