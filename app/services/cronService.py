import logging
import threading
import time
from datetime import datetime
from app.services.webhookScheduler import WebhookScheduler

logger = logging.getLogger(__name__)


class CronService:
    def __init__(self, app=None):
        self.webhook_scheduler = WebhookScheduler()
        self.running = False
        self.thread = None
        self.check_interval = 60  # Check every minute
        self.app = app
    
    def set_app(self, app):
        """Set Flask app instance"""
        self.app = app
    
    def start(self):
        """Start cron service"""
        if self.running:
            logger.warning("Cron service is already running")
            return
        
        if not self.app:
            logger.error("Flask app not set. Call set_app() first.")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("Cron service started")
    
    def stop(self):
        """Stop the cron service"""
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("Cron service stopped")
    
    def _run(self):
        """Main cron loop"""
        while self.running:
            try:
                logger.debug("Running cron job check...")
                
                # Run within application context
                with self.app.app_context():
                    self.webhook_scheduler.check_calendar_webhooks()
                
            except Exception as e:
                logger.error(f"Error in cron service: {e}")
            
            # Sleep for the specified interval
            time.sleep(self.check_interval)
    
    def set_check_interval(self, seconds: int):
        """Set the check interval in seconds"""
        self.check_interval = seconds
        logger.info(f"Cron check interval set to {seconds} seconds")


# Global cron service instance
cron_service = CronService()


def start_cron_service():
    """Start the global cron service"""
    cron_service.start()


def stop_cron_service():
    """Stop the global cron service"""
    cron_service.stop()


def get_cron_status():
    """Get the status of the cron service"""
    return {
        "running": cron_service.running,
        "check_interval": cron_service.check_interval,
        "thread_alive": cron_service.thread.is_alive() if cron_service.thread else False
    }


def initialize_cron_service(app):
    """Initialize cron service with Flask app"""
    cron_service.set_app(app)
