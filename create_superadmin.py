#!/usr/bin/env python3
"""
Create Super Admin User Script
Similar to Django's createsuperuser command
"""

import os
import sys
import getpass
import re
from datetime import datetime, timezone, timedelta

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.extension import db
from app import create_app
from app.models.userModel import userModel, UserRole, SubscriptionStatus
from app.models.planModel import PlanModel, PlanType
from app.helper.validations import validated_Pass, EmailType
import re


def validate_email_simple(email):
    """Simple but robust email validation"""
    if not email or '@' not in email:
        raise ValueError("Email must contain @ symbol")
    
    if '.' not in email:
        raise ValueError("Email must contain domain")
    
    # Basic email regex - covers most common cases
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValueError("Invalid email format")
    
    # Additional checks
    local_part = email.split('@')[0]
    domain_part = email.split('@')[1]
    
    if len(local_part) > 64:
        raise ValueError("Email username too long (max 64 characters)")
    
    if len(domain_part) > 253:
        raise ValueError("Email domain too long")
    
    if local_part.startswith('.') or local_part.endswith('.'):
        raise ValueError("Email cannot start or end with dot")
    
    return email.lower()


def get_user_input(prompt, required=True, default=None):
    """Get user input with validation"""
    while True:
        try:
            if default:
                user_input = input(f"{prompt} [{default}]: ").strip() or default
            else:
                user_input = input(f"{prompt}: ").strip()
            
            if not user_input and required:
                print("❌ This field is required.")
                continue
            
            return user_input
                
        except KeyboardInterrupt:
            print("\n❌ Operation cancelled.")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Invalid input: {e}")
            continue


def get_email_input(prompt, required=True, default=None):
    """Get email input with simple validation"""
    while True:
        try:
            if default:
                user_input = input(f"{prompt} [{default}]: ").strip() or default
            else:
                user_input = input(f"{prompt}: ").strip()
            
            if not user_input and required:
                print("❌ Email is required.")
                continue
            
            return validate_email_simple(user_input)
                
        except KeyboardInterrupt:
            print("\n❌ Operation cancelled.")
            sys.exit(1)
        except ValueError as e:
            print(f"❌ {e}")
            continue
        except Exception as e:
            print(f"❌ Invalid input: {e}")
            continue


def get_password():
    """Get password with validation using the existing validator"""
    while True:
        try:
            password = getpass.getpass("Password: ")
            if not password:
                print("❌ Password cannot be empty.")
                continue
            
            # Use the existing password validator
            validated_password = validated_Pass(password)
            
            confirm_password = getpass.getpass("Confirm Password: ")
            if password != confirm_password:
                print("❌ Passwords do not match.")
                continue
            
            return validated_password
            
        except KeyboardInterrupt:
            print("\n❌ Operation cancelled.")
            sys.exit(1)
        except ValueError as e:
            print(f"❌ {e}")
            continue
        except Exception as e:
            print(f"❌ Error: {e}")
            continue


def check_user_exists(username, email):
    """Check if user already exists and return the user object"""
    try:
        # Create the Flask app
        app = create_app()
        
        with app.app_context():
            existing_user = userModel.get_by_email_or_username(username)
            if existing_user:
                return existing_user
            
            # Check email separately
            email_user = userModel.query.filter_by(email=email, is_deleted=False).first()
            if email_user:
                return email_user
            
            return None
    except Exception as e:
        print(f"❌ Error checking existing user: {e}")
        return None  # Return None instead of True


def get_or_create_plan():
    """Get or create a suitable plan for super admin"""
    try:
        # Create the Flask app
        app = create_app()
        
        with app.app_context():
            # Try to find an enterprise plan first
            enterprise_plan = PlanModel.query.filter_by(
                plan_type=PlanType.ENTERPRISE, 
                is_active=True
            ).first()
            
            if enterprise_plan:
                print(f"✅ Using existing plan: {enterprise_plan.name}")
                return enterprise_plan
            
            # Try pro plan
            pro_plan = PlanModel.query.filter_by(
                plan_type=PlanType.PRO, 
                is_active=True
            ).first()
            
            if pro_plan:
                print(f"✅ Using existing plan: {pro_plan.name}")
                return pro_plan
            
            # Create a super admin plan
            super_admin_plan = PlanModel(
                name="Super Admin Plan",
                plan_type=PlanType.ENTERPRISE,
                description="Unlimited access for super administrators",
                price=0.00,
                max_meetings=None,  # Unlimited
                max_users=None,     # Unlimited
                features='{"all_features": true, "unlimited_meetings": true, "unlimited_users": true}',
                is_active=True
            )
            
            db.session.add(super_admin_plan)
            db.session.commit()
            
            print(f"✅ Created new plan: {super_admin_plan.name}")
            return super_admin_plan
            
    except Exception as e:
        print(f"❌ Error with plan: {e}")
        return None


