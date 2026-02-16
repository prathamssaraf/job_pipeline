"""
Job Pipeline Tracker - Web Dashboard Server
Flask API for managing job sources and viewing tracked jobs.
"""


import threading
import time
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from logger import get_logger
from storage import storage
from unified_fetcher import unified_fetcher, JobSource
from parser import parser
from notifier import notifier

logger = get_logger(__name__)

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)

# Scheduler state
scheduler_state = {
    "running": False,
    "interval_minutes": 60,  # Default 1 hour
    "last_run": None,
    "next_run": None,
    "thread": None,
    "checks_today": 0,
    "changes_detected_today": 0,
    "last_reset": datetime.now().date()
}


# ============================================================
# API ROUTES
# ============================================================

@app.route('/')
def index():
    """Serve the dashboard."""
    return send_from_directory('static', 'index.html')


@app.route('/styles.css')
def serve_css():
    """Serve CSS file."""
    return send_from_directory('static', 'styles.css')


@app.route('/app.js')
def serve_js():
    """Serve JavaScript file."""
    return send_from_directory('static', 'app.js')


@app.route('/api/sources', methods=['GET'])
def get_sources():
    """Get all job sources."""
    sources = storage.get_sources()
    return jsonify(sources)


@app.route('/api/sources', methods=['POST'])
def add_source():
    """Add a new job source."""
    data = request.json
    if not data.get('url'):
        return jsonify({"error": "URL is required"}), 400
    
    source = {
        "name": data.get('name', ''),
        "url": data['url'],
        "requires_browser": data.get('requires_browser', True)
    }
    
    source_id = storage.add_source(source)
    return jsonify({"id": source_id, "message": "Source added"})


@app.route('/api/sources/<source_id>', methods=['DELETE'])
def delete_source(source_id):
    """Delete a job source."""
    storage.delete_source(source_id)
    return jsonify({"message": "Source deleted"})


@app.route('/api/jobs', methods=['GET'])
def get_jobs():
    """Get all tracked jobs."""
    limit = request.args.get('limit', 100, type=int)
    jobs = storage.get_all_jobs(limit=limit)
    return jsonify(jobs)


@app.route('/api/jobs/by-source', methods=['GET'])
def get_jobs_by_source():
    """Get jobs grouped by source."""
    sources = storage.get_sources()
    jobs = storage.get_all_jobs(limit=500)
    
    result = []
    for source in sources:
        source_jobs = [j for j in jobs if source['url'] in (j.get('source_url') or '')]
        result.append({
            "source": source,
            "jobs": source_jobs
        })
    
    # Also include jobs with unknown source
    known_urls = [s['url'] for s in sources]
    unknown_jobs = [j for j in jobs if not any(url in (j.get('source_url') or '') for url in known_urls)]
    if unknown_jobs:
        result.append({
            "source": {"id": 0, "name": "Other Sources", "url": ""},
            "jobs": unknown_jobs
        })
    
    return jsonify(result)


