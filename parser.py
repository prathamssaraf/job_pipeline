"""
Gemini-powered HTML Parser for Job Pipeline Tracker.
Uses Gemini AI to extract structured job data from raw HTML.
"""

import json
import google.generativeai as genai
from typing import Optional
from config import config
from logger import get_logger

logger = get_logger(__name__)


class Parser:
    """Parses job listings from HTML using Gemini AI."""
    
    EXTRACTION_PROMPT = '''You are a job listing extractor. Analyze the HTML below and extract ALL job postings you can find.

For each job, extract:
- title: The job title
- company: Company name (if visible, otherwise use "Unknown")
- location: Job location (if visible, otherwise use "Not specified")
- url: Link to the job posting (if available, otherwise use "")
- description: Brief description or requirements snippet (first 200 chars)

Return ONLY a valid JSON array. If no jobs found, return empty array [].

Example output:
[
  {"title": "Software Engineer", "company": "Google", "location": "Mountain View, CA", "url": "https://...", "description": "We are looking for..."},
  {"title": "Data Analyst", "company": "Google", "location": "New York, NY", "url": "https://...", "description": "Join our data team..."}
]

HTML to analyze:'''

    def __init__(self):
        self.model = None
        self._current_key_val = None
        self._current_key_idx = 0
    
    def _initialize_client(self, key_idx: int = 0) -> bool:
        """
        Initialize Gemini client with a specific key.
        
        Args:
            key_idx: Index of the key to use from config.GEMINI_API_KEYS
            
        Returns:
            True if initialization successful with a new key, False otherwise.
        """
        keys = config.GEMINI_API_KEYS
        if not keys:
            raise ValueError("No GEMINI_API_KEYS configured")
        
        # Ensure index is valid (circular)
        self._current_key_idx = key_idx % len(keys)
        new_key = keys[self._current_key_idx]
        
        # Configure genai with the new key
        try:
            genai.configure(api_key=new_key)
            self.model = genai.GenerativeModel("gemini-2.5-flash-lite")
            self._current_key_val = new_key
            logger.info(f"Initialized Gemini with key #{self._current_key_idx + 1}/{len(keys)} (ending in ...{new_key[-4:]})")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize key #{self._current_key_idx + 1}: {e}")
            return False

    def _rotate_key(self) -> bool:
        """
        Switch to the next available API key.
        
        Returns:
            True if rotated to a new key, False if all keys exhausted/failed (though currently circular).
        """
        keys = config.GEMINI_API_KEYS
        if not keys or len(keys) <= 1:
            logger.warning("Cannot rotate: Only one key available.")
            return False
            
        next_idx = self._current_key_idx + 1
        logger.info(f"Rotating API key (from #{self._current_key_idx + 1} to #{next_idx % len(keys) + 1})...")
        return self._initialize_client(next_idx)

    def parse(self, html: str, source_url: str = "") -> list[dict]:
        """
        Parse HTML and extract job listings using Gemini with automatic key rotation.
        """
        if self.model is None:
            self._initialize_client()
        
        # Strip script and style tags to reduce size
        import re
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
        html = re.sub(r'\s+', ' ', html)
        
        logger.debug(f"HTML cleaned to {len(html)} chars")
        
        max_html_length = 800000 
        if len(html) > max_html_length:
            html = html[:max_html_length]
            logger.warning(f"HTML truncated to {max_html_length} chars")
        
        prompt = self.EXTRACTION_PROMPT + "\n\n" + html
        
        # Retry loop for key rotation
        max_retries = len(config.GEMINI_API_KEYS)
        attempts = 0
        
        while attempts < max_retries:
            try:
                response = self.model.generate_content(prompt)
                
                # If we get here, the call succeeded. Process response.
                return self._process_response(response, source_url)
                
            except Exception as e:
                # Check for likely quota/auth errors that warrant rotation
                error_str = str(e).lower()
                is_quota_error = "429" in error_str or "resourceexhausted" in error_str or "quota" in error_str
                is_auth_error = "403" in error_str or "permissiondenied" in error_str or "api_key" in error_str
                
                if is_quota_error or is_auth_error:
                    logger.warning(f"API Error (Attempt {attempts + 1}/{max_retries}): {e}")
                    
                    # Try to rotate. If rotation fails (e.g. only 1 key), re-raise
                    if self._rotate_key():
                        attempts += 1
                        continue
                    else:
                        logger.error("Rotation failed or single key exhausted.")
                        break
                else:
                    # Non-rotation error (e.g. bad request, network), just log and break/return empty
                    logger.error(f"Non-rotation error during parsing: {e}")
                    break
        
        logger.error("Failed to extract jobs after trying available keys.")
        return []

    def _process_response(self, response, source_url):
        """Helper to process the raw Gemini response into job list."""
        try:
            text = response.text.strip()
            
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            
            jobs = json.loads(text)
            for job in jobs:
                job["source_url"] = source_url
            
            logger.info(f"Extracted {len(jobs)} jobs from {source_url}")
            return jobs
            
        except json.JSONDecodeError:
            logger.warning(f"JSON incomplete, attempting partial extraction...")
            return self._extract_partial_json(response.text, source_url)
        except Exception as e:
            logger.error(f"Error processing response: {e}")
            return []

    def _extract_partial_json(self, text, source_url):
        """Attempt to extract valid JSON objects from broken response."""
        try:
            jobs = []
            start = text.find('[')
            if start != -1:
                depth = 0
                obj_start = None
                i = start
                
                while i < len(text):
                    char = text[i]
                    if char == '{':
                        if depth == 0: obj_start = i
                        depth += 1
                    elif char == '}':
                        depth -= 1
                        if depth == 0 and obj_start is not None:
                            obj_str = text[obj_start:i+1]
                            try:
                                job = json.loads(obj_str)
                                if 'title' in job:
                                    job["source_url"] = source_url
                                    jobs.append(job)
                            except: pass
                            obj_start = None
                    elif char == '"':
                        i += 1
                        while i < len(text):
                            if text[i] == '\\': i += 2; continue
                            if text[i] == '"': break
                            i += 1
                    i += 1
            
            if jobs:
                logger.info(f"Recovered {len(jobs)} jobs from partial response")
                return jobs
        except Exception as e:
            logger.error(f"Partial extraction failed: {e}")
        return []
    
    def parse_multiple(self, html_dict: dict[str, Optional[str]]) -> list[dict]:
        """
        Parse multiple HTML pages.
        
        Args:
            html_dict: Dictionary mapping URL to HTML content
            
        Returns:
            Combined list of all jobs from all pages
        """
        all_jobs = []
        for url, html in html_dict.items():
            if html:
                jobs = self.parse(html, source_url=url)
                all_jobs.extend(jobs)
        return all_jobs


# Default parser instance
parser = Parser()
