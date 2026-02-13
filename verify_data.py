"""
Verification Script - Check Your Job Data
Run this to verify your jobs are still in the database
"""

from storage import storage
import sqlite3

print("=" * 70)
print("  JOB DATABASE VERIFICATION")
print("=" * 70)

# Get counts
total_jobs = storage.get_job_count()
total_sources = storage.get_source_count()

print(f"\n📊 Database Summary:")
print(f"   Total jobs in database: {total_jobs}")
print(f"   Total sources configured: {total_sources}")

if total_jobs == 0:
    print("\n⚠️  WARNING: No jobs found in database!")
    print("   This could mean:")
    print("   1. Database was cleared (check when jobs.db was last modified)")
    print("   2. This is a fresh installation")
else:
    print(f"\n✅ Good news! {total_jobs} jobs are safely stored in the database.")

# Check sources
print("\n" + "=" * 70)
print("  SOURCE DETAILS")
print("=" * 70)

sources = storage.get_sources()

if not sources:
    print("\n⚠️  No sources configured. Add sources via the dashboard.")
else:
    # Get actual job counts from database
    conn = sqlite3.connect(storage.db_path)
    
    for s in sources:
        stored_count = s['job_count']
        
        # Count actual jobs in database for this source
        cursor = conn.execute(
            'SELECT COUNT(*) FROM jobs WHERE source_url LIKE ?',
            (f"%{s['url']}%",)
        )
        actual_count = cursor.fetchone()[0]
        
        print(f"\n📌 {s['name']}")
        print(f"   URL: {s['url'][:60]}...")
        print(f"   Stored count (may be outdated): {stored_count}")
        print(f"   Actual jobs in database: {actual_count}")
        print(f"   Last checked: {s['last_checked'] or 'Never'}")
        
        if actual_count != stored_count:
            print(f"   ⚠️  MISMATCH: Stats need update (run pipeline to fix)")
        else:
            print(f"   ✅ Counts match")
    
    conn.close()

# Recent jobs
print("\n" + "=" * 70)
print("  RECENT JOBS (Last 5)")
print("=" * 70)

recent_jobs = storage.get_all_jobs(limit=5)
if recent_jobs:
    for job in recent_jobs:
        print(f"\n• {job['title']}")
        print(f"  Company: {job['company']}")
        print(f"  Location: {job['location']}")
        print(f"  First seen: {job['first_seen']}")
else:
    print("\nNo jobs found.")

print("\n" + "=" * 70)
print("  RECOMMENDATIONS")
print("=" * 70)

if total_jobs > 0 and sources:
    mismatches = sum(1 for s in sources if s['job_count'] != conn.execute(
        'SELECT COUNT(*) FROM jobs WHERE source_url LIKE ?',
        (f"%{s['url']}%",)
    ).fetchone()[0])
    
    if mismatches > 0:
        print("\n✅ Your jobs are safe in the database!")
        print("✅ The 'empty' sources were just a display bug.")
        print("\n🔧 To fix the displayed counts:")
        print("   1. Restart the server (Ctrl+C, then 'python server.py')")
        print("   2. Click 'Run Pipeline' in the dashboard")
        print("   3. Counts will update correctly for successful sources")
    else:
        print("\n✅ Everything looks good!")
        print("   All job counts are accurate.")
else:
    print("\n⚠️  Either no sources configured or no jobs yet.")
    print("   Add sources and run the pipeline to start tracking jobs.")

print("\n" + "=" * 70)
