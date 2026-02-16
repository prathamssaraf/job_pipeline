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

STRICT INSTRUCTIONS:
1. **MANDATORY**: A valid job posting MUST have a specific **Job Link** (URL) or **Apply Button**. If there is no specific link to the job details, IGNORE IT.
2. **CONTEXT CHECK**: Besides the link, the job MUST have at least ONE of the following:
   - Specific LOCATION (e.g. "Seattle, WA", "Remote")
   - Posting DATE or STATUS (e.g. "2 days ago", "New", "Updated: 2/12/2026")
   - "Apply" button text next to it
   - Short Job Description snippet
3. **EXCLUSION**: 
   - If a text is just a Title (e.g. "Software Development") with NO specific link and NO context, it is a Category or Menu. IGNORE IT.
   - Exclude Video titles (e.g. "Senior Program Manager" header for a video).
4. EXTRACT TITLES EXACTLY AS THEY APPEAR.
5. If no jobs are found, return an empty array [].

For each job, extract:
- title: The job title (EXACT MATCH)
- company: Company name (if visible, otherwise use "Unknown")
- location: Job location (if visible, otherwise use "Not specified")
- url: Link to the job posting (REQUIRED - return empty string ONLY if absolutely standard text parsing fails, but generally reject jobs with no link)
- description: Brief description or requirements snippet (first 200 chars)

Return ONLY a valid JSON array.

Example output:
[
  {"title": "Software Engineer", "company": "Google", "location": "Mountain View, CA", "url": "https://...", "description": "We are looking for..."},
  {"title": "Data Analyst", "company": "Google", "location": "New York, NY", "url": "https://...", "description": "Join our data team..."}
]

HTML to analyze:'''

    VERIFICATION_PROMPT = '''You are a Truth Verification AI. 
I will provide you with a list of jobs extracted from the HTML below.
Your task is to VERIFY that each job actually exists in the provided HTML.

