import json
import os
from datetime import datetime
from typing import Optional

from agency_swarm.tools import BaseTool
from pydantic import Field

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
CONTACTS_FILE = os.path.join(DATA_DIR, "contacts.json")
TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")


def _load_contacts():
    if not os.path.exists(CONTACTS_FILE):
        return {}
    with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_tasks():
    if not os.path.exists(TASKS_FILE):
        return []
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


class MeetingPrep(BaseTool):
    """
    Given an upcoming meeting, compile a preparation brief for Ellah.

    Pulls background on known attendees from the CRM (contacts.json), surfaces
    any open tasks or action items related to the meeting's project or attendees,
    and drafts a suggested agenda based on the meeting purpose.

    Use this before any donor meeting, foundation conversation, board session,
    partner call, or consulting client check-in.
    """

    meeting_title: str = Field(
        ..., description="Title or description of the meeting (e.g., 'Q2 check-in with Weingart Foundation')"
    )
    meeting_date: Optional[str] = Field(
        None, description="Meeting date in YYYY-MM-DD format"
    )
    meeting_purpose: Optional[str] = Field(
        None,
        description="Brief description of the meeting's goal or agenda (e.g., 'discuss renewal grant proposal for FY27')",
    )
    attendees: Optional[str] = Field(
        None,
        description="Comma-separated list of attendee names (e.g., 'Sarah Kim, James Okafor')",
    )
    org_context: Optional[str] = Field(
        None,
        description="Which org this meeting is for: 'LFLA', 'Crestline', or 'Board'",
    )
    project: Optional[str] = Field(
        None, description="Project name to pull related open tasks"
    )

    def run(self):
        contacts = _load_contacts()
        tasks = _load_tasks()
        lines = []

        # Header
        date_str = self.meeting_date or "Date TBD"
        lines.append(f"# Meeting Prep: {self.meeting_title}")
        lines.append(f"Date: {date_str}" + (f"  |  Org: {self.org_context}" if self.org_context else ""))
        if self.meeting_purpose:
            lines.append(f"Purpose: {self.meeting_purpose}")
        lines.append("")

        # Attendee backgrounds from CRM
        if self.attendees:
            attendee_list = [a.strip() for a in self.attendees.split(",") if a.strip()]
            lines.append("## 👥 Attendee Background")
            for name in attendee_list:
                # Try exact match first, then case-insensitive
                record = contacts.get(name) or next(
                    (v for k, v in contacts.items() if k.lower() == name.lower()), None
                )
                if record:
                    lines.append(f"\n### {name}")
                    if record.get("title"):
                        lines.append(f"  Title: {record['title']}")
                    if record.get("org"):
                        lines.append(f"  Org: {record['org']}")
                    if record.get("relationship"):
                        lines.append(f"  Relationship: {record['relationship']}")
                    if record.get("last_touch"):
                        lines.append(f"  Last contact: {record['last_touch']}")
                    if record.get("notes"):
                        notes_preview = record["notes"][:400]
                        lines.append(f"  Notes: {notes_preview}" + ("…" if len(record.get("notes","")) > 400 else ""))
                    if record.get("open_items"):
                        lines.append(f"  Open items: {record['open_items']}")
                else:
                    lines.append(
                        f"\n### {name}\n  ⚠️ Not found in CRM. Add a contact record after the meeting."
                    )
            lines.append("")

        # Open tasks related to this meeting's project or attendees
        open_tasks = [t for t in tasks if t.get("status", "open") == "open"]
        relevant_tasks = []

        if self.project:
            relevant_tasks = [
                t for t in open_tasks
                if self.project.lower() in t.get("project", "").lower()
            ]

        if not relevant_tasks and self.attendees:
            attendee_list = [a.strip().lower() for a in self.attendees.split(",")]
            relevant_tasks = [
                t for t in open_tasks
                if any(a in t.get("notes", "").lower() or a in t.get("title", "").lower() for a in attendee_list)
            ]

        if relevant_tasks:
            lines.append("## ✅ Open Action Items")
            for t in relevant_tasks:
                due_str = f"  (due {t['due_date']})" if t.get("due_date") else ""
                lines.append(f"  • [{t['priority'].upper()}] {t['title']}{due_str}")
            lines.append("")

        # Draft agenda
        lines.append("## 📋 Suggested Agenda")
        if self.meeting_purpose:
            lines.append(f"  1. Welcome / context — {self.meeting_title}")
            lines.append(f"  2. {self.meeting_purpose}")
            if relevant_tasks:
                lines.append("  3. Review open action items")
            lines.append(f"  {'3' if not relevant_tasks else '4'}. Questions / next steps")
            lines.append(f"  {'4' if not relevant_tasks else '5'}. Confirm follow-ups and timeline")
        else:
            lines.append("  (Provide meeting_purpose to generate a tailored agenda.)")
        lines.append("")

        # Talking points placeholder
        lines.append("## 💬 Talking Points / Key Messages")
        lines.append("  (Populate with Development Agent or Communications Agent output before the meeting.)")
        lines.append("")

        lines.append("## 📝 Post-Meeting")
        lines.append("  Log notes and action items using the CRMUpdater tool after the meeting concludes.")

        return "\n".join(lines)


if __name__ == "__main__":
    # Seed a sample contact first
    DATA_DIR_TEST = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
    contacts_path = os.path.join(DATA_DIR_TEST, "contacts.json")
    os.makedirs(DATA_DIR_TEST, exist_ok=True)
    sample_contacts = {
        "Sarah Kim": {
            "title": "Program Officer",
            "org": "Weingart Foundation",
            "relationship": "Active grant relationship — LFLA literacy programming",
            "last_touch": "2026-03-15",
            "notes": "Interested in LAPL literacy outcomes data. Flagged potential for multi-year support.",
            "open_items": "Follow up on LOI submitted Feb 2026",
        }
    }
    with open(contacts_path, "w") as f:
        json.dump(sample_contacts, f, indent=2)

    print("=== Test: Meeting Prep ===")
    tool = MeetingPrep(
        meeting_title="Q2 Check-in with Weingart Foundation",
        meeting_date="2026-05-15",
        meeting_purpose="Review outcomes from FY26 grant and discuss FY27 renewal scope",
        attendees="Sarah Kim",
        org_context="LFLA",
        project="Grants",
    )
    print(tool.run())
