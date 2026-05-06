import os
from typing import Optional

import requests
from agency_swarm.tools import BaseTool
from dotenv import load_dotenv
from pydantic import Field

load_dotenv()

CENSUS_API_KEY = os.getenv("CENSUS_API_KEY", "")
CENSUS_ACS5_URL = "https://api.census.gov/data/2022/acs/acs5"

# Common variable sets for nonprofit needs assessment narratives
VARIABLE_SETS = {
    "poverty": {
        "B17001_001E": "Total population for poverty status",
        "B17001_002E": "Population below poverty level",
    },
    "education": {
        "B15003_001E": "Population 25+ (education)",
        "B15003_017E": "High school diploma or GED",
        "B15003_022E": "Bachelor's degree",
        "B15003_025E": "Graduate or professional degree",
    },
    "internet_access": {
        "B28002_001E": "Total households (internet)",
        "B28002_004E": "With broadband internet",
        "B28002_013E": "No internet access",
    },
    "race_ethnicity": {
        "B03002_001E": "Total population",
        "B03002_003E": "White alone, not Hispanic",
        "B03002_004E": "Black or African American alone",
        "B03002_006E": "Asian alone",
        "B03002_012E": "Hispanic or Latino",
    },
    "housing": {
        "B25003_001E": "Total occupied housing units",
        "B25003_002E": "Owner-occupied",
        "B25003_003E": "Renter-occupied",
    },
    "income": {
        "B19013_001E": "Median household income",
        "B19001_002E": "Households earning less than $10,000",
    },
}


class CensusData(BaseTool):
    """
    Pull ACS 5-year Census data by geography for use in grant narratives,
    needs assessments, program design rationale, and impact reporting.

    Supports city, county, ZIP code, and congressional/state district geographies
    for Los Angeles and other California areas.

    Requires a Census API key (free: https://api.census.gov/data/key_signup.html).
    Degrades gracefully with manual lookup links if key is not configured.
    """

    geography: str = Field(
        ...,
        description=(
            "Geographic area. Examples: 'Los Angeles city', 'Los Angeles County', "
            "'90001' (ZIP), 'city of Pasadena', 'California'"
        ),
    )
    variable_set: Optional[str] = Field(
        "poverty",
        description=(
            "Which data set to pull: 'poverty', 'education', 'internet_access', "
            "'race_ethnicity', 'housing', or 'income' (default: 'poverty')"
        ),
    )
    program_context: Optional[str] = Field(
        None,
        description="Grant or program context — used to frame the narrative output.",
    )

    def run(self):
        var_set = self.variable_set or "poverty"
        variables = VARIABLE_SETS.get(var_set)
        if not variables:
            available = ", ".join(VARIABLE_SETS.keys())
            return f"Unknown variable set '{var_set}'. Available: {available}"

        if not CENSUS_API_KEY:
            return self._fallback_links(var_set)

        geo_params = self._parse_geography()
        if not geo_params:
            return (
                f"Could not parse geography '{self.geography}'.\n"
                + self._fallback_links(var_set)
            )

        var_string = ",".join(["NAME"] + list(variables.keys()))

        try:
            params = {"get": var_string, "key": CENSUS_API_KEY}
            params.update(geo_params)
            resp = requests.get(CENSUS_ACS5_URL, params=params, timeout=15)
            resp.raise_for_status()
            rows = resp.json()
        except requests.exceptions.RequestException as e:
            return f"Census API error: {str(e)}\n" + self._fallback_links(var_set)
        except (ValueError, IndexError):
            return "Could not parse Census API response.\n" + self._fallback_links(var_set)

        if len(rows) < 2:
            return f"No data returned for '{self.geography}'.\n" + self._fallback_links(var_set)

        headers = rows[0]
        values = rows[1]
        data = dict(zip(headers, values))

        geo_name = data.get("NAME", self.geography)
        lines = [f"## Census Data: {geo_name}", f"Source: ACS 5-Year Estimates (2022)\n"]

        context_note = f"Context: {self.program_context}\n" if self.program_context else ""
        if context_note:
            lines.append(context_note)

        for var_code, label in variables.items():
            val = data.get(var_code)
            if val and val != "-666666666":
                try:
                    formatted = f"{int(val):,}"
                except (ValueError, TypeError):
                    formatted = str(val)
                lines.append(f"  {label}: {formatted}")

        # Compute useful ratios
        if var_set == "poverty":
            total = data.get("B17001_001E")
            below = data.get("B17001_002E")
            if total and below and total != "-666666666":
                try:
                    pct = int(below) / int(total) * 100
                    lines.append(f"\n  **Poverty rate: {pct:.1f}%**")
                except (ValueError, ZeroDivisionError):
                    pass

        if var_set == "internet_access":
            total = data.get("B28002_001E")
            no_internet = data.get("B28002_013E")
            if total and no_internet and total != "-666666666":
                try:
                    pct = int(no_internet) / int(total) * 100
                    lines.append(f"\n  **Households without internet: {pct:.1f}%**")
                except (ValueError, ZeroDivisionError):
                    pass

        lines.append(
            "\n---\n"
            "Use these figures in grant narratives to document community need. "
            "Always cite: 'U.S. Census Bureau, ACS 5-Year Estimates, 2022.'"
        )
        return "\n".join(lines)

    def _parse_geography(self) -> Optional[dict]:
        geo = self.geography.lower().strip()
        # ZIP code
        if geo.isdigit() and len(geo) == 5:
            return {"for": f"zip code tabulation area:{geo}"}
        # California statewide
        if geo in ("california", "ca"):
            return {"for": "state:06"}
        # LA County
        if "los angeles county" in geo or "la county" in geo:
            return {"for": "county:037", "in": "state:06"}
        # City of LA
        if "los angeles city" in geo or "city of los angeles" in geo:
            return {"for": "place:44000", "in": "state:06"}
        return None

    def _fallback_links(self, var_set: str) -> str:
        lines = [
            "⚠️ CENSUS_API_KEY not configured or geography not parsed. "
            "Add your free Census API key to .env to enable data retrieval.",
            "   → Register at: https://api.census.gov/data/key_signup.html\n",
            "**Manual lookup resources:**",
            f"  • Census Data Explorer: https://data.census.gov",
            f"  • American FactFinder: https://www.census.gov/acs/www/data/data-tables-and-tools/",
            f"  • LA County Dashboard: https://economicprofile.lacounty.gov",
            f"  • California Health & Human Services: https://data.chhs.ca.gov",
        ]
        if self.geography:
            geo_encoded = self.geography.replace(" ", "+")
            lines.append(
                f"  • Quick lookup: https://censusreporter.org/profiles/?q={geo_encoded}"
            )
        return "\n".join(lines)


if __name__ == "__main__":
    print("=== Test: LA County poverty data ===")
    tool = CensusData(
        geography="Los Angeles County",
        variable_set="poverty",
        program_context="LFLA grant narrative — documenting need in underserved communities",
    )
    print(tool.run())

    print("\n=== Test: Internet access (no key) ===")
    tool2 = CensusData(geography="Los Angeles city", variable_set="internet_access")
    print(tool2.run())
