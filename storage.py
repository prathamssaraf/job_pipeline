"""
SQLite Storage module for Job Pipeline Tracker.
Handles persistence of seen jobs and new job detection.
"""

import sqlite3
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from config import config
from logger import get_logger

logger = get_logger(__name__)


class Storage:
    """SQLite-based storage for tracking seen jobs."""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.DB_PATH
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            # Jobs table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    company TEXT,
                    location TEXT,
                    url TEXT,
                    description TEXT,
                    source_url TEXT,
                    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    notified BOOLEAN DEFAULT FALSE
                )
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_jobs_notified 
                ON jobs(notified)
            ''')
            
            # Sources table for dashboard management
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE,
                    requires_browser BOOLEAN DEFAULT TRUE,
                    last_checked DATETIME,
                    job_count INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    @staticmethod
    def generate_job_id(job: dict) -> str:
        """
        Generate unique ID for a job based on normalized title and URL.
        Aggressively normalizes to handle slight variations (spaces, params, casing).
        """
        # 1. Normalize Title: lowercase, keep only alphanumeric (removes spaces, -, etc)
        # "Software Engineer " -> "softwareengineer"
        # "Software Engineer - Backend" -> "softwareengineerbackend"
        raw_title = job.get('title', '')
        normalized_title = re.sub(r'[^a-z0-9]', '', raw_title.lower())
        
        # 2. Normalize URL: remove query params, fragments, trailing slashes
        # "example.com/job?ref=123" -> "example.com/job"
        raw_url = job.get('url', '')
        normalized_url = raw_url.split('?')[0].split('#')[0].rstrip('/').lower()
        
        unique_str = f"{normalized_title}|{normalized_url}"
        return hashlib.md5(unique_str.encode()).hexdigest()
    
    def is_new_job(self, job: dict) -> bool:
        """Check if a job is new (not in database)."""
        job_id = self.generate_job_id(job)
        with self._get_connection() as conn:
            result = conn.execute(
                "SELECT 1 FROM jobs WHERE job_id = ?", 
                (job_id,)
            ).fetchone()
            return result is None
    
    def find_new_jobs(self, jobs: list[dict]) -> list[dict]:
        """
        Filter list of jobs to only include new ones.
        
        Args:
            jobs: List of job dictionaries
            
        Returns:
            List of jobs not yet in database
        """
        new_jobs = []
        for job in jobs:
            if self.is_new_job(job):
                job["job_id"] = self.generate_job_id(job)
                new_jobs.append(job)
        return new_jobs
    
    def save_job(self, job: dict):
        """Save a job to the database."""
        job_id = job.get("job_id") or self.generate_job_id(job)
        
        with self._get_connection() as conn:
            conn.execute('''
                INSERT OR IGNORE INTO jobs 
                (job_id, title, company, location, url, description, source_url, notified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                job_id,
                job.get("title", "Unknown"),
                job.get("company", "Unknown"),
                job.get("location", "Not specified"),
                job.get("url", ""),
                job.get("description", ""),
                job.get("source_url", ""),
                False
            ))
            conn.commit()
    
    def save_jobs(self, jobs: list[dict]):
        """Save multiple jobs to database."""
        for job in jobs:
            self.save_job(job)
    
    def mark_notified(self, jobs: list[dict]):
        """Mark jobs as having been notified."""
        with self._get_connection() as conn:
            for job in jobs:
                job_id = job.get("job_id") or self.generate_job_id(job)
                conn.execute(
                    "UPDATE jobs SET notified = TRUE WHERE job_id = ?",
                    (job_id,)
                )
            conn.commit()
    
    def get_all_jobs(self, limit: int = 100) -> list[dict]:
        """Get all stored jobs."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY first_seen DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(row) for row in rows]
    
    def get_job_count(self) -> int:
        """Get total number of jobs in database."""
        with self._get_connection() as conn:
            result = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()
            return result[0]
    
    def clear_all(self, confirmation: str = ""):
        """
        Clear all jobs from database. DANGEROUS operation!
        
        To confirm, you must pass confirmation="DELETE_ALL_JOBS_PERMANENTLY"
        
        This method should NEVER be called in normal operation.
        Jobs should never be automatically deleted.
        """
        if confirmation != "DELETE_ALL_JOBS_PERMANENTLY":
            raise ValueError(
                "Deletion not confirmed. To clear all jobs, you must call:\n"
                "  storage.clear_all(confirmation='DELETE_ALL_JOBS_PERMANENTLY')\n"
                "⚠️  WARNING: This will permanently delete ALL job records!"
            )
        
        with self._get_connection() as conn:
            conn.execute("DELETE FROM jobs")
            conn.commit()
            logger.warning("⚠️  ALL JOBS DELETED - Database cleared")
    
    # ============================================================
    # SOURCE MANAGEMENT (for dashboard)
    # ============================================================
    
    def get_sources(self) -> list[dict]:
        """Get all job sources."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM sources ORDER BY created_at DESC"
            ).fetchall()
            return [dict(row) for row in rows]
    
    def get_source_count(self) -> int:
        """Get total number of sources."""
        with self._get_connection() as conn:
            result = conn.execute("SELECT COUNT(*) FROM sources").fetchone()
            return result[0]
    
    def add_source(self, source: dict) -> int:
        """Add a new job source. Returns source ID."""
        with self._get_connection() as conn:
            cursor = conn.execute('''
                INSERT OR IGNORE INTO sources (name, url, requires_browser)
                VALUES (?, ?, ?)
            ''', (
                source.get('name', 'Unnamed'),
                source['url'],
                source.get('requires_browser', True)
            ))
            conn.commit()
            return cursor.lastrowid
    
    def delete_source(self, source_id: int):
        """Delete a job source by ID."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))
            conn.commit()
    
    def update_source_stats(self, source_id: int, job_count: int):
        """Update source statistics after a run."""
        with self._get_connection() as conn:
            conn.execute('''
                UPDATE sources 
                SET last_checked = CURRENT_TIMESTAMP, job_count = ?
                WHERE id = ?
            ''', (job_count, source_id))
            conn.commit()


# Default storage instance
storage = Storage()
