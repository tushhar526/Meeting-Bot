from datetime import datetime, timezone
import pytz


def get_ist_now():
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(timezone.utc).astimezone(ist).replace(tzinfo=None)

def format_ist_datetime(dt):
    """Format datetime in readable IST format for frontend"""
    if dt is None:
        return None
    # If datetime is naive (no timezone), assume it's already in IST
    if dt.tzinfo is None:
        ist = pytz.timezone("Asia/Kolkata")
        dt = ist.localize(dt)
    return dt.strftime("%d-%m-%Y %I:%M %p")