import logging
from flask import Blueprint, request, jsonify, Response
from app.controller.webhook.webhookController import WebhookController

logger = logging.getLogger(__name__)

webhook_receiver_bp = Blueprint("webhook_receiver", __name__, url_prefix="/webhooks")


@webhook_receiver_bp.route("/receive/zoom", methods=["POST"])
def receive_zoom_webhook():
    """Receive Zoom webhook notifications"""
    try:
        result, status_code = WebhookController.dispatch("zoom", request)
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"Error processing Zoom webhook: {e}")
        return jsonify({"error": "Failed to process webhook"}), 500


@webhook_receiver_bp.route("/receive/microsoft", methods=["POST"])
def receive_microsoft_webhook():
    """Receive Microsoft Teams webhook notifications"""
    try:
        # Microsoft sends a GET with validationToken on subscription creation — must respond first
        validation_token = request.args.get("validationToken")
        if validation_token:
            return Response(validation_token, status=200, mimetype="text/plain")

        result, status_code = WebhookController.dispatch("microsoft", request)
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"Error processing Microsoft webhook: {e}")
        return jsonify({"error": "Failed to process webhook"}), 500


@webhook_receiver_bp.route("/receive/google", methods=["POST"])
def receive_google_webhook():
    """Receive Google Calendar webhook notifications"""
    try:
        channel_id = request.headers.get("X-Goog-Channel-ID")
        resource_state = request.headers.get("X-Goog-Resource-State")
        logger.info(
            f"Received Google webhook: channel={channel_id}, state={resource_state}"
        )

        result, status_code = WebhookController.dispatch("google", request)
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"Error processing Google webhook: {e}")
        return jsonify({"error": "Failed to process webhook"}), 500


@webhook_receiver_bp.route("/check-meetings", methods=["POST"])
def check_meetings_and_create_bots():
    """Schedule all pending jobs (useful for manual recovery)"""
    try:
        from app.services.schedulerService import scheduler_service

        scheduler_service.schedule_all_pending_jobs()
        return (
            jsonify(
                {"status": "success", "message": "All pending jobs have been scheduled"}
            ),
            200,
        )
    except Exception as e:
        logger.error(f"Error scheduling pending jobs: {e}")
        return jsonify({"error": "Failed to schedule pending jobs"}), 500


@webhook_receiver_bp.route("/scheduler/status", methods=["GET"])
def scheduler_status():
    """Get current scheduler status and scheduled jobs"""
    try:
        from app.services.schedulerService import scheduler_service

        if not scheduler_service.scheduler:
            return jsonify({"error": "Scheduler not initialized"}), 500

        jobs = scheduler_service.get_scheduled_jobs()
        job_info = [
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": (
                    job.next_run_time.isoformat() if job.next_run_time else None
                ),
                "trigger": str(job.trigger),
            }
            for job in jobs
        ]

        return (
            jsonify(
                {
                    "scheduler_running": scheduler_service.scheduler.running,
                    "total_jobs": len(jobs),
                    "jobs": job_info,
                }
            ),
            200,
        )
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        return jsonify({"error": "Failed to get scheduler status"}), 500


@webhook_receiver_bp.route("/ngrok/status", methods=["GET"])
def ngrok_status():
    """Check ngrok status and current webhook URL"""
    try:
        from app.utils.ngrokWebhookManager import NgrokWebhookManager

        return jsonify(NgrokWebhookManager.check_ngrok_status()), 200
    except Exception as e:
        logger.error(f"Error checking ngrok status: {e}")
        return jsonify({"error": "Failed to check ngrok status"}), 500


@webhook_receiver_bp.route("/ngrok/update-webhooks", methods=["POST"])
def update_ngrok_webhooks():
    """Update all webhook URLs to current ngrok URL"""
    try:
        from app.utils.ngrokWebhookManager import NgrokWebhookManager

        result = NgrokWebhookManager.update_all_webhook_urls()
        if "error" in result:
            return jsonify(result), 500
        return jsonify({"message": "Webhook URLs updated successfully", **result}), 200
    except Exception as e:
        logger.error(f"Error updating webhook URLs: {e}")
        return jsonify({"error": "Failed to update webhook URLs"}), 500


@webhook_receiver_bp.route("/ngrok/webhook-url/<platform>", methods=["GET"])
def get_webhook_url(platform: str):
    """Get current webhook URL for platform"""
    try:
        from app.utils.ngrokWebhookManager import NgrokWebhookManager

        return (
            jsonify(
                {
                    "platform": platform,
                    "webhook_url": NgrokWebhookManager.get_webhook_url(platform),
                    "base_url": NgrokWebhookManager.get_webhook_base_url(),
                }
            ),
            200,
        )
    except Exception as e:
        logger.error(f"Error getting webhook URL: {e}")
        return jsonify({"error": "Failed to get webhook URL"}), 500
