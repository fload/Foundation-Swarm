from agency_swarm import Agent, ModelSettings
from agency_swarm.tools import IPythonInterpreter, LoadFileAttachment, WebSearchTool
from openai.types.shared import Reasoning

from config import get_default_model, is_openai_provider
from shared_tools import CopyFile
from virtual_assistant.tools.ReadFile import ReadFile
from slides_documents_agent.tools.chart_builder import ChartBuilder

from .tools.financial_ratios import FinancialRatios
from .tools.logic_model_builder import LogicModelBuilder


def create_strategy_impact_agent() -> Agent:
    return Agent(
        name="Strategy & Impact Agent",
        description=(
            "Ellah's analytical and strategic planning partner. Performs nonprofit financial "
            "analysis, builds program logic models and evaluation frameworks, produces impact "
            "measurement reports, and develops strategic plans. Works for LFLA and "
            "Crestline Collective clients."
        ),
        instructions="./instructions.md",
        files_folder="./files",
        tools=[
            FinancialRatios,
            LogicModelBuilder,
            ChartBuilder,
            IPythonInterpreter,
            LoadFileAttachment,
            ReadFile,
            CopyFile,
            WebSearchTool(),
        ],
        model=get_default_model(),
        model_settings=ModelSettings(
            reasoning=Reasoning(effort="high", summary="auto") if is_openai_provider() else None,
        ),
        conversation_starters=[
            "Analyze LFLA's financial health from this 990.",
            "Build a logic model for our new digital equity program.",
            "Create an evaluation framework for the literacy initiative.",
            "Produce a strategic planning deck for the board retreat.",
        ],
    )


if __name__ == "__main__":
    from agency_swarm import Agency
    Agency(create_strategy_impact_agent()).terminal_demo()
