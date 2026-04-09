import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import jsonify
from datetime import datetime, timezone, timedelta
from app.controller.authController import signup, login
from app.controller.userController import get_user_profile, update_user_profile
from app.models.userModel import userModel, UserRole, SubscriptionStatus
from app.models.planModel import PlanModel


class TestAuthController:
    """Test cases for authentication controller"""
    
    def test_signup_success(self, app, db_session):
        """Test successful user signup"""
        with app.test_request_context(json={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'password123',
            'organization_name': 'New Org'
        }):
            with patch('app.controller.authController.db.session.commit'):
                response, status_code = signup(Mock())
                
                assert status_code == 201
                # Note: Actual response structure depends on implementation
    
    def test_signup_existing_username(self, app, db_session, sample_user):
        """Test signup with existing username"""
        with app.test_request_context(json={
            'username': 'testuser',  # Already exists
            'email': 'newemail@example.com',
            'password': 'password123',
            'organization_name': 'New Org'
        }):
            response, status_code = signup(Mock())
            
            assert status_code == 400
            assert "Username already exists" in response.json['message']
    
    def test_signup_existing_email(self, app, db_session, sample_user):
        """Test signup with existing email"""
        with app.test_request_context(json={
            'username': 'newuser',
            'email': 'test@example.com',  # Already exists
            'password': 'password123',
            'organization_name': 'New Org'
        }):
            response, status_code = signup(Mock())
            
            assert status_code == 400
            assert "Email already exists" in response.json['message']
    
    def test_signup_missing_organization(self, app, db_session):
        """Test signup without organization name"""
        with app.test_request_context(json={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'password123',
            'organization_name': ''
        }):
            response, status_code = signup(Mock())
            
            assert status_code == 400
            assert "Organization name is required" in response.json['message']
    
    def test_login_success(self, app, db_session, sample_user):
        """Test successful user login"""
        with app.test_request_context(json={
            'username': 'testuser',
            'password': 'testpassword'
        }):
            with patch('app.controller.authController.create_access_token') as mock_access_token, \
                 patch('app.controller.authController.create_refresh_token') as mock_refresh_token, \
                 patch('app.controller.authController.set_access_cookies'), \
                 patch('app.controller.authController.set_refresh_cookies'), \
                 patch('app.controller.authController.db.session.commit'):
                
                mock_access_token.return_value = 'access_token'
                mock_refresh_token.return_value = 'refresh_token'
                
                response, status_code = login(Mock())
                
                assert status_code == 200
                mock_access_token.assert_called_once()
                mock_refresh_token.assert_called_once()
    
    def test_login_invalid_credentials(self, app, db_session, sample_user):
        """Test login with invalid credentials"""
        with app.test_request_context(json={
            'username': 'testuser',
            'password': 'wrongpassword'
        }):
            response, status_code = login(Mock())
            
            assert status_code == 401
            assert "Invalid credentials" in response.json['message']
    
    def test_login_nonexistent_user(self, app, db_session):
        """Test login with nonexistent user"""
        with app.test_request_context(json={
            'username': 'nonexistent',
            'password': 'password'
        }):
            response, status_code = login(Mock())
            
            assert status_code == 401
            assert "Invalid credentials" in response.json['message']


class TestUserController:
    """Test cases for user controller"""
    
    def test_get_user_profile_success(self, app, db_session, sample_user):
        """Test successful user profile retrieval"""
        with app.test_request_context():
            response, status_code = get_user_profile(sample_user.user_id)
            
            assert status_code == 200
            data = response.get_json()
            assert data['user_id'] == sample_user.user_id
            assert data['username'] == sample_user.username
            assert data['email'] == sample_user.email
    
    def test_get_user_profile_not_found(self, app, db_session):
        """Test getting profile for nonexistent user"""
        with app.test_request_context():
            response, status_code = get_user_profile(999999)
            
            assert status_code == 404
            assert "User not found" in response.json['error']
    
    def test_update_user_profile_success(self, app, db_session, sample_user):
        """Test successful user profile update"""
        with app.test_request_context(json={
            'organization_name': 'Updated Organization'
        }):
            with patch('app.controller.userController.db.session.commit'):
                response, status_code = update_user_profile(sample_user.user_id, Mock())
                
                assert status_code == 200
                # Note: Actual response structure depends on implementation
    
    def test_update_user_profile_not_found(self, app, db_session):
        """Test updating profile for nonexistent user"""
        with app.test_request_context(json={
            'organization_name': 'Updated Organization'
        }):
            response, status_code = update_user_profile(999999, Mock())
            
            assert status_code == 404
            assert "User not found" in response.json['error']


