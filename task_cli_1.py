#!/usr/bin/env python3
"""
Task Tracker CLI
A simple command-line tool to track tasks stored in a local JSON file.
"""

import sys
import json
import os
from datetime import datetime

# ─── Constants ────────────────────────────────────────────────────────────────

TASKS_FILE = "tasks.json"
VALID_STATUSES = {"todo", "in-progress", "done"}

# ─── Colour helpers (no external libs) ────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
DIM    = "\033[2m"

def _colour(text: str, *codes: str) -> str:
    """Wrap text in ANSI colour codes (skipped if not a TTY)."""
    if not sys.stdout.isatty():
        return text
    return "".join(codes) + text + RESET


# ─── File helpers ──────────────────────────────────────────────────────────────

def _load_tasks() -> list[dict]:
    """Load tasks from the JSON file; create it if missing."""
    if not os.path.exists(TASKS_FILE):
        _save_tasks([])
        return []
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("JSON root must be a list.")
            return data
    except (json.JSONDecodeError, ValueError) as exc:
        _die(f"Could not read '{TASKS_FILE}': {exc}")


def _save_tasks(tasks: list[dict]) -> None:
    """Persist tasks to the JSON file."""
    try:
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2, ensure_ascii=False)
    except OSError as exc:
        _die(f"Could not write '{TASKS_FILE}': {exc}")


# ─── ID helpers ────────────────────────────────────────────────────────────────

def _next_id(tasks: list[dict]) -> int:
    """Return the next available integer ID."""
    return max((t["id"] for t in tasks), default=0) + 1


def _find_task(tasks: list[dict], task_id: int) -> dict | None:
    """Return the task with the given ID, or None."""
    for task in tasks:
        if task["id"] == task_id:
            return task
    return None


# ─── Timestamp ─────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ─── Error / exit ──────────────────────────────────────────────────────────────

def _die(msg: str) -> None:
    print(_colour(f"Error: {msg}", RED, BOLD), file=sys.stderr)
    sys.exit(1)


def _ok(msg: str) -> None:
    print(_colour("✔ ", GREEN, BOLD) + msg)


# ─── Commands ──────────────────────────────────────────────────────────────────

def cmd_add(args: list[str]) -> None:
    """Add a new task.  Usage: add <description>"""
    if not args:
        _die("'add' requires a description.\n  Usage: task-cli add \"Buy groceries\"")

    description = " ".join(args).strip()
    if not description:
        _die("Description cannot be empty.")

    tasks = _load_tasks()
    new_id = _next_id(tasks)
    now = _now()
    task = {
        "id":          new_id,
        "description": description,
        "status":      "todo",
        "createdAt":   now,
        "updatedAt":   now,
    }
    tasks.append(task)
    _save_tasks(tasks)
    _ok(f"Task added successfully (ID: {_colour(str(new_id), CYAN, BOLD)})")


def cmd_update(args: list[str]) -> None:
    """Update a task's description.  Usage: update <id> <new description>"""
    if len(args) < 2:
        _die("'update' requires an ID and a new description.\n"
             "  Usage: task-cli update 1 \"New description\"")

    task_id = _parse_id(args[0])
    new_desc = " ".join(args[1:]).strip()
    if not new_desc:
        _die("New description cannot be empty.")

    tasks = _load_tasks()
    task = _find_task(tasks, task_id)
    if task is None:
        _die(f"No task found with ID {task_id}.")

    task["description"] = new_desc
    task["updatedAt"] = _now()
    _save_tasks(tasks)
    _ok(f"Task {_colour(str(task_id), CYAN, BOLD)} updated.")


def cmd_delete(args: list[str]) -> None:
    """Delete a task.  Usage: delete <id>"""
    if not args:
        _die("'delete' requires an ID.\n  Usage: task-cli delete 1")

    task_id = _parse_id(args[0])
    tasks = _load_tasks()
    original_len = len(tasks)
    tasks = [t for t in tasks if t["id"] != task_id]

    if len(tasks) == original_len:
        _die(f"No task found with ID {task_id}.")

    _save_tasks(tasks)
    _ok(f"Task {_colour(str(task_id), CYAN, BOLD)} deleted.")


def cmd_mark(args: list[str], status: str) -> None:
    """Mark a task with a given status.  Usage: mark-* <id>"""
    if not args:
        cmd_name = "mark-" + status
        _die(f"'{cmd_name}' requires an ID.\n  Usage: task-cli {cmd_name} 1")

    task_id = _parse_id(args[0])
    tasks = _load_tasks()
    task = _find_task(tasks, task_id)
    if task is None:
        _die(f"No task found with ID {task_id}.")

    task["status"] = status
    task["updatedAt"] = _now()
    _save_tasks(tasks)
    _ok(f"Task {_colour(str(task_id), CYAN, BOLD)} marked as "
        f"{_colour(status, _status_colour(status), BOLD)}.")


