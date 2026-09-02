# Agent Guidelines

## Diff hygiene

- Keep every change minimal and directly related to the requested task.
- Preserve existing formatting, indentation, blank lines, and line-ending style.
- Do not make whitespace-only changes unless they are explicitly requested or required for correctness.
- Do not reformat whole files or run repository-wide formatting or auto-fix commands unless explicitly requested.
- Modify only the lines needed for the requested change. Avoid unrelated cleanup or refactoring.
- If an editor or formatter would normalize an entire file, use a targeted edit instead.
- Before finishing, inspect the Git diff and remove unrelated formatting, whitespace, or newline changes.

## Response style

- Write replies in simple, plain language. Prefer short sentences and everyday words.
- Explain things the way you would to a smart colleague who is new to this codebase.
- Avoid jargon. If a technical term is unavoidable, explain it in a few words the first time.
- Skip filler, hedging, and long preambles. Lead with the answer, then the detail.
- Use short paragraphs or bullets instead of dense blocks of text.
- Keep this style for prose only. Code, commands, file paths, and identifiers stay exact.
