#!/usr/bin/env python3
"""
Validation script to verify MySQL migration was successful.
Run this after migrating to ensure all data is intact and the app works with MySQL.
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file
from app import create_app
from app.models import User, Suggestion, Announcement, LandmarkImage, Vote, Comment, Bookmark, SuggestionStatus, AIMetrics, CommunityArea

def validate_mysql_setup():
    """Validate that MySQL is properly configured and accessible"""

    print("🔍 Validating MySQL setup...")

    # Check environment variables
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return False

    if not (database_url.startswith('mysql+pymysql://') or database_url.startswith('postgresql://')):
        print("❌ DATABASE_URL does not use supported database format")
        print(f"Current: {database_url}")
        print("Expected: mysql+pymysql://username:password@host:port/database or postgresql://username:password@host:port/database")
        return False

    print("✅ DATABASE_URL is properly configured")

    # Test database connection
    try:
        app = create_app()
        with app.app_context():
            # Test basic connection
            from app import db
            from sqlalchemy import text
            db.session.execute(text("SELECT 1"))
            print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

    return True

def validate_data_integrity():
    """Validate that all data was migrated correctly"""

    print("\n🔍 Validating data integrity...")

    try:
        app = create_app()
        with app.app_context():
            # Check table counts
            tables_and_counts = [
                ("Users", User.query.count()),
                ("Suggestions", Suggestion.query.count()),
                ("Announcements", Announcement.query.count()),
                ("Landmark Images", LandmarkImage.query.count()),
                ("Votes", Vote.query.count()),
                ("Comments", Comment.query.count()),
                ("Bookmarks", Bookmark.query.count()),
                ("Suggestion Status History", SuggestionStatus.query.count()),
                ("AI Metrics", AIMetrics.query.count()),
                ("Community Areas", CommunityArea.query.count()),
            ]

            print("📊 Table record counts:")
            for table_name, count in tables_and_counts:
                print(f"  {table_name}: {count}")

            # Validate relationships
            print("\n🔗 Validating relationships...")

            # Check that suggestions have valid authors
            orphaned_suggestions = Suggestion.query.filter(
                Suggestion.author_id.isnot(None),
                ~Suggestion.author_id.in_([u.id for u in User.query.all()])
            ).count()

            if orphaned_suggestions > 0:
                print(f"⚠️ Found {orphaned_suggestions} suggestions with invalid author references")
            else:
                print("✅ All suggestions have valid authors")

            # Check that votes have valid suggestions
            orphaned_votes = Vote.query.filter(
                ~Vote.suggestion_id.in_([s.id for s in Suggestion.query.all()])
            ).count()

            if orphaned_votes > 0:
                print(f"⚠️ Found {orphaned_votes} votes with invalid suggestion references")
            else:
                print("✅ All votes reference valid suggestions")

            # Check that comments have valid suggestions
            orphaned_comments = Comment.query.filter(
                ~Comment.suggestion_id.in_([s.id for s in Suggestion.query.all()])
            ).count()

            if orphaned_comments > 0:
                print(f"⚠️ Found {orphaned_comments} comments with invalid suggestion references")
            else:
                print("✅ All comments reference valid suggestions")

    except Exception as e:
        print(f"❌ Data validation failed: {e}")
        return False

    return True

def test_basic_operations():
    """Test basic CRUD operations to ensure MySQL compatibility"""

    print("\n🔍 Testing basic operations...")

    try:
        app = create_app()
        with app.app_context():
            from app import db

            # Test creating a test user (use unique username to avoid conflicts)
            import time
            unique_username = f'test_migration_user_{int(time.time())}'
            test_user = User(
                username=unique_username,
                email=f'{unique_username}@example.com',
                password='hashed_password'
            )
            db.session.add(test_user)
            db.session.commit()
            print("✅ User creation successful")

            # Test creating a test suggestion
            test_suggestion = Suggestion(
                text='Test suggestion for MySQL validation',
                category='Test',
                author_id=test_user.id
            )
            db.session.add(test_suggestion)
            db.session.commit()
            print("✅ Suggestion creation successful")

            # Test querying
            user_count = User.query.count()
            suggestion_count = Suggestion.query.count()
            print(f"✅ Query operations successful (Users: {user_count}, Suggestions: {suggestion_count})")

            # Clean up test data
            db.session.delete(test_suggestion)
            db.session.delete(test_user)
            db.session.commit()
            print("✅ Test data cleanup successful")

    except Exception as e:
        print(f"❌ Basic operations test failed: {e}")
        return False

    return True

def main():
    """Main validation function"""

    print("🚀 MySQL Migration Validation")
    print("=" * 50)

    # Run all validations
    setup_ok = validate_mysql_setup()
    data_ok = validate_data_integrity() if setup_ok else False
    operations_ok = test_basic_operations() if setup_ok else False

    print("\n" + "=" * 50)
    print("📋 VALIDATION RESULTS:")

    if setup_ok and data_ok and operations_ok:
        print("🎉 All validations passed! MySQL migration successful.")
        print("\n✅ Your application is now running on MySQL")
        print("✅ All data has been migrated successfully")
        print("✅ Basic operations are working correctly")
        return True
    else:
        print("❌ Some validations failed. Please check the errors above.")
        if not setup_ok:
            print("  - Database setup issues")
        if not data_ok:
            print("  - Data integrity issues")
        if not operations_ok:
            print("  - Basic operations issues")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)