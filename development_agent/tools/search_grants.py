import os
from typing import Optional

import requests
from agency_swarm.tools import BaseTool
from dotenv import load_dotenv
from pydantic import Field

load_dotenv()

# Grants.gov public search endpoint — no API key required
GRANTS_GOV_URL = "https://apply07.grants.gov/grantsws/rest/opportunities/search/"

# California state grants portal (SVOG-style XML feed) — public
CA_GRANTS_URL = "https://www.grants.ca.gov/grants/get-grant-opportunities/"

# Request timeout in seconds
REQUEST_TIMEOUT = 15


class SearchGrants(BaseTool):
    """
    Search for open grant opportunities on Grants.gov and California state portals
    filtered by keyword, agency, and category.

    Returns a structured list of matching opportunities with title, funder, deadline,
    award amount range, and a direct link for each match.

    Use this to build or refresh the grant calendar for LFLA or to identify funding
    opportunities for Crestline Collective clients.
    """

    keywords: str = Field(
        ...,
        description=(
            "Search keywords (e.g., 'public library literacy', 'digital equity', "
            "'arts education Los Angeles')"
        ),
    )
    source: Optional[str] = Field(
        "grants.gov",
        description="Which portal to search: 'grants.gov' (default) or 'california'",
    )
    max_results: Optional[int] = Field(
        10,
        description="Maximum number of results to return (default: 10, max: 25)",
    )
    opportunity_status: Optional[str] = Field(
        "posted",
        description=(
            "Filter by status: 'posted' (open, default), 'forecasted', "
            "'closed', or 'archived'"
        ),
    )
    eligible_applicants: Optional[str] = Field(
        None,
        description=(
            "Filter by applicant type, e.g. 'Nonprofits having a 501(c)(3) status', "
            "'State governments', 'Native American tribal organizations'"
        ),
    )

    def run(self):
        limit = min(self.max_results or 10, 25)

        if self.source == "california":
            return self._search_california(limit)
        else:
            return self._search_grants_gov(limit)

    def _search_grants_gov(self, limit: int) -> str:
        # Build the Grants.gov v2 search payload
        payload = {
            "keyword": self.keywords,
            "oppStatuses": self.opportunity_status or "posted",
            "rows": limit,
            "sortBy": "openDate|desc",
            "oppTypes": "",
        }
        if self.eligible_applicants:
            payload["eligibilities"] = self.eligible_applicants

        try:
            resp = requests.post(
                GRANTS_GOV_URL,
                json=payload,
                timeout=REQUEST_TIMEOUT,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.Timeout:
            return "Error: Grants.gov request timed out. Try again or search California portal."
        except requests.exceptions.RequestException as e:
            return f"Error connecting to Grants.gov: {str(e)}"
        except ValueError:
            return "Error: Could not parse Grants.gov response."

        opportunities = data.get("oppHits", [])
        if not opportunities:
            return (
                f"No open opportunities found on Grants.gov for '{self.keywords}'.\n"
                "Try broader keywords or check the California grants portal."
            )

        lines = [
            f"## Grants.gov Results: '{self.keywords}'",
            f"Found {len(opportunities)} matching opportunit{'y' if len(opportunities) == 1 else 'ies'}\n",
        ]

        for i, opp in enumerate(opportunities, 1):
            title = opp.get("oppTitle", "Untitled")
            agency = opp.get("agencyName", "Unknown Agency")
            opp_number = opp.get("oppNumber", "")
            close_date = opp.get("closeDate", "Not specified")
            post_date = opp.get("openDate", "")
            award_floor = opp.get("awardCeiling", "")
            award_ceiling = opp.get("awardFloor", "")
            opp_id = opp.get("id", "")

            award_str = ""
            if award_floor or award_ceiling:
                floor_fmt = f"${int(award_floor):,}" if award_floor else "?"
                ceil_fmt = f"${int(award_ceiling):,}" if award_ceiling else "?"
                award_str = f"  Award range: {floor_fmt} – {ceil_fmt}\n"

            link = f"https://www.grants.gov/search-results-detail/{opp_id}" if opp_id else ""

            lines.append(
                f"### {i}. {title}\n"
                f"  Agency: {agency}\n"
                f"  Number: {opp_number}\n"
                f"  Posted: {post_date}  |  Deadline: {close_date}\n"
                f"{award_str}"
                f"  Link: {link or 'grants.gov/search'}"
            )

        lines.append(
            "\n---\nTo add a deadline to the register, pass the title and close date "
            "to the DeadlineTracker tool (action='add')."
        )
        return "\n".join(lines)

    def _search_california(self, limit: int) -> str:
        # California Grants Portal public API
        try:
            params = {
                "q": self.keywords,
                "status": "open",
                "limit": limit,
            }
            resp = requests.get(
                CA_GRANTS_URL,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.Timeout:
            return "Error: California Grants Portal request timed out."
        except requests.exceptions.RequestException as e:
            return (
                f"Error connecting to California Grants Portal: {str(e)}\n"
                "You can search manually at https://www.grants.ca.gov"
            )
        except ValueError:
            return "Error: Could not parse California Grants Portal response."

        # The CA portal returns a 'grants' or 'results' key depending on version
        grants = data.get("grants") or data.get("results") or []
        if not grants:
            return (
                f"No open opportunities found on California Grants Portal for '{self.keywords}'.\n"
                "Search manually at https://www.grants.ca.gov"
            )

        lines = [
            f"## California Grants Portal Results: '{self.keywords}'",
            f"Found {len(grants)} matching grant{'s' if len(grants) != 1 else ''}\n",
        ]
        for i, g in enumerate(grants[:limit], 1):
            title = g.get("title") or g.get("grantTitle", "Untitled")
            agency = g.get("agency") or g.get("grantor", "Unknown")
            deadline = g.get("deadline") or g.get("closeDate", "Not specified")
            amount = g.get("amount") or g.get("maxAward", "")
            url = g.get("url") or g.get("link", "https://www.grants.ca.gov")
            lines.append(
                f"### {i}. {title}\n"
                f"  Agency: {agency}\n"
                f"  Deadline: {deadline}\n"
                + (f"  Max Award: {amount}\n" if amount else "")
                + f"  Link: {url}"
            )

        return "\n".join(lines)


if __name__ == "__main__":
    print("=== Test: Grants.gov search for public library literacy ===")
    tool = SearchGrants(
        keywords="public library literacy digital equity",
        source="grants.gov",
        max_results=5,
    )
    print(tool.run())

    print("\n=== Test: California grants search ===")
    tool2 = SearchGrants(
        keywords="arts education Los Angeles nonprofit",
        source="california",
        max_results=5,
    )
    print(tool2.run())
