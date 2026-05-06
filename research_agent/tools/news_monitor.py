import os
from typing import Optional

import requests
from agency_swarm.tools import BaseTool
from dotenv import load_dotenv
from pydantic import Field

load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
NEWS_API_URL = "https://newsapi.org/v2/everything"

# Curated RSS-style web queries for key focus areas (used when no API key)
FOCUS_AREAS = {
    "public_libraries": "public library Los Angeles LAPL funding advocacy",
    "la_philanthropy": "Los Angeles philanthropy foundation grants nonprofit",
    "literacy": "literacy education reading nonprofit Los Angeles",
    "education_equity": "education equity digital access community Los Angeles",
    "library_policy": "public library policy legislation funding federal state",
}

REQUEST_TIMEOUT = 15


class NewsMonitor(BaseTool):
    """
    Fetch a news digest from RSS feeds and NewsAPI filtered to Ellah's focus areas:
    public libraries, LA philanthropy, literacy, education equity, and library/education policy.

    When a NewsAPI key is configured (NEWS_API_KEY), returns full-text article summaries.
    Without a key, returns structured search queries and RSS links for manual review.

    Use for morning digests, advocacy background, and staying current on sector developments.
    """

    focus_area: Optional[str] = Field(
        None,
        description=(
            "Focus area to monitor: 'public_libraries', 'la_philanthropy', 'literacy', "
            "'education_equity', 'library_policy', or leave blank for all areas."
        ),
    )
    custom_query: Optional[str] = Field(
        None,
        description="Custom search query to supplement or replace focus area filters.",
    )
    max_articles: Optional[int] = Field(
        5, description="Maximum articles per focus area (default: 5)"
    )
    days_back: Optional[int] = Field(
        3, description="How many days back to search (default: 3)"
    )

    def run(self):
        if NEWS_API_KEY:
            return self._newsapi_fetch()
        else:
            return self._fallback_links()

    def _newsapi_fetch(self) -> str:
        from datetime import datetime, timedelta

        limit = min(self.max_articles or 5, 10)
        days = self.days_back or 3
        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        areas = {}
        if self.custom_query:
            areas["custom"] = self.custom_query
        elif self.focus_area and self.focus_area in FOCUS_AREAS:
            areas[self.focus_area] = FOCUS_AREAS[self.focus_area]
        else:
            areas = dict(list(FOCUS_AREAS.items())[:3])  # Top 3 to stay concise

        all_lines = [f"## News Digest — {datetime.now().strftime('%B %d, %Y')} (last {days} days)\n"]

        for area_key, query in areas.items():
            label = area_key.replace("_", " ").title()
            try:
                resp = requests.get(
                    NEWS_API_URL,
                    params={
                        "q": query,
                        "from": from_date,
                        "sortBy": "relevancy",
                        "pageSize": limit,
                        "apiKey": NEWS_API_KEY,
                        "language": "en",
                    },
                    timeout=REQUEST_TIMEOUT,
                )
                resp.raise_for_status()
                articles = resp.json().get("articles", [])
            except requests.exceptions.RequestException as e:
                all_lines.append(f"### {label}\n  Error: {str(e)}\n")
                continue

            if not articles:
                all_lines.append(f"### {label}\n  No new articles found.\n")
                continue

            all_lines.append(f"### {label}")
            for art in articles[:limit]:
                title = art.get("title", "Untitled")
                source = art.get("source", {}).get("name", "")
                published = art.get("publishedAt", "")[:10]
                url = art.get("url", "")
                description = art.get("description") or ""
                if len(description) > 200:
                    description = description[:197] + "…"
                all_lines.append(
                    f"  • **{title}**\n"
                    f"    {source} | {published}\n"
                    + (f"    {description}\n" if description else "")
                    + f"    {url}"
                )
            all_lines.append("")

        return "\n".join(all_lines)

    def _fallback_links(self) -> str:
        from datetime import datetime
        lines = [
            f"## News Monitor — {datetime.now().strftime('%B %d, %Y')}",
            "⚠️  NEWS_API_KEY not configured. Add your NewsAPI key to .env for article summaries.",
            "   → Get a free key at https://newsapi.org\n",
            "**Recommended daily reading sources:**\n",
        ]

        area_filter = self.focus_area or "all"
        sources = {
            "Public Libraries": [
                "https://americanlibrariesmagazine.org",
                "https://www.ala.org/news/",
                "https://www.libraryjournal.com",
                "https://lapl.org/about-lapl/news",
            ],
            "LA Philanthropy": [
                "https://www.philanthropy.com",
                "https://www.nonprofitquarterly.org",
                "https://losangelestimes.com/topic/nonprofits",
                "https://www.calpnonprofits.org/news",
            ],
            "Literacy / Education Equity": [
                "https://www.literacyworldwide.org/blog",
                "https://www.edweek.org",
                "https://laschoolreport.com",
            ],
            "Policy / Advocacy": [
                "https://ala.org/advocacy",
                "https://leginfo.legislature.ca.gov",
                "https://lacity.gov/government/council-committees",
            ],
        }

        for category, urls in sources.items():
            lines.append(f"**{category}:**")
            for url in urls:
                lines.append(f"  • {url}")
            lines.append("")

        if self.custom_query:
            lines.append(f"**Google News search for your query:**")
            lines.append(
                f"  https://news.google.com/search?q={self.custom_query.replace(' ', '+')}"
            )

        return "\n".join(lines)


if __name__ == "__main__":
    print("=== Test: News Monitor — Public Libraries ===")
    tool = NewsMonitor(focus_area="public_libraries", days_back=7, max_articles=3)
    print(tool.run())
