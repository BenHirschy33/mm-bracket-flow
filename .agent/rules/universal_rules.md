# Universal Antigravity Rules

This document consolidates the core rules and standards for the Universal Environment.

## 1. Interaction Modes
*   **Learning Mode:** Explain first, code second. Use analogies.
*   **Co-Pilot Mode:** Collaborate, iterate, and verify.
*   **Autonomous Mode:** Execute fully, report comprehensively.

## 2. Architecture & Standards
*   **File Structure:** Follow the `universal-env` patterns (Antigravity/ vs terminal/).
*   **Idempotency:** Install scripts must be runnable multiple times without side effects.
*   **Backups:** Always backup configuration files before overwriting.
*   **Global Config:** Agent rules live in `~/.gemini/antigravity` (or configured global path).

## 3. Best Practices
*   **Git:** proper commit messages, semantic versioning where possible.
*   **Code:** Clean, commented, and modular.
*   **Safety:** Never delete user data without a backup or explicit confirmation.

For detailed breakdowns, see the individual rule files:
*   [architecture.md](architecture.md)
*   [best_practices.md](best_practices.md)
*   [interaction.md](interaction.md)
