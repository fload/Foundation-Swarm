from agency_swarm import Agent, ModelSettings
from agency_swarm.tools import (
    IPythonInterpreter,
    PersistentShellTool,
    LoadFileAttachment,
    WebSearchTool,
)
from datetime import datetime, timezone
from openai.types.shared import Reasoning
from pathlib import Path

from config import get_default_model, is_openai_provider
from shared_tools.CopyFile import CopyFile
from virtual_assistant.tools.ReadFile import ReadFile

# Import all existing slide tools from slides_agent
from slides_agent.tools import (
    InsertNewSlides,
    ModifySlide,
    ManageTheme,
    DeleteSlide,
    SlideScreenshot,
    ReadSlide,
    BuildPptxFromHtmlSlides,
    RestoreSnapshot,
    CreatePptxThumbnailGrid,
    CheckSlideCanvasOverflow,
    CheckSlide,
    DownloadImage,
    EnsureRasterImage,
    ImageSearch,
    GenerateImage,
)

# Import docs tools from docs_agent for Word document production
from docs_agent.tools.CreateDocument import CreateDocument
from docs_agent.tools.ModifyDocument import ModifyDocument
from docs_agent.tools.ViewDocument import ViewDocument
from docs_agent.tools.ListDocuments import ListDocuments
from docs_agent.tools.ConvertDocument import ConvertDocument

# Import new slides_documents_agent-specific tools
from .tools.brand_loader import BrandLoader
from .tools.chart_builder import ChartBuilder

_INSTRUCTIONS_PATH = Path(__file__).parent / "instructions.md"


def _list_existing_projects() -> str:
    from slides_agent.tools.slide_file_utils import get_mnt_dir
    base = get_mnt_dir()
    if not base.exists():
        return "(none)"
    dirs = sorted(d.name for d in base.iterdir() if d.is_dir())
    return "\n".join(f"  - {d}" for d in dirs) if dirs else "(none)"


def _build_instructions() -> str:
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = _INSTRUCTIONS_PATH.read_text(encoding="utf-8")
    projects_block = _list_existing_projects()
    return (
        f"{body}\n\n"
        f"Current date/time (UTC): {now_utc}\n\n"
        f"Existing project folders (do NOT reuse these names for a new presentation):\n{projects_block}"
    )


def create_slides_documents_agent() -> Agent:
    return Agent(
        name="Slides & Documents Agent",
        description=(
            "Produces polished, presentation-ready slides and documents on demand. "
            "Board decks, funder pitch decks, strategic plans, program reports, "
            "one-pagers, meeting materials, and data visualizations — formatted and ready. "
            "Always confirms org brand (LFLA or Crestline) before generating branded output."
        ),
        instructions=_build_instructions(),
        tools=[
            # Brand and chart tools (new)
            BrandLoader,
            ChartBuilder,
            # PowerPoint slide tools (from slides_agent)
            InsertNewSlides,
            ModifySlide,
            ManageTheme,
            DeleteSlide,
            SlideScreenshot,
            ReadSlide,
            BuildPptxFromHtmlSlides,
            RestoreSnapshot,
            CreatePptxThumbnailGrid,
            CheckSlideCanvasOverflow,
            CheckSlide,
            DownloadImage,
            EnsureRasterImage,
            GenerateImage,
            ImageSearch,
            # Word document tools (from docs_agent)
            CreateDocument,
            ModifyDocument,
            ViewDocument,
            ListDocuments,
            ConvertDocument,
            # Utility
            IPythonInterpreter,
            PersistentShellTool,
            LoadFileAttachment,
            CopyFile,
            ReadFile,
            WebSearchTool(search_context_size="high"),
        ],
        model=get_default_model(),
        model_settings=ModelSettings(
            reasoning=Reasoning(effort="high", summary="auto") if is_openai_provider() else None,
            verbosity="medium" if is_openai_provider() else None,
            response_include=["web_search_call.action.sources"] if is_openai_provider() else None,
        ),
        conversation_starters=[
            "Create a board meeting deck for the June LFLA board meeting.",
            "Turn this strategy content into a funder pitch deck for Weingart Foundation.",
            "Draft a formatted one-pager on LFLA's student success programs.",
            "Build a program report for our Q2 literacy initiative.",
        ],
    )


if __name__ == "__main__":
    from agency_swarm import Agency
    Agency(create_slides_documents_agent()).terminal_demo(reload=False)
