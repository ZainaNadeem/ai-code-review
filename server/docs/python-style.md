# Python Style Guide

These conventions apply to all backend Python code. The reviewer should flag
violations of these rules.

## Formatting
- Follow PEP 8. Lines should not exceed 100 characters.
- Use 4 spaces for indentation; never tabs.
- Use double quotes for strings unless the string contains a double quote.

## Imports
- Group imports: standard library, third-party, then local (`app.*`).
- Do not use wildcard imports (`from module import *`).

## Typing
- All public functions must have type annotations on parameters and return.
- Prefer `list[str]` / `dict[str, int]` builtins over `typing.List` / `Dict`.

## Naming
- Functions and variables use `snake_case`; classes use `PascalCase`.
- Constants are `UPPER_SNAKE_CASE` at module level.
- Avoid single-letter names except for short loop counters.

## Error handling
- Never use a bare `except:`; catch specific exceptions.
- Do not silently swallow exceptions — at minimum log them.
- Raise `HTTPException` with an appropriate status code in API routes.

## Security
- Never hardcode secrets, API keys, or passwords. Read them from settings/env.
- Always validate and sanitize external input before use.
- Use parameterized queries; never build SQL with string formatting.

## Functions
- Keep functions focused; prefer functions under ~50 lines.
- Avoid mutable default arguments (e.g. `def f(x=[])`).
