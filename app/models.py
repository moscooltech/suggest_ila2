from . import db
from flask_login import UserMixin
from datetime import datetime
import json

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    bio = db.Column(db.Text)
    location = db.Column(db.String(100))
    reputation_score = db.Column(db.Integer, default=0)
    suggestions_count = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    votes_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    authored_suggestions = db.relationship('Suggestion', back_populates='author', lazy=True)
    user_comments = db.relationship('Comment', back_populates='user', lazy=True)
    user_votes = db.relationship('Vote', back_populates='user', lazy=True)
    user_bookmarks = db.relationship('Bookmark', back_populates='user', lazy=True)
    status_changes = db.relationship('SuggestionStatus', back_populates='admin', lazy=True)

class Suggestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    summary = db.Column(db.Text)
    sentiment = db.Column(db.String(20))
    is_anonymous = db.Column(db.Boolean, default=False)
    contact_info = db.Column(db.String(150))
    location = db.Column(db.String(200))  # Street, Road, Avenue, etc.
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, resolved, in_progress, completed
    upvotes = db.Column(db.Integer, default=0)
    downvotes = db.Column(db.Integer, default=0)
    embedding_vector = db.Column(db.Text)  # JSON string of list
    image_filename = db.Column(db.String(255))  # Filename of uploaded image (legacy)
    image_data = db.Column(db.LargeBinary(length=(2**32)-1))  # Binary image data stored in database (PostgreSQL compatible)
    image_mimetype = db.Column(db.String(50))  # MIME type of the image
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    can_edit = db.Column(db.Boolean, default=True)  # Allow editing before approval
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    author = db.relationship('User', back_populates='authored_suggestions', lazy=True)
    votes = db.relationship('Vote', back_populates='suggestion', lazy=True)
    comments = db.relationship('Comment', back_populates='suggestion', lazy=True)
    bookmarks = db.relationship('Bookmark', back_populates='suggestion', lazy=True)
    status_history = db.relationship('SuggestionStatus', back_populates='suggestion', lazy=True, order_by='SuggestionStatus.created_at')

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(300))
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LandmarkImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    image_url = db.Column(db.String(300), nullable=False)
    caption = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    suggestion_id = db.Column(db.Integer, db.ForeignKey('suggestion.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # For authenticated users
    vote_type = db.Column(db.String(10), nullable=False)  # up, down
    session_id = db.Column(db.String(150), nullable=False)  # for anonymous voting
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='user_votes', lazy=True)
    suggestion = db.relationship('Suggestion', back_populates='votes', lazy=True)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    suggestion_id = db.Column(db.Integer, db.ForeignKey('suggestion.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    user_name = db.Column(db.String(150), default='Anonymous')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='user_comments', lazy=True)
    suggestion = db.relationship('Suggestion', back_populates='comments', lazy=True)

class Bookmark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    suggestion_id = db.Column(db.Integer, db.ForeignKey('suggestion.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='user_bookmarks', lazy=True)
    suggestion = db.relationship('Suggestion', back_populates='bookmarks', lazy=True)

class SuggestionStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    suggestion_id = db.Column(db.Integer, db.ForeignKey('suggestion.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.Text)
    admin_response = db.Column(db.Text)
    changed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    suggestion = db.relationship('Suggestion', back_populates='status_history', lazy=True)
    admin = db.relationship('User', back_populates='status_changes', lazy=True)

class AIMetrics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    operation = db.Column(db.String(50), nullable=False)  # categorize, summarize, sentiment, duplicate_check, etc.
    provider = db.Column(db.String(20), nullable=False)  # gemini, groq, openrouter, fallback
    success = db.Column(db.Boolean, default=True)
    response_time = db.Column(db.Float)  # in seconds
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CommunityArea(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)