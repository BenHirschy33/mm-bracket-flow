# Antigravity Architecture Standards

This file defines the architectural principles for projects managed by Antigravity.

## 1. 🧠 Agent-Optimized Structure
Agents flourish in environments that are modular and explicit.
*   **Small Files:** Keep files under 300 lines where possible. This improves retrieval accuracy and context management.
*   **Colocation:** Keep related code, tests, and documentation close together.
    ```
    src/
      auth/
        login.ts
        login.test.ts
        README.md
    ```
*   **Explicit Exports:** Avoid "barrel files" (`index.ts` re-exporting everything) unless necessary for a public library API. They obscure dependency graphs for agents.

## 2. 🏛 Core Architecture Patterns
*   **Functional Core, Imperative Shell:** Keep business logic pure and testable. Push side effects (DB, API types, IO) to the boundaries.
*   **Service Layer Pattern:** For backend/CLI apps, separate:
    *   *Controller/Interface:* Handles input/output.
    *   *Service:* Contains business logic.
    *   *Repository:* Handles data access.
*   **Component Composition:** For UI, favor composition over inheritance. Use small, dumb presentation components and smart container components.

## 3. 🛡 Defensive Coding
*   **Parse, Don't Validate:** Use parsing libraries (like Zod, Pydantic) to type-check data at the system boundaries. Once data is inside the "Core", it should be trusted.
*   **Result Types:** Prefer returning Result objects (Success/Failure) over throwing exceptions for expected errors.

## 4. 📝 Documentation as Code
*   **Architecture Decision Records (ADR):** Significant structural changes must be documented in `docs/adr/` or similar.
*   **Self-Documenting Code:** Variable names should be verbose enough to explain their purpose. `d` -> `daysSinceLastLogin`.
