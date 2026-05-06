import json
import os
from datetime import datetime
from typing import Optional

from agency_swarm.tools import BaseTool
from dotenv import load_dotenv
from pydantic import Field

load_dotenv()

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
DEADLINES_FILE = os.path.join(DATA_DIR, "deadlines.json")


def _load():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(DEADLINES_FILE):
        return []
    with open(DEADLINES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(deadlines: list):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DEADLINES_FILE, "w", encoding="utf-8") as f:
        json.dump(deadlines, f, indent=2)


class DeadlineLog(BaseTool):
    """
    Log a new grant deadline to the unified deadline register (data/deadlines.json),
    which is shared with the Virtual Assistant for proactive reminders.

    Use this immediately after identifying a grant opportunity, parsing an RFP,
    or receiving confirmation of a reporting due date. The Virtual Assistant will
    automatically surface 14-day and 48-hour warnings.

    This tool writes directly to the shared deadline register — it is the
    Development Agent's write interface to the system managed by DeadlineTracker.
    """

    title: str = Field(
        ...,
        description="Name of the grant or deadline (e.g., 'NEA Our Town Application — LFLA')",
    )
    deadline_date: str = Field(
        ...,
        description="Deadline date in YYYY-MM-DD format",
    )
    org: str = Field(
        ...,
        description="Organization submitting: 'LFLA' or the Crestline client name",
    )
    funder: Optional[str] = Field(
        None,
        description="Name of the funder or grant program (e.g., 'National Endowment for the Arts')",
    )
    deadline_type: Optional[str] = Field(
        "grant_submission",
        description=(
            "Type: 'grant_submission' (default), 'grant_report', 'loi', "
            "'letter_of_intent', 'concept_paper', or 'other'"
        ),
    )
    award_amount: Optional[str] = Field(
        None,
        description="Award amount or range (e.g., '$50,000', 'up to $250,000')",
    )
    notes: Optional[str] = Field(
        None,
        description="Additional notes (e.g., 'Requires board resolution', 'Prior relationship required')",
    )
    internal_lead: Optional[str] = Field(
        None,
        description="Who at LFLA or Crestline is leading this application",
    )

    def run(self):
        # Validate date
        try:
            datetime.strptime(self.deadline_date, "%Y-%m-%d")
        except ValueError:
            return "Error: deadline_date must be in YYYY-MM-DD format (e.g., '2026-06-15')."

        # Check for conflicts — if a Crestline client and LFLA are competing for the same funder
        conflict_warning = self._check_funder_conflict()

        deadlines = _load()

        # Check for duplicate
        for d in deadlines:
            if (
                d.get("title", "").lower() == self.title.lower()
                and d.get("date") == self.deadline_date
            ):
                return (
                    f"⚠️ A deadline with this title and date already exists (ID: {d['id']}).\n"
                    f"  Title: {d['title']}\n"
                    f"  Date: {d['date']}  Org: {d['org']}"
                )

        new_id = f"dl_{int(datetime.now().timestamp())}"
        notes_parts = []
        if self.funder:
            notes_parts.append(f"Funder: {self.funder}")
        if self.award_amount:
            notes_parts.append(f"Award: {self.award_amount}")
        if self.internal_lead:
            notes_parts.append(f"Lead: {self.internal_lead}")
        if self.notes:
            notes_parts.append(self.notes)

        entry = {
            "id": new_id,
            "title": self.title,
            "date": self.deadline_date,
            "org": self.org,
            "type": self.deadline_type or "grant_submission",
            "notes": " | ".join(notes_parts),
            "added": datetime.now().strftime("%Y-%m-%d"),
            "funder": self.funder or "",
        }
        deadlines.append(entry)
        _save(deadlines)

        # Calculate days until deadline
        deadline_dt = datetime.strptime(self.deadline_date, "%Y-%m-%d")
        days_out = (deadline_dt - datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)).days

        urgency = ""
        if days_out < 0:
            urgency = "⚠️ PAST DUE — verify this date"
        elif days_out <= 2:
            urgency = "🚨 URGENT — due in 48 hours"
        elif days_out <= 14:
            urgency = "📅 Due soon — 14-day window"
        else:
            urgency = f"🗓 {days_out} days until deadline"

        result = (
            f"✓ Deadline logged (ID: {new_id})\n"
            f"  {self.title}\n"
            f"  Due: {self.deadline_date}  Org: {self.org}  {urgency}\n"
            f"  Type: {self.deadline_type or 'grant_submission'}"
        )
        if self.funder:
            result += f"\n  Funder: {self.funder}"
        if self.award_amount:
            result += f"\n  Award: {self.award_amount}"
        if entry["notes"]:
            result += f"\n  Notes: {entry['notes']}"

        result += (
            "\n\n📋 Virtual Assistant will surface 14-day and 48-hour reminders automatically."
        )

        if conflict_warning:
            result += f"\n\n{conflict_warning}"

        return result

    def _check_funder_conflict(self) -> str:
        """Check if the same funder appears in both LFLA and Crestline deadline records."""
        if not self.funder:
            return ""
        deadlines = _load()
        conflicts = [
            d for d in deadlines
            if self.funder.lower() in d.get("funder", "").lower()
            and d.get("org") != self.org
        ]
        if conflicts:
            conflict_orgs = list({d["org"] for d in conflicts})
            return (
                f"⚠️ CONFLICT DETECTED: Funder '{self.funder}' appears in deadlines for "
                f"{', '.join(conflict_orgs)} and is now being added for {self.org}.\n"
                "  If LFLA and a Crestline client are competing for the same funder, "
                "pause and get Ellah's guidance before proceeding."
            )
        return ""


if __name__ == "__main__":
    print("=== Test: Log grant deadline ===")
    tool = DeadlineLog(
        title="NEA Our Town — LFLA Community Spaces",
        deadline_date="2026-06-15",
        org="LFLA",
        funder="National Endowment for the Arts",
        deadline_type="grant_submission",
        award_amount="up to $150,000",
        notes="Requires org chart, board list, and LAPL partnership letter",
        internal_lead="Ellah Ronen",
    )
    print(tool.run())

    print("\n=== Test: Log grant report deadline ===")
    tool2 = DeadlineLog(
        title="Ahmanson Foundation — FY26 Final Report",
        deadline_date="2026-05-30",
        org="LFLA",
        funder="Ahmanson Foundation",
        deadline_type="grant_report",
        notes="Requires narrative and budget actuals",
    )
    print(tool2.run())
