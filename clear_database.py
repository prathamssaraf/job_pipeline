"""
Clear all jobs from the database.
This will remove all existing job entries to start fresh with the new deduplication logic.
"""

from storage import storage

print("\n" + "="*80)
print("  ⚠️  DATABASE CLEARING UTILITY")
print("="*80)

# Get current count
total_jobs = storage.get_job_count()
print(f"\nCurrent jobs in database: {total_jobs}")

if total_jobs == 0:
    print("\n✅ Database is already empty. Nothing to clear.")
    exit(0)

print("\n⚠️  WARNING: This will permanently delete ALL job records!")
print("   This action cannot be undone.\n")

# Require confirmation
confirmation = input("Type 'DELETE_ALL_JOBS_PERMANENTLY' to confirm: ")

if confirmation == "DELETE_ALL_JOBS_PERMANENTLY":
    print("\n🗑️  Clearing database...")
    try:
        storage.clear_all(confirmation="DELETE_ALL_JOBS_PERMANENTLY")
        remaining = storage.get_job_count()
        print(f"\n✅ Database cleared successfully!")
        print(f"   Jobs remaining: {remaining}")
        print("\n💡 Next steps:")
        print("   1. The new deduplication logic is now active")
        print("   2. Run the pipeline to fetch fresh jobs")
        print("   3. No more duplicates from inconsistent company names!")
    except Exception as e:
        print(f"\n❌ Error clearing database: {e}")
else:
    print("\n❌ Confirmation failed. Database NOT cleared.")
    print(f"   You entered: '{confirmation}'")
    print(f"   Required: 'DELETE_ALL_JOBS_PERMANENTLY'")

print("\n" + "="*80 + "\n")
