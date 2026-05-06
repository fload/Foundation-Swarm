import json
import os
from typing import Optional

from agency_swarm.tools import BaseTool
from pydantic import Field

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
CONTACTS_FILE = os.path.join(DATA_DIR, "contacts.json")


class ContactContext(BaseTool):
    """
    Pull relationship notes and communication history for a named contact to personalize
    a draft communication.

    Use this before drafting any outreach to a donor, foundation officer, partner,
    board member, or colleague. Returns relationship context that should inform the
    tone, opening, and specific references in the draft.

    Reads from data/contacts.json — the shared CRM maintained by the Virtual Assistant.
    """

    contact_name: str = Field(
        ...,
        description="Full name of the contact to look up (e.g., 'Sarah Kim')",
    )
    org_context: Optional[str] = Field(
        None,
        description=(
            "Filter by org context: 'LFLA' or 'Crestline'. If not specified, "
            "returns all records for this contact."
        ),
    )

    def run(self):
        if not os.path.exists(CONTACTS_FILE):
            return (
                f"No contact record found for '{self.contact_name}'.\n"
                "Add a contact record using the Virtual Assistant's CRMUpdater tool "
                "(action='upsert') before drafting this communication."
            )

        with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
            contacts = json.load(f)

        # Exact match first, then case-insensitive
        record = contacts.get(self.contact_name) or next(
            (v for k, v in contacts.items() if k.lower() == self.contact_name.lower()),
            None,
        )

        if not record:
            return (
                f"No contact record found for '{self.contact_name}'.\n"
                "Consider adding one via the Virtual Assistant before drafting.\n"
                "Proceed with drafting a warm but general-purpose message."
            )

        # Filter by org context if specified
        if self.org_context and record.get("org_context") and record["org_context"] != self.org_context:
            return (
                f"⚠️ Contact '{self.contact_name}' is recorded under org context "
                f"'{record.get('org_context')}', not '{self.org_context}'.\n"
                "Confirm which org relationship applies before drafting."
            )

        lines = [f"## Contact Context: {self.contact_name}\n"]
        lines.append("*Use this to personalize your draft — reference specific details naturally.*\n")

        fields = [
            ("title", "Title"),
            ("org", "Organization"),
            ("org_context", "Relationship Org"),
            ("relationship", "Relationship"),
            ("last_touch", "Last Contact"),
            ("email", "Email"),
        ]
        for key, label in fields:
            if record.get(key):
                lines.append(f"  **{label}:** {record[key]}")

        if record.get("open_items"):
            lines.append(f"\n  **Open Items / Follow-ups:** {record['open_items']}")

        if record.get("notes"):
            lines.append(f"\n  **Background Notes:** {record['notes'][:600]}")

        history = record.get("history", [])
        if history:
            lines.append("\n  **Recent Interactions (last 3):**")
            for entry in history[-3:]:
                ctx = f" [{entry.get('org_context', '')}]" if entry.get("org_context") else ""
                lines.append(f"    {entry['date']}{ctx}: {entry['note'][:200]}")

        lines.append(
            "\n---\n"
            "**Drafting guidance:**\n"
            f"  • Reference the relationship context above to open naturally\n"
            f"  • If there are open items, address or acknowledge them\n"
            f"  • Confirm org context ({record.get('org_context', '?')}) before adding signature"
        )

        return "\n".join(lines)


if __name__ == "__main__":
    # Seed a test contact
    os.makedirs(DATA_DIR, exist_ok=True)
    sample = {
        "Sarah Kim": {
            "title": "Program Officer",
            "org": "Weingart Foundation",
            "org_context": "LFLA",
            "relationship": "Active grant relationship — LFLA literacy programming",
            "last_touch": "2026-03-15",
            "notes": "Interested in LAPL literacy outcomes. Positive on multi-year support.",
            "open_items": "Follow up on LOI submitted Feb 2026",
            "history": [
                {
                    "date": "2026-03-15",
                    "org_context": "LFLA",
                    "note": "Met at Philanthropy Forum. Agreed to send one-pager on student success programs.",
                }
            ],
        }
    }
    with open(CONTACTS_FILE, "w") as f:
        json.dump(sample, f, indent=2)

    print("=== Test: Get contact context ===")
    tool = ContactContext(contact_name="Sarah Kim", org_context="LFLA")
    print(tool.run())

    print("\n=== Test: Unknown contact ===")
    tool2 = ContactContext(contact_name="James Okafor")
    print(tool2.run())
