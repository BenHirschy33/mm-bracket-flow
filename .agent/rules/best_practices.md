# Antigravity General Best Practices

## 1. Types & Safety
*   **No `any`:** Strict typing is mandatory. Usage of `any` (TS) or unstructured `dict` (Python) without schemas is forbidden unless strictly scoped.
*   **Immutability:** Prefer `const` (JS/TS) or immutable data structures. Mutability is a source of bugs.

## 2. Error Handling
*   **Catch & Context:** Never catch an error just to suppress it. Always log it or wrap it with additional context before re-throwing.
    ```python
    # BAD
    except Exception:
        pass

    # GOOD
    except ConnectionError as e:
        raise ServiceUnavailableError("Failed to connect to primary DB") from e
    ```

## 3. Comments & Docs
*   **Run "Why", not "What":**
    ```javascript
    // BAD: Increment i by 1
    i++;

    // GOOD: Move to the next user in the round-robin queue
    currentUserIndex++;
    ```
*   **Docstrings:** Public functions must have docstrings explaining parameters, return values, and exceptions.

## 4. Git Hygiene
*   **Atomic Commits:** One feature/fix per commit.
*   **Local First:** Commit frequently locally to save progress. **NEVER PUSH** to `origin` without explicit user approval.
*   **Conventional Commits:** Use standard prefixes:
    *   `feat:` New feature
    *   `fix:` Bug fix
    *   `docs:` Documentation only
    *   `style:` Formatting, missing semi colons, etc
    *   `refactor:` Code change that neither fixes a bug nor adds a feature
    *   `test:` Adding missing tests
    *   `chore:` Build process, aux tool changes

