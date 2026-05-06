import os
from typing import Optional

import requests
from agency_swarm.tools import BaseTool
from dotenv import load_dotenv
from pydantic import Field

load_dotenv()

LEGISCAN_API_KEY = os.getenv("LEGISCAN_API_KEY", "")
LEGISCAN_URL = "https://api.legiscan.com/"

REQUEST_TIMEOUT = 15


class LegiscanTracker(BaseTool):
    """
    Track relevant California and federal bill status using the LegiScan API.

    Use for policy advocacy monitoring — tracking legislation that affects public
    libraries, literacy programs, digital equity, education funding, and community
    access. Supports Ellah's advocacy work at LFLA and policy context for grants.

    Requires a LegiScan API key (free tier available: https://legiscan.com/legiscan).
    Without a key, returns structured links to manual tracking resources.

    Actions:
    - 'search' — search for bills by keyword in California or US Congress
    - 'status' — get current status of a specific bill by LegiScan bill ID
    """

    action: str = Field(
        "search",
        description="Action: 'search' (default) or 'status'",
    )
    keywords: Optional[str] = Field(
        None,
        description="Keywords to search for (required for 'search', e.g., 'public library funding')",
    )
    state: Optional[str] = Field(
        "CA",
        description="State to search: 'CA' (California, default) or 'US' (US Congress)",
    )
    bill_id: Optional[int] = Field(
        None,
        description="LegiScan bill ID (required for 'status' action)",
    )

    def run(self):
        if not LEGISCAN_API_KEY:
            return self._fallback_links()

        if self.action == "status":
            return self._get_bill_status()
        else:
            return self._search_bills()

    def _search_bills(self) -> str:
        if not self.keywords:
            return "Error: 'search' requires keywords."

        try:
            params = {
                "key": LEGISCAN_API_KEY,
                "op": "getSearch",
                "state": self.state or "CA",
                "query": self.keywords,
            }
            resp = requests.get(LEGISCAN_URL, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            return f"LegiScan API error: {str(e)}\n" + self._fallback_links()
        except ValueError:
            return "Could not parse LegiScan response.\n" + self._fallback_links()

        if data.get("status") != "OK":
            return (
                f"LegiScan returned status: {data.get('status')}\n"
                + self._fallback_links()
            )

        results = data.get("searchresult", {})
        summary = results.get("summary", {})
        bills = [v for k, v in results.items() if k != "summary" and isinstance(v, dict)]

        state_label = "California" if (self.state or "CA") == "CA" else "U.S. Congress"
        lines = [
            f"## LegiScan Results: '{self.keywords}' ({state_label})",
            f"Found {summary.get('count', len(bills))} matching bills\n",
        ]

        for bill in bills[:8]:
            bill_number = bill.get("bill_number", "")
            title = bill.get("title", "Untitled")
            last_action = bill.get("last_action", "")
            last_action_date = bill.get("last_action_date", "")
            status = bill.get("status", "")
            url = bill.get("url", "")
            bill_id = bill.get("bill_id", "")

            status_label = {
                "1": "Introduced",
                "2": "In Committee",
                "3": "Passed One Chamber",
                "4": "Passed Legislature",
                "5": "Sent to Executive",
                "6": "Signed",
                "7": "Vetoed",
                "8": "Failed",
            }.get(str(status), f"Status {status}")

            lines.append(
                f"**{bill_number}**: {title}\n"
                f"  Status: {status_label}  |  Last Action: {last_action_date}\n"
                f"  Last Action: {last_action}\n"
                f"  ID: {bill_id}  |  {url}"
            )

        if not bills:
            lines.append(f"No bills found matching '{self.keywords}' in {state_label}.")

        lines.append(
            "\n---\nTo track a specific bill, use action='status' with the bill_id."
        )
        return "\n".join(lines)

    def _get_bill_status(self) -> str:
        if not self.bill_id:
            return "Error: 'status' action requires a bill_id."

        try:
            params = {
                "key": LEGISCAN_API_KEY,
                "op": "getBill",
                "id": self.bill_id,
            }
            resp = requests.get(LEGISCAN_URL, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            return f"LegiScan API error: {str(e)}"
        except ValueError:
            return "Could not parse LegiScan response."

        bill = data.get("bill", {})
        if not bill:
            return f"No bill found with ID {self.bill_id}."

        title = bill.get("title", "")
        bill_number = bill.get("bill_number", "")
        description = bill.get("description", "")
        status = bill.get("status", "")
        state = bill.get("state", "")
        url = bill.get("url", "")

        status_label = {
            "1": "Introduced",
            "2": "In Committee",
            "3": "Passed One Chamber",
            "4": "Passed Legislature",
            "5": "Sent to Executive",
            "6": "Signed",
            "7": "Vetoed",
            "8": "Failed",
        }.get(str(status), f"Status {status}")

        history = bill.get("history", [])
        sponsors = bill.get("sponsors", [])

        lines = [
            f"## Bill Status: {bill_number} ({state})",
            f"**Title:** {title}",
            f"**Status:** {status_label}",
        ]
        if description:
            lines.append(f"**Description:** {description[:400]}")
        if url:
            lines.append(f"**Link:** {url}")

        if sponsors:
            sponsor_names = [s.get("name", "") for s in sponsors[:3]]
            lines.append(f"**Sponsors:** {', '.join(filter(None, sponsor_names))}")

        if history:
            lines.append("\n**Recent History:**")
            for h in history[-5:]:
                lines.append(f"  {h.get('date', '')}: {h.get('action', '')}")

        return "\n".join(lines)

    def _fallback_links(self) -> str:
        lines = [
            "⚠️ LEGISCAN_API_KEY not configured.",
            "   → Get a free API key at https://legiscan.com/legiscan\n",
            "**Manual tracking resources:**",
            "  • California Legislature: https://leginfo.legislature.ca.gov",
            "  • Congress.gov: https://www.congress.gov",
            "  • ALA Advocacy: https://www.ala.org/advocacy/legislation",
            "  • California Library Association: https://www.cla-net.org/advocacy",
            "  • CALeaflet (CA Library Advocacy): https://www.cla-net.org/page/advocacy",
        ]
        if self.keywords:
            kw = self.keywords.replace(" ", "+")
            lines.append(
                f"\n  Search California Legislature for '{self.keywords}':\n"
                f"  https://leginfo.legislature.ca.gov/faces/billSearchClient.xhtml?keywords={kw}"
            )
        return "\n".join(lines)


if __name__ == "__main__":
    print("=== Test: Search CA bills — library funding ===")
    tool = LegiscanTracker(
        action="search",
        keywords="public library funding digital equity",
        state="CA",
    )
    print(tool.run())
