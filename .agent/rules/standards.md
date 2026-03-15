# Antigravity Environment Standards

This file defines the mandatory "Perfect Environment" standards for all Antigravity-managed projects.

## 1. Universal Configuration
Projects must strictly adhere to these configuration files to ensure cross-environment consistency.
*   **`.editorconfig`**: Mandatory. Must define `indent_style`, `indent_size`, `end_of_line`, `insert_final_newline`, and `trim_trailing_whitespace`.
*   **`.gitignore`**: Mandatory. Must be comprehensive (OS files, IDE files, dependency directories, build artifacts).

## 2. Toolchain Standards
We enforce a "Zero-Config" philosophy where possible, preferring tools with sensible defaults or single configuration files.

### Python
*   **Linter/Formatter:** `ruff`. It replaces Black, Isort, and Flake8.
*   **Config:** `ruff.toml` or `pyproject.toml`.
*   **Virtual Env:** `.venv/` in the project root.

### Web (JS/TS)
*   **Preferred:** `biome` (Fast, integrated linter/formatter).
*   **Legacy/Specific:** `eslint` + `prettier` (only if Biome is insufficient for specific framework needs).
*   **Package Manager:** `pnpm` (preferred for speed) or `npm`.

### C/C++
*   **Formatter:** `clang-format` (Google style).
*   **Build:** `CMake` or `Bazel` (for larger projects).

## 3. Automation & CI
*   **Pre-commit:** Strongly encouraged using the `pre-commit` framework to run linters before commit.
*   **CI:** GitHub Actions pipeline to run `lint` and `test` on every PR.

## 4. Initialization Logic
When initializing a new project (`setup_project` workflow):
1.  **Detection:** Identify the primary language.
2.  **Standardize:** Copy the relevant `Antigravity/templates` (to be created) or generate standard configs.
3.  **Link:** Run `Antigravity/install.sh` to link agent rules.

