from flask import Blueprint, jsonify
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix="/admin")
