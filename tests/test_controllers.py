import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import jsonify, request
from datetime import datetime, timezone, timedelta
from app.controller.authController import signup, login
from app.controller.userController import get_user_profile, update_user_profile
from app.models.userModel import userModel, UserRole, SubscriptionStatus
from app.models.planModel import PlanModel


class TestAuthController:
    """Test cases for authentication controller"""

    def test_signup_success(self, app, db_session):
        """Test successful user signup"""
        with app.test_request_context(
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "visH@234",
                "organization_name": "New Org",
            }
        ):
            with patch("app.controller.authController.db.session.commit"):
                response, status_code = signup(request)
                assert status_code == 201

    def test_signup_existing_username(self, app, db_session, sample_user):
        """Test signup with existing username"""
        with app.test_request_context(
            json={
                "username": "testuser",  # Already exists
                "email": "newemail@example.com",
                "password": "password123",
                "organization_name": "New Org",
            }
        ):
            response, status_code = signup(Mock())

            assert status_code == 400
            assert "Username already exists" in response.json["message"]

    def test_signup_existing_email(self, app, db_session, sample_user):
        """Test signup with existing email"""
        with app.test_request_context(
            json={
                "username": "newuser",
                "email": "test@example.com",  # Already exists
                "password": "password123",
                "organization_name": "New Org",
            }
        ):
            response, status_code = signup(Mock())

            assert status_code == 400
            assert "Email already exists" in response.json["message"]

    def test_signup_missing_organization(self, app, db_session):
        """Test signup without organization name"""
        with app.test_request_context(
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "password123",
                "organization_name": "",
            }
        ):
            response, status_code = signup(Mock())

            assert status_code == 400
            assert "Organization name is required" in response.json["message"]

    def test_login_success(self, app, db_session, sample_user):
        """Test successful user login"""
        with app.test_request_context(
            json={"username": "testuser", "password": "testpassword"}
        ):
            with patch(
                "app.controller.authController.create_access_token"
            ) as mock_access_token, patch(
                "app.controller.authController.create_refresh_token"
            ) as mock_refresh_token, patch(
                "app.controller.authController.set_access_cookies"
            ), patch(
                "app.controller.authController.set_refresh_cookies"
            ), patch(
                "app.controller.authController.db.session.commit"
            ):

                mock_access_token.return_value = "access_token"
                mock_refresh_token.return_value = "refresh_token"

                response, status_code = login(Mock())

                assert status_code == 200
                mock_access_token.assert_called_once()
                mock_refresh_token.assert_called_once()

    def test_login_invalid_credentials(self, app, db_session, sample_user):
        """Test login with invalid credentials"""
        with app.test_request_context(
            json={"username": "testuser", "password": "wrongpassword"}
        ):
            response, status_code = login(Mock())

            assert status_code == 401
            assert "Invalid credentials" in response.json["message"]

    def test_login_nonexistent_user(self, app, db_session):
        """Test login with nonexistent user"""
        with app.test_request_context(
            json={"username": "nonexistent", "password": "password"}
        ):
            response, status_code = login(Mock())

            assert status_code == 401
            assert "Invalid credentials" in response.json["message"]

    def test_user_role_methods(self, app, db_session):
        """Test user role methods from userModel"""
        # Test admin user
        admin_user = userModel(
            username="adminuser",
            email="admin@example.com",
            organization_name="Admin Org",
            role=UserRole.ADMIN,
        )
        db_session.add(admin_user)
        db_session.commit()

        assert admin_user.is_admin() is True
        assert admin_user.is_super_admin() is False

        # Test super admin user
        super_admin_user = userModel(
            username="superadmin",
            email="superadmin@example.com",
            organization_name="Super Admin Org",
            role=UserRole.SUPER_ADMIN,
        )
        db_session.add(super_admin_user)
        db_session.commit()

        assert super_admin_user.is_admin() is False
        assert super_admin_user.is_super_admin() is True

    def test_user_subscription_methods(self, app, db_session, sample_plan):
        """Test user subscription methods"""
        user = userModel(
            username="testuser", email="test@example.com", organization_name="Test Org"
        )
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

    def test_user_password_methods(self, app, db_session):
        """Test user password methods"""
        user = userModel(
            username="testuser", email="test@example.com", organization_name="Test Org"
        )
        user.set_password("password123")
        db_session.add(user)
        db_session.commit()

        # Test password checking
        assert user.check_password("password123") is True
        assert user.check_password("wrongpassword") is False
        assert user.password != "password123"  # Should be hashed

    def test_user_soft_delete_methods(self, app, db_session):
        """Test user soft delete functionality"""
        user = userModel(
            username="testuser", email="test@example.com", organization_name="Test Org"
        )
        db_session.add(user)
        db_session.commit()

        # Test soft delete
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

    def test_user_class_methods(self, app, db_session):
        """Test user class methods"""
        # Create active and deleted users
        active_user = userModel(
            username="activeuser",
            email="active@example.com",
            organization_name="Active Org",
        )
        deleted_user = userModel(
            username="deleteduser",
            email="deleted@example.com",
            organization_name="Deleted Org",
        )

        db_session.add(active_user)
        db_session.add(deleted_user)
        db_session.commit()

        # Soft delete one user
        deleted_user.soft_delete()
        db_session.commit()

        # Test get_active_users
        active_users = userModel.get_active_users().all()
        usernames = [user.username for user in active_users]

        assert "activeuser" in usernames
        assert "deleteduser" not in usernames

        # Test get_by_email_or_username
        found_by_email = userModel.get_by_email_or_username("active@example.com")
        found_by_username = userModel.get_by_email_or_username("activeuser")
        not_found = userModel.get_by_email_or_username("nonexistent")

        assert found_by_email is not None
        assert found_by_username is not None
        assert found_by_email.user_id == found_by_username.user_id
        assert not_found is None

    def test_subscription_status_methods(self, app, db_session, sample_plan):
        """Test subscription status methods"""
        user = userModel(
            username="testuser", email="test@example.com", organization_name="Test Org"
        )
        db_session.add(user)
        db_session.commit()

        # Test initial subscription status
        assert user.subscription_status == SubscriptionStatus.INACTIVE

        # Test assign plan
        user.assign_plan(sample_plan)
        db_session.commit()

        assert user.subscription_status == SubscriptionStatus.ACTIVE
        assert user.subscription_start_date is not None

        # Test cancel subscription
        user.cancel_subscription()
        db_session.commit()

        assert user.subscription_status == SubscriptionStatus.CANCELLED