def create_super_admin():
    """Create a super admin user"""
    print("🚀 Create Super Admin User")
    print("=" * 50)
    
    # Get user details
    username = get_user_input("Username", required=True)
    email = get_email_input("Email", required=True)
    organization = get_user_input("Organization Name", required=False, default="")
    password = get_password()
    
    # Check if user already exists
    print("\n🔍 Checking if user already exists...")
    existing_user = check_user_exists(username, email)
    
    if existing_user:
        print(f"❌ User already exists:")
        print(f"   Username: {existing_user.username}")
        print(f"   Email: {existing_user.email}")
        print(f"   Role: {existing_user.role}")
        print(f"   Active: {existing_user.is_active}")
        
        if input("\nDo you want to update this user to super admin? (y/N): ").lower() == 'y':
            try:
                with app.app_context():
                    existing_user.role = UserRole.SUPER_ADMIN
                    existing_user.is_active = True
                    existing_user.is_deleted = False
                    existing_user.deleted_at = None
                    existing_user.updated_at = datetime.now(timezone.utc)
                    
                    # Set new password if provided
                    if password:
                        existing_user.set_password(password)
                    
                    db.session.commit()
                    print(f"✅ User '{username}' updated to Super Admin successfully!")
                    return True
            except Exception as e:
                print(f"❌ Error updating user: {e}")
                return False
        else:
            print("❌ Operation cancelled.")
            return False
    
    # Get or create plan
    print("\n📋 Setting up plan...")
    plan = get_or_create_plan()
    if not plan:
        print("❌ Could not set up plan. Aborting.")
        return False
    
    # Create the super admin user
    print("\n👤 Creating super admin user...")
    try:
        # Create the Flask app
        app = create_app()
        
        with app.app_context():
            super_admin = userModel(
                username=username,
                email=email,
                organization_name=organization if organization else None,
                role=UserRole.SUPER_ADMIN,
                plan_id=plan.plan_id,
                subscription_status=SubscriptionStatus.ACTIVE,
                subscription_start_date=datetime.now(timezone.utc),
                subscription_end_date=datetime.now(timezone.utc) + timedelta(days=365*10),  # 10 years
                is_active=True,
                is_deleted=False,
                meetings=0
            )
            
            # Set password
            super_admin.set_password(password)
            
            # Save to database
            db.session.add(super_admin)
            db.session.commit()
            
            print(f"\n✅ Super Admin user created successfully!")
            print(f"   📧 Email: {super_admin.email}")
            print(f"   👤 Username: {super_admin.username}")
            print(f"   🏢 Role: {super_admin.role}")
            print(f"   📋 Plan: {plan.name}")
            print(f"   📅 Subscription: Active until {super_admin.subscription_end_date.strftime('%Y-%m-%d')}")
            print(f"   🔢 User ID: {super_admin.user_id}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error creating super admin: {e}")
        return False


def list_super_admins():
    """List all super admin users"""
    try:
        # Create the Flask app
        app = create_app()
        
        with app.app_context():
            super_admins = userModel.query.filter_by(
                role=UserRole.SUPER_ADMIN, 
                is_deleted=False
            ).all()
            
            if not super_admins:
                print("📭 No super admin users found.")
                return
            
            print(f"👥 Found {len(super_admins)} super admin user(s):")
            print("-" * 80)
            
            for admin in super_admins:
                status = "✅ Active" if admin.is_active else "❌ Inactive"
                print(f"📧 Email: {admin.email}")
                print(f"👤 Username: {admin.username}")
                print(f"🏢 Organization: {admin.organization_name or 'N/A'}")
                print(f"📋 Plan: {admin.plan.name if admin.plan else 'No Plan'}")
                print(f"📊 Status: {status}")
                print(f"📅 Created: {admin.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"🔢 User ID: {admin.user_id}")
                print("-" * 80)
                
    except Exception as e:
        print(f"❌ Error listing super admins: {e}")


def main():
    """Main function"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "--list" or command == "-l":
            list_super_admins()
            return
        elif command == "--help" or command == "-h":
            print_help()
            return
        else:
            print(f"❌ Unknown command: {command}")
            print_help()
            sys.exit(1)
    
    # Create the Flask app
    app = create_app()
    
    # Initialize app context
    with app.app_context():
        # Create tables if they don't exist
        try:
            db.create_all()
            print("✅ Database tables ready.")
        except Exception as e:
            print(f"❌ Error with database: {e}")
            sys.exit(1)
        
        # Create super admin
        success = create_super_admin()
        
        if success:
            print("\n🎉 Super admin setup completed!")
            print("\n📝 Next steps:")
            print("   1. Start the application")
            print("   2. Login with the super admin credentials")
            print("   3. Access admin features")
        else:
            print("\n❌ Super admin creation failed!")
            sys.exit(1)


def print_help():
    """Print help information"""
    print("Create Super Admin User Script")
    print("=" * 40)
    print("\nUsage:")
    print("  python create_superadmin.py          # Create a new super admin")
    print("  python create_superadmin.py --list   # List all super admins")
    print("  python create_superadmin.py --help   # Show this help")
    print("\nFeatures:")
    print("  ✅ Interactive user creation")
    print("  ✅ Password validation")
    print("  ✅ Duplicate user checking")
    print("  ✅ Automatic plan setup")
    print("  ✅ User update option")
    print("  ✅ Comprehensive error handling")


if __name__ == "__main__":
    main()
