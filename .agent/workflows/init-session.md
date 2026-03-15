---
description: Initialize a new agent session by re-reading local project rules and state.
---
# Workspace Initialization Protocol

When starting a new session in this workspace, the agent MUST run this workflow to re-familiarize itself with the specific project rules, as they may not appear in the Customization UI.

1. Read all files in `.agent/rules/` to understand the project-specific architecture, best practices, and formatting standards.
// turbo-all
2. Run `cat .agent/rules/*` in the terminal to quickly load the rules into context.
3. Read `task.md` and `implementation_plan.md` in the `.gemini/antigravity/brain/` directory to understand the current progress.
4. Confirm with the user that initialization is complete and state the current pending task.
