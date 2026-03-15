---
description: How to initialize a new project with Antigravity standards
---

# Project Setup Workflow

This workflow guides the initialization of a new project or the standardization of an existing one.

1.  **Initialize Git**
    *   Command: `git init` (if not already initialized)

2.  **Apply Antigravity Configuration**
    *   Run the Antigravity setup script (assumed to be in `~/universal-env/Antigravity/install.sh`).
    *   Command: `~/universal-env/Antigravity/install.sh .`

3.  **Language Specific Setup**
    *   **Python:**
        *   Create `venv`: `python -m venv .venv`
        *   Create `pyproject.toml` or `requirements.txt`.
        *   Install formatting/linting: `pip install ruff`
    *   **Node/TS:**
        *   Init: `npm init -y`
        *   Install tools: `npm install -D typescript @types/node biome`
        *   Init TSConfig: `npx tsc --init`

4.  **Create Documentation**
    *   Create `README.md` with:
        *   Project Title
        *   Purpose
        *   Install/Run instructions
    *   Create `task.md` for tracking initial work.
    *   Create `implementation_plan.md` for the first feature.

5.  **Initial Commit**
    *   Stage all files.
    *   Commit: `git commit -m "chore: initial project setup with Antigravity standards"`
