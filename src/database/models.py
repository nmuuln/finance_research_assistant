"""Database models for session and artifact management."""
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import json


class Database:
    """SQLite database manager for sessions, artifacts, and uploaded files."""

    def __init__(self, db_path: str = "data/app.db"):
        """Initialize database connection."""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize database schema."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                topic TEXT,
                language TEXT DEFAULT 'mn',
                status TEXT DEFAULT 'active',
                metadata TEXT
            )
        """)

        # Artifacts table (research reports)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                artifact_type TEXT DEFAULT 'report',
                title TEXT,
                content TEXT,
                format TEXT DEFAULT 'markdown',
                research_brief TEXT,
                reference_list TEXT,
                file_url TEXT,
                metadata TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            )
        """)

        # Uploaded files table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uploaded_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER,
                storage_path TEXT NOT NULL,
                processed BOOLEAN DEFAULT 0,
                extracted_content TEXT,
                metadata TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            )
        """)

        # Messages table (conversation history)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_artifacts_session ON artifacts(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_session ON uploaded_files(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")

        conn.commit()
        conn.close()

    # Session methods
    def create_session(self, session_id: str, topic: Optional[str] = None,
                      language: str = "mn", metadata: Optional[Dict] = None) -> Dict:
        """Create a new session."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO sessions (id, topic, language, metadata)
            VALUES (?, ?, ?, ?)
        """, (session_id, topic, language, json.dumps(metadata or {})))

        conn.commit()
        conn.close()

        result = self.get_session(session_id)
        assert result is not None, f"Session {session_id} should exist after creation"
        return result

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def update_session(self, session_id: str, **kwargs):
        """Update session fields."""
        conn = self.get_connection()
        cursor = conn.cursor()

        allowed_fields = ['topic', 'language', 'status', 'metadata']
        updates = []
        values = []

        for key, value in kwargs.items():
            if key in allowed_fields:
                if key == 'metadata':
                    value = json.dumps(value)
                updates.append(f"{key} = ?")
                values.append(value)

        if updates:
            values.append(datetime.utcnow())
            values.append(session_id)
            query = f"UPDATE sessions SET {', '.join(updates)}, updated_at = ? WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()

        conn.close()

    def list_sessions(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """List all sessions with pagination."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT s.*,
                   COUNT(a.id) as artifact_count,
                   COUNT(f.id) as file_count
            FROM sessions s
            LEFT JOIN artifacts a ON s.id = a.session_id
            LEFT JOIN uploaded_files f ON s.id = f.session_id
            GROUP BY s.id
            ORDER BY s.updated_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    # Artifact methods
    def create_artifact(self, session_id: str, title: str, content: str,
                       research_brief: Optional[str] = None,
                       reference_list: Optional[str] = None,
                       file_url: Optional[str] = None,
                       metadata: Optional[Dict] = None) -> Dict:
        """Create a new artifact (research report)."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO artifacts (session_id, title, content, research_brief,
                                  reference_list, file_url, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session_id, title, content, research_brief, reference_list,
              file_url, json.dumps(metadata or {})))

        artifact_id = cursor.lastrowid
        conn.commit()
        conn.close()

        assert artifact_id is not None, "Artifact ID should exist after insertion"
        result = self.get_artifact(artifact_id)
        assert result is not None, f"Artifact {artifact_id} should exist after creation"
        return result

    def get_artifact(self, artifact_id: int) -> Optional[Dict]:
        """Get artifact by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def list_artifacts(self, session_id: str) -> List[Dict]:
        """List all artifacts for a session."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM artifacts
            WHERE session_id = ?
            ORDER BY created_at DESC
        """, (session_id,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    # Uploaded file methods
    def create_uploaded_file(self, session_id: str, filename: str,
                            file_type: str, storage_path: str,
                            file_size: int = 0,
                            metadata: Optional[Dict] = None) -> Dict:
        """Record an uploaded file."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO uploaded_files (session_id, filename, file_type,
                                       storage_path, file_size, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, filename, file_type, storage_path, file_size,
              json.dumps(metadata or {})))

        file_id = cursor.lastrowid
        conn.commit()
        conn.close()

        assert file_id is not None, "File ID should exist after insertion"
        result = self.get_uploaded_file(file_id)
        assert result is not None, f"Uploaded file {file_id} should exist after creation"
        return result

    def get_uploaded_file(self, file_id: int) -> Optional[Dict]:
        """Get uploaded file by ID."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM uploaded_files WHERE id = ?", (file_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def update_uploaded_file(self, file_id: int, **kwargs):
        """Update uploaded file record."""
        conn = self.get_connection()
        cursor = conn.cursor()

        allowed_fields = ['processed', 'extracted_content', 'metadata']
        updates = []
        values = []

        for key, value in kwargs.items():
            if key in allowed_fields:
                if key == 'metadata':
                    value = json.dumps(value)
                updates.append(f"{key} = ?")
                values.append(value)

        if updates:
            values.append(file_id)
            query = f"UPDATE uploaded_files SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()

        conn.close()

    def list_uploaded_files(self, session_id: str) -> List[Dict]:
        """List all uploaded files for a session."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM uploaded_files
            WHERE session_id = ?
            ORDER BY uploaded_at DESC
        """, (session_id,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    # Message methods
    def add_message(self, session_id: str, role: str, content: str,
                   metadata: Optional[Dict] = None):
        """Add a message to conversation history."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO messages (session_id, role, content, metadata)
            VALUES (?, ?, ?, ?)
        """, (session_id, role, content, json.dumps(metadata or {})))

        conn.commit()
        conn.close()

    def get_messages(self, session_id: str, limit: int = 100) -> List[Dict]:
        """Get conversation history for a session."""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM messages
            WHERE session_id = ?
            ORDER BY created_at ASC
            LIMIT ?
        """, (session_id, limit))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]