def cmd_list(args: list[str]) -> None:
    """List tasks, optionally filtered by status.  Usage: list [status]"""
    filter_status: str | None = None

    if args:
        filter_status = args[0].lower()
        if filter_status not in VALID_STATUSES:
            _die(f"Unknown status '{filter_status}'. "
                 f"Valid values: {', '.join(sorted(VALID_STATUSES))}")

    tasks = _load_tasks()

    if filter_status:
        tasks = [t for t in tasks if t["status"] == filter_status]

    if not tasks:
        label = f" with status '{filter_status}'" if filter_status else ""
        print(_colour(f"No tasks found{label}.", DIM))
        return

    # ── Header ──
    header_label = f" [{filter_status}]" if filter_status else ""
    print()
    print(_colour(f"  Tasks{header_label}", BOLD))
    print(_colour("  " + "─" * 68, DIM))

    for task in tasks:
        _print_task(task)

    print()
    print(_colour(f"  Total: {len(tasks)} task(s)", DIM))
    print()


# ─── Display helpers ──────────────────────────────────────────────────────────

def _status_colour(status: str) -> str:
    return {
        "todo":        YELLOW,
        "in-progress": CYAN,
        "done":        GREEN,
    }.get(status, RESET)


def _status_badge(status: str) -> str:
    badges = {
        "todo":        "[ TODO ]",
        "in-progress": "[ IN-PROGRESS ]",
        "done":        "[ DONE ]",
    }
    badge = badges.get(status, f"[{status}]")
    return _colour(badge, _status_colour(status), BOLD)


def _print_task(task: dict) -> None:
    """Pretty-print a single task row."""
    id_str   = _colour(f"#{task['id']:<4}", CYAN)
    badge    = _status_badge(task["status"])
    desc     = task["description"]
    created  = _colour(task["createdAt"], DIM)
    updated  = _colour(task["updatedAt"], DIM)

    print(f"  {id_str} {badge}  {desc}")
    print(_colour(f"         Created: {created}   Updated: {updated}", DIM))
    print()


# ─── Input validation ─────────────────────────────────────────────────────────

def _parse_id(raw: str) -> int:
    """Parse a task ID from a string, exiting on error."""
    try:
        value = int(raw)
        if value < 1:
            raise ValueError
        return value
    except ValueError:
        _die(f"'{raw}' is not a valid task ID. IDs must be positive integers.")


# ─── Help ─────────────────────────────────────────────────────────────────────

HELP = """
{bold}Task Tracker CLI{reset}  —  manage your tasks from the terminal

{bold}USAGE{reset}
  task-cli <command> [arguments]

{bold}COMMANDS{reset}
  {cyan}add{reset} <description>              Add a new task
  {cyan}update{reset} <id> <description>      Update a task's description
  {cyan}delete{reset} <id>                    Delete a task

  {cyan}mark-in-progress{reset} <id>          Mark a task as in-progress
  {cyan}mark-done{reset} <id>                 Mark a task as done

  {cyan}list{reset}                           List all tasks
  {cyan}list todo{reset}                      List tasks with status 'todo'
  {cyan}list in-progress{reset}               List tasks with status 'in-progress'
  {cyan}list done{reset}                      List tasks with status 'done'

  {cyan}help{reset}                           Show this help message

{bold}EXAMPLES{reset}
  task-cli add "Buy groceries"
  task-cli update 1 "Buy groceries and cook dinner"
  task-cli mark-in-progress 1
  task-cli mark-done 1
  task-cli list in-progress
  task-cli delete 1

{bold}STORAGE{reset}
  Tasks are saved to {dim}tasks.json{reset} in the current working directory.
""".format(
    bold=BOLD if sys.stdout.isatty() else "",
    reset=RESET if sys.stdout.isatty() else "",
    cyan=CYAN if sys.stdout.isatty() else "",
    dim=DIM if sys.stdout.isatty() else "",
)


# ─── Main dispatcher ──────────────────────────────────────────────────────────

def main() -> None:
    args = sys.argv[1:]  # drop the script name

    if not args or args[0] in ("help", "--help", "-h"):
        print(HELP)
        return

    command = args[0].lower()
    rest    = args[1:]

    dispatch = {
        "add":              lambda: cmd_add(rest),
        "update":           lambda: cmd_update(rest),
        "delete":           lambda: cmd_delete(rest),
        "mark-in-progress": lambda: cmd_mark(rest, "in-progress"),
        "mark-done":        lambda: cmd_mark(rest, "done"),
        "list":             lambda: cmd_list(rest),
    }

    handler = dispatch.get(command)
    if handler is None:
        _die(f"Unknown command '{command}'. Run 'task-cli help' for usage.")

    handler()


if __name__ == "__main__":
    main()
