import os
from typing import Optional

import requests
from agency_swarm.tools import BaseTool
from dotenv import load_dotenv
from pydantic import Field

load_dotenv()

PROPUBLICA_URL = "https://projects.propublica.org/nonprofits/api/v2"
REQUEST_TIMEOUT = 15


class OrgDeepDive(BaseTool):
    """
    Compile a structured background brief on any nonprofit organization — mission,
    programs, financials (from IRS 990 via ProPublica), leadership, and recent news.

    Use for due diligence on potential partners, grantees, corporate sponsors, or
    peer organizations. Also used by the orchestrator for meeting prep when an
    attendee's organization is not in the CRM.

    Returns a one-page brief suitable for use in meeting prep, funder research,
    or partnership strategy.
    """

    org_name: str = Field(
        ...,
        description="Full name of the nonprofit organization to research",
    )
    ein: Optional[str] = Field(
        None,
        description="EIN (e.g., '95-3510055') for exact match — recommended for common names",
    )
    research_purpose: Optional[str] = Field(
        None,
        description=(
            "Why this research is needed: 'partnership_due_diligence', 'funder_research', "
            "'peer_benchmarking', 'meeting_prep', or 'crestline_client_mapping'"
        ),
    )
    include_financials: Optional[bool] = Field(
        True,
        description="Include financial data from most recent 990 (default: True)",
    )

    def run(self):
        lines = [f"# Org Deep Dive: {self.org_name}"]
        if self.research_purpose:
            lines.append(f"Purpose: {self.research_purpose.replace('_', ' ').title()}\n")

        # Fetch from ProPublica
        org_data, filings = self._fetch_propublica()

        if org_data:
            lines.append("## Organization Overview")
            name = org_data.get("name", self.org_name)
            city = org_data.get("city", "")
            state = org_data.get("state", "")
            ein_val = org_data.get("ein", "")
            ntee = org_data.get("ntee_code", "")

            if name:
                lines.append(f"  **Name:** {name}")
            if ein_val:
                lines.append(f"  **EIN:** {ein_val}")
            if city or state:
                lines.append(f"  **Location:** {city}, {state}")
            if ntee:
                lines.append(f"  **NTEE Code:** {ntee}")

            pp_ein = str(ein_val).replace("-", "") if ein_val else ""
            if pp_ein:
                lines.append(
                    f"  **ProPublica Profile:** "
                    f"https://projects.propublica.org/nonprofits/organizations/{pp_ein}"
                )

        if self.include_990_financials(filings):
            lines.append("\n## Financial Snapshot (Most Recent 990)")
            latest = filings[0]
            year = latest.get("tax_prd_yr", "")
            revenue = latest.get("totrevenue")
            expenses = latest.get("totfuncexpns")
            assets = latest.get("totassetsend")
            grants = latest.get("totgrnts")
            employees = latest.get("noemployees")

            if year:
                lines.append(f"  Tax Year: {year}")
            if revenue is not None:
                lines.append(f"  Total Revenue:  ${int(revenue):,}")
            if expenses is not None:
                lines.append(f"  Total Expenses: ${int(expenses):,}")
            if assets is not None:
                lines.append(f"  Total Assets:   ${int(assets):,}")
            if grants is not None:
                lines.append(f"  Grants Paid:    ${int(grants):,}")
            if employees:
                lines.append(f"  Employees: {employees}")

            # Compute program expense ratio
            if revenue and expenses:
                try:
                    prog_ratio = int(expenses) / int(revenue) * 100
                    lines.append(f"\n  Program expense ratio: ~{prog_ratio:.0f}%")
                except (ValueError, ZeroDivisionError):
                    pass

        lines.append("\n## Research Checklist (complete via web search)")
        lines.append(
            "  □ Mission statement (website 'About' page)\n"
            "  □ Current programs and key initiatives\n"
            "  □ Executive Director / CEO name and background\n"
            "  □ Board chair and notable board members\n"
            "  □ Recent news, press releases, or annual reports\n"
            "  □ Social media presence and community engagement\n"
            "  □ Known funders and funding sources (check 990 Schedule I if available)\n"
        )

        if self.research_purpose == "partnership_due_diligence":
            lines.append(
                "## Partnership Notes\n"
                "  □ Do their programs complement or overlap with LFLA/Crestline client work?\n"
                "  □ Any shared funders? (potential conflict or collaboration opportunity)\n"
                "  □ Leadership relationships with LFLA board or Ellah's network?\n"
                "  □ Any prior collaboration or referrals?\n"
            )

        if self.research_purpose == "crestline_client_mapping":
            lines.append(
                "## Competitive / Complementary Mapping Note\n"
                "  This research is for a Crestline Collective client — treat as confidential.\n"
                "  Do not reference alongside LFLA materials.\n"
            )

        if not org_data:
            lines.append(
                "\n⚠️ No ProPublica record found. Search manually:\n"
                f"  https://projects.propublica.org/nonprofits/search?q={self.org_name.replace(' ', '+')}"
            )

        lines.append(
            "\n---\n"
            "**Next steps:**\n"
            "  • Log key findings to CRM with CRMUpdater (action='upsert')\n"
            "  • Use Research Agent's WebSearch to find recent news and leadership\n"
            "  • Use FunderProfile for deeper financial due diligence on foundations"
        )

        return "\n".join(lines)

    def include_990_financials(self, filings: list) -> bool:
        return bool(self.include_financials and filings)

    def _fetch_propublica(self):
        try:
            if self.ein:
                clean_ein = self.ein.replace("-", "")
                resp = requests.get(
                    f"{PROPUBLICA_URL}/organizations/{clean_ein}.json",
                    timeout=REQUEST_TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("organization", {}), data.get("filings_with_data", [])
            else:
                resp = requests.get(
                    f"{PROPUBLICA_URL}/search.json",
                    params={"q": self.org_name},
                    timeout=REQUEST_TIMEOUT,
                )
                resp.raise_for_status()
                results = resp.json().get("organizations", [])
                if not results:
                    return {}, []
                clean_ein = str(results[0].get("ein", "")).replace("-", "")
                resp2 = requests.get(
                    f"{PROPUBLICA_URL}/organizations/{clean_ein}.json",
                    timeout=REQUEST_TIMEOUT,
                )
                resp2.raise_for_status()
                data = resp2.json()
                return data.get("organization", {}), data.get("filings_with_data", [])
        except requests.exceptions.RequestException:
            return {}, []
        except (ValueError, KeyError):
            return {}, []


if __name__ == "__main__":
    print("=== Test: Org Deep Dive — California Community Foundation ===")
    tool = OrgDeepDive(
        org_name="California Community Foundation",
        research_purpose="funder_research",
        include_financials=True,
    )
    print(tool.run())
