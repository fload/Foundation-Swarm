import os
import re
from typing import Optional
from urllib.parse import urlparse

import requests
from agency_swarm.tools import BaseTool
from dotenv import load_dotenv
from pydantic import Field

load_dotenv()

REQUEST_TIMEOUT = 20


class ParseRFP(BaseTool):
    """
    Extract structured data from a grant RFP, funding guidelines, or NOFA (Notice of
    Funding Availability) — either from a local file path (PDF or TXT) or a URL.

    Returns: deadline, award amounts, eligibility requirements, match requirements,
    key submission criteria, and a recommendation on whether LFLA or the specified
    Crestline client is a strong fit.

    Use this before committing to write a full proposal — it prevents wasted effort
    on ineligible opportunities and ensures hard deadlines are captured.
    """

    source: str = Field(
        ...,
        description=(
            "Path to a local PDF/TXT file (absolute path) or a URL pointing to "
            "the RFP or funder guidelines (e.g., 'https://funder.org/rfp.pdf')"
        ),
    )
    org_context: Optional[str] = Field(
        None,
        description="Which org is applying: 'LFLA' or the Crestline client name",
    )
    org_mission: Optional[str] = Field(
        None,
        description=(
            "Brief description of the applying org's mission, to use for fit assessment "
            "(e.g., 'Public library support, literacy, and equitable access to information in Los Angeles')"
        ),
    )

    def run(self):
        raw_text = self._fetch_text()
        if raw_text.startswith("Error:"):
            return raw_text

        extracted = self._extract_fields(raw_text)
        report = self._format_report(extracted, raw_text)
        return report

    def _fetch_text(self) -> str:
        """Fetch text from a URL or local file."""
        src = self.source.strip()

        # URL source
        if src.startswith("http://") or src.startswith("https://"):
            try:
                resp = requests.get(src, timeout=REQUEST_TIMEOUT, allow_redirects=True)
                resp.raise_for_status()
                content_type = resp.headers.get("Content-Type", "")

                if "pdf" in content_type or src.lower().endswith(".pdf"):
                    return self._extract_pdf_from_bytes(resp.content)
                else:
                    # Strip HTML tags for plain text extraction
                    text = resp.text
                    text = re.sub(r"<[^>]+>", " ", text)
                    text = re.sub(r"\s{3,}", "\n\n", text)
                    return text[:40000]

            except requests.exceptions.Timeout:
                return "Error: Request timed out fetching the RFP URL."
            except requests.exceptions.RequestException as e:
                return f"Error: Could not fetch URL: {str(e)}"

        # Local file source
        if not os.path.exists(src):
            return f"Error: File not found: {src}"

        if src.lower().endswith(".pdf"):
            try:
                with open(src, "rb") as f:
                    return self._extract_pdf_from_bytes(f.read())
            except Exception as e:
                return f"Error reading PDF: {str(e)}"

        try:
            with open(src, "r", encoding="utf-8", errors="replace") as f:
                return f.read(40000)
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def _extract_pdf_from_bytes(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF bytes using pdfplumber (preferred) or PyPDF2 fallback."""
        try:
            import io
            import pdfplumber
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                pages = []
                for page in pdf.pages[:40]:
                    text = page.extract_text()
                    if text:
                        pages.append(text)
            return "\n\n".join(pages)[:40000]
        except ImportError:
            pass

        try:
            import io
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            pages = []
            for page in reader.pages[:40]:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return "\n\n".join(pages)[:40000]
        except ImportError:
            return "Error: PDF parsing requires pdfplumber or PyPDF2. Run: pip install pdfplumber"
        except Exception as e:
            return f"Error parsing PDF: {str(e)}"

    def _extract_fields(self, text: str) -> dict:
        """Use regex heuristics to pull structured fields from RFP text."""
        result = {}

        # Deadline / due date
        deadline_patterns = [
            r"(?:deadline|due date|submission date|applications? due|proposals? due)[:\s]+([A-Z][a-z]+ \d{1,2},?\s*\d{4})",
            r"(?:deadline|due date|submission date)[:\s]+(\d{1,2}/\d{1,2}/\d{2,4})",
            r"(?:deadline|due date|submission date)[:\s]+(\d{4}-\d{2}-\d{2})",
        ]
        for pat in deadline_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                result["deadline"] = m.group(1).strip()
                break

        # Award amount
        award_patterns = [
            r"(?:award (?:amount|ceiling|floor|range)|grant (?:amount|size|award)|up to|maximum award)[:\s]*\$?([\d,]+(?:\.\d{2})?(?:\s*[–\-to]+\s*\$?[\d,]+(?:\.\d{2})?)?)",
            r"\$\s*([\d,]+(?:,\d{3})*(?:\.\d{2})?)\s*(?:per (?:year|grant|award|project))?",
        ]
        awards = []
        for pat in award_patterns:
            for m in re.finditer(pat, text[:5000], re.IGNORECASE):
                val = m.group(0).strip()
                if len(val) < 100:
                    awards.append(val)
        if awards:
            result["award_amounts"] = awards[:3]

        # Match / cost share requirement
        match_patterns = [
            r"(?:matching|cost.?share|match requirement)[:\s]+([^\n.]{10,120})",
            r"(?:requires?|must provide)\s+(?:a\s+)?(?:(\d+(?:\.\d+)?%?)\s+match)",
        ]
        for pat in match_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                result["match_requirement"] = m.group(1).strip()[:200]
                break

        # Eligibility
        elig_patterns = [
            r"(?:eligib(?:ility|le applicants?|le organizations?)|who (?:can|may) apply)[:\s]*([^\n]{20,400})",
        ]
        for pat in elig_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                result["eligibility"] = m.group(1).strip()[:400]
                break

        # Project period
        period_patterns = [
            r"(?:project period|performance period|grant period|award period)[:\s]+([^\n.]{5,80})",
            r"(?:(\d+)\s+(?:year|month)s?\s+(?:project|grant|award))",
        ]
        for pat in period_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                result["project_period"] = m.group(1).strip()[:100]
                break

        # Geographic restrictions
        geo_patterns = [
            r"(?:geographic(?:al)? (?:area|focus|eligibility|restriction)|service area|applicants? (?:must|located|based))[:\s]+([^\n.]{10,200})",
        ]
        for pat in geo_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                result["geographic_focus"] = m.group(1).strip()[:200]
                break

        return result

    def _format_report(self, extracted: dict, raw_text: str) -> str:
        org = self.org_context or "LFLA"
        lines = [f"# RFP Analysis — {os.path.basename(self.source)}\n"]

        lines.append("## Extracted Key Fields")

        deadline = extracted.get("deadline", "⚠️ NOT FOUND — search manually for submission deadline")
        lines.append(f"  **Deadline:** {deadline}")

        awards = extracted.get("award_amounts", [])
        if awards:
            lines.append(f"  **Award Amount(s):** {' | '.join(awards)}")
        else:
            lines.append("  **Award Amount:** ⚠️ Not clearly stated in document")

        if extracted.get("match_requirement"):
            lines.append(f"  **Match Requirement:** {extracted['match_requirement']}")
        else:
            lines.append("  **Match Requirement:** Not mentioned (likely not required)")

        if extracted.get("eligibility"):
            lines.append(f"  **Eligibility:** {extracted['eligibility']}")
        else:
            lines.append("  **Eligibility:** ⚠️ Review full document — not extracted automatically")

        if extracted.get("project_period"):
            lines.append(f"  **Project Period:** {extracted['project_period']}")

        if extracted.get("geographic_focus"):
            lines.append(f"  **Geographic Focus:** {extracted['geographic_focus']}")

        # Fit assessment
        lines.append(f"\n## Fit Assessment for {org}")
        org_mission = self.org_mission or (
            "Supporting the Los Angeles Public Library through fundraising, literacy programs, "
            "digital equity, and community access to information"
            if "LFLA" in org
            else "(org mission not provided — add org_mission for a tailored assessment)"
        )
        lines.append(f"  Applying org mission: {org_mission}")

        # Simple keyword-based fit signals
        fit_keywords = {
            "libraries": "Strong — opportunity explicitly mentions libraries",
            "literacy": "Strong — literacy is a core LFLA program area",
            "digital equity": "Strong — digital equity aligns with LFLA priorities",
            "arts": "Moderate — relevant to LFLA's ALOUD and exhibition programs",
            "education": "Moderate — aligns with student success and lifelong learning",
            "community": "Moderate — broad community benefit language is common",
            "Los Angeles": "Local — geographically aligned with LFLA",
        }
        signals = []
        text_lower = raw_text.lower()
        for kw, msg in fit_keywords.items():
            if kw.lower() in text_lower:
                signals.append(f"  ✓ '{kw}' — {msg}")
        if signals:
            lines.append("  Fit signals found:")
            lines.extend(signals[:5])
        else:
            lines.append(
                "  ⚠️ No strong fit keywords detected automatically. "
                "Review the full document for mission alignment."
            )

        # Deadline reminder
        if extracted.get("deadline"):
            lines.append(
                f"\n## ⚠️ Action Required\n"
                f"  **Add deadline to register:** '{deadline}' for {org}\n"
                f"  Use DeadlineTracker(action='add') with this deadline."
            )

        # Government grant flag
        govt_signals = ["IMLS", "NEA", "LSTA", "CDBG", "federal", "Federal Register", "NOFA", "CFDA"]
        if any(sig in raw_text for sig in govt_signals):
            lines.append(
                "\n## 🏛 Government Grant Flag\n"
                "  This appears to be a federal or government grant. "
                "Government grants have strict formatting requirements that override defaults. "
                "Always review the full guidelines before drafting — do not rely on extracted fields alone."
            )

        lines.append(
            "\n---\n"
            "**Next steps:**\n"
            "  • Log the deadline with DeadlineTracker\n"
            "  • Use the full extracted fields as the outline for your proposal draft\n"
            "  • Check eligibility carefully before committing writing time"
        )
        return "\n".join(lines)


if __name__ == "__main__":
    # Test with a publicly accessible grant document
    print("=== Test: Parse RFP from URL ===")
    tool = ParseRFP(
        source="https://www.imls.gov/sites/default/files/2024-02/fy24-libraries-museums-communities-nofo.pdf",
        org_context="LFLA",
        org_mission=(
            "Supporting the Los Angeles Public Library through fundraising, literacy programs, "
            "digital equity, and community access to information"
        ),
    )
    print(tool.run())
