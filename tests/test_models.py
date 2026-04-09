import pytest
from datetime import datetime, timezone, timedelta
from app.models.userModel import userModel, UserRole, SubscriptionStatus
from app.models.planModel import PlanModel
from app.models.jobModel import JobModel
from app.models.logModel import SystemLog
from app.models.summaryModel import SummaryModel
from app.models.transcriptionModel import TranscriptionsModel
from app.models.userIntegrationModel import UserIntegration
from app.models.webhookModel import WebhookModel


class TestUserModel:
    """Test cases for userModel"""
    
    def test_create_user(self, db_session):
        """Test creating a new user"""
        user = userModel(
            username="testuser",
            email="test@example.com",
            organization_name="Test Org"
        )
        user.set_password("password123")
        db_session.add(user)
        db_session.commit()
        
        assert user.user_id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == UserRole.ADMIN
        assert user.is_active is True
        assert user.is_deleted is False
    
    def test_password_hashing(self, db_session):
        """Test password hashing and verification"""
        user = userModel(username="testuser", email="test@example.com")
        user.set_password("password123")
        
        assert user.password != "password123"
        assert user.check_password("password123") is True
        assert user.check_password("wrongpassword") is False
    
    def test_user_roles(self, db_session):
        """Test user role methods"""
        admin_user = userModel(username="admin", email="admin@example.com", role=UserRole.ADMIN)
        super_admin_user = userModel(username="superadmin", email="super@example.com", role=UserRole.SUPER_ADMIN)
        
        assert admin_user.is_admin() is True
        assert admin_user.is_super_admin() is False
        assert super_admin_user.is_super_admin() is True
        assert super_admin_user.is_admin() is False
    
    def test_subscription_methods(self, db_session, sample_plan):
        """Test subscription related methods"""
        user = userModel(username="testuser", email="test@example.com")
        user.assign_plan(sample_plan)
        db_session.add(user)
        db_session.commit()
        
        # Test active subscription
        assert user.has_active_subscription() is True
        assert user.can_create_meeting() is True
        
        # Test expired subscription
        user.subscription_end_date = datetime.now(timezone.utc) - timedelta(days=1)
        db_session.commit()
        assert user.has_active_subscription() is False
        assert user.can_create_meeting() is False
    
    def test_soft_delete(self, db_session):
        """Test soft delete functionality"""
        user = userModel(username="testuser", email="test@example.com")
        db_session.add(user)
        db_session.commit()
        
        user.soft_delete()
        db_session.commit()
        
        assert user.is_deleted is True
        assert user.is_active is False
        assert user.deleted_at is not None
        
        # Test restore
        user.restore()
        db_session.commit()
        
        assert user.is_deleted is False
        assert user.is_active is True
        assert user.deleted_at is None
    
    def test_get_active_users(self, db_session):
        """Test getting active users only"""
        active_user = userModel(username="active", email="active@example.com")
        deleted_user = userModel(username="deleted", email="deleted@example.com")
        
        db_session.add(active_user)
        db_session.add(deleted_user)
        db_session.commit()
        
        deleted_user.soft_delete()
        db_session.commit()
        
        active_users = userModel.get_active_users().all()
        usernames = [user.username for user in active_users]
        
        assert "active" in usernames
        assert "deleted" not in usernames
    
    def test_get_by_email_or_username(self, db_session):
        """Test getting user by email or username"""
        user = userModel(username="testuser", email="test@example.com")
        db_session.add(user)
        db_session.commit()
        
        found_by_email = userModel.get_by_email_or_username("test@example.com")
        found_by_username = userModel.get_by_email_or_username("testuser")
        not_found = userModel.get_by_email_or_username("nonexistent")
        
        assert found_by_email is not None
        assert found_by_username is not None
        assert found_by_email.user_id == found_by_username.user_id
        assert not_found is None


class TestPlanModel:
    """Test cases for PlanModel"""
    
    def test_create_plan(self, db_session):
        """Test creating a new plan"""
        plan = PlanModel(
            name="Basic Plan",
            description="Basic plan description",
            price=29.99,
            duration_days=30,
            max_meetings=50
        )
        db_session.add(plan)
        db_session.commit()
        
        assert plan.plan_id is not None
        assert plan.name == "Basic Plan"
        assert plan.price == 29.99
        assert plan.max_meetings == 50


class TestJobModel:
    """Test cases for JobModel"""
    
    def test_create_job(self, db_session, sample_user):
        """Test creating a new job"""
        job = JobModel(
            user_id=sample_user.user_id,
            job_type="transcription",
            status="pending",
            file_path="/path/to/file.mp3"
        )
        db_session.add(job)
        db_session.commit()
        
        assert job.job_id is not None
        assert job.user_id == sample_user.user_id
        assert job.job_type == "transcription"
        assert job.status == "pending"


class TestSystemLog:
    """Test cases for SystemLog"""
    
    def test_create_log(self, db_session, sample_user):
        """Test creating a new system log"""
        log = SystemLog(
            user_id=sample_user.user_id,
            action="login",
            details="User logged in successfully",
            level="INFO"
        )
        db_session.add(log)
        db_session.commit()
        
        assert log.log_id is not None
        assert log.user_id == sample_user.user_id
        assert log.action == "login"
        assert log.level == "INFO"


class TestSummaryModel:
    """Test cases for SummaryModel"""
    
    def test_create_summary(self, db_session, sample_user):
        """Test creating a new summary"""
        summary = SummaryModel(
            user_id=sample_user.user_id,
            meeting_title="Test Meeting",
            summary_content="This is a test summary",
            meeting_date=datetime.now(timezone.utc)
        )
        db_session.add(summary)
        db_session.commit()
        
        assert summary.summary_id is not None
        assert summary.user_id == sample_user.user_id
        assert summary.meeting_title == "Test Meeting"


class TestTranscriptionModel:
    """Test cases for TranscriptionsModel"""
    
    def test_create_transcription(self, db_session, sample_user):
        """Test creating a new transcription"""
        transcription = TranscriptionsModel(
            user_id=sample_user.user_id,
            file_name="meeting.mp3",
            file_path="/path/to/meeting.mp3",
            transcription_text="This is the transcribed text"
        )
        db_session.add(transcription)
        db_session.commit()
        
        assert transcription.transcription_id is not None
        assert transcription.user_id == sample_user.user_id
        assert transcription.file_name == "meeting.mp3"


class TestUserIntegration:
    """Test cases for UserIntegration"""
    
    def test_create_integration(self, db_session, sample_user):
        """Test creating a new user integration"""
        integration = UserIntegration(
            user_id=sample_user.user_id,
            service_type="google_calendar",
            access_token="access_token_123",
            refresh_token="refresh_token_123"
        )
        db_session.add(integration)
        db_session.commit()
        
        assert integration.integration_id is not None
        assert integration.user_id == sample_user.user_id
        assert integration.service_type == "google_calendar"


class TestWebhookModel:
    """Test cases for WebhookModel"""
    
    def test_create_webhook(self, db_session, sample_user):
        """Test creating a new webhook"""
        webhook = WebhookModel(
            user_id=sample_user.user_id,
            webhook_url="https://example.com/webhook",
            event_type="meeting_completed"
        )
        db_session.add(webhook)
        db_session.commit()
        
        assert webhook.webhook_id is not None
        assert webhook.user_id == sample_user.user_id
        assert webhook.webhook_url == "https://example.com/webhook"
