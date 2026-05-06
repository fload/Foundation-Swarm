"""
Foundation Swarm — Ellah Ronen's nonprofit leadership swarm.

Agents:
  orchestrator          — Routes tasks, manages multi-agent workflows
  virtual_assistant     — Operational backbone: deadlines, tasks, CRM, meeting prep
  development_agent     — Fundraising brain: grants, prospects, proposals, major gifts
  research_agent        — Intelligence: news, policy, funder/org research, community data
  communications_agent  — Voice on the page: drafts, edits, voice-checks
  slides_documents_agent — Formatted output: decks, docs, one-pagers, charts
  strategy_impact_agent — Analysis: financial health, logic models, evaluation, strategy

Connection map (left can initiate to right):
  orchestrator → all agents
  virtual_assistant → development_agent        (flag grant deadlines to pipeline)
  virtual_assistant → communications_agent     (draft outreach from CRM context)
  development_agent → communications_agent     (voice-check proposals/LOIs)
  development_agent → research_agent           (funder research feeds proposal work)
  development_agent → slides_documents_agent   (grant calendars and pitch decks)
  research_agent    → development_agent        (research feeds proposal writing)
  research_agent    → communications_agent     (research feeds thought leadership)
  strategy_impact_agent → slides_documents_agent  (financial analysis → board decks)
  strategy_impact_agent → development_agent    (logic models feed grant narratives)
"""

from dotenv import load_dotenv
from agency_swarm import Agency

from orchestrator.orchestrator import create_orchestrator
from virtual_assistant import create_virtual_assistant
from development_agent import create_development_agent
from research_agent import create_research_agent
from communications_agent import create_communications_agent
from slides_documents_agent import create_slides_documents_agent
from strategy_impact_agent import create_strategy_impact_agent

load_dotenv()


def create_agency(load_threads_callback=None):
    orchestrator = create_orchestrator()
    virtual_assistant = create_virtual_assistant()
    development_agent = create_development_agent()
    research_agent = create_research_agent()
    communications_agent = create_communications_agent()
    slides_documents_agent = create_slides_documents_agent()
    strategy_impact_agent = create_strategy_impact_agent()

    agency = Agency(
        orchestrator,
        communication_flows=[
            # Orchestrator → all specialists
            (orchestrator, virtual_assistant),
            (orchestrator, development_agent),
            (orchestrator, research_agent),
            (orchestrator, communications_agent),
            (orchestrator, slides_documents_agent),
            (orchestrator, strategy_impact_agent),
            # Operational cross-agent flows
            (virtual_assistant, development_agent),
            (virtual_assistant, communications_agent),
            (development_agent, communications_agent),
            (development_agent, research_agent),
            (development_agent, slides_documents_agent),
            (research_agent, development_agent),
            (research_agent, communications_agent),
            (strategy_impact_agent, slides_documents_agent),
            (strategy_impact_agent, development_agent),
        ],
        shared_instructions="shared_instructions.md",
    )

    if load_threads_callback:
        load_threads_callback(agency)

    return agency


if __name__ == "__main__":
    agency = create_agency()
    agency.terminal_demo()
