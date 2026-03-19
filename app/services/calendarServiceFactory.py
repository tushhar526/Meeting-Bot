"""
Improved Calendar Service Factory
Creates platform-specific calendar services with centralized timezone handling
"""

import logging
from typing import Dict, Type, List
from app.controller.calendar.base.baseCalendarService import BaseCalendarService
from app.controller.calendar.platform.microsoftCalendarService import MicrosoftCalendarService
from app.controller.calendar.platform.googleCalendarService import GoogleCalendarService
from app.controller.calendar.platform.zoomCalendarService import ZoomCalendarService

logger = logging.getLogger(__name__)

class CalendarServiceFactory:
    """Factory for creating platform-specific calendar services"""
    
    # Registry of available services
    _services: Dict[str, Type[BaseCalendarService]] = {
        'microsoft': MicrosoftCalendarService,
        'google': GoogleCalendarService,
        'zoom': ZoomCalendarService,
    }
    
    @classmethod
    def create_service(cls, platform: str) -> BaseCalendarService:
        """Create a calendar service for the specified platform"""
        try:
            if platform not in cls._services:
                raise ValueError(f"Unsupported platform: {platform}")
            
            service_class = cls._services[platform]
            service = service_class()
            
            logger.info(f"✅ Created {platform} calendar service: {type(service).__name__}")
            return service
            
        except Exception as e:
            logger.error(f"❌ Failed to create {platform} service: {e}")
            raise
    
    @classmethod
    def register_service(cls, platform: str, service_class: Type[BaseCalendarService]):
        """Register a new platform service"""
        cls._services[platform] = service_class
        logger.info(f"📝 Registered {platform} service: {service_class.__name__}")
    
    @classmethod
    def get_supported_platforms(cls) -> List[str]:
        """Get list of supported platforms"""
        return list(cls._services.keys())
    
    @classmethod
    def is_platform_supported(cls, platform: str) -> bool:
        """Check if a platform is supported"""
        return platform in cls._services
