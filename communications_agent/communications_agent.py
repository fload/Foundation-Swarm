from agency_swarm import Agent, ModelSettings
from agency_swarm.tools import WebSearchTool, IPythonInterpreter, LoadFileAttachment
from openai.types.shared import Reasoning

from config import get_default_model, is_openai_provider
from shared_tools import CopyFile
from virtual_assistant.tools.ReadFile import ReadFile

from .tools.voice_library import VoiceLibrary
from .tools.contact_context import ContactContext
from .tools.audience_register import AudienceRegister


def create_communications_agent() -> Agent:
    return Agent(
        name="Communications Agent",
        description=(
            "Ellah's voice on the page. Drafts, edits, and refines all written communications — "
            "donor and funder outreach, board memos, partner letters, organizational "
            "communications, thought leadership, event copy, and talking points. "
            "Also performs final voice-checks on output from other agents before anything "
            "goes external."
        ),
        instructions="./instructions.md",
        files_folder="./files",
        tools=[
            VoiceLibrary,
            ContactContext,
            AudienceRegister,
            WebSearchTool(),
            IPythonInterpreter,
            LoadFileAttachment,
            ReadFile,
            CopyFile,
        ],
        model=get_default_model(),
        model_settings=ModelSettings(
            reasoning=Reasoning(effort="medium", summary="auto") if is_openai_provider() else None,
        ),
        conversation_starters=[
            "Draft a thank-you letter to [donor name] for their recent gift.",
            "Write a cultivation email to [foundation] ahead of our grant conversation.",
            "Draft a LinkedIn post about [topic] for Ellah.",
            "Voice-check this draft from the Development Agent before I send it.",
        ],
    )


if __name__ == "__main__":
    from agency_swarm import Agency
    Agency(create_communications_agent()).terminal_demo()
