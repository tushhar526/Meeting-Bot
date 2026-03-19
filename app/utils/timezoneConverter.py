"""
Centralized Timezone Utilities
Handles all UTC to IST conversions in one place
"""

import logging
from datetime import datetime, timezone
import pytz

logger = logging.getLogger(__name__)

class TimezoneConverter:
    """Centralized timezone conversion utility"""
    
    @staticmethod
    def convert_to_ist_or_keep(event_datetime_str: str, event_timezone: str = None) -> str:
        """Convert datetime to IST if not already in IST, otherwise keep as-is"""
        try:
            if not event_datetime_str:
                return event_datetime_str
            
            # Clean up the datetime string - handle Microsoft 7-digit microseconds
            clean_datetime_str = TimezoneConverter._clean_datetime_string(event_datetime_str)
            
            # Parse the datetime
            dt = TimezoneConverter._parse_datetime(clean_datetime_str)
            
            if dt is None:
                return event_datetime_str
            
            # If naive, assume UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
                logger.info(f"🌍 Naive datetime, assuming UTC: {dt}")
            
            # Convert to IST
            ist = pytz.timezone('Asia/Kolkata')
            dt_ist = dt.astimezone(ist)
            # Return timezone-aware ISO format string
            result = dt_ist.isoformat()
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error converting datetime to IST: {e}")
            logger.error(f"🔍 Input was: {event_datetime_str}, timezone: {event_timezone}")
            return event_datetime_str
    
    @staticmethod
    def _clean_datetime_string(datetime_str: str) -> str:
        """Clean datetime string for parsing"""
        if '.' in datetime_str:
            # Handle Microsoft 7-digit microseconds
            parts = datetime_str.split('.')
            if len(parts) > 1:
                microsecond_part = parts[1]
                if 'Z' in microsecond_part:
                    # Microsoft format: 2026-03-16T13:00:00.0000000Z
                    microsecond_digits = microsecond_part.replace('Z', '')[:6]
                    return parts[0] + '.' + microsecond_digits + 'Z'
                else:
                    # Standard format: 2026-03-16T13:00:00.0000000
                    microsecond_digits = microsecond_part[:6]
                    return parts[0] + '.' + microsecond_digits
        return datetime_str
    
    @staticmethod
    def _parse_datetime(datetime_str: str) -> datetime:
        """Parse datetime string with various formats"""
        try:
            if 'T' in datetime_str:
                if datetime_str.endswith('Z'):
                    return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                else:
                    return datetime.fromisoformat(datetime_str)
            else:
                return datetime.fromisoformat(datetime_str)
        except ValueError:
            logger.error(f"❌ Failed to parse datetime: {datetime_str}")
            return None
    
    @staticmethod
    def convert_to_utc_for_api(event_datetime_str: str, event_timezone: str = None) -> str:
        """Convert datetime string to UTC ISO format for API calls"""
        try:
            if not event_datetime_str:
                return event_datetime_str
            
            # Parse the datetime
            dt = TimezoneConverter._parse_datetime(event_datetime_str)
            if dt is None:
                return event_datetime_str
            
            # If naive, assume UTC
            if dt.tzinfo is None:
                if event_timezone and 'Asia/Kolkata' in event_timezone:
                    # Convert from IST to UTC
                    ist = pytz.timezone('Asia/Kolkata')
                    dt = ist.localize(dt)
                else:
                    # Assume UTC
                    dt = dt.replace(tzinfo=timezone.utc)
            
            # Convert to UTC
            dt_utc = dt.astimezone(timezone.utc)
            return dt_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
            
        except Exception as e:
            logger.error(f"❌ Error converting datetime to UTC: {e}")
            return event_datetime_str
