# Agent Guidelines

## Diff hygiene

- Keep every change minimal and directly related to the requested task.
- Preserve existing formatting, indentation, blank lines, and line-ending style.
- Do not make whitespace-only changes unless they are explicitly requested or required for correctness.
- Do not reformat whole files or run repository-wide formatting or auto-fix commands unless explicitly requested.
- Modify only the lines needed for the requested change. Avoid unrelated cleanup or refactoring.
- If an editor or formatter would normalize an entire file, use a targeted edit instead.
- Before finishing, inspect the Git diff and remove unrelated formatting, whitespace, or newline changes.
