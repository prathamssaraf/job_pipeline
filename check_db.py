"""Quick database inspection script"""
import sqlite3

conn = sqlite3.connect('jobs.db')
conn.row_factory = sqlite3.Row

print("=" * 60)
print("DATABASE INSPECTION")
print("=" * 60)

# Total jobs
total_jobs = conn.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]
print(f"\n📊 Total jobs in database: {total_jobs}")

# Source stats from sources table
print("\n📋 Sources table (what dashboard shows):")
print("-" * 60)
sources = conn.execute('SELECT id, name, url, job_count, last_checked FROM sources').fetchall()
for s in sources:
    print(f"  [{s['id']}] {s['name']}")
    print(f"      Stored count: {s['job_count']} jobs")
    print(f"      Last checked: {s['last_checked']}")
    print()

# Actual job counts
print("\n🔍 Actual jobs in database per source:")
print("-" * 60)
for s in sources:
    actual_count = conn.execute(
        'SELECT COUNT(*) FROM jobs WHERE source_url LIKE ?',
        (f"%{s['url']}%",)
    ).fetchone()[0]
    
    stored_count = s['job_count']
    status = "✅ MATCH" if actual_count == stored_count else "❌ MISMATCH"
    
    print(f"  {s['name']}: {actual_count} actual jobs | {stored_count} stored count | {status}")

# Recent jobs
print("\n📅 Recent jobs (last 5):")
print("-" * 60)
recent = conn.execute(
    'SELECT title, company, source_url, first_seen FROM jobs ORDER BY first_seen DESC LIMIT 5'
).fetchall()
for job in recent:
    print(f"  • {job['title']} at {job['company']}")
    print(f"    Added: {job['first_seen']}")

conn.close()
print("\n" + "=" * 60)
