import os

from agency_swarm import Agent, ModelSettings
from agency_swarm.tools import IPythonInterpreter, PersistentShellTool
from openai.types.shared import Reasoning
from dotenv import load_dotenv

from config import get_default_model, is_openai_provider
from shared_tools import CopyFile

from .tools.deadline_tracker import DeadlineTracker
from .tools.task_manager import TaskManager
from .tools.meeting_prep import MeetingPrep
from .tools.crm_updater import CRMUpdater
from .tools.GetCurrentTime import GetCurrentTime
from .tools.ReadFile import ReadFile
from .tools.WriteFile import WriteFile
from .tools.EditFile import EditFile
from .tools.ListDirectory import ListDirectory

load_dotenv()

# Optional live integrations — enable ONLY after confirming access with LFLA IT.
# Set the corresponding env var to "true" to activate each integration.
#
# VA_INTEGRATIONS_ENABLED=true  — master switch; enables ExecuteTool/ManageConnections/SearchTools/FindTools
#
# Once enabled, the agent can connect to:
#   Gmail / Outlook   — VA_GMAIL_ENABLED, VA_OUTLOOK_ENABLED
#   Google Calendar   — VA_GCAL_ENABLED
#   Google Drive      — VA_GDRIVE_ENABLED
#   Notion / Airtable — VA_NOTION_ENABLED (lower institutional friction; can enable early)
#
# DO NOT enable these without explicit IT and org approval.
# The agent works fully in file-upload / manual-input mode without them.

_INTEGRATIONS_ENABLED = os.getenv("VA_INTEGRATIONS_ENABLED", "false").lower() == "true"


def create_virtual_assistant() -> Agent:
    tools = [
        # Core operational tools — always enabled
        DeadlineTracker,
        TaskManager,
        MeetingPrep,
        CRMUpdater,
        GetCurrentTime,
        ReadFile,
        WriteFile,
        EditFile,
        ListDirectory,
        CopyFile,
        IPythonInterpreter,
        PersistentShellTool,
    ]

    if _INTEGRATIONS_ENABLED:
        # Live system integrations — requires IT approval before enabling
        from shared_tools import ExecuteTool, FindTools, ManageConnections, SearchTools
        tools += [ExecuteTool, FindTools, ManageConnections, SearchTools]

    return Agent(
        name="Virtual Assistant",
        description=(
            "Ellah's operational backbone — deadline tracking, task management, "
            "meeting prep, CRM hygiene, and daily/weekly briefings. "
            "Works fully in file-upload and manual-input mode. "
            "Live email/calendar/Drive integrations available after IT approval."
        ),
        instructions="./instructions.md",
        files_folder="./files",
        tools=tools,
        model=get_default_model(),
        model_settings=ModelSettings(
            reasoning=Reasoning(effort="medium", summary="auto") if is_openai_provider() else None,
        ),
        conversation_starters=[
            "Give me my daily briefing — what's due, what's on the calendar, and what needs a response?",
            "Add a grant deadline to the register.",
            "Prep me for my meeting with [name] tomorrow.",
            "What tasks are overdue or due this week?",
        ],
    )


if __name__ == "__main__":
    from agency_swarm import Agency
    Agency(create_virtual_assistant()).terminal_demo()
