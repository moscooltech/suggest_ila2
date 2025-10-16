from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from .models import Suggestion, Vote, Announcement, LandmarkImage, Comment, User, Bookmark, SuggestionStatus
from .ai import categorize, summarize, analyze_sentiment, check_duplicate, get_embedding, get_ai_status_message
from sqlalchemy import func
import json
from datetime import datetime

# Import CommunityArea model for dynamic areas
from .models import CommunityArea

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    announcements = Announcement.query.filter(Announcement.expires_at.is_(None) | (Announcement.expires_at > db.func.now())).all()
    landmarks = LandmarkImage.query.all()
    suggestions = Suggestion.query.filter_by(status='approved').order_by(Suggestion.created_at.desc()).limit(10).all()

    # Recent activity feed
    from datetime import datetime, timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)

    recent_suggestions = Suggestion.query.filter(
        Suggestion.created_at >= week_ago,
        Suggestion.status == 'approved'
    ).order_by(Suggestion.created_at.desc()).limit(5).all()

    recent_comments = Comment.query.filter(
        Comment.created_at >= week_ago
    ).order_by(Comment.created_at.desc()).limit(5).all()

    recent_votes = Vote.query.filter(
        Vote.id.in_(
            db.session.query(func.max(Vote.id)).group_by(Vote.suggestion_id, Vote.session_id)
        )
    ).join(Suggestion).filter(
        Suggestion.created_at >= week_ago
    ).order_by(Vote.id.desc()).limit(5).all()

    # Combine and sort activities
    activities = []

    for sugg in recent_suggestions:
        activities.append({
            'type': 'suggestion',
            'title': f'New suggestion: {sugg.summary[:50]}...',
            'user': sugg.author.username if sugg.author else 'Anonymous',
            'timestamp': sugg.created_at,
            'icon': 'fas fa-lightbulb',
            'color': 'text-primary'
        })

    for comment in recent_comments:
        activities.append({
            'type': 'comment',
            'title': f'Comment on suggestion',
            'user': comment.user_name,
            'timestamp': comment.created_at,
            'icon': 'fas fa-comment',
            'color': 'text-success'
        })

    for vote in recent_votes:
        activities.append({
            'type': 'vote',
            'title': f'Voted on suggestion',
            'user': vote.user.username if vote.user else 'Anonymous',
            'timestamp': vote.suggestion.created_at,  # Using suggestion timestamp as approximation
            'icon': 'fas fa-thumbs-up',
            'color': 'text-info'
        })

    # Sort by timestamp and take top 10
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activities = activities[:10]

    return render_template('index.html',
                         announcements=announcements,
                         landmarks=landmarks,
                         suggestions=suggestions,
                         recent_activities=recent_activities,
                         now=datetime.utcnow())