Rules:
1. **LINK CHECK**: Does the job have a valid, specific URL/Apply Link extracted? 
   - If NO link -> REMOVE IT (It's likely a category header).
2. **CONTEXT CHECK**: Does it have a visible LOCATION, DATE, APPLY BUTTON, or DESCRIPTION in the HTML?
   - If NO context -> REMOVE IT.
3. Check the HTML for the specific Job Title and Company.
4. REMOVE items that are just Categories (e.g. "Operations", "MBA"), Video Titles, or Navigation Links.
5. Return the filtered list of valid jobs as a JSON array.

Jobs to Verify:
{jobs_json}

HTML Context:
'''

    VERIFY_PAGE_PROMPT = '''You are a Job Validator.
I have a potential job posting for:
- Title: {title}
- Company: {company}

Analyze the HTML of the destination page below.
Does this page confirm that this is indeed a job listing for the above position?
Check for:
- Presence of specific job description/requirements.
- "Apply" button.
- Title matching the one provided.

If it's a login page, a generic search result list, or a "job not found" error, return FALSE.
If it is the actual job description, return TRUE.

Return strictly JSON: {{"valid": true, "reason": "..."}} or {{"valid": false, "reason": "..."}}

HTML:
'''

    def __init__(self):
        self.model = None
        self._current_key_val = None
        self._current_key_idx = 0
    
    def _initialize_client(self, key_idx: int = 0) -> bool:
        """
        Initialize Gemini client with a specific key.
        """
        keys = config.GEMINI_API_KEYS
        if not keys:
            raise ValueError("No GEMINI_API_KEYS configured")
        
        self._current_key_idx = key_idx % len(keys)
        new_key = keys[self._current_key_idx]
        
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
        """Switch to the next available API key."""
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
        Includes a self-correction/verification pass.
        """
        # 1. Initial Extraction
        jobs = self._generate_with_retry(self.EXTRACTION_PROMPT + "\n\n" + self._clean_html(html))
        
        if not jobs:
            return []
            
        # Add source URL to initial results
        for job in jobs:
            job["source_url"] = source_url

        # 2. Verification Pass (Consensus Check)
        # Only verify if we actually found something
        logger.info(f"Initial pass found {len(jobs)} jobs. Verifying...")
        verified_jobs = self._verify_integrity(jobs, self._clean_html(html))
        
        # Re-attach source URL
        for job in verified_jobs:
             if "source_url" not in job:
                 job["source_url"] = source_url
                 
        logger.info(f"Verification complete. Valid jobs: {len(verified_jobs)} (Filtered: {len(jobs) - len(verified_jobs)})")
        return verified_jobs

    def _clean_html(self, html: str) -> str:
        """Clean HTML for token efficiency."""
        import re
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
        html = re.sub(r'\s+', ' ', html)
        
        max_html_length = 800000 
        if len(html) > max_html_length:
            html = html[:max_html_length]
        return html

    def _generate_with_retry(self, prompt: str) -> list[dict]:
        """
        Helper to run generation with retry logic (key rotation).
        Returns parsed list of dicts.
        """
        if self.model is None:
            self._initialize_client()
            
        max_retries = len(config.GEMINI_API_KEYS)
        attempts = 0
        
        while attempts < max_retries:
            try:
                response = self.model.generate_content(prompt)
                return self._process_response(response)
                
            except Exception as e:
                error_str = str(e).lower()
                is_quota_error = "429" in error_str or "resourceexhausted" in error_str or "quota" in error_str
                is_auth_error = "403" in error_str or "permissiondenied" in error_str or "api_key" in error_str
                
                if is_quota_error or is_auth_error:
                    logger.warning(f"API Error (Attempt {attempts + 1}/{max_retries}): {e}")
                    if self._rotate_key():
                        attempts += 1
                        continue
                    else:
                        logger.error("Rotation failed or single key exhausted.")
                        break
                else:
                    logger.error(f"Non-rotation error during parsing: {e}")
                    break
        
        return []

    def _verify_integrity(self, jobs: list[dict], html_context: str) -> list[dict]:
        """
        Ask the AI to self-correct and verify the jobs exist in the HTML.
        """
        try:
            jobs_json = json.dumps(jobs, indent=2)
            prompt = self.VERIFICATION_PROMPT.format(jobs_json=jobs_json) + "\n\n" + html_context
            
            # Use the same retry logic for verification
            verified_jobs = self._generate_with_retry(prompt)
            
            # Fallback for empty return on verification (paranoid check)
            if not verified_jobs and jobs:
                logger.warning("Verification returned empty list. Assuming AI error and keeping original jobs (risky but safer than losing all).")
                return jobs
                
            return verified_jobs
        except Exception as e:
            logger.error(f"Verification check failed: {e}. Returning original jobs.")
            return jobs

    def _process_response(self, response, source_url=""):
        """Helper to process the raw Gemini response into job list."""
        try:
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            
            jobs = json.loads(text)
            return jobs
            
        except json.JSONDecodeError:
            logger.warning(f"JSON incomplete, attempting partial extraction...")
            return self._extract_partial_json(response.text)
        except Exception as e:
            logger.error(f"Error processing response: {e}")
            return []

    def _extract_partial_json(self, text):
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
            
            return jobs
        except Exception as e:
            logger.error(f"Partial extraction failed: {e}")
        return []
    
    def verify_job_page(self, html: str, job: dict) -> bool:
        """
        Verify that a job detail page actually matches the job.
        
        Args:
            html: HTML content of the job detail page.
            job: The job dictionary containing 'title' and 'company'.
            
        Returns:
            True if the page validates as a real job listing for this title.
        """
        if not html:
            return False
            
        clean_html = self._clean_html(html)
        title = job.get('title', 'Unknown')
        company = job.get('company', 'Unknown')
        
        prompt = self.VERIFY_PAGE_PROMPT.format(title=title, company=company) + "\n\n" + clean_html
        
        try:
            # Use retry logic
            response_list = self._generate_with_retry(prompt)
            # Response is expected to be a single dict, but _generate_with_retry returns list
            # We need to handle that or adjust _generate_with_retry
            # Actually _generate_with_retry returns parsed JSON (list or dict)
            # But the prompt asks for a SINGLE JSON object.
            # _process_response expects a list of jobs usually?
            # Let's override or check type.
            
            # Since _generate_with_retry returns result of _process_response -> returns list or dict
            result = response_list
            
            if isinstance(result, list) and result:
                result = result[0]
                
            if isinstance(result, dict) and result.get("valid") is True:
                return True
                
            logger.warning(f"Job validation failed for '{title}': {result.get('reason', 'Unknown reason')}")
            return False
            
        except Exception as e:
            logger.error(f"Error validating job page: {e}")
            return False  # Fail safe: if we can't verify, don't add strictly? Or add loosely? User wants EXTRA layer. So fail safe = reject.

    def parse_multiple(self, html_dict: dict[str, Optional[str]]) -> list[dict]:
        """Combine lists of all jobs from all pages."""
        all_jobs = []
        for url, html in html_dict.items():
            if html:
                jobs = self.parse(html, source_url=url)
                all_jobs.extend(jobs)
        return all_jobs


# Default parser instance
parser = Parser()
