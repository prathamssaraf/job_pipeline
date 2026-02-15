"""
Utility to clear jobs database (keeping sources/trackers).
Usage: python reset_jobs.py [-y]
"""
from storage import storage
import sys

def main():
    print("⚠️  CLEARING JOBS DATABASE ⚠️")
    print("This will remove all job listings.")
    print("Your Sources/Trackers (e.g., URLs) are SAFE and will NOT be deleted.")
    print("-" * 50)
    
    # Check for force flag
    if len(sys.argv) > 1 and sys.argv[1] == '-y':
        confirm = 'y'
    else:
        confirm = input("Are you sure you want to clear all jobs? (y/N): ").lower()
        
    if confirm == 'y':
        try:
            storage.clear_all(confirmation="DELETE_ALL_JOBS_PERMANENTLY")
            print("✅ Success: All jobs have been cleared.")
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print("❌ Operation cancelled.")

if __name__ == "__main__":
    main()
