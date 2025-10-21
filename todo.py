#!/usr/bin/env python3
import argparse, json, os, sys, uuid, time, datetime
from typing import List, Dict, Any, Optional

STORE_FILE = os.path.join(os.path.dirname(__file__), "tasks.json")
PRIORITIES = ("high", "normal", "low")

def now_ts() -> int:
    return int(time.time())

def today_date() -> datetime.date:
    return datetime.date.today()

def parse_date(s: Optional[str]) -> Optional[str]:
    if not s: return None
    try:
        # Accept YYYY-MM-DD or relative words: today, tomorrow
        if s.lower() == "today":
            return today_date().isoformat()
        if s.lower() == "tomorrow":
            return (today_date() + datetime.timedelta(days=1)).isoformat()
        return datetime.date.fromisoformat(s).isoformat()
    except ValueError:
        sys.exit(f"Invalid date '{s}'. Use YYYY-MM-DD, 'today', or 'tomorrow'.")

def load() -> List[Dict[str, Any]]:
    if not os.path.exists(STORE_FILE): return []
    try:
        with open(STORE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list): return data
            return []
    except json.JSONDecodeError:
        sys.exit("Corrupt tasks.json. Fix or delete the file.")

def save(items: List[Dict[str, Any]]) -> None:
    with open(STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)

def short_id() -> str:
    return uuid.uuid4().hex[:8]

def find(items: List[Dict[str, Any]], tid: str) -> Optional[Dict[str, Any]]:
    return next((t for t in items if t["id"].startswith(tid)), None)

def pri_rank(p: str) -> int:
    order = {"high": 0, "normal": 1, "low": 2}
    return order.get(p, 1)

def is_overdue(due_iso: Optional[str], completed: bool) -> bool:
    if not due_iso or completed: return False
    return datetime.date.fromisoformat(due_iso) < today_date()

def fmt_date(iso: Optional[str]) -> str:
    return "" if not iso else iso

def fmt_check(b: bool) -> str:
    return "✓" if b else "·"

def print_table(rows: List[List[str]], headers: List[str]) -> None:
    cols = list(zip(*([headers] + rows))) if rows else [headers]
    widths = [max(len(str(x)) for x in col) for col in cols]
    def line(parts): return "  ".join(str(p).ljust(w) for p, w in zip(parts, widths))
    print(line(headers))
    print(line(["-" * w for w in widths]))
    for r in rows:
        print(line(r))

def cmd_add(args):
    items = load()
    title = " ".join(args.title).strip()
    if not title:
        sys.exit("Title required.")
    p = args.priority.lower()
    if p not in PRIORITIES:
        sys.exit(f"Priority must be one of {', '.join(PRIORITIES)}.")
    due = parse_date(args.due)
    task = {
        "id": short_id(),
        "title": title,
        "priority": p,
        "due": due,
        "completed": False,
        "created_at": now_ts(),
        "completed_at": None
    }
    items.append(task)
    save(items)
    print(f"Added [{task['id']}]: {task['title']}")

def filtered_sorted(items, show, q, sort_key, reverse, overdue_only):
    # filter by completion
    if show == "active":
        items = [t for t in items if not t["completed"]]
    elif show == "completed":
        items = [t for t in items if t["completed"]]
    # query
    if q:
        ql = q.lower()
        items = [t for t in items if ql in t["title"].lower()]
    # overdue
    if overdue_only:
        items = [t for t in items if is_overdue(t["due"], t["completed"])]
    # sort
    if sort_key == "priority":
        items = sorted(items, key=lambda t: (pri_rank(t["priority"]), t.get("due") or "9999-99-99", -t["created_at"]))
    elif sort_key == "due":
        items = sorted(items, key=lambda t: (t.get("due") or "9999-99-99", pri_rank(t["priority"]), -t["created_at"]))
    else:  # created
        items = sorted(items, key=lambda t: t["created_at"], reverse=True)
    if reverse: items.reverse()
    return items

def cmd_list(args):
    items = load()
    items = filtered_sorted(items, args.show, args.query, args.sort, args.reverse, args.overdue)
    rows = []
    for t in items:
        rows.append([
            t["id"],
            fmt_check(t["completed"]),
            t["title"],
            t["priority"],
            fmt_date(t["due"]),
            "overdue" if is_overdue(t["due"], t["completed"]) else ""
        ])
    print_table(rows, ["id", "✓", "title", "priority", "due", "status"])
    remaining = sum(1 for t in load() if not t["completed"])
    print(f"\n{remaining} item{'s' if remaining!=1 else ''} left")

def cmd_done(args):
    items = load()
    t = find(items, args.id)
    if not t: sys.exit("Task not found.")
    t["completed"] = True
    t["completed_at"] = now_ts()
    save(items)
    print(f"Completed [{t['id']}]: {t['title']}")

def cmd_undo(args):
    items = load()
    t = find(items, args.id)
    if not t: sys.exit("Task not found.")
    t["completed"] = False
    t["completed_at"] = None
    save(items)
    print(f"Reopened [{t['id']}]: {t['title']}")

