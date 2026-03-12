from flask import Blueprint, jsonify
import logging
from app.services.cronService import get_cron_status

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix="/admin")


@admin_bp.route('/cron/status', methods=['GET'])
def get_cron_service_status():
    """Get the status of the cron service"""
    try:
        status = get_cron_status()
        return jsonify({
            "cron_service": status,
            "message": "Cron service status retrieved successfully"
        })
        
    except Exception as e:
        logger.error(f"Failed to get cron service status: {e}")
        return jsonify({"error": "Failed to get cron service status"}), 500
