import json
import os
from datetime import datetime, timedelta
from typing import Optional

from agency_swarm.tools import BaseTool
from pydantic import Field

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
CONTACTS_FILE = os.path.join(DATA_DIR, "contacts.json")


def _load():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(CONTACTS_FILE):
        return {}
    with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(contacts: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONTACTS_FILE, "w", encoding="utf-8") as f:
        json.dump(contacts, f, indent=2)


class CRMUpdater(BaseTool):
    """
    Manage relationship notes and contact records for donors, funders, partners,
    board members, and consulting clients. Logs interactions and flags contacts
    who haven't been touched in 90+ days.

    Contact records are stored in data/contacts.json. Each contact is keyed by
    name and tagged with an org context (LFLA or Crestline) to prevent
    conflicts of interest from going unnoticed.

    Actions:
    - 'add_note'        — log a new interaction note for a contact
    - 'upsert'          — create or update a contact record
    - 'get'             — retrieve a contact record by name
    - 'list'            — list all contacts (optionally filtered by org or relationship type)
    - 'flag_neglected'  — list contacts not touched in 90+ days
    - 'remove'          — delete a contact record
    """

    action: str = Field(
        ...,
        description="Action: 'add_note', 'upsert', 'get', 'list', 'flag_neglected', or 'remove'",
    )
    contact_name: Optional[str] = Field(
        None, description="Full name of the contact (required for most actions)"
    )
    org_context: Optional[str] = Field(
        None,
        description="Which org this relationship belongs to: 'LFLA', 'Crestline', or 'Board'",
    )
    title: Optional[str] = Field(None, description="Contact's title/role")
    org_affiliation: Optional[str] = Field(
        None, description="Contact's organization or employer"
    )
    relationship: Optional[str] = Field(
        None,
        description="Brief description of the relationship (e.g., 'Major donor — LFLA', 'Foundation program officer')",
    )
    note: Optional[str] = Field(
        None,
        description="Interaction note to log (e.g., 'Met at LFLA board meeting. Expressed interest in ALOUD sponsorship.')",
    )
    open_items: Optional[str] = Field(
        None, description="Open action items for this contact"
    )
    contact_email: Optional[str] = Field(None, description="Contact's email address")
    filter_org: Optional[str] = Field(
        None, description="Filter by org context for 'list': 'LFLA', 'Crestline', or 'Board'"
    )
    neglect_days: Optional[int] = Field(
        90, description="Days without contact to consider neglected (default: 90)"
    )

    def run(self):
        if self.action == "upsert":
            if not self.contact_name:
                return "Error: 'upsert' requires contact_name."
            contacts = _load()
            existing = contacts.get(self.contact_name, {})
            updated = {
                **existing,
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
            }
            if self.org_context:
                updated["org_context"] = self.org_context
            if self.title:
                updated["title"] = self.title
            if self.org_affiliation:
                updated["org"] = self.org_affiliation
            if self.relationship:
                updated["relationship"] = self.relationship
            if self.open_items is not None:
                updated["open_items"] = self.open_items
            if self.contact_email:
                updated["email"] = self.contact_email
            contacts[self.contact_name] = updated
            _save(contacts)
            verb = "Updated" if self.contact_name in contacts else "Created"
            return f"✓ {verb} contact record: {self.contact_name}"

        elif self.action == "add_note":
            if not self.contact_name:
                return "Error: 'add_note' requires contact_name."
            if not self.note:
                return "Error: 'add_note' requires a note."
            contacts = _load()
            if self.contact_name not in contacts:
                contacts[self.contact_name] = {}
            record = contacts[self.contact_name]
            history = record.get("history", [])
            history.append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "note": self.note,
                "org_context": self.org_context or record.get("org_context", ""),
            })
            record["history"] = history
            record["last_touch"] = datetime.now().strftime("%Y-%m-%d")
            if self.open_items is not None:
                record["open_items"] = self.open_items
            if self.org_context:
                record["org_context"] = self.org_context
            contacts[self.contact_name] = record
            _save(contacts)
            return (
                f"✓ Note logged for {self.contact_name} ({datetime.now().strftime('%Y-%m-%d')})\n"
                f"  \"{self.note[:120]}{'…' if len(self.note) > 120 else ''}\""
            )

        elif self.action == "get":
            if not self.contact_name:
                return "Error: 'get' requires contact_name."
            contacts = _load()
            record = contacts.get(self.contact_name) or next(
                (v for k, v in contacts.items() if k.lower() == self.contact_name.lower()),
                None,
            )
            if not record:
                return f"No contact record found for '{self.contact_name}'."
            lines = [f"## Contact: {self.contact_name}"]
            for key in ["title", "org", "org_context", "relationship", "email", "last_touch", "last_updated"]:
                if record.get(key):
                    lines.append(f"  {key.replace('_',' ').title()}: {record[key]}")
            if record.get("open_items"):
                lines.append(f"  Open Items: {record['open_items']}")
            if record.get("notes"):
                lines.append(f"  Notes: {record['notes']}")
            if record.get("history"):
                lines.append("\n  Interaction History:")
                for entry in record["history"][-5:]:
                    ctx = f" [{entry.get('org_context','')}]" if entry.get("org_context") else ""
                    lines.append(f"    {entry['date']}{ctx}: {entry['note']}")
            return "\n".join(lines)

        elif self.action == "list":
            contacts = _load()
            if not contacts:
                return "No contacts in CRM."
            items = list(contacts.items())
            if self.filter_org:
                items = [(k, v) for k, v in items if v.get("org_context") == self.filter_org]
            if not items:
                return f"No contacts found for org '{self.filter_org}'."
            lines = [f"Contacts ({len(items)})\n" + "=" * 50]
            for name, r in sorted(items):
                last = r.get("last_touch", "never")
                org_ctx = r.get("org_context", "")
                role = r.get("title", "")
                affil = r.get("org", "")
                detail = " — ".join(filter(None, [role, affil]))
                lines.append(f"  {name} [{org_ctx}]{(' — ' + detail) if detail else ''}  (last: {last})")
            return "\n".join(lines)

        elif self.action == "flag_neglected":
            contacts = _load()
            threshold = self.neglect_days or 90
            cutoff = datetime.now() - timedelta(days=threshold)
            neglected = []
            for name, r in contacts.items():
                last_touch = r.get("last_touch")
                if not last_touch:
                    neglected.append((name, r, None))
                else:
                    try:
                        lt_dt = datetime.strptime(last_touch, "%Y-%m-%d")
                        if lt_dt < cutoff:
                            days_since = (datetime.now() - lt_dt).days
                            neglected.append((name, r, days_since))
                    except ValueError:
                        neglected.append((name, r, None))

            if not neglected:
                return f"✓ No neglected contacts (threshold: {threshold} days)."

            neglected.sort(key=lambda x: (x[2] is None, -(x[2] or 0)))
            lines = [f"## ⚠️ Neglected Contacts ({len(neglected)} contacts not touched in {threshold}+ days)\n"]
            for name, r, days in neglected:
                org_ctx = r.get("org_context", "?")
                rel = r.get("relationship", "")
                last = r.get("last_touch", "never")
                days_str = f"{days} days ago" if days else "never contacted"
                lines.append(f"  • [{org_ctx}] {name} — last: {last} ({days_str})")
                if rel:
                    lines.append(f"    Relationship: {rel}")
            return "\n".join(lines)

        elif self.action == "remove":
            if not self.contact_name:
                return "Error: 'remove' requires contact_name."
            contacts = _load()
            if self.contact_name not in contacts:
                return f"No contact found for '{self.contact_name}'."
            del contacts[self.contact_name]
            _save(contacts)
            return f"✓ Contact '{self.contact_name}' removed from CRM."

        else:
            return f"Error: Unknown action '{self.action}'."


if __name__ == "__main__":
    print("=== Test: Upsert contact ===")
    t1 = CRMUpdater(
        action="upsert",
        contact_name="Maria Gonzalez",
        org_context="LFLA",
        title="Vice President, Programs",
        org_affiliation="Annenberg Foundation",
        relationship="Warm prospect — introduced by board member David Park",
    )
    print(t1.run())

    print("\n=== Test: Add note ===")
    t2 = CRMUpdater(
        action="add_note",
        contact_name="Maria Gonzalez",
        org_context="LFLA",
        note="Met at LA Philanthropy Forum. She expressed strong interest in LAPL student success programs. Agreed to send one-pager.",
        open_items="Send LAPL student success one-pager by May 15",
    )
    print(t2.run())

    print("\n=== Test: Get contact ===")
    t3 = CRMUpdater(action="get", contact_name="Maria Gonzalez")
    print(t3.run())

    print("\n=== Test: Flag neglected ===")
    t4 = CRMUpdater(action="flag_neglected", neglect_days=30)
    print(t4.run())
