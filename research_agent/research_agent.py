from agency_swarm import Agent, ModelSettings
from agency_swarm.tools import WebSearchTool, IPythonInterpreter, LoadFileAttachment
from openai.types.shared import Reasoning

from config import get_default_model, is_openai_provider
from shared_tools import CopyFile
from virtual_assistant.tools.ReadFile import ReadFile
from virtual_assistant.tools.ScholarSearch import ScholarSearch

from .tools.news_monitor import NewsMonitor
from .tools.census_data import CensusData
from .tools.legiscan_tracker import LegiscanTracker
from .tools.org_deep_dive import OrgDeepDive


def create_research_agent() -> Agent:
    return Agent(
        name="Research Agent",
        description=(
            "Intelligence gatherer and research associate. Produces policy analyses, "
            "landscape scans, funder deep-dives, community data reports, news digests, "
            "and background documents that feed Ellah's strategy, advocacy, and communications. "
            "Works for both LFLA and Crestline Collective clients."
        ),
        instructions="./instructions.md",
        files_folder="./files",
        tools=[
            NewsMonitor,
            CensusData,
            LegiscanTracker,
            OrgDeepDive,
            ScholarSearch,
            WebSearchTool(search_context_size="high"),
            IPythonInterpreter,
            LoadFileAttachment,
            ReadFile,
            CopyFile,
        ],
        model=get_default_model(),
        model_settings=ModelSettings(
            reasoning=Reasoning(effort="high", summary="auto") if is_openai_provider() else None,
            response_include=["web_search_call.action.sources"] if is_openai_provider() else None,
        ),
        conversation_starters=[
            "Give me a news digest on LA philanthropy and public libraries from the last week.",
            "Research the Weingart Foundation's current priorities before my meeting Thursday.",
            "Pull community data for South LA for our literacy grant narrative.",
            "What's happening with California library funding legislation this session?",
        ],
    )


if __name__ == "__main__":
    from agency_swarm import Agency
    Agency(create_research_agent()).terminal_demo()