class TestUserController:
    """Test cases for user controller"""

    def test_get_user_profile_success(self, app, db_session, sample_user):
        """Test successful user profile retrieval"""
        with app.test_request_context():
            response, status_code = get_user_profile(sample_user.user_id)

            assert status_code == 200
            data = response.get_json()
            assert data["user_id"] == sample_user.user_id
            assert data["username"] == sample_user.username
            assert data["email"] == sample_user.email

    def test_get_user_profile_not_found(self, app, db_session):
        """Test getting profile for nonexistent user"""
        with app.test_request_context():
            response, status_code = get_user_profile(999999)

            assert status_code == 404
            assert "User not found" in response.json["error"]

    def test_update_user_profile_success(self, app, db_session, sample_user):
        """Test successful user profile update"""
        with app.test_request_context(
            json={"organization_name": "Updated Organization"}
        ):
            with patch("app.controller.userController.db.session.commit"):
                response, status_code = update_user_profile(sample_user.user_id, Mock())

                assert status_code == 200
                # Note: Actual response structure depends on implementation

    def test_update_user_profile_not_found(self, app, db_session):
        """Test updating profile for nonexistent user"""
        with app.test_request_context(
            json={"organization_name": "Updated Organization"}
        ):
            response, status_code = update_user_profile(999999, Mock())

            assert status_code == 404
            assert "User not found" in response.json["error"]


