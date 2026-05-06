import json
import os
from datetime import datetime, timedelta
from typing import Optional

from agency_swarm.tools import BaseTool
from pydantic import Field

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _load():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(TASKS_FILE):
        return []
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(tasks: list):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2)


class TaskManager(BaseTool):
    """
    Maintain a prioritized task list for LFLA and Crestline Collective work.
    Surfaces overdue and upcoming items in briefings.

    Actions:
    - 'add'      — add a new task
    - 'list'     — list tasks (optionally filtered by project, org, or status)
    - 'complete' — mark a task as complete
    - 'remove'   — delete a task by ID
    - 'briefing' — generate a formatted task briefing showing overdue and high-priority items
    """

    action: str = Field(
        ...,
        description="Action: 'add', 'list', 'complete', 'remove', or 'briefing'",
    )
    title: Optional[str] = Field(None, description="Task title (required for 'add')")
    org: Optional[str] = Field(
        None,
        description="Organization: 'LFLA', 'Crestline', or 'Board' (required for 'add')",
    )
    project: Optional[str] = Field(
        None, description="Project name this task belongs to"
    )
    priority: Optional[str] = Field(
        "medium",
        description="Priority: 'high', 'medium', or 'low' (default: 'medium')",
    )
    due_date: Optional[str] = Field(
        None, description="Due date in YYYY-MM-DD format (optional)"
    )
    notes: Optional[str] = Field(None, description="Additional context for the task")
    task_id: Optional[str] = Field(
        None, description="Task ID (required for 'complete' and 'remove')"
    )
    filter_org: Optional[str] = Field(
        None, description="Filter by org for 'list': 'LFLA', 'Crestline', or 'Board'"
    )
    filter_status: Optional[str] = Field(
        None,
        description="Filter by status for 'list': 'open' or 'complete' (default: 'open')",
    )
    filter_project: Optional[str] = Field(
        None, description="Filter by project name for 'list'"
    )

    def run(self):
        now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if self.action == "add":
            if not self.title or not self.org:
                return "Error: 'add' requires title and org."
            tasks = _load()
            new_id = f"task_{int(datetime.now().timestamp())}"
            entry = {
                "id": new_id,
                "title": self.title,
                "org": self.org,
                "project": self.project or "",
                "priority": self.priority or "medium",
                "due_date": self.due_date or "",
                "notes": self.notes or "",
                "status": "open",
                "added": datetime.now().strftime("%Y-%m-%d"),
                "completed": "",
            }
            tasks.append(entry)
            _save(tasks)
            due_str = f"  Due: {self.due_date}" if self.due_date else ""
            return (
                f"✓ Task added (ID: {new_id})\n"
                f"  {self.title}\n"
                f"  Org: {self.org}  Priority: {self.priority or 'medium'}"
                + due_str
            )

        elif self.action == "list":
            tasks = _load()
            status_filter = self.filter_status or "open"
            tasks = [t for t in tasks if t.get("status", "open") == status_filter]
            if self.filter_org:
                tasks = [t for t in tasks if t.get("org") == self.filter_org]
            if self.filter_project:
                tasks = [
                    t
                    for t in tasks
                    if self.filter_project.lower() in t.get("project", "").lower()
                ]
            if not tasks:
                return f"No {status_filter} tasks found."
            tasks.sort(
                key=lambda t: (
                    PRIORITY_ORDER.get(t.get("priority", "medium"), 1),
                    t.get("due_date") or "9999-99-99",
                )
            )
            lines = [f"Tasks ({status_filter})\n" + "=" * 60]
            for t in tasks:
                due_str = ""
                if t.get("due_date"):
                    due_dt = datetime.strptime(t["due_date"], "%Y-%m-%d")
                    days = (due_dt - now).days
                    if days < 0:
                        due_str = f"  ⚠️ OVERDUE by {abs(days)} days"
                    elif days <= 3:
                        due_str = f"  🚨 Due in {days} days"
                    else:
                        due_str = f"  Due: {t['due_date']}"
                proj_str = f" [{t['project']}]" if t.get("project") else ""
                lines.append(
                    f"[{t.get('priority','med').upper()}] [{t['org']}]{proj_str} {t['title']}"
                    + due_str
                    + f"\n  ID: {t['id']}"
                    + (f"\n  Notes: {t['notes']}" if t.get("notes") else "")
                )
            return "\n\n".join(lines)

        elif self.action == "complete":
            if not self.task_id:
                return "Error: 'complete' requires a task_id."
            tasks = _load()
            for t in tasks:
                if t["id"] == self.task_id:
                    t["status"] = "complete"
                    t["completed"] = datetime.now().strftime("%Y-%m-%d")
                    _save(tasks)
                    return f"✓ Task '{t['title']}' marked complete."
            return f"Error: No task found with ID '{self.task_id}'."

        elif self.action == "remove":
            if not self.task_id:
                return "Error: 'remove' requires a task_id."
            tasks = _load()
            original = len(tasks)
            tasks = [t for t in tasks if t["id"] != self.task_id]
            if len(tasks) == original:
                return f"Error: No task found with ID '{self.task_id}'."
            _save(tasks)
            return f"✓ Task '{self.task_id}' removed."

        elif self.action == "briefing":
            tasks = _load()
            open_tasks = [t for t in tasks if t.get("status", "open") == "open"]
            if not open_tasks:
                return "## Task Briefing\nNo open tasks."

            overdue, urgent_high, upcoming = [], [], []
            for t in open_tasks:
                if t.get("due_date"):
                    due_dt = datetime.strptime(t["due_date"], "%Y-%m-%d")
                    days = (due_dt - now).days
                    if days < 0:
                        overdue.append((t, days))
                    elif days <= 7:
                        urgent_high.append((t, days))
                    else:
                        upcoming.append((t, days))
                elif t.get("priority") == "high":
                    urgent_high.append((t, None))

            high_no_date = [
                (t, None)
                for t in open_tasks
                if t.get("priority") == "high" and not t.get("due_date")
                and (t, None) not in urgent_high
            ]

            lines = [f"## 📋 Task Briefing — {datetime.now().strftime('%B %d, %Y')}\n"]
            lines.append(f"Open tasks: {len(open_tasks)}")

            if overdue:
                overdue.sort(key=lambda x: x[1])
                lines.append("\n### ⚠️ Overdue:")
                for t, days in overdue:
                    proj = f" [{t['project']}]" if t.get("project") else ""
                    lines.append(
                        f"  • [{t['org']}]{proj} {t['title']} — {abs(days)} day(s) overdue"
                    )

            if urgent_high:
                urgent_high.sort(key=lambda x: (x[1] is None, x[1] or 999))
                lines.append("\n### 🔴 High Priority / Due This Week:")
                for t, days in urgent_high:
                    proj = f" [{t['project']}]" if t.get("project") else ""
                    due_str = f" (due in {days} days)" if days is not None else " (no due date)"
                    lines.append(
                        f"  • [{t['org']}]{proj} {t['title']}{due_str}"
                    )

            if high_no_date:
                lines.append("\n### 🟡 High Priority (No Due Date):")
                for t, _ in high_no_date:
                    proj = f" [{t['project']}]" if t.get("project") else ""
                    lines.append(f"  • [{t['org']}]{proj} {t['title']}")

            return "\n".join(lines)

        else:
            return f"Error: Unknown action '{self.action}'."


if __name__ == "__main__":
    print("=== Test: Add tasks ===")
    t1 = TaskManager(
        action="add",
        title="Draft Q2 development report for board",
        org="LFLA",
        project="Board Meeting June",
        priority="high",
        due_date="2026-05-30",
    )
    print(t1.run())

    t2 = TaskManager(
        action="add",
        title="Follow up with Weingart Foundation re: letter of inquiry",
        org="LFLA",
        project="Grants",
        priority="high",
        due_date="2026-05-10",
    )
    print(t2.run())

    print("\n=== Test: Briefing ===")
    t3 = TaskManager(action="briefing")
    print(t3.run())

    print("\n=== Test: List open ===")
    t4 = TaskManager(action="list")
    print(t4.run())
