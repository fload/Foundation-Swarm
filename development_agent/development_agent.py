from agency_swarm import Agent, ModelSettings
from agency_swarm.tools import WebSearchTool, IPythonInterpreter, LoadFileAttachment
from openai.types.shared import Reasoning

from config import get_default_model, is_openai_provider
from shared_tools import CopyFile
from virtual_assistant.tools.ReadFile import ReadFile

from .tools.search_grants import SearchGrants
from .tools.funder_profile import FunderProfile
from .tools.parse_rfp import ParseRFP
from .tools.prospect_brief import ProspectBrief
from .tools.deadline_log import DeadlineLog


def create_development_agent() -> Agent:
    return Agent(
        name="Development Agent",
        description=(
            "Ellah's dedicated fundraising brain. Handles the full arc of philanthropic "
            "development work — prospect research, grant intelligence and proposal writing, "
            "grant reporting, major gift strategy, corporate partnership development, "
            "and campaign analysis. Works for both LFLA and Crestline Collective clients."
        ),
        instructions="./instructions.md",
        files_folder="./files",
        tools=[
            SearchGrants,
            FunderProfile,
            ParseRFP,
            ProspectBrief,
            DeadlineLog,
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
            "Search for open grant opportunities for LFLA in literacy and digital equity.",
            "Build me a prospect brief for [funder name] before Friday's meeting.",
            "Parse this RFP and tell me if we're a fit and what the deadline is.",
            "Draft a letter of inquiry to [foundation] for our ALOUD program.",
        ],
    )


if __name__ == "__main__":
    from agency_swarm import Agency
    Agency(create_development_agent()).terminal_demo()