class TestBotController:
    """Test cases for bot controller"""

    def test_create_meeting_success(self, app, db_session, sample_user):
        """Test successful meeting creation"""
        with app.test_request_context(
            json={
                "title": "Test Meeting",
                "description": "Test Description",
                "start_time": datetime.now(timezone.utc).isoformat(),
                "duration": 60,
                "participants": ["user@example.com"],
            }
        ):
            with patch("app.controller.botController.db.session.commit"), patch(
                "app.controller.botController.get_jwt_identity",
                return_value=sample_user.user_id,
            ):

                # Import here to avoid circular imports
                from app.controller.botController import create_meeting

                response, status_code = create_meeting(Mock())

                # Note: Actual implementation may vary
                assert status_code in [200, 201]

    def test_create_meeting_invalid_data(self, app, db_session, sample_user):
        """Test meeting creation with invalid data"""
        with app.test_request_context(
            json={
                "title": "",  # Empty title should be invalid
                "start_time": "invalid-date",
                "duration": -1,  # Negative duration
            }
        ):
            with patch(
                "app.controller.botController.get_jwt_identity",
                return_value=sample_user.user_id,
            ):

                from app.controller.botController import create_meeting

                response, status_code = create_meeting(Mock())

                assert status_code == 400


class TestSummaryController:
    """Test cases for summary controller"""

    def test_create_summary_success(self, app, db_session, sample_user):
        """Test successful summary creation"""
        with app.test_request_context(
            json={
                "meeting_title": "Test Meeting",
                "meeting_content": "Meeting content here",
                "meeting_date": datetime.now(timezone.utc).isoformat(),
            }
        ):
            with patch("app.controller.summaryController.db.session.commit"), patch(
                "app.controller.summaryController.get_jwt_identity",
                return_value=sample_user.user_id,
            ):

                from app.controller.summaryController import create_summary

                response, status_code = create_summary(Mock())

                assert status_code in [200, 201]

    def test_get_summaries_success(self, app, db_session, sample_user):
        """Test getting user summaries"""
        with app.test_request_context():
            with patch(
                "app.controller.summaryController.get_jwt_identity",
                return_value=sample_user.user_id,
            ):

                from app.controller.summaryController import get_summaries

                response, status_code = get_summaries(Mock())

                assert status_code == 200
                data = response.get_json()
                assert isinstance(data, list)


class TestTranscriptController:
    """Test cases for transcript controller"""

    def test_upload_transcript_success(self, app, db_session, sample_user):
        """Test successful transcript upload"""
        with app.test_request_context():
            with patch(
                "app.controller.transcriptController.get_jwt_identity",
                return_value=sample_user.user_id,
            ), patch("app.controller.transcriptController.db.session.commit"), patch(
                "werkzeug.datastructures.FileStorage"
            ) as mock_file:

                mock_file.filename = "test.mp3"
                mock_file.save = Mock()

                from app.controller.transcriptController import upload_transcript

                response, status_code = upload_transcript(
                    Mock(files={"file": mock_file})
                )

                assert status_code in [200, 201]

    def test_get_transcripts_success(self, app, db_session, sample_user):
        """Test getting user transcripts"""
        with app.test_request_context():
            with patch(
                "app.controller.transcriptController.get_jwt_identity",
                return_value=sample_user.user_id,
            ):

                from app.controller.transcriptController import get_transcripts

                response, status_code = get_transcripts(Mock())

                assert status_code == 200
                data = response.get_json()
                assert isinstance(data, list)


class TestAdminController:
    """Test cases for admin controller"""

    def test_get_users_success(self, app, db_session, sample_super_admin):
        """Test getting users list as super admin"""
        with app.test_request_context():
            with patch(
                "app.controller.adminController.get_jwt_identity",
                return_value=sample_super_admin.user_id,
            ):

                from app.controller.adminController import get_users

                response, status_code = get_users(Mock())

                assert status_code == 200
                data = response.get_json()
                assert isinstance(data, list)

    def test_get_users_unauthorized(self, app, db_session, sample_user):
        """Test getting users list as regular user"""
        with app.test_request_context():
            with patch(
                "app.controller.adminController.get_jwt_identity",
                return_value=sample_user.user_id,
            ):

                from app.controller.adminController import get_users

                response, status_code = get_users(Mock())

                assert status_code == 403
                assert "Unauthorized" in response.json["error"]
