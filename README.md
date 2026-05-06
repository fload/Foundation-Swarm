# Foundation Swarm

A multi-agent AI team for a senior philanthropic strategist — built on [Agency Swarm](https://agency-swarm.ai).

Supports two organizational contexts:

- **Library Foundation of Los Angeles (LFLA)** — development strategy, grant writing, donor stewardship, board management, and communications for one of LA's largest public library funders
- **Crestline Collective** — philanthropic consulting practice (client work is kept strictly separate from LFLA)

---

## Agents

| Agent | Role | Key Tools |
|---|---|---|
| **Orchestrator** | Routes tasks, manages multi-agent workflows, enforces org context | — |
| **Virtual Assistant** | Daily briefings, deadlines, tasks, meeting prep, CRM hygiene | DeadlineTracker, TaskManager, MeetingPrep, CrmUpdater |
| **Development Agent** | Grant research, RFP parsing, proposal writing, prospect briefs, major gift strategy | SearchGrants, FunderProfile, ParseRFP, ProspectBrief, DeadlineLog |
| **Research Agent** | News monitoring, policy tracking, Census data, org/funder deep dives | NewsMonitor, CensusData, LegiscanTracker, OrgDeepDive |
| **Communications Agent** | Donor letters, board memos, LinkedIn posts, event copy, voice-checking | VoiceLibrary, ContactContext, AudienceRegister |
| **Slides & Documents Agent** | Board decks, funder pitch decks, strategic plans, one-pagers, reports | BrandLoader, ChartBuilder, + all PPTX and Word doc tools |
| **Strategy & Impact Agent** | Financial analysis, logic models, evaluation frameworks, strategic planning | FinancialRatios, LogicModelBuilder, ChartBuilder |

## Agent Communication Map

```
orchestrator → all agents
virtual_assistant → development_agent       (flag grant deadlines)
virtual_assistant → communications_agent    (draft outreach from CRM context)
development_agent → communications_agent    (voice-check proposals/LOIs)
development_agent → research_agent          (funder research feeds proposals)
development_agent → slides_documents_agent  (grant calendars, pitch decks)
research_agent    → development_agent       (research feeds proposal writing)
research_agent    → communications_agent    (research feeds thought leadership)
strategy_impact_agent → slides_documents_agent  (financial analysis → board decks)
strategy_impact_agent → development_agent   (logic models feed grant narratives)
```

---

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/your-org/Foundation-Swarm.git
cd Foundation-Swarm
uv sync
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and add your API keys. The minimum required key is `OPENAI_API_KEY`.

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | ✅ Required | Powers all agents |
| `CANDID_API_KEY` | Optional | Funder profile data (Development Agent) |
| `NEWS_API_KEY` | Optional | News monitoring (Research Agent) |
| `CENSUS_API_KEY` | Optional | Community data for grant narratives (Research Agent) |
| `LEGISCAN_API_KEY` | Optional | CA/federal bill tracking (Research Agent) |
| `VA_INTEGRATIONS_ENABLED` | Optional | Master switch for live integrations (default: `false`) |
| `COMPOSIO_API_KEY` | Optional | Required only if `VA_INTEGRATIONS_ENABLED=true` |

### 3. Run

**Terminal (interactive demo):**
```bash
uv run python run.py
```

**API server:**
```bash
uv run python server.py
```

---

## Virtual Assistant — Integrations

The Virtual Assistant works **fully in file-upload / manual-input mode** without any live integrations. This is the default and recommended starting point.

Live integrations (Gmail, Google Calendar, Google Drive, Outlook) are available but **must be explicitly enabled** after confirming IT and organizational approval:

```bash
# In .env — enable only after confirmed IT approval
VA_INTEGRATIONS_ENABLED=true
VA_GMAIL_ENABLED=true     # Requires Google Workspace admin approval
VA_GCAL_ENABLED=true      # Requires org Google account access
VA_GDRIVE_ENABLED=true    # Requires org Google account access
VA_OUTLOOK_ENABLED=true   # Requires IT approval
```

Notion has lower IT friction and can be enabled independently:
```bash
VA_NOTION_ENABLED=true
```

---

## Shared Data Files

The swarm uses three shared JSON files in `data/` that persist across sessions:

| File | Purpose |
|---|---|
| `data/contacts.json` | CRM — donors, funders, partners, board members |
| `data/deadlines.json` | Deadline register — grants, governance, reports |
| `data/tasks.json` | Task tracker — open items, owners, statuses |

These files are read and written by the Virtual Assistant and Development Agent. Never commit files containing real donor or contact data.

---

## Brand Assets

LFLA and Crestline Collective brand specs (colors, fonts, logo paths) are managed by the `BrandLoader` tool:

- Store brand specs at: `slides_documents_agent/files/brand/brand.json`
- Place logo files in the same directory
- Update via the agent: `"Update LFLA brand colors to [official hex codes]"`

Default placeholder colors are included — update with official brand guidelines before producing external materials.

---

## Org Context Rules

Every agent confirms org context before producing branded or sensitive content:

- **LFLA** — supports the Los Angeles Public Library
- **Crestline** — consulting practice, clients are confidential
- **Board** — Ellah's personal board service (CNM-SoCal, LAGCC)

If org context is ambiguous, agents ask before proceeding — they never guess.

**Conflict of interest**: if the same funder or partner appears in both LFLA and Crestline contexts, all agents stop and flag to Ellah before taking any action.

---

## Project Structure

```
swarm.py                     ← main config: imports agents, defines connections
shared_instructions.md       ← org context shared across all agents
run.py                       ← CLI entry point
server.py                    ← FastAPI server entry point

orchestrator/                ← routing and orchestration
virtual_assistant/           ← deadlines, tasks, CRM, meeting prep
development_agent/           ← grants, proposals, prospect research
research_agent/              ← news, policy, Census, org research
communications_agent/        ← voice, drafting, editing
slides_documents_agent/      ← PPTX decks, Word docs, charts
strategy_impact_agent/       ← financial analysis, logic models, strategy

shared_tools/                ← tools available to all agents
data/                        ← shared JSON data files (CRM, deadlines, tasks)
```

---

## Development

```bash
# Run individual tool tests
uv run python development_agent/tools/search_grants.py
uv run python research_agent/tools/census_data.py
uv run python strategy_impact_agent/tools/financial_ratios.py

# Run test suite
uv run python -m pytest tests/ -v

# Smoke test agency imports
uv run python -c "from swarm import create_agency; a = create_agency(); print('OK', len(a.agents), 'agents')"
```