def cmd_delete(args):
    items = load()
    t = find(items, args.id)
    if not t: sys.exit("Task not found.")
    items = [x for x in items if x["id"] != t["id"]]
    save(items)
    print(f"Deleted [{t['id']}]: {t['title']}")

def cmd_edit(args):
    items = load()
    t = find(items, args.id)
    if not t: sys.exit("Task not found.")
    changed = []
    if args.title:
        t["title"] = " ".join(args.title).strip()
        changed.append("title")
    if args.priority:
        p = args.priority.lower()
        if p not in PRIORITIES:
            sys.exit(f"Priority must be one of {', '.join(PRIORITIES)}.")
        t["priority"] = p
        changed.append("priority")
    if args.due is not None:  # provided
        t["due"] = parse_date(args.due)
        changed.append("due")
    if args.clear_due:
        t["due"] = None
        changed.append("due")
    save(items)
    if changed:
        print(f"Updated [{t['id']}]: {', '.join(changed)}")
    else:
        print("No changes.")

def cmd_clear_completed(_args):
    items = load()
    before = len(items)
    items = [t for t in items if not t["completed"]]
    save(items)
    print(f"Removed {before - len(items)} completed task(s)")

def cmd_search(args):
    args.show = "all"
    args.sort = "priority"
    args.reverse = False
    args.overdue = False
    cmd_list(args)

def cmd_export(args):
    items = load()
    path = args.path or "tasks_export.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    print(f"Exported {len(items)} task(s) to {path}")

def cmd_import(args):
    if not os.path.exists(args.path):
        sys.exit("Import file not found.")
    with open(args.path, "r", encoding="utf-8") as f:
        data = json.load(f)
        if not isinstance(data, list):
            sys.exit("Invalid import file format.")
    items = load()
    # Merge by creating fresh IDs to avoid collisions
    for t in data:
        items.append({
            "id": short_id(),
            "title": t.get("title", "Untitled"),
            "priority": (t.get("priority") or "normal") if (t.get("priority") in PRIORITIES) else "normal",
            "due": t.get("due"),
            "completed": bool(t.get("completed", False)),
            "created_at": int(t.get("created_at", now_ts())),
            "completed_at": t.get("completed_at", None)
        })
    save(items)
    print(f"Imported {len(data)} task(s)")

def main():
    p = argparse.ArgumentParser(prog="todo", description="Simple CLI To-Do (Python, JSON-backed).")
    sub = p.add_subparsers(dest="cmd", required=True)

    # add
    ap = sub.add_parser("add", help="Add a task")
    ap.add_argument("title", nargs="+", help="Task title")
    ap.add_argument("-p", "--priority", default="normal", help="high|normal|low")
    ap.add_argument("-d", "--due", default=None, help="YYYY-MM-DD | today | tomorrow")
    ap.set_defaults(func=cmd_add)

    # list
    lp = sub.add_parser("list", help="List tasks")
    lp.add_argument("-s", "--show", choices=("all", "active", "completed"), default="all")
    lp.add_argument("-q", "--query", default="", help="Substring match")
    lp.add_argument("--sort", choices=("created", "priority", "due"), default="created")
    lp.add_argument("-r", "--reverse", action="store_true", help="Reverse order")
    lp.add_argument("--overdue", action="store_true", help="Only overdue")
    lp.set_defaults(func=cmd_list)

    # done/undo/delete
    dp = sub.add_parser("done", help="Mark task as completed")
    dp.add_argument("id", help="Task id (prefix ok)")
    dp.set_defaults(func=cmd_done)

    up = sub.add_parser("undo", help="Reopen a completed task")
    up.add_argument("id", help="Task id (prefix ok)")
    up.set_defaults(func=cmd_undo)

    delp = sub.add_parser("delete", help="Delete a task")
    delp.add_argument("id", help="Task id (prefix ok)")
    delp.set_defaults(func=cmd_delete)

    # edit
    ep = sub.add_parser("edit", help="Edit a task")
    ep.add_argument("id", help="Task id (prefix ok)")
    ep.add_argument("--title", nargs="+", help="New title")
    ep.add_argument("--priority", choices=PRIORITIES, help="New priority")
    ep.add_argument("--due", nargs="?", const="", help="Set due date; omit value to keep current")
    ep.add_argument("--clear-due", action="store_true", help="Clear due date")
    ep.set_defaults(func=cmd_edit)

    # clear-completed
    cp = sub.add_parser("clear-completed", help="Remove completed tasks")
    cp.set_defaults(func=cmd_clear_completed)

    # search
    sp = sub.add_parser("search", help="Search tasks by text")
    sp.add_argument("query", nargs="?", default="", help="Substring match")
    sp.set_defaults(func=cmd_search)

    # export/import
    exp = sub.add_parser("export", help="Export tasks to JSON")
    exp.add_argument("-o", "--path", help="Output file path")
    exp.set_defaults(func=cmd_export)

    imp = sub.add_parser("import", help="Import tasks from JSON")
    imp.add_argument("path", help="Input file path")
    imp.set_defaults(func=cmd_import)

    args = p.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
