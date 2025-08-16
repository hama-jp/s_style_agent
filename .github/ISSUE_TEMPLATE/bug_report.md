---
name: Bug report
about: Create a report to help us improve
title: '[BUG] '
labels: 'bug'
assignees: ''

---

**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Set environment variables: `export LLM_BASE_URL="..."`
2. Run command: `uv run python -m s_style_agent.cli.main`
3. Enter S-expression: `(calc "2+3")`
4. See error

**Expected behavior**
A clear and concise description of what you expected to happen.

**Environment:**
 - OS: [e.g. Ubuntu 22.04, macOS 14, Windows 11]
 - Python version: [e.g. 3.12.1]
 - LLM Provider: [e.g. OpenAI GPT-4, Local LLM, Anthropic Claude]
 - UV version: [e.g. 0.1.10]

**Configuration:**
- LLM_BASE_URL: [e.g. https://api.openai.com/v1]
- LLM_MODEL_NAME: [e.g. gpt-4]
- Any MCP configuration: [Yes/No]

**Additional context**
Add any other context about the problem here. Include logs if available.

**S-expressions tested (if relevant):**
```lisp
(your s-expression here)
```