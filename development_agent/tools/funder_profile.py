import os
from typing import Optional

import requests
from agency_swarm.tools import BaseTool
from dotenv import load_dotenv
from pydantic import Field

load_dotenv()

# Candid (formerly GuideStar) API — requires API key
# Apply at https://candid.org/our-products/apis
CANDID_API_KEY = os.getenv("CANDID_API_KEY", "")
CANDID_BASE_URL = "https://api.candid.org"

# ProPublica Nonprofit Explorer — fully public, no key required
# Returns IRS 990 data for any 501(c)(3)
PROPUBLICA_URL = "https://projects.propublica.org/nonprofits/api/v2"

REQUEST_TIMEOUT = 15


class FunderProfile(BaseTool):
    """
    Compile a funder profile for a foundation or nonprofit — pulling giving history,
    stated priorities, and contact information from Candid/GuideStar (if API key is
    configured) and ProPublica Nonprofit Explorer (public IRS 990 data, no key required).

    Use this before writing a grant proposal, LOI, or funder outreach email.
    Also useful for prospect research on individual foundations for Crestline clients.
    """

    funder_name: str = Field(
        ...,
        description="Name of the foundation or nonprofit to research (e.g., 'Weingart Foundation')",
    )
    ein: Optional[str] = Field(
        None,
        description=(
            "Employer Identification Number (EIN) for the organization, if known "
            "(e.g., '95-2142715'). Providing the EIN ensures an exact match."
        ),
    )
    include_990_financials: Optional[bool] = Field(
        True,
        description="Whether to include financial data from the most recent 990 filing (default: True)",
    )

    def run(self):
        lines = [f"# Funder Profile: {self.funder_name}\n"]

        # Step 1: ProPublica lookup (always available, no key needed)
        propublica_data = self._propublica_lookup()
        if propublica_data:
            lines.append("## Organization Overview (IRS 990 / ProPublica)")
            lines.append(propublica_data)

        # Step 2: Candid lookup if API key is configured
        if CANDID_API_KEY:
            candid_data = self._candid_lookup()
            if candid_data:
                lines.append("\n## Candid / GuideStar Profile")
                lines.append(candid_data)
        else:
            lines.append(
                "\n## Candid / GuideStar Profile\n"
                "  ⚠️  CANDID_API_KEY not configured. "
                "Add your Candid API key to .env to enable full profile data.\n"
                "  → Get an API key at https://candid.org/our-products/apis"
            )

        lines.append(
            "\n---\n"
            "**Next steps:**\n"
            "  • Review giving history and stated priorities before drafting an LOI\n"
            "  • Use ParseRFP to analyze any available RFP or guidelines\n"
            "  • Use ProspectBrief for individual donor research"
        )
        return "\n".join(lines)

    def _propublica_lookup(self) -> str:
        """Search ProPublica Nonprofit Explorer for 990 data."""
        try:
            # If EIN is provided, fetch directly
            if self.ein:
                clean_ein = self.ein.replace("-", "")
                url = f"{PROPUBLICA_URL}/organizations/{clean_ein}.json"
                resp = requests.get(url, timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
                data = resp.json()
                org = data.get("organization", {})
                filings = data.get("filings_with_data", [])
            else:
                # Search by name
                resp = requests.get(
                    f"{PROPUBLICA_URL}/search.json",
                    params={"q": self.funder_name},
                    timeout=REQUEST_TIMEOUT,
                )
                resp.raise_for_status()
                results = resp.json().get("organizations", [])
                if not results:
                    return f"  No results found for '{self.funder_name}' in ProPublica database."
                # Take the best match
                org = results[0]
                clean_ein = str(org.get("ein", "")).replace("-", "")
                # Fetch full record for filings
                detail_resp = requests.get(
                    f"{PROPUBLICA_URL}/organizations/{clean_ein}.json",
                    timeout=REQUEST_TIMEOUT,
                )
                detail_resp.raise_for_status()
                detail = detail_resp.json()
                org = detail.get("organization", org)
                filings = detail.get("filings_with_data", [])

        except requests.exceptions.Timeout:
            return "  ProPublica request timed out."
        except requests.exceptions.HTTPError as e:
            return f"  ProPublica lookup failed: {e.response.status_code}"
        except requests.exceptions.RequestException as e:
            return f"  ProPublica connection error: {str(e)}"
        except (ValueError, KeyError):
            return "  Could not parse ProPublica response."

        lines = []
        name = org.get("name", self.funder_name)
        ein_display = org.get("ein", "")
        city = org.get("city", "")
        state = org.get("state", "")
        ntee = org.get("ntee_code", "")
        subsection = org.get("subsection_code", "")
        affiliation = org.get("affiliation_name", "")

        lines.append(f"  Name: {name}")
        if ein_display:
            lines.append(f"  EIN: {ein_display}")
        if city or state:
            lines.append(f"  Location: {city}, {state}")
        if ntee:
            lines.append(f"  NTEE Code: {ntee}")
        if subsection:
            lines.append(f"  IRS Subsection: 501(c)({subsection})")
        if affiliation:
            lines.append(f"  Affiliation: {affiliation}")

        if self.include_990_financials and filings:
            latest = filings[0]
            tax_year = latest.get("tax_prd_yr", "")
            total_revenue = latest.get("totrevenue")
            total_expenses = latest.get("totfuncexpns")
            total_assets = latest.get("totassetsend")
            grants_paid = latest.get("totgrnts")

            lines.append(f"\n  Most Recent 990 (Tax Year {tax_year}):")
            if total_revenue is not None:
                lines.append(f"    Total Revenue:  ${int(total_revenue):>14,}")
            if total_expenses is not None:
                lines.append(f"    Total Expenses: ${int(total_expenses):>14,}")
            if total_assets is not None:
                lines.append(f"    Total Assets:   ${int(total_assets):>14,}")
            if grants_paid is not None:
                lines.append(f"    Grants Paid:    ${int(grants_paid):>14,}")

        lines.append(
            f"\n  ProPublica profile: "
            f"https://projects.propublica.org/nonprofits/organizations/"
            f"{str(org.get('ein', '')).replace('-','')}"
        )
        return "\n".join(lines)

    def _candid_lookup(self) -> str:
        """Fetch profile from Candid Essential endpoint."""
        try:
            # Candid v3 Essentials — public charity summary
            headers = {"Subscription-Key": CANDID_API_KEY}
            if self.ein:
                clean_ein = self.ein.replace("-", "")
                url = f"{CANDID_BASE_URL}/v3/publicprofile/organizations/{clean_ein}"
            else:
                url = f"{CANDID_BASE_URL}/v3/publicprofile/organizations"
                resp = requests.get(
                    f"{CANDID_BASE_URL}/v3/publicprofile/search",
                    params={"search_terms": self.funder_name},
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                )
                resp.raise_for_status()
                results = resp.json().get("data", {}).get("hits", [])
                if not results:
                    return f"  No results found on Candid for '{self.funder_name}'."
                clean_ein = results[0].get("ein", "").replace("-", "")
                url = f"{CANDID_BASE_URL}/v3/publicprofile/organizations/{clean_ein}"

            resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            profile = resp.json().get("data", {})

        except requests.exceptions.Timeout:
            return "  Candid request timed out."
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                return "  Candid API key is invalid or expired. Check CANDID_API_KEY in .env."
            return f"  Candid lookup failed: {e.response.status_code}"
        except requests.exceptions.RequestException as e:
            return f"  Candid connection error: {str(e)}"
        except (ValueError, KeyError):
            return "  Could not parse Candid response."

        lines = []
        org = profile.get("organization", profile)

        mission = org.get("mission", "")
        if mission:
            lines.append(f"  Mission: {mission[:500]}{'…' if len(mission) > 500 else ''}")

        contact = org.get("contact", {})
        if contact:
            phone = contact.get("phone", "")
            email = contact.get("email", "")
            website = contact.get("website", "")
            if phone:
                lines.append(f"  Phone: {phone}")
            if email:
                lines.append(f"  Email: {email}")
            if website:
                lines.append(f"  Website: {website}")

        program_areas = org.get("subject_codes", [])
        if program_areas:
            lines.append(f"  Program Areas: {', '.join(program_areas[:8])}")

        leadership = org.get("people", [])
        if leadership:
            lines.append("  Key Contacts:")
            for person in leadership[:4]:
                name = person.get("name", "")
                title = person.get("title", "")
                if name:
                    lines.append(f"    • {name}" + (f" — {title}" if title else ""))

        if not lines:
            return "  Candid returned a profile but with limited public data."
        return "\n".join(lines)


if __name__ == "__main__":
    print("=== Test: Funder profile lookup (ProPublica only) ===")
    tool = FunderProfile(
        funder_name="Weingart Foundation",
        include_990_financials=True,
    )
    print(tool.run())

    print("\n=== Test: Lookup by EIN ===")
    tool2 = FunderProfile(
        funder_name="California Community Foundation",
        ein="95-3510055",
        include_990_financials=True,
    )
    print(tool2.run())
