import os
from typing import Optional

from agency_swarm.tools import BaseTool
from pydantic import Field

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "files", "charts"))


class ChartBuilder(BaseTool):
    """
    Produce clean, publication-ready charts (bar, line, pie, stacked bar, horizontal bar)
    for embedding in presentations, reports, and one-pagers.

    Charts are saved as PNG files and returned with file paths for embedding.
    Designed for nonprofit impact data: program metrics, fundraising pipelines,
    budget breakdowns, and demographic data.

    Requires matplotlib (pip install matplotlib).
    """

    chart_type: str = Field(
        ...,
        description="Chart type: 'bar', 'horizontal_bar', 'line', 'pie', 'stacked_bar'",
    )
    title: str = Field(..., description="Chart title")
    labels: list = Field(
        ...,
        description="Category labels (x-axis for bar/line, slice labels for pie). Example: ['FY23', 'FY24', 'FY25']",
    )
    values: list = Field(
        ...,
        description="Data values matching labels. For stacked_bar, provide a list of series lists.",
    )
    series_labels: Optional[list] = Field(
        None,
        description="Series names for stacked_bar or multi-line charts (e.g., ['Foundations', 'Individuals', 'Government'])",
    )
    x_label: Optional[str] = Field(None, description="X-axis label")
    y_label: Optional[str] = Field(None, description="Y-axis label")
    color_scheme: Optional[str] = Field(
        "lfla",
        description="Color scheme: 'lfla' (navy/gold), 'crestline' (green/brown), 'neutral', or 'accessible'",
    )
    filename: Optional[str] = Field(
        None,
        description="Output filename without extension (default: auto-generated from title)",
    )
    output_dir: Optional[str] = Field(
        None,
        description="Output directory path (default: slides_documents_agent/files/charts/)",
    )
    value_format: Optional[str] = Field(
        None,
        description="Format for value labels: 'dollar' ($1,234), 'percent' (12%), 'number' (1,234), or None for no labels",
    )

    def run(self):
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import matplotlib.ticker as mticker
            import numpy as np
        except ImportError:
            return "Error: matplotlib is required. Run: pip install matplotlib"

        out_dir = self.output_dir or OUTPUT_DIR
        os.makedirs(out_dir, exist_ok=True)

        # Filename
        fname = self.filename or self.title.lower().replace(" ", "_").replace("/", "_")[:40]
        fname = "".join(c for c in fname if c.isalnum() or c in "_-")
        output_path = os.path.join(out_dir, f"{fname}.png")

        # Color palettes
        palettes = {
            "lfla": ["#003366", "#C8921A", "#4A7AB5", "#E8B84B", "#1A4D80", "#F0D080"],
            "crestline": ["#2C4A2E", "#8B6914", "#4A7A4E", "#B8902A", "#366038", "#D4A840"],
            "neutral": ["#4A4A4A", "#7A7A7A", "#AAAAAA", "#2A2A2A", "#6A6A6A", "#9A9A9A"],
            "accessible": ["#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD", "#8C564B"],
        }
        colors = palettes.get(self.color_scheme or "lfla", palettes["lfla"])

        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")

        def fmt_val(v):
            if self.value_format == "dollar":
                return f"${int(v):,}"
            elif self.value_format == "percent":
                return f"{v:.1f}%"
            elif self.value_format == "number":
                return f"{int(v):,}"
            return str(v)

        if self.chart_type == "bar":
            ax.bar(self.labels, self.values, color=colors[0], edgecolor="white")
            if self.value_format:
                for i, v in enumerate(self.values):
                    ax.text(i, v * 1.01, fmt_val(v), ha="center", va="bottom", fontsize=9)

        elif self.chart_type == "horizontal_bar":
            ax.barh(self.labels, self.values, color=colors[0], edgecolor="white")
            if self.value_format:
                for i, v in enumerate(self.values):
                    ax.text(v * 1.01, i, fmt_val(v), ha="left", va="center", fontsize=9)

        elif self.chart_type == "line":
            ax.plot(self.labels, self.values, color=colors[0], linewidth=2.5, marker="o", markersize=6)
            ax.fill_between(range(len(self.labels)), self.values, alpha=0.1, color=colors[0])

        elif self.chart_type == "pie":
            wedge_colors = colors[: len(self.labels)]
            ax.pie(
                self.values,
                labels=self.labels,
                colors=wedge_colors,
                autopct="%1.1f%%" if not self.value_format else lambda p: fmt_val(p),
                startangle=90,
                pctdistance=0.85,
            )
            ax.axis("equal")

        elif self.chart_type == "stacked_bar":
            if not self.series_labels or not isinstance(self.values[0], (list, tuple)):
                return (
                    "Error: stacked_bar requires series_labels and values as a list of series lists.\n"
                    "Example: values=[[100, 200, 150], [80, 90, 120]], series_labels=['Foundations', 'Individuals']"
                )
            x = range(len(self.labels))
            bottoms = [0] * len(self.labels)
            for i, (series, slabel) in enumerate(zip(self.values, self.series_labels)):
                ax.bar(x, series, bottom=bottoms, label=slabel, color=colors[i % len(colors)])
                bottoms = [b + v for b, v in zip(bottoms, series)]
            ax.legend(loc="upper right", fontsize=9)
            ax.set_xticks(list(x))
            ax.set_xticklabels(self.labels)

        else:
            return f"Unknown chart type '{self.chart_type}'. Use: bar, horizontal_bar, line, pie, stacked_bar"

        ax.set_title(self.title, fontsize=14, fontweight="bold", pad=12)
        if self.x_label:
            ax.set_xlabel(self.x_label, fontsize=10)
        if self.y_label:
            ax.set_ylabel(self.y_label, fontsize=10)

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)

        return f"✓ Chart saved: {output_path}\n  Title: {self.title}\n  Type: {self.chart_type}\n  Labels: {self.labels}"


if __name__ == "__main__":
    print("=== Test: Bar chart — fundraising by source ===")
    tool = ChartBuilder(
        chart_type="bar",
        title="LFLA FY25 Revenue by Source",
        labels=["Major Donors", "Foundation Grants", "Corporate", "Government", "Events"],
        values=[3200000, 2800000, 1500000, 1200000, 800000],
        y_label="Revenue ($)",
        value_format="dollar",
        color_scheme="lfla",
        filename="fy25_revenue_by_source",
    )
    print(tool.run())
