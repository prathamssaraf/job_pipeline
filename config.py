"""
Configuration module for Job Pipeline Tracker.
Loads settings from environment variables and .env file.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)


class Config:
    """Application configuration loaded from environment."""
    
    # Gemini API
    # Support for multiple keys for rotation (comma-separated)
    GEMINI_API_KEYS: list[str] = [
        k.strip() for k in os.getenv("GEMINI_API_KEYS", "").split(",") if k.strip()
    ]
    
    # Backwards compatibility: if GEMINI_API_KEYS is empty, try single GEMINI_API_KEY
    if not GEMINI_API_KEYS:
        _single_key = os.getenv("GEMINI_API_KEY", "")
        if _single_key:
            GEMINI_API_KEYS.append(_single_key)
            
    # For backward compatibility properties if needed elsewhere
    @property
    def GEMINI_API_KEY(self) -> str:
        """Return the first available key or empty string."""
        return self.GEMINI_API_KEYS[0] if self.GEMINI_API_KEYS else ""
    
    # Email settings
    EMAIL_SENDER: str = os.getenv("EMAIL_SENDER", "")
    EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "")
    EMAIL_RECIPIENT: str = os.getenv("EMAIL_RECIPIENT", "")
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    
    # Job sources configuration
    # Supports two formats:
    # 1. Simple: JOB_URLS=url1,url2,url3 (uses default_browser setting)
    # 2. Enhanced: JOB_SOURCES=[{"url": "...", "requires_browser": true, "name": "Meta"}]
    
    # Default fetch mode: if True, all simple JOB_URLS use browser by default
    DEFAULT_USE_BROWSER: bool = os.getenv("DEFAULT_USE_BROWSER", "false").lower() == "true"
    
    @property
    def job_urls(self) -> list[str]:
        """Get simple URL list (for backwards compatibility)."""
        urls_str = os.getenv("JOB_URLS", "")
        return [url.strip() for url in urls_str.split(",") if url.strip()]
    
    @property
    def job_sources(self) -> list[dict]:
        """
        Get job sources with full configuration.
        
        Returns list of dicts with keys: url, name, requires_browser
        Supports both simple JOB_URLS and enhanced JOB_SOURCES format.
        """
        from unified_fetcher import JobSource
        
        sources = []
        
        # Check for enhanced JSON format first
        sources_json = os.getenv("JOB_SOURCES", "")
        if sources_json:
            try:
                parsed = json.loads(sources_json)
                for item in parsed:
                    sources.append(JobSource(
                        url=item.get("url", ""),
                        name=item.get("name", ""),
                        requires_browser=item.get("requires_browser", False)
                    ))
            except json.JSONDecodeError as e:
                print(f"[Config] Warning: Invalid JOB_SOURCES JSON: {e}")
        
        # Fallback to simple URL list
        if not sources:
            for url in self.job_urls:
                sources.append(JobSource(
                    url=url,
                    requires_browser=self.DEFAULT_USE_BROWSER
                ))
        
        return sources
    
    # Scheduling
    CHECK_INTERVAL_HOURS: int = int(os.getenv("CHECK_INTERVAL_HOURS", "6"))
    
    # Database
    DB_PATH: Path = Path(__file__).parent / "jobs.db"
    
    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if not self.GEMINI_API_KEYS:
            errors.append("GEMINI_API_KEYS (or GEMINI_API_KEY) is required")
        
        if not self.EMAIL_SENDER:
            errors.append("EMAIL_SENDER is required")
        
        if not self.EMAIL_PASSWORD:
            errors.append("EMAIL_PASSWORD is required")
        
        if not self.EMAIL_RECIPIENT:
            errors.append("EMAIL_RECIPIENT is required")
        
        if not self.job_sources:
            errors.append("At least one job source is required (JOB_URLS or JOB_SOURCES)")
        
        return errors


# Global config instance
config = Config()
