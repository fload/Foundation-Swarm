# data/

Shared runtime data files for the Foundation Swarm. These files are read and written
by multiple agents and must not be committed with sensitive information.

## Files

| File | Owner | Description |
|---|---|---|
| `deadlines.json` | virtual_assistant, development_agent | Unified deadline register for grant submissions, reporting deadlines, board meetings, and governance filings across LFLA and Crestline Collective. Array of deadline objects. |
| `tasks.json` | virtual_assistant | Prioritized task list. Array of task objects with project, priority, due date, and status. |
| `contacts.json` | virtual_assistant, communications_agent | Lightweight CRM. Object keyed by contact name or ID. Stores relationship notes, last-touch date, org context (LFLA vs. Crestline), and communication history. |

## Notes

- All files store JSON. Do not add binary data or credentials.
- `contacts.json` may contain names and relationship notes — treat as confidential.
- These files are gitignored by default. Add them to `.gitignore` if not already present.
