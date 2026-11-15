import sqlite3
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal
from config import APPDATA_DIR

class TaskService(QObject):
    tasks_changed = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.db_path = APPDATA_DIR / "tasks.db"
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        completed INTEGER DEFAULT 0,
                        due_time TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
        except Exception as e:
            print(f"[TaskService] DB init error: {e}")

    def get_tasks(self) -> list:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, title, completed, due_time FROM tasks ORDER BY completed ASC, id DESC")
                rows = cursor.fetchall()
                return [
                    {"id": r[0], "title": r[1], "completed": bool(r[2]), "due_time": r[3] or ""}
                    for r in rows
                ]
        except Exception as e:
            print(f"[TaskService] Error fetching tasks: {e}")
            return []

    def add_task(self, title: str, due_time: str = None) -> bool:
        if not title or not title.strip():
            return False
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO tasks (title, completed, due_time) VALUES (?, 0, ?)",
                    (title.strip(), due_time)
                )
            self.tasks_changed.emit(self.get_tasks())
            return True
        except Exception as e:
            print(f"[TaskService] Error adding task: {e}")
            return False

    def toggle_task(self, task_id: int):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("UPDATE tasks SET completed = 1 - completed WHERE id = ?", (task_id,))
            self.tasks_changed.emit(self.get_tasks())
        except Exception as e:
            print(f"[TaskService] Error toggling task: {e}")

    def delete_task(self, task_id: int):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            self.tasks_changed.emit(self.get_tasks())
        except Exception as e:
            print(f"[TaskService] Error deleting task: {e}")

    def clear_completed(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM tasks WHERE completed = 1")
            self.tasks_changed.emit(self.get_tasks())
        except Exception as e:
            print(f"[TaskService] Error clearing completed tasks: {e}")