class TestBotController:
    """Test cases for bot controller"""
    
    def test_create_meeting_success(self, app, db_session, sample_user):
        """Test successful meeting creation"""
        with app.test_request_context(json={
            'title': 'Test Meeting',
            'description': 'Test Description',
            'start_time': datetime.now(timezone.utc).isoformat(),
            'duration': 60,
            'participants': ['user@example.com']
        }):
            with patch('app.controller.botController.db.session.commit'), \
                 patch('app.controller.botController.get_jwt_identity', return_value=sample_user.user_id):
                
                # Import here to avoid circular imports
                from app.controller.botController import create_meeting
                
                response, status_code = create_meeting(Mock())
                
                # Note: Actual implementation may vary
                assert status_code in [200, 201]
    
    def test_create_meeting_invalid_data(self, app, db_session, sample_user):
        """Test meeting creation with invalid data"""
        with app.test_request_context(json={
            'title': '',  # Empty title should be invalid
            'start_time': 'invalid-date',
            'duration': -1  # Negative duration
        }):
            with patch('app.controller.botController.get_jwt_identity', return_value=sample_user.user_id):
                
                from app.controller.botController import create_meeting
                
                response, status_code = create_meeting(Mock())
                
                assert status_code == 400


class TestSummaryController:
    """Test cases for summary controller"""
    
    def test_create_summary_success(self, app, db_session, sample_user):
        """Test successful summary creation"""
        with app.test_request_context(json={
            'meeting_title': 'Test Meeting',
            'meeting_content': 'Meeting content here',
            'meeting_date': datetime.now(timezone.utc).isoformat()
        }):
            with patch('app.controller.summaryController.db.session.commit'), \
                 patch('app.controller.summaryController.get_jwt_identity', return_value=sample_user.user_id):
                
                from app.controller.summaryController import create_summary
                
                response, status_code = create_summary(Mock())
                
                assert status_code in [200, 201]
    
    def test_get_summaries_success(self, app, db_session, sample_user):
        """Test getting user summaries"""
        with app.test_request_context():
            with patch('app.controller.summaryController.get_jwt_identity', return_value=sample_user.user_id):
                
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
            with patch('app.controller.transcriptController.get_jwt_identity', return_value=sample_user.user_id), \
                 patch('app.controller.transcriptController.db.session.commit'), \
                 patch('werkzeug.datastructures.FileStorage') as mock_file:
                
                mock_file.filename = 'test.mp3'
                mock_file.save = Mock()
                
                from app.controller.transcriptController import upload_transcript
                
                response, status_code = upload_transcript(Mock(files={'file': mock_file}))
                
                assert status_code in [200, 201]
    
    def test_get_transcripts_success(self, app, db_session, sample_user):
        """Test getting user transcripts"""
        with app.test_request_context():
            with patch('app.controller.transcriptController.get_jwt_identity', return_value=sample_user.user_id):
                
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
            with patch('app.controller.adminController.get_jwt_identity', return_value=sample_super_admin.user_id):
                
                from app.controller.adminController import get_users
                
                response, status_code = get_users(Mock())
                
                assert status_code == 200
                data = response.get_json()
                assert isinstance(data, list)
    
    def test_get_users_unauthorized(self, app, db_session, sample_user):
        """Test getting users list as regular user"""
        with app.test_request_context():
            with patch('app.controller.adminController.get_jwt_identity', return_value=sample_user.user_id):
                
                from app.controller.adminController import get_users
                
                response, status_code = get_users(Mock())
                
                assert status_code == 403
                assert "Unauthorized" in response.json['error']
