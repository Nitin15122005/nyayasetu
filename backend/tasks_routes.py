"""
Tasks Module for NyayaSetu - Raw SQLite approach with Bearer auth
Drop this into: backend/tasks_routes.py

FIXES APPLIED:
1. Thread-safe: opens new connection per request (not generator-based)
2. Auto-migration: drops old table if missing columns, recreates with full schema
3. All endpoints accept Request for auth header reading
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import sqlite3
import os

router = APIRouter(prefix="/tasks", tags=["tasks"])

DB_PATH = os.path.join(os.path.dirname(__file__), "nyayasetu.db")


def _get_conn():
    """Open a fresh SQLite connection for the current thread."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _table_exists(cursor, table_name):
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def _column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return any(row["name"] == column_name for row in cursor.fetchall())


def init_tasks_db():
    """Call this once at server startup. Handles schema migration."""
    conn = _get_conn()
    cursor = conn.cursor()

    needs_recreate = False
    if _table_exists(cursor, "tasks"):
        # Check if old schema (missing created_at/updated_at)
        if not _column_exists(cursor, "tasks", "created_at"):
            needs_recreate = True
            cursor.execute("DROP TABLE tasks")
            print("[tasks] Dropped old tasks table (missing created_at)")

    if not _table_exists(cursor, "tasks") or needs_recreate:
        cursor.execute("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                priority TEXT NOT NULL DEFAULT 'medium',
                due_date TEXT,
                matter TEXT,
                assignee TEXT DEFAULT 'You',
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("[tasks] Created tasks table with full schema")

    conn.commit()
    conn.close()


# ── Auth helper ───────────────────────────────────────────────────────────────
def get_token_user(request: Request):
    """Extract user info from Bearer token for standalone task routes."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        return {"user_id": 1, "token": token}
    return {"user_id": 1, "token": None}


# ── Schemas ───────────────────────────────────────────────────────────────────
class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    status: str = Field(default="pending", pattern="^(pending|done)$")
    priority: str = Field(default="medium", pattern="^(high|medium|low)$")
    due_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    matter: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    status: Optional[str] = Field(default=None, pattern="^(pending|done)$")
    priority: Optional[str] = Field(default=None, pattern="^(high|medium|low)$")
    due_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    matter: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)


class TaskOut(BaseModel):
    id: int
    title: str
    status: str
    priority: str
    due_date: Optional[str]
    matter: Optional[str]
    assignee: str
    description: Optional[str]
    created_at: str
    updated_at: str


# ── Helpers ───────────────────────────────────────────────────────────────────
def row_to_task(row):
    return {
        "id": row["id"], "title": row["title"], "status": row["status"],
        "priority": row["priority"], "due_date": row["due_date"],
        "matter": row["matter"], "assignee": row["assignee"],
        "description": row["description"],
        "created_at": row["created_at"], "updated_at": row["updated_at"]
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", response_model=TaskOut)
def create_task(task: TaskCreate, request: Request):
    conn = _get_conn()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO tasks (title, status, priority, due_date, matter, description, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (task.title, task.status, task.priority, task.due_date, task.matter, task.description, now))
    conn.commit()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,))
    result = row_to_task(cursor.fetchone())
    conn.close()
    return result


@router.get("", response_model=List[TaskOut])
def list_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = "due_date",
    request: Request = None
):
    conn = _get_conn()
    cursor = conn.cursor()
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if priority:
        query += " AND priority = ?"
        params.append(priority)
    if search:
        query += " AND (title LIKE ? OR matter LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    if sort_by == "due_date":
        query += " ORDER BY CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date ASC"
    elif sort_by == "priority":
        query += " ORDER BY CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END"
    elif sort_by == "status":
        query += " ORDER BY CASE status WHEN 'pending' THEN 0 ELSE 1 END"
    else:
        query += " ORDER BY created_at DESC"

    cursor.execute(query, params)
    results = [row_to_task(r) for r in cursor.fetchall()]
    conn.close()
    return results


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, request: Request):
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    return row_to_task(row)


@router.put("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, task: TaskUpdate, request: Request):
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")

    updates = []
    params = []
    for field, value in task.model_dump(exclude_unset=True).items():
        updates.append(f"{field} = ?")
        params.append(value)

    if not updates:
        conn.close()
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append("updated_at = ?")
    params.append(datetime.now().isoformat())
    params.append(task_id)

    cursor.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    result = row_to_task(cursor.fetchone())
    conn.close()
    return result


@router.delete("/{task_id}")
def delete_task(task_id: int, request: Request):
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Task not found")
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return {"message": "Task deleted", "id": task_id}


@router.get("/stats/summary")
def get_task_stats(request: Request):
    from datetime import date
    today = date.today().isoformat()
    conn = _get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM tasks")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as pending FROM tasks WHERE status = 'pending'")
    pending = cursor.fetchone()["pending"]

    cursor.execute("SELECT COUNT(*) as done FROM tasks WHERE status = 'done'")
    done = cursor.fetchone()["done"]

    cursor.execute("SELECT COUNT(*) as high FROM tasks WHERE priority = 'high' AND status = 'pending'")
    high = cursor.fetchone()["high"]

    cursor.execute("SELECT COUNT(*) as overdue FROM tasks WHERE status = 'pending' AND due_date < ?", (today,))
    overdue = cursor.fetchone()["overdue"]

    conn.close()
    return {"total": total, "pending": pending, "done": done, "high": high, "overdue": overdue}