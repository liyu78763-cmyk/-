# Project Notes for Agents

This repository builds a Python 3.12 automation that collects recent cross-border
e-commerce news, filters and scores it, formats a Chinese DingTalk briefing, and
sends it through a DingTalk custom robot.

Operational rules:

- Never log `DINGTALK_WEBHOOK`, `DINGTALK_SECRET`, `AI_API_KEY`, access tokens, or generated DingTalk signatures.
- Tests must never send real DingTalk messages.
- Keep the report prompt in `prompts/daily_report.md`; do not move the long report-format prompt into business code.
- Provider failures should be logged and skipped, not allowed to stop the whole run.
- Prefer official or regulator sources for policy, fees, tariffs, recalls, compliance, and account-risk news.
- `data/history.sqlite` is runtime state and must not be committed.

Recommended local checks:

```bash
python -m ruff format --check .
python -m ruff check .
python -m mypy src
python -m pytest
```
