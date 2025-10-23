#!/usr/bin/env python3
"""
Migration script to transfer data from SQLite to MySQL.
This script reads data from the existing SQLite database and inserts it into MySQL.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app import create_app
from app.models import User, Suggestion, Announcement, LandmarkImage, Vote, Comment, Bookmark, SuggestionStatus, AIMetrics, CommunityArea

def create_mysql_app():
    """Create Flask app with MySQL configuration"""
    # Temporarily override DATABASE_URL for MySQL
    mysql_url = os.environ.get('MYSQL_DATABASE_URL') or os.environ.get('DATABASE_URL')
    if not mysql_url:
        print("❌ MYSQL_DATABASE_URL or DATABASE_URL environment variable not set")
        print("Please set MYSQL_DATABASE_URL to your MySQL database URL, e.g.:")
        print("mysql+pymysql://username:password@localhost/dbname")
        sys.exit(1)

    # Create app with MySQL URL
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = mysql_url
    return app

def migrate_data():
    """Migrate data from SQLite to MySQL"""

    # Create SQLite engine (source)
    sqlite_url = 'sqlite:///suggestions.db'
    sqlite_engine = create_engine(sqlite_url, echo=False)
    SQLiteSession = sessionmaker(bind=sqlite_engine)

    # Create MySQL app and engine (target)
    mysql_app = create_mysql_app()
    with mysql_app.app_context():
        mysql_engine = mysql_app.extensions['sqlalchemy'].engine
        MySQLSession = sessionmaker(bind=mysql_engine)

    print("🚀 Starting data migration from SQLite to MySQL...")

    try:
        with SQLiteSession() as sqlite_session, MySQLSession() as mysql_session:
            # Migrate Users
            print("📦 Migrating users...")
            users = sqlite_session.query(User).all()
            for user in users:
                mysql_session.merge(user)
            mysql_session.commit()
            print(f"✅ Migrated {len(users)} users")

            # Migrate Community Areas
            print("📦 Migrating community areas...")
            areas = sqlite_session.query(CommunityArea).all()
            for area in areas:
                mysql_session.merge(area)
            mysql_session.commit()
            print(f"✅ Migrated {len(areas)} community areas")

            # Migrate Suggestions (with image migration)
            print("📦 Migrating suggestions...")
            suggestions = sqlite_session.query(Suggestion).all()
            for suggestion in suggestions:
                # If suggestion has image_filename, try to load the file and store in database
                if suggestion.image_filename and not suggestion.image_data:
                    image_path = os.path.join('static', 'uploads', suggestion.image_filename)
                    if os.path.exists(image_path):
                        try:
                            with open(image_path, 'rb') as f:
                                suggestion.image_data = f.read()
                                # Guess mimetype from filename
                                if suggestion.image_filename.lower().endswith('.png'):
                                    suggestion.image_mimetype = 'image/png'
                                elif suggestion.image_filename.lower().endswith(('.jpg', '.jpeg')):
                                    suggestion.image_mimetype = 'image/jpeg'
                                elif suggestion.image_filename.lower().endswith('.gif'):
                                    suggestion.image_mimetype = 'image/gif'
                                print(f"  📸 Migrated image for suggestion {suggestion.id}")
                        except Exception as e:
                            print(f"  ⚠️ Failed to migrate image for suggestion {suggestion.id}: {e}")

                mysql_session.merge(suggestion)
            mysql_session.commit()
            print(f"✅ Migrated {len(suggestions)} suggestions")

            # Migrate Votes
            print("📦 Migrating votes...")
            votes = sqlite_session.query(Vote).all()
            for vote in votes:
                mysql_session.merge(vote)
            mysql_session.commit()
            print(f"✅ Migrated {len(votes)} votes")

            # Migrate Comments
            print("📦 Migrating comments...")
            comments = sqlite_session.query(Comment).all()
            for comment in comments:
                mysql_session.merge(comment)
            mysql_session.commit()
            print(f"✅ Migrated {len(comments)} comments")

            # Migrate Bookmarks
            print("📦 Migrating bookmarks...")
            bookmarks = sqlite_session.query(Bookmark).all()
            for bookmark in bookmarks:
                mysql_session.merge(bookmark)
            mysql_session.commit()
            print(f"✅ Migrated {len(bookmarks)} bookmarks")

            # Migrate Suggestion Status History
            print("📦 Migrating suggestion status history...")
            status_history = sqlite_session.query(SuggestionStatus).all()
            for status in status_history:
                mysql_session.merge(status)
            mysql_session.commit()
            print(f"✅ Migrated {len(status_history)} status history entries")

            # Migrate Announcements
            print("📦 Migrating announcements...")
            announcements = sqlite_session.query(Announcement).all()
            for announcement in announcements:
                mysql_session.merge(announcement)
            mysql_session.commit()
            print(f"✅ Migrated {len(announcements)} announcements")

            # Migrate Landmark Images
            print("📦 Migrating landmark images...")
            landmarks = sqlite_session.query(LandmarkImage).all()
            for landmark in landmarks:
                mysql_session.merge(landmark)
            mysql_session.commit()
            print(f"✅ Migrated {len(landmarks)} landmark images")

            # Migrate AI Metrics
            print("📦 Migrating AI metrics...")
            ai_metrics = sqlite_session.query(AIMetrics).all()
            for metric in ai_metrics:
                mysql_session.merge(metric)
            mysql_session.commit()
            print(f"✅ Migrated {len(ai_metrics)} AI metrics")

        print("🎉 Data migration completed successfully!")
        print("\n📋 Next steps:")
        print("1. Update your .env file to use MYSQL_DATABASE_URL instead of DATABASE_URL")
        print("2. Test your application with the MySQL database")
        print("3. Once confirmed working, you can remove the SQLite database file")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        mysql_session.rollback()
        sys.exit(1)

if __name__ == '__main__':
    migrate_data()