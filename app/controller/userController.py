from app.models.userModel import userModel
from app.models.jobModel import JobModel, get_ist_now
from flask import jsonify
from app.extension import db
from flask_jwt_extended import get_jwt_identity
from datetime import datetime, timedelta
from sqlalchemy import func, extract
import calendar


def get_user_profile(user_id):
    user = userModel.query.filter_by(user_id=user_id).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    return (
        jsonify(
            {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "created_at": (
                    user.created_at.isoformat()
                    if hasattr(user, "created_at") and user.created_at
                    else None
                ),
            }
        ),
        200,
    )


def update_user_profile(user_id, request):
    user = userModel.query.filter_by(user_id=user_id).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.json

    # Update username if provided
    if "username" in data:
        if not data["username"] or len(data["username"].strip()) < 3:
            return (
                jsonify({"error": "Username must be at least 3 characters long"}),
                400,
            )
        user.username = data["username"].strip()

    # Update email if provided
    if "email" in data:
        if not data["email"] or "@" not in data["email"]:
            return jsonify({"error": "Valid email is required"}), 400

        # Check if email is already taken by another user
        existing_user = userModel.query.filter(
            userModel.email == data["email"], userModel.user_id != user_id
        ).first()
        if existing_user:
            return jsonify({"error": "Email is already taken"}), 400

        user.email = data["email"].strip()

    db.session.commit()

    return (
        jsonify(
            {
                "message": "Profile updated successfully",
                "user": {
                    "user_id": user.user_id,
                    "username": user.username,
                    "email": user.email,
                },
            }
        ),
        200,
    )


def change_password(user_id, request):
    user = userModel.query.filter_by(user_id=user_id).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.json

    current_password = data.get("current_password")
    new_password = data.get("new_password")

    if not current_password or not new_password:
        return jsonify({"error": "Current password and new password are required"}), 400

    # Verify current password
    if not user.check_password(current_password):
        return jsonify({"error": "Current password is incorrect"}), 400

    # Validate new password
    if len(new_password) < 6:
        return (
            jsonify({"error": "New password must be at least 6 characters long"}),
            400,
        )

    # Update password
    user.set_password(new_password)
    db.session.commit()

    return jsonify({"message": "Password changed successfully"}), 200


def delete_user_account(user_id):
    user = userModel.query.filter_by(user_id=user_id).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    # Delete user (this will also delete associated jobs due to cascade)
    db.session.delete(user)
    db.session.commit()

    return jsonify({"message": "Account deleted successfully"}), 200


# Legacy functions for backward compatibility
def get_all_bot_details(request):
    pass


def get_bot_detail(request):
    pass


def get_user_analytics(user_id):
    """Get comprehensive analytics for user's meetings"""

    # Total meetings
    total_meetings = JobModel.query.filter_by(user_id=user_id).count()

    # Completed meetings (with duration data)
    completed_meetings = (
        JobModel.query.filter_by(user_id=user_id, status="Completed")
        .filter(JobModel.started_at.isnot(None), JobModel.ended_at.isnot(None))
        .all()
    )

    # Calculate average meeting duration
    total_duration = timedelta()
    meeting_count = 0

    for job in completed_meetings:
        if job.started_at and job.ended_at:
            duration = job.ended_at - job.started_at
            total_duration += duration
            meeting_count += 1

    avg_duration_hours = 0
    if meeting_count > 0:
        avg_duration_seconds = total_duration.total_seconds() / meeting_count
        avg_duration_hours = round(avg_duration_seconds / 3600, 2)

    # This week's meetings
    now = get_ist_now()
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    this_week_meetings = (
        JobModel.query.filter_by(user_id=user_id)
        .filter(JobModel.created_at >= week_start)
        .count()
    )

    # This month's meetings
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    this_month_meetings = (
        JobModel.query.filter_by(user_id=user_id)
        .filter(JobModel.created_at >= month_start)
        .count()
    )

    # Meetings by day of week (for all time)
    meetings_by_day = (
        db.session.query(
            extract("dow", JobModel.created_at).label("day_of_week"),
            func.count(JobModel.job_id).label("count"),
        )
        .filter_by(user_id=user_id)
        .group_by(extract("dow", JobModel.created_at))
        .all()
    )

    # Convert to readable format (0=Sunday, 1=Monday, etc.)
    day_names = [
        "Sunday",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
    ]
    meetings_by_day_dict = {}

    for day_num, count in meetings_by_day:
        day_name = day_names[int(day_num)]
        meetings_by_day_dict[day_name] = count

    # Ensure all days are present
    for day in day_names:
        if day not in meetings_by_day_dict:
            meetings_by_day_dict[day] = 0

    # Platform distribution
    platform_stats = (
        db.session.query(JobModel.platform, func.count(JobModel.job_id).label("count"))
        .filter_by(user_id=user_id)
        .group_by(JobModel.platform)
        .all()
    )

    platform_distribution = {platform: count for platform, count in platform_stats}

    # Recent meetings (last 10)
    recent_meetings = (
        JobModel.query.filter_by(user_id=user_id)
        .order_by(JobModel.created_at.desc())
        .limit(10)
        .all()
    )

    recent_meetings_data = []
    for job in recent_meetings:
        meeting_data = {
            "job_id": job.job_id,
            "meeting_url": job.job_url,
            "platform": job.platform,
            "status": job.status,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None,
        }

        # Calculate duration if available
        if job.started_at and job.ended_at:
            duration = job.ended_at - job.started_at
            meeting_data["duration_hours"] = round(duration.total_seconds() / 3600, 2)

        recent_meetings_data.append(meeting_data)

    return (
        jsonify(
            {
                "total_meetings": total_meetings,
                "completed_meetings": len(completed_meetings),
                "average_duration_hours": avg_duration_hours,
                "this_week_meetings": this_week_meetings,
                "this_month_meetings": this_month_meetings,
                "meetings_by_day": meetings_by_day_dict,
                "platform_distribution": platform_distribution,
                "recent_meetings": recent_meetings_data,
                "analytics_period": {
                    "week_start": week_start.isoformat(),
                    "month_start": month_start.isoformat(),
                    "current_date": now.isoformat(),
                },
            }
        ),
        200,
    )


def get_meeting_trends(user_id, days=30):
    """Get meeting trends over specified number of days"""

    end_date = get_ist_now()
    start_date = end_date - timedelta(days=days)

    # Daily meeting counts
    daily_meetings = (
        db.session.query(
            func.date(JobModel.created_at).label("date"),
            func.count(JobModel.job_id).label("count"),
        )
        .filter_by(user_id=user_id)
        .filter(JobModel.created_at >= start_date, JobModel.created_at <= end_date)
        .group_by(func.date(JobModel.created_at))
        .order_by("date")
        .all()
    )

    # Convert to dict with all dates
    trends_data = {}
    current_date = start_date.date()

    while current_date <= end_date.date():
        trends_data[current_date.isoformat()] = 0
        current_date += timedelta(days=1)

    # Fill in actual counts
    for date_str, count in daily_meetings:
        trends_data[date_str] = count

    return (
        jsonify(
            {
                "period_days": days,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "daily_trends": trends_data,
                "total_meetings_in_period": sum(trends_data.values()),
                "average_per_day": round(sum(trends_data.values()) / days, 2),
            }
        ),
        200,
    )