@bp.route('/submit', methods=['GET', 'POST'])
def submit():
    if request.method == 'POST':
        text = request.form['text']
        is_anonymous = 'anonymous' in request.form
        contact_info = request.form.get('contact', '')
        area = request.form['area']
        specific_location = request.form.get('location', '')

        # Combine area and specific location
        if specific_location:
            location = f"{area} - {specific_location}"
        else:
            location = area

        # Get all approved suggestions for duplicate check
        existing = Suggestion.query.filter_by(status='approved').all()
        duplicate = check_duplicate(text, existing)

        if duplicate:
            # Upvote the existing suggestion
            duplicate.upvotes += 1
            db.session.commit()
            flash('This suggestion already exists. We\'ve added your upvote to it.', 'info')
            return redirect(url_for('main.feed'))

        # Check if AI services are working for categorization
        from .ai import ai_service_status
        ai_available = any(status['available'] for status in ai_service_status.values())
        if not ai_available:
            flash('AI services are currently unavailable. Your suggestion will be processed with basic text analysis.', 'warning')

        # New suggestion
        category = categorize(text)
        summary = summarize(text)
        sentiment = analyze_sentiment(text)
        embedding = get_embedding(text)
        embedding_str = json.dumps(embedding) if embedding else None

        print(f"New suggestion - Category: {category}, Sentiment: {sentiment}")
        print(f"Summary: {summary}")
        print(f"Embedding generated: {embedding is not None}")

        # Auto-approve suggestions from registered users, keep anonymous ones pending
        default_status = 'approved' if current_user.is_authenticated and not is_anonymous else 'pending'

        new_sugg = Suggestion(
            text=text,
            category=category,
            summary=summary,
            sentiment=sentiment,
            is_anonymous=is_anonymous,
            contact_info=contact_info,
            location=location,
            embedding_vector=embedding_str,
            status=default_status,
            author_id=current_user.id if current_user.is_authenticated else None
        )

        if current_user.is_authenticated:
            current_user.suggestions_count += 1

        db.session.add(new_sugg)
        db.session.commit()
        flash('Suggestion submitted successfully!', 'success')
        return redirect(url_for('main.feed'))

    ai_status = get_ai_status_message()
    community_areas = CommunityArea.query.filter_by(is_active=True).order_by(CommunityArea.name).all()
    return render_template('submit.html', ai_status=ai_status, community_areas=community_areas)

@bp.route('/feed')
def feed():

    sort_by = request.args.get('sort', 'newest')
    category_filter = request.args.get('category', 'all')
    area_filter = request.args.get('area', 'all')
    search_query = request.args.get('search', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 6  # Show 6 suggestions per page

    query = Suggestion.query.filter_by(status='approved')

    # Apply search filter
    if search_query:
        search_filter = f"%{search_query}%"
        query = query.filter(
            db.or_(
                Suggestion.text.ilike(search_filter),
                Suggestion.summary.ilike(search_filter),
                Suggestion.category.ilike(search_filter),
                Suggestion.location.ilike(search_filter)
            )
        )

    if category_filter != 'all':
        query = query.filter_by(category=category_filter)

    if area_filter != 'all':
        # Filter by area (check if location starts with the selected area)
        area_filter_pattern = f"{area_filter}%"
        query = query.filter(Suggestion.location.ilike(area_filter_pattern))

    if sort_by == 'newest':
        query = query.order_by(Suggestion.created_at.desc())
    elif sort_by == 'upvoted':
        query = query.order_by(Suggestion.upvotes.desc())
    elif sort_by == 'category':
        query = query.order_by(Suggestion.category, Suggestion.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    suggestions = pagination.items

    categories = ['Roads', 'Power', 'Water', 'Security', 'Health', 'Education', 'Other']
    community_areas = CommunityArea.query.filter_by(is_active=True).order_by(CommunityArea.name).all()
    return render_template('feed.html', suggestions=suggestions, categories=categories, community_areas=community_areas, sort_by=sort_by, category_filter=category_filter, area_filter=area_filter, search_query=search_query, pagination=pagination)

@bp.route('/vote/<int:sugg_id>/<vote_type>', methods=['POST'])
def vote(sugg_id, vote_type):
    sugg = Suggestion.query.get_or_404(sugg_id)

    # Check if user is authenticated for vote limiting
    if current_user.is_authenticated:
        # Authenticated users: one vote per suggestion (up or down)
        existing_vote = Vote.query.filter_by(suggestion_id=sugg_id, user_id=current_user.id).first()
        if existing_vote:
            if existing_vote.vote_type == vote_type:
                # Remove vote
                if vote_type == 'up':
                    sugg.upvotes -= 1
                else:
                    sugg.downvotes -= 1
                db.session.delete(existing_vote)
                flash('Vote removed.', 'info')
            else:
                # Change vote type
                if vote_type == 'up':
                    sugg.upvotes += 1
                    sugg.downvotes -= 1
                else:
                    sugg.downvotes += 1
                    sugg.upvotes -= 1
                existing_vote.vote_type = vote_type
                flash('Vote updated.', 'success')
        else:
            # New vote for authenticated user
            if vote_type == 'up':
                sugg.upvotes += 1
                # Award reputation to suggestion author
                if sugg.author and sugg.author != current_user:
                    sugg.author.reputation_score += 1
            else:
                sugg.downvotes += 1
                # Deduct reputation from suggestion author
                if sugg.author and sugg.author != current_user:
                    sugg.author.reputation_score = max(0, sugg.author.reputation_score - 1)

            new_vote = Vote(suggestion_id=sugg_id, vote_type=vote_type, user_id=current_user.id)
            current_user.votes_count += 1
            db.session.add(new_vote)
            flash('Vote recorded.', 'success')
    else:
        # Anonymous users: use session-based limiting
        session_id = session.get('session_id', str(hash(request.remote_addr + request.headers.get('User-Agent', ''))))
        session['session_id'] = session_id

        existing_vote = Vote.query.filter_by(suggestion_id=sugg_id, session_id=session_id).first()
        if existing_vote:
            if existing_vote.vote_type == vote_type:
                # Remove vote
                if vote_type == 'up':
                    sugg.upvotes -= 1
                else:
                    sugg.downvotes -= 1
                db.session.delete(existing_vote)
                flash('Vote removed.', 'info')
            else:
                # Change vote type
                if vote_type == 'up':
                    sugg.upvotes += 1
                    sugg.downvotes -= 1
                else:
                    sugg.downvotes += 1
                    sugg.upvotes -= 1
                existing_vote.vote_type = vote_type
                flash('Vote updated.', 'success')
        else:
            # New vote for anonymous user
            if vote_type == 'up':
                sugg.upvotes += 1
            else:
                sugg.downvotes += 1
            new_vote = Vote(suggestion_id=sugg_id, vote_type=vote_type, session_id=session_id)
            db.session.add(new_vote)
            flash('Vote recorded.', 'success')

    db.session.commit()
    return redirect(request.referrer or url_for('main.feed'))

@bp.route('/comment/<int:sugg_id>', methods=['POST'])
def comment(sugg_id):
    sugg = Suggestion.query.get_or_404(sugg_id)
    text = request.form['comment']
    user_name = request.form.get('name', 'Anonymous')

    if current_user.is_authenticated:
        new_comment = Comment(suggestion_id=sugg_id, text=text, user_name=current_user.username, user_id=current_user.id)
        current_user.comments_count += 1
    else:
        new_comment = Comment(suggestion_id=sugg_id, text=text, user_name=user_name)

    db.session.add(new_comment)
    db.session.commit()
    flash('Comment added!', 'success')
    return redirect(request.referrer or url_for('main.feed'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()

        # Validation
        if not username or not email or not password:
            flash('All fields are required', 'error')
            return redirect(url_for('main.register'))

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('main.register'))

        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return redirect(url_for('main.register'))

        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('main.register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('main.register'))

        # Create new user
        new_user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            first_name=first_name,
            last_name=last_name
        )

        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('main.login'))

    return render_template('auth/register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        remember = 'remember' in request.form

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()

            next_page = request.args.get('next')
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(next_page or url_for('main.dashboard'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.index'))

@bp.route('/dashboard')
@login_required
def dashboard():
    # User's suggestions
    user_suggestions = Suggestion.query.filter_by(author_id=current_user.id).order_by(Suggestion.created_at.desc()).all()

    # User's bookmarked suggestions
    bookmarked_suggestion_ids = [b.suggestion_id for b in current_user.user_bookmarks]
    bookmarked_suggestions = Suggestion.query.filter(Suggestion.id.in_(bookmarked_suggestion_ids)).order_by(Suggestion.created_at.desc()).limit(5).all()

    # Recent activity (user's comments and votes)
    recent_comments = Comment.query.filter_by(user_id=current_user.id).order_by(Comment.created_at.desc()).limit(5).all()
    recent_votes = Vote.query.filter_by(user_id=current_user.id).order_by(Vote.id.desc()).limit(5).all()

    return render_template('user/dashboard.html',
                         user_suggestions=user_suggestions,
                         bookmarked_suggestions=bookmarked_suggestions,
                         recent_comments=recent_comments,
                         recent_votes=recent_votes)

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.first_name = request.form.get('first_name', '').strip()
        current_user.last_name = request.form.get('last_name', '').strip()
        current_user.bio = request.form.get('bio', '').strip()
        current_user.location = request.form.get('location', '').strip()

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('main.profile'))

    community_areas = CommunityArea.query.filter_by(is_active=True).order_by(CommunityArea.name).all()
    return render_template('user/profile.html', community_areas=community_areas)

@bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_user.first_name = request.form.get('first_name', '').strip()
        current_user.last_name = request.form.get('last_name', '').strip()
        current_user.bio = request.form.get('bio', '').strip()
        current_user.location = request.form.get('location', '').strip()

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('main.profile'))

    return render_template('user/edit_profile.html')

@bp.route('/bookmark/<int:sugg_id>', methods=['POST'])
@login_required
def bookmark(sugg_id):
    suggestion = Suggestion.query.get_or_404(sugg_id)

    # Check if already bookmarked
    existing_bookmark = Bookmark.query.filter_by(user_id=current_user.id, suggestion_id=sugg_id).first()

    if existing_bookmark:
        db.session.delete(existing_bookmark)
        flash('Suggestion removed from bookmarks', 'info')
    else:
        bookmark = Bookmark(user_id=current_user.id, suggestion_id=sugg_id)
        db.session.add(bookmark)
        flash('Suggestion bookmarked!', 'success')

    db.session.commit()
    return redirect(request.referrer or url_for('main.feed'))

@bp.route('/suggestion/<int:sugg_id>')
def suggestion_detail(sugg_id):
    suggestion = Suggestion.query.get_or_404(sugg_id)

    # Only show approved suggestions to non-admin users
    if suggestion.status != 'approved' and (not current_user.is_authenticated or not hasattr(current_user, 'is_admin')):
        flash('Suggestion not found', 'error')
        return redirect(url_for('main.feed'))

    return render_template('suggestion_detail.html', suggestion=suggestion)

@bp.route('/suggestion/<int:sugg_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_suggestion(sugg_id):
    suggestion = Suggestion.query.get_or_404(sugg_id)

    # Only allow editing if user is the author and suggestion can still be edited
    if suggestion.author_id != current_user.id:
        flash('You can only edit your own suggestions', 'error')
        return redirect(url_for('main.feed'))

    if not suggestion.can_edit:
        flash('This suggestion can no longer be edited', 'error')
        return redirect(url_for('main.feed'))

    if request.method == 'POST':
        suggestion.text = request.form['text']
        area = request.form['area']
        specific_location = request.form.get('location', '')

        if specific_location:
            suggestion.location = f"{area} - {specific_location}"
        else:
            suggestion.location = area

        # Re-process with AI
        suggestion.category = categorize(suggestion.text)
        suggestion.summary = summarize(suggestion.text)
        suggestion.sentiment = analyze_sentiment(suggestion.text)

        db.session.commit()
        flash('Suggestion updated successfully!', 'success')
        return redirect(url_for('main.dashboard'))

    # Pre-fill form with current data
    current_area = ""
    current_location = ""
    if suggestion.location and " - " in suggestion.location:
        parts = suggestion.location.split(" - ", 1)
        current_area = parts[0]
        current_location = parts[1]
    else:
        current_area = suggestion.location or ""

    community_areas = CommunityArea.query.filter_by(is_active=True).order_by(CommunityArea.name).all()
    return render_template('user/edit_suggestion.html',
                          suggestion=suggestion,
                          community_areas=community_areas,
                          current_area=current_area,
                          current_location=current_location)