import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

print("--- VERIFICATION START ---")

try:
    print("1. Checking 'laboral.py'...")
    from app.scrapers.laboral import get_events_laboral
    print("✅ 'laboral.py' imported successfully.")
except ImportError as e:
    print(f"❌ ImportError in laboral: {e}")
except NameError as e:
    print(f"❌ NameError in laboral: {e}")
except Exception as e:
    print(f"❌ Error importing laboral: {e}")

print("--- VERIFICATION END ---")
