"""
Gemini-powered HTML Parser for Job Pipeline Tracker.
Uses Gemini AI to extract structured job data from raw HTML.
"""

import json
import google.generativeai as genai
from typing import Optional
from config import config


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
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy initialization of Gemini client."""
        if not self._initialized:
            if not config.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY not configured")
            
            genai.configure(api_key=config.GEMINI_API_KEY)
            self.model = genai.GenerativeModel("gemini-2.5-flash-lite")
            self._initialized = True
    
    def parse(self, html: str, source_url: str = "") -> list[dict]:
        """
        Parse HTML and extract job listings using Gemini.
        
        Args:
            html: Raw HTML content
            source_url: The URL this HTML was fetched from (for context)
            
        Returns:
            List of job dictionaries
        """
        self._ensure_initialized()
        
        # Strip script and style tags to reduce size (job info is in visible HTML)
        import re
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)  # Remove comments
        html = re.sub(r'\s+', ' ', html)  # Collapse whitespace
        
        print(f"[Parser] HTML cleaned to {len(html)} chars")
        
        # Truncate if still too long (gemini-2.5-flash-lite can handle ~250K tokens)
        max_html_length = 800000  # ~800KB after cleaning
        if len(html) > max_html_length:
            html = html[:max_html_length]
            print(f"[Parser] HTML truncated to {max_html_length} chars")
        
        try:
            # Use string concatenation instead of .format() to avoid issues with {} in HTML
            prompt = self.EXTRACTION_PROMPT + "\n\n" + html
            response = self.model.generate_content(prompt)
            
            # Extract JSON from response
            text = response.text.strip()
            
            # Clean up response - remove markdown code blocks if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            
            jobs = json.loads(text)
            
            # Add source URL to each job for tracking
            for job in jobs:
                job["source_url"] = source_url
            
            print(f"[Parser] Extracted {len(jobs)} jobs from {source_url}")
            return jobs
            
        except json.JSONDecodeError as e:
            print(f"[Parser] JSON incomplete, attempting to extract partial results...")
            # Try to extract complete job objects from truncated response
            try:
                import re
                # More robust: find JSON objects by matching balanced braces
                text = response.text
                jobs = []
                
                # Find the start of the JSON array
                start = text.find('[')
                if start != -1:
                    # Try to parse each object individually
                    depth = 0
                    obj_start = None
                    i = start
                    
                    while i < len(text):
                        char = text[i]
                        if char == '{':
                            if depth == 0:
                                obj_start = i
                            depth += 1
                        elif char == '}':
                            depth -= 1
                            if depth == 0 and obj_start is not None:
                                # Found a complete object
                                obj_str = text[obj_start:i+1]
                                try:
                                    job = json.loads(obj_str)
                                    if 'title' in job:  # Validate it's a job object
                                        job["source_url"] = source_url
                                        jobs.append(job)
                                except json.JSONDecodeError:
                                    pass  # Malformed object, skip
                                obj_start = None
                        elif char == '"':
                            # Skip string content (handle escaped quotes)
                            i += 1
                            while i < len(text):
                                if text[i] == '\\':
                                    i += 2  # Skip escaped character
                                    continue
                                if text[i] == '"':
                                    break
                                i += 1
                        i += 1
                
                if jobs:
                    print(f"[Parser] Recovered {len(jobs)} jobs from partial response")
                    return jobs
                    
            except Exception as regex_error:
                print(f"[Parser] Extraction failed: {regex_error}")
            
            print(f"[Parser] Could not extract jobs. Response preview: {response.text[:300]}...")
            return []
            
        except Exception as e:
            print(f"[Parser] Error during parsing: {e}")
            # Print response if available for debugging
            try:
                print(f"[Parser] Raw response: {response.text[:1000]}...")
            except:
                pass
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
