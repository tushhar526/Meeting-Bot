import pytest
import tempfile
import os
from datetime import datetime, timezone
from flask import Flask
from app import create_app
from app.extension import db
from app.models.userModel import userModel, UserRole, SubscriptionStatus
from app.models.planModel import PlanModel


@pytest.fixture
def app():
    """Create and configure a test app."""
    # Create a temporary database
    db_fd, db_path = tempfile.mkstemp()
    
    # Test configuration
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'WTF_CSRF_ENABLED': False,
        'JWT_SECRET_KEY': 'test-secret-key',
        'SECRET_KEY': 'test-secret-key',
        'JWT_ACCESS_TOKEN_EXPIRES': 3600,  # 1 hour
        'JWT_REFRESH_TOKEN_EXPIRES': 2592000,  # 30 days
        'CELERY_BROKER_URL': 'redis://localhost:6379/0',
        'CELERY_RESULT_BACKEND': 'redis://localhost:6379/0',
    }
    
    app = create_app()
    app.config.update(test_config)
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()
    
    # Close and remove the temporary database
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test CLI runner."""
    return app.test_cli_runner()


@pytest.fixture
def db_session(app):
    """Create a database session for testing."""
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        
        session = db.session(bind=connection)
        
        yield session
        
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing."""
    user = userModel(
        username="testuser",
        email="test@example.com",
        organization_name="Test Org",
        role=UserRole.ADMIN
    )
    user.set_password("testpassword")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def sample_super_admin(db_session):
    """Create a sample super admin for testing."""
    admin = userModel(
        username="superadmin",
        email="admin@example.com",
        organization_name="Admin Org",
        role=UserRole.SUPER_ADMIN
    )
    admin.set_password("adminpassword")
    db_session.add(admin)
    db_session.commit()
    return admin


@pytest.fixture
def sample_plan(db_session):
    """Create a sample plan for testing."""
    plan = PlanModel(
        name="Test Plan",
        description="Test plan description",
        price=99.99,
        duration_days=30,
        max_meetings=100
    )
    db_session.add(plan)
    db_session.commit()
    return plan


@pytest.fixture
def auth_headers(client, sample_user):
    """Get authentication headers for a sample user."""
    response = client.post('/api/auth/login', json={
        'username': 'testuser',
        'password': 'testpassword'
    })
    token = response.json['access_token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def admin_auth_headers(client, sample_super_admin):
    """Get authentication headers for a super admin."""
    response = client.post('/api/auth/login', json={
        'username': 'superadmin',
        'password': 'adminpassword'
    })
    token = response.json['access_token']
    return {'Authorization': f'Bearer {token}'}
