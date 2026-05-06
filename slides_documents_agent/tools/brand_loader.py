import json
import os
from typing import Optional

from agency_swarm.tools import BaseTool
from pydantic import Field

# Brand specs live in the agent's files directory
BRAND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "files", "brand")
)

# Default brand specs — updated when Ellah provides official brand assets
DEFAULT_BRANDS = {
    "LFLA": {
        "full_name": "Library Foundation of Los Angeles",
        "primary_color": "#003366",     # Deep navy — update with official LFLA brand color
        "accent_color": "#C8921A",      # Gold — update with official LFLA brand color
        "background_color": "#FFFFFF",
        "text_color": "#1A1A1A",
        "font_heading": "Georgia",      # Update with official LFLA brand font
        "font_body": "Arial",
        "logo_path": "",                # Set to absolute path after placing logo file
        "tagline": "Supporting the Los Angeles Public Library",
        "website": "www.lfla.org",
        "note": "⚠️ Default brand spec — update with official LFLA brand guidelines",
    },
    "Crestline": {
        "full_name": "Crestline Collective",
        "primary_color": "#2C4A2E",     # Forest green — update with official Crestline color
        "accent_color": "#8B6914",      # Warm brown — update with official Crestline color
        "background_color": "#FFFFFF",
        "text_color": "#1A1A1A",
        "font_heading": "Georgia",
        "font_body": "Arial",
        "logo_path": "",
        "tagline": "Philanthropic strategy and capacity building",
        "website": "",
        "note": "⚠️ Default brand spec — update with official Crestline Collective brand guidelines",
    },
}


class BrandLoader(BaseTool):
    """
    Load brand assets (colors, fonts, logos) for LFLA or Crestline Collective
    to apply consistent branding to slides, documents, and reports.

    ALWAYS call this before generating any branded output. If org context is
    ambiguous, ask Ellah which brand to apply — never guess.

    Brand specs are stored in slides_documents_agent/files/brand/.
    Place official logo files there and update brand.json with official colors.

    Actions:
    - 'load'   — load brand spec for the specified org (default)
    - 'list'   — list available brand configurations
    - 'update' — update or create a brand configuration
    """

    action: str = Field(
        "load",
        description="Action: 'load' (default), 'list', or 'update'",
    )
    org: Optional[str] = Field(
        None,
        description="Organization: 'LFLA' or 'Crestline' (required for 'load' and 'update')",
    )
    updates: Optional[dict] = Field(
        None,
        description="Brand property updates for 'update' action (e.g., {'primary_color': '#003366', 'logo_path': '/path/to/logo.png'})",
    )

    def run(self):
        os.makedirs(BRAND_DIR, exist_ok=True)
        brand_file = os.path.join(BRAND_DIR, "brand.json")

        # Load saved brands, falling back to defaults
        if os.path.exists(brand_file):
            with open(brand_file, "r", encoding="utf-8") as f:
                brands = json.load(f)
        else:
            brands = dict(DEFAULT_BRANDS)

        if self.action == "list":
            lines = ["## Available Brand Configurations\n"]
            for key, spec in brands.items():
                note = spec.get("note", "")
                lines.append(
                    f"**{key}** — {spec.get('full_name', key)}\n"
                    f"  Primary: {spec.get('primary_color')}  Accent: {spec.get('accent_color')}\n"
                    f"  Fonts: {spec.get('font_heading')} / {spec.get('font_body')}\n"
                    f"  Logo: {spec.get('logo_path') or '(not set)'}"
                    + (f"\n  {note}" if note else "")
                )
            return "\n\n".join(lines)

        elif self.action == "update":
            if not self.org:
                return "Error: 'update' requires org ('LFLA' or 'Crestline')."
            if not self.updates:
                return "Error: 'update' requires an updates dict."
            existing = brands.get(self.org, dict(DEFAULT_BRANDS.get(self.org, {})))
            existing.update(self.updates)
            existing.pop("note", None)  # Remove the default warning once updated
            brands[self.org] = existing
            with open(brand_file, "w", encoding="utf-8") as f:
                json.dump(brands, f, indent=2)
            return f"✓ Brand spec updated for {self.org}."

        else:  # load
            if not self.org:
                return (
                    "Error: 'load' requires org. Specify 'LFLA' or 'Crestline'.\n"
                    "⚠️ Do not guess the org context — confirm with Ellah before applying brand."
                )
            spec = brands.get(self.org)
            if not spec:
                return f"No brand spec found for '{self.org}'. Use action='list' to see available brands."

            lines = [f"## Brand Spec: {spec.get('full_name', self.org)}\n"]
            for key, val in spec.items():
                if key != "note":
                    lines.append(f"  **{key}:** {val}")
            if spec.get("note"):
                lines.append(f"\n  {spec['note']}")

            lines.append(
                "\n**Usage:**\n"
                f"  primary_color = \"{spec.get('primary_color')}\"\n"
                f"  accent_color = \"{spec.get('accent_color')}\"\n"
                f"  font_heading = \"{spec.get('font_heading')}\"\n"
                f"  font_body = \"{spec.get('font_body')}\"\n"
                f"  logo_path = \"{spec.get('logo_path') or 'NOT SET — add logo file'}\""
            )
            return "\n".join(lines)


if __name__ == "__main__":
    print("=== Test: Load LFLA brand ===")
    tool = BrandLoader(action="load", org="LFLA")
    print(tool.run())

    print("\n=== Test: List brands ===")
    tool2 = BrandLoader(action="list")
    print(tool2.run())

    print("\n=== Test: Update Crestline brand ===")
    tool3 = BrandLoader(
        action="update",
        org="Crestline",
        updates={"primary_color": "#2C4A2E", "website": "crestlinecollective.com"},
    )
    print(tool3.run())
