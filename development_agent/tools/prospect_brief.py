import os
import re
from typing import Optional

import requests
from agency_swarm.tools import BaseTool
from dotenv import load_dotenv
from pydantic import Field

load_dotenv()

PROPUBLICA_URL = "https://projects.propublica.org/nonprofits/api/v2"
REQUEST_TIMEOUT = 15


class ProspectBrief(BaseTool):
    """
    Compile a one-page donor or prospect brief from publicly available information.

    For individual prospects: pulls web search context and any publicly available
    information (board affiliations, giving history from published sources,
    professional background).

    For foundation prospects: pulls 990 data via ProPublica, stated priorities,
    and recent grant history.

    IMPORTANT: This tool uses only publicly available information. It never
    aggregates private financial data or uses sources that require special access.
    Individual donor research must stay within public information boundaries.

    Use before a cultivation meeting, cold outreach, or ask conversation.
    """

    prospect_name: str = Field(
        ...,
        description="Full name of the individual, family, or foundation to research",
    )
    prospect_type: str = Field(
        ...,
        description="Type of prospect: 'individual', 'family_foundation', or 'public_foundation'",
    )
    org_context: Optional[str] = Field(
        None,
        description="Which org this research is for: 'LFLA' or Crestline client name",
    )
    connection_path: Optional[str] = Field(
        None,
        description="Known connection to Ellah or LFLA (e.g., 'Introduced by board member Jane Smith')",
    )
    known_interests: Optional[str] = Field(
        None,
        description="Any known philanthropic interests or prior giving areas",
    )
    ein: Optional[str] = Field(
        None,
        description="EIN for foundation prospects (e.g., '95-2142715') — improves match accuracy",
    )

    def run(self):
        org = self.org_context or "LFLA"
        lines = [f"# Prospect Brief: {self.prospect_name}"]
        lines.append(f"Prepared for: {org}  |  Type: {self.prospect_type}\n")

        if self.connection_path:
            lines.append(f"**Connection path:** {self.connection_path}")
        if self.known_interests:
            lines.append(f"**Known interests:** {self.known_interests}")
        lines.append("")

        if self.prospect_type in ("family_foundation", "public_foundation"):
            lines.append(self._foundation_brief())
        else:
            lines.append(self._individual_brief())

        # Conflict of interest check
        lines.append("\n## ⚠️ Conflict of Interest Check")
        lines.append(
            "  If this prospect is being cultivated for both LFLA and a Crestline Collective client, "
            "flag this conflict to Ellah before proceeding. Do not pursue simultaneous asks "
            "from both organizations without explicit guidance."
        )

        lines.append(
            "\n---\n"
            "**Suggested next steps:**\n"
            "  • Review public giving history and philanthropy news\n"
            "  • Use Communications Agent to draft a personalized outreach message\n"
            "  • Log this research to CRM with CRMUpdater (action='upsert')\n"
            "  • Set a cultivation timeline in TaskManager"
        )
        return "\n".join(lines)

    def _foundation_brief(self) -> str:
        lines = ["## Foundation Profile"]
        try:
            # Fetch from ProPublica
            if self.ein:
                clean_ein = self.ein.replace("-", "")
                resp = requests.get(
                    f"{PROPUBLICA_URL}/organizations/{clean_ein}.json",
                    timeout=REQUEST_TIMEOUT,
                )
            else:
                resp = requests.get(
                    f"{PROPUBLICA_URL}/search.json",
                    params={"q": self.prospect_name},
                    timeout=REQUEST_TIMEOUT,
                )
                results = resp.json().get("organizations", [])
                if not results:
                    lines.append(f"  No ProPublica record found for '{self.prospect_name}'.")
                    return "\n".join(lines)
                clean_ein = str(results[0].get("ein", "")).replace("-", "")
                resp = requests.get(
                    f"{PROPUBLICA_URL}/organizations/{clean_ein}.json",
                    timeout=REQUEST_TIMEOUT,
                )

            resp.raise_for_status()
            data = resp.json()
            org = data.get("organization", {})
            filings = data.get("filings_with_data", [])

        except requests.exceptions.RequestException as e:
            lines.append(f"  Could not fetch ProPublica data: {str(e)}")
            return "\n".join(lines)
        except (ValueError, KeyError):
            lines.append("  Error parsing ProPublica response.")
            return "\n".join(lines)

        name = org.get("name", self.prospect_name)
        city = org.get("city", "")
        state = org.get("state", "")
        ntee = org.get("ntee_code", "")

        lines.append(f"  Name: {name}")
        ein_str = org.get("ein", "")
        if ein_str:
            lines.append(f"  EIN: {ein_str}")
        if city or state:
            lines.append(f"  Location: {city}, {state}")
        if ntee:
            lines.append(f"  NTEE Code: {ntee}")

        if filings:
            latest = filings[0]
            tax_year = latest.get("tax_prd_yr", "")
            grants_paid = latest.get("totgrnts")
            total_assets = latest.get("totassetsend")

            lines.append(f"\n  Most Recent 990 (Year {tax_year}):")
            if total_assets is not None:
                lines.append(f"    Assets: ${int(total_assets):,}")
            if grants_paid is not None:
                lines.append(f"    Grants Paid: ${int(grants_paid):,}")

            # Recent grants list (if available)
            recent = data.get("filings_with_data", [])[:3]
            if len(recent) > 1:
                lines.append("\n  Recent Grant Totals by Year:")
                for f in recent:
                    yr = f.get("tax_prd_yr", "")
                    gp = f.get("totgrnts")
                    if yr and gp is not None:
                        lines.append(f"    {yr}: ${int(gp):,}")

        pp_link = f"https://projects.propublica.org/nonprofits/organizations/{clean_ein}"
        lines.append(f"\n  ProPublica: {pp_link}")

        if not filings and not org:
            lines.append("  No financial data available.")

        return "\n".join(lines)

    def _individual_brief(self) -> str:
        lines = ["## Individual Prospect Summary"]
        lines.append("  *(Based on publicly available information only)*\n")

        # Search for board affiliations via ProPublica
        lines.append("  **Board Affiliations (Public Nonprofits):**")
        try:
            resp = requests.get(
                f"{PROPUBLICA_URL}/search.json",
                params={"q": self.prospect_name},
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            # ProPublica doesn't directly search by individual name — surface note
            lines.append(
                f"  Search for '{self.prospect_name}' on ProPublica Nonprofit Explorer: "
                f"https://projects.propublica.org/nonprofits/search?q={self.prospect_name.replace(' ', '+')}"
            )
        except requests.exceptions.RequestException:
            lines.append("  Could not connect to ProPublica.")

        lines.append(
            "\n  **Research checklist (complete manually or via web search):**\n"
            f"  □ LinkedIn: https://www.linkedin.com/search/results/all/?keywords={self.prospect_name.replace(' ', '%20')}\n"
            f"  □ LA Times 990 look up: https://projects.propublica.org/nonprofits/search?q={self.prospect_name.replace(' ', '+')}\n"
            "  □ Check Foundation Center / 990 Finder for any family foundation\n"
            "  □ Review LFLA donor database for prior giving history\n"
            "  □ Ask board connector for introduction memo\n"
        )

        lines.append(
            "  **Prospect capacity signals to document:**\n"
            "  □ Board affiliations (nonprofit and corporate)\n"
            "  □ Published philanthropic statements or interviews\n"
            "  □ Notable gifts to peer organizations\n"
            "  □ Professional background and current role\n"
            "  □ Geographic and issue area connections\n"
        )

        lines.append(
            "  ⚠️ Do not use data sources that aggregate private financial records "
            "(wealth screening tools require separate approval before use in LFLA research)."
        )
        return "\n".join(lines)


if __name__ == "__main__":
    print("=== Test: Foundation prospect brief ===")
    tool = ProspectBrief(
        prospect_name="Weingart Foundation",
        prospect_type="public_foundation",
        org_context="LFLA",
        known_interests="Education, equity, health, and community development in Southern California",
    )
    print(tool.run())

    print("\n=== Test: Individual prospect brief ===")
    tool2 = ProspectBrief(
        prospect_name="Jane Smith",
        prospect_type="individual",
        org_context="LFLA",
        connection_path="Introduced by board member Robert Park at the 2025 LFLA Gala",
        known_interests="Libraries, arts, and education funding in Los Angeles",
    )
    print(tool2.run())
