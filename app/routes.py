from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file, make_response
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from . import db
from .models import Suggestion, Vote, Announcement, LandmarkImage, Comment, User, Bookmark, SuggestionStatus
from .ai import categorize, summarize, analyze_sentiment, check_duplicate, get_embedding, get_ai_status_message
from sqlalchemy import func
import json
import os
from datetime import datetime
from io import BytesIO

# Import CommunityArea model for dynamic areas
from .models import CommunityArea

bp = Blueprint('main', __name__)

# Configuration for file uploads
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def secure_filename_custom(filename):
    """Custom secure filename that preserves extension"""
    if not filename:
        return None
    name, ext = os.path.splitext(filename)
    secure_name = secure_filename(name)
    return secure_name + ext.lower()

@bp.route('/image/<int:suggestion_id>')
def get_image(suggestion_id):
    """Serve image from database"""
    suggestion = Suggestion.query.get_or_404(suggestion_id)

    if not suggestion.image_data:
        # Fallback to file system if no database image
        if suggestion.image_filename:
            try:
                return send_file(os.path.join(UPLOAD_FOLDER, suggestion.image_filename))
            except FileNotFoundError:
                pass
        return "Image not found", 404

    # Serve from database
    response = make_response(suggestion.image_data)
    response.headers.set('Content-Type', suggestion.image_mimetype or 'image/jpeg')
    return response