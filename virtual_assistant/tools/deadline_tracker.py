import json
import os
from datetime import datetime, timedelta
from typing import Optional

from agency_swarm.tools import BaseTool
from pydantic import Field

# Shared deadline register lives at project root data/deadlines.json
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


class DeadlineTracker(BaseTool):
    """
    Read and write the unified deadline register across LFLA and Crestline Collective.
    Tracks grant submissions, reporting deadlines, board meetings, and governance filing dates.

    Proactively flags items within 14 days and within 48 hours — use action='briefing'
    to generate a full formatted deadline briefing.

    Actions:
    - 'add'      — add a new deadline entry
    - 'list'     — list all deadlines (optionally filtered by org)
    - 'upcoming' — show deadlines in the next N days (default 14)
    - 'remove'   — remove a deadline by its ID
    - 'briefing' — generate a formatted briefing with 48-hour and 14-day flags
    """

    action: str = Field(
        ...,
        description="Action to perform: 'add', 'list', 'upcoming', 'remove', or 'briefing'",
    )
    title: Optional[str] = Field(
        None, description="Name of the deadline (required for 'add')"
    )
    deadline_date: Optional[str] = Field(
        None, description="Deadline date in YYYY-MM-DD format (required for 'add')"
    )
    org: Optional[str] = Field(
        None,
        description="Organization context: 'LFLA', 'Crestline', or 'Board' (required for 'add')",
    )
    deadline_type: Optional[str] = Field(
        None,
        description=(
            "Type of deadline: 'grant_submission', 'grant_report', 'board_meeting', "
            "'governance', 'campaign', 'event', or 'other'"
        ),
    )
    notes: Optional[str] = Field(
        None, description="Additional notes about this deadline"
    )
    deadline_id: Optional[str] = Field(
        None, description="ID of deadline to remove (required for 'remove')"
    )
    days_ahead: Optional[int] = Field(
        14, description="Days ahead to include for 'upcoming' action (default 14)"
    )
    filter_org: Optional[str] = Field(
        None,
        description="Filter by org for 'list' action: 'LFLA', 'Crestline', or 'Board'",
    )

    def run(self):
        now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if self.action == "add":
            if not self.title or not self.deadline_date or not self.org:
                return "Error: 'add' requires title, deadline_date, and org."
            try:
                datetime.strptime(self.deadline_date, "%Y-%m-%d")
            except ValueError:
                return "Error: deadline_date must be in YYYY-MM-DD format."

            deadlines = _load()
            new_id = f"dl_{int(datetime.now().timestamp())}"
            entry = {
                "id": new_id,
                "title": self.title,
                "date": self.deadline_date,
                "org": self.org,
                "type": self.deadline_type or "other",
                "notes": self.notes or "",
                "added": datetime.now().strftime("%Y-%m-%d"),
            }
            deadlines.append(entry)
            _save(deadlines)
            return (
                f"✓ Deadline added (ID: {new_id})\n"
                f"  {self.title}\n"
                f"  Due: {self.deadline_date}  Org: {self.org}  Type: {self.deadline_type or 'other'}"
            )

        elif self.action in ("list", "upcoming"):
            deadlines = _load()
            if not deadlines:
                return "No deadlines in the register."

            if self.filter_org:
                deadlines = [d for d in deadlines if d.get("org") == self.filter_org]

            if self.action == "upcoming":
                cutoff = now + timedelta(days=self.days_ahead or 14)
                deadlines = [
                    d
                    for d in deadlines
                    if now
                    <= datetime.strptime(d["date"], "%Y-%m-%d")
                    <= cutoff
                ]

            deadlines.sort(key=lambda d: d["date"])

            if not deadlines:
                return "No deadlines found matching the filter."

            lines = ["Deadline Register\n" + "=" * 60]
            for d in deadlines:
                dl_dt = datetime.strptime(d["date"], "%Y-%m-%d")
                days_out = (dl_dt - now).days
                urgency = ""
                if days_out < 0:
                    urgency = " ⚠️ PAST DUE"
                elif days_out <= 2:
                    urgency = " 🚨 URGENT"
                elif days_out <= 14:
                    urgency = " 📅 SOON"
                lines.append(
                    f"[{d.get('org','?')}] {d['title']}\n"
                    f"  Due: {d['date']} (in {days_out} days){urgency}\n"
                    f"  Type: {d.get('type','other')}  ID: {d['id']}"
                    + (f"\n  Notes: {d['notes']}" if d.get("notes") else "")
                )
            return "\n\n".join(lines)

        elif self.action == "briefing":
            deadlines = _load()
            now_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_14 = now_dt + timedelta(days=14)

            urgent, soon, later = [], [], []
            for d in deadlines:
                dl_dt = datetime.strptime(d["date"], "%Y-%m-%d")
                days_out = (dl_dt - now_dt).days
                if days_out < 0:
                    urgent.append((d, days_out))
                elif days_out <= 2:
                    urgent.append((d, days_out))
                elif dl_dt <= cutoff_14:
                    soon.append((d, days_out))
                else:
                    later.append((d, days_out))

            urgent.sort(key=lambda x: x[1])
            soon.sort(key=lambda x: x[1])
            later.sort(key=lambda x: x[1])

            lines = [f"## 📋 Deadline Briefing — {datetime.now().strftime('%B %d, %Y')}\n"]

            if not deadlines:
                lines.append("No deadlines in the register.")
                return "\n".join(lines)

            if urgent:
                lines.append("### 🚨 Requires Immediate Attention:")
                for d, days in urgent:
                    if days < 0:
                        day_str = f"{abs(days)} day(s) OVERDUE"
                    elif days == 0:
                        day_str = "TODAY"
                    else:
                        day_str = f"in {days} day{'s' if days != 1 else ''}"
                    lines.append(f"  • [{d['org']}] **{d['title']}** — {d['date']} ({day_str})")
                    if d.get("notes"):
                        lines.append(f"    → {d['notes']}")

            if soon:
                lines.append("\n### 📅 Coming Up (Next 14 Days):")
                for d, days in soon:
                    lines.append(
                        f"  • [{d['org']}] {d['title']} — {d['date']} "
                        f"(in {days} days) [{d.get('type', 'other')}]"
                    )
                    if d.get("notes"):
                        lines.append(f"    → {d['notes']}")

            if later:
                lines.append(f"\n### 🗓 Further Out ({len(later)} items):")
                for d, days in later[:5]:
                    lines.append(f"  • [{d['org']}] {d['title']} — {d['date']} (in {days} days)")
                if len(later) > 5:
                    lines.append(f"  … and {len(later) - 5} more.")

            return "\n".join(lines)

        elif self.action == "remove":
            if not self.deadline_id:
                return "Error: 'remove' requires a deadline_id."
            deadlines = _load()
            original = len(deadlines)
            deadlines = [d for d in deadlines if d["id"] != self.deadline_id]
            if len(deadlines) == original:
                return f"Error: No deadline found with ID '{self.deadline_id}'."
            _save(deadlines)
            return f"✓ Deadline '{self.deadline_id}' removed."

        else:
            return f"Error: Unknown action '{self.action}'. Use 'add', 'list', 'upcoming', 'remove', or 'briefing'."


if __name__ == "__main__":
    print("=== Test: Add deadlines ===")
    t1 = DeadlineTracker(
        action="add",
        title="NEA Our Town Grant Application",
        deadline_date="2026-06-15",
        org="LFLA",
        deadline_type="grant_submission",
        notes="Requires org chart and board list",
    )
    print(t1.run())

    t2 = DeadlineTracker(
        action="add",
        title="Q2 Donor Report — Ahmanson Foundation",
        deadline_date="2026-05-08",
        org="LFLA",
        deadline_type="grant_report",
    )
    print(t2.run())

    print("\n=== Test: Briefing ===")
    t3 = DeadlineTracker(action="briefing")
    print(t3.run())

    print("\n=== Test: Upcoming (30 days) ===")
    t4 = DeadlineTracker(action="upcoming", days_ahead=30)
    print(t4.run())