@app.route('/api/companies', methods=['GET'])
def get_companies():
    """Get unique company names from all jobs."""
    jobs = storage.get_all_jobs(limit=1000)
    companies = sorted(set(j.get('company', 'Unknown') for j in jobs if j.get('company')))
    return jsonify(companies)


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get dashboard statistics."""
    # Reset daily stats if it's a new day
    if scheduler_state["last_reset"] != datetime.now().date():
        scheduler_state["checks_today"] = 0
        scheduler_state["changes_detected_today"] = 0
        scheduler_state["last_reset"] = datetime.now().date()

    return jsonify({
        "total_jobs": storage.get_job_count(),
        "total_sources": storage.get_source_count(),
        "last_run": scheduler_state["last_run"],
        "next_run": scheduler_state["next_run"],
        "scheduler_running": scheduler_state["running"],
        "interval_minutes": scheduler_state["interval_minutes"],
        "checks_today": scheduler_state["checks_today"],
        "changes_detected": scheduler_state["changes_detected_today"]
    })


@app.route('/api/run', methods=['POST'])
def run_pipeline():
    """Manually trigger the pipeline."""
    result = run_pipeline_once()
    return jsonify(result)


@app.route('/api/scheduler', methods=['POST'])
def update_scheduler():
    """Update scheduler settings."""
    data = request.json
    interval = data.get('interval_minutes', 60)
    enabled = data.get('enabled', True)
    
    scheduler_state["interval_minutes"] = interval
    
    if enabled and not scheduler_state["running"]:
        start_scheduler()
    elif not enabled and scheduler_state["running"]:
        stop_scheduler()
    
    return jsonify({
        "message": "Scheduler updated",
        "interval_minutes": interval,
        "running": scheduler_state["running"]
    })


# ============================================================
# PIPELINE LOGIC
# ============================================================

def run_pipeline_once():
    """Run the job tracking pipeline once."""
    logger.info(f"Running pipeline at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Reset daily stats if it's a new day
    if scheduler_state["last_reset"] != datetime.now().date():
        scheduler_state["checks_today"] = 0
        scheduler_state["changes_detected_today"] = 0
        scheduler_state["last_reset"] = datetime.now().date()
        
    scheduler_state["checks_today"] += 1
    
    sources = storage.get_sources()
    if not sources:
        return {"success": False, "message": "No sources configured", "new_jobs": 0}
    
    # Convert to JobSource objects
    job_sources = [
        JobSource(
            url=s['url'],
            name=s['name'],
            requires_browser=s.get('requires_browser', True)
        ) for s in sources
    ]
    
    # Fetch HTML
    html_dict = unified_fetcher.fetch_multiple(job_sources)
    successful = sum(1 for h in html_dict.values() if h)
    
    if successful == 0:
        return {"success": False, "message": "Failed to fetch any sources", "new_jobs": 0}
    
    # Parse jobs
    all_jobs = parser.parse_multiple(html_dict)
    
    # Find new jobs
    new_candidates = storage.find_new_jobs(all_jobs)
    
    # Deep Verification Layer
    verified_jobs = []
    if new_candidates:
        logger.info(f"🔍 Deep Verification: Checking {len(new_candidates)} new candidates...")
        
        for job in new_candidates:
            url = job.get('url')
            if not url:
                continue
                
            try:
                # Fetch detail page to confirm existence and content
                # passing requires_browser=False for speed, assuming detail pages are largely static
                detail_html = unified_fetcher.fetch(url, requires_browser=False)
                
                if parser.verify_job_page(detail_html, job):
                    verified_jobs.append(job)
                    logger.info(f"✅ Verified: {job['title']}")
                else:
                    logger.warning(f"❌ Rejected: {job['title']} (Detail Page Verification Failed)")
                    
            except Exception as e:
                logger.error(f"⚠️ Verification error for {job.get('title')}: {e}")
                
    # Save verified jobs and notify
    if verified_jobs:
        storage.save_jobs(verified_jobs)
        notifier.send(verified_jobs)
        scheduler_state["changes_detected_today"] += len(verified_jobs)
    
    # Update source stats - FIXED: Now outside 'if new_jobs' block
    # Only update stats for sources that successfully fetched
    for source in sources:
        source_url = source['url']
        
        # Check if this source was successfully fetched
        if html_dict.get(source_url) is not None:
            # Count jobs from this source in the parsed results
            job_count_this_run = sum(1 for j in all_jobs if source_url in j.get('source_url', ''))
            
            # Update stats only for successful fetches
            # This prevents overwriting with 0 when a source fails
            storage.update_source_stats(source['id'], job_count_this_run)
            logger.info(f"Updated {source['name']}: {job_count_this_run} jobs found in this run")
        else:
            # Source failed to fetch - leave stats unchanged
            logger.warning(f"Skipped stats update for {source['name']} (fetch failed)")
    
    scheduler_state["last_run"] = datetime.now().isoformat()
    # forced sync trigger
    
    return {
        "success": True,
        "message": f"Found {len(verified_jobs)} new jobs",
        "new_jobs": len(verified_jobs),
        "total_parsed": len(all_jobs),
        "sources_checked": len(sources),
        "sources_successful": successful
    }


# ============================================================
# SCHEDULER
# ============================================================

def scheduler_loop():
    """Background scheduler loop."""
    while scheduler_state["running"]:
        # Calculate next run
        interval_seconds = scheduler_state["interval_minutes"] * 60
        next_run = datetime.now().timestamp() + interval_seconds
        scheduler_state["next_run"] = datetime.fromtimestamp(next_run).isoformat()
        
        # Wait for interval
        time.sleep(interval_seconds)
        
        if scheduler_state["running"]:
            try:
                run_pipeline_once()
            except Exception as e:
                logger.error(f"Scheduler error: {e}", exc_info=True)


def start_scheduler():
    """Start the background scheduler."""
    if not scheduler_state["running"]:
        scheduler_state["running"] = True
        scheduler_state["thread"] = threading.Thread(target=scheduler_loop, daemon=True)
        scheduler_state["thread"].start()
        logger.info(f"Scheduler started - running every {scheduler_state['interval_minutes']} minutes")


def stop_scheduler():
    """Stop the background scheduler."""
    scheduler_state["running"] = False
    scheduler_state["next_run"] = None
    logger.info("Scheduler stopped")


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("Job Pipeline Tracker - Dashboard")
    logger.info("http://localhost:5000")
    logger.info("=" * 70)
    
    # Start scheduler by default
    start_scheduler()
    
    app.run(host='0.0.0.0', debug=True, port=5000, use_reloader=False)
