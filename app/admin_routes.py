from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import os
import pandas as pd
from io import BytesIO
from datetime import datetime
from . import db
from .models import User, Suggestion, Announcement, LandmarkImage, AIMetrics, Vote, CommunityArea, SuggestionStatus
from .ai import check_ai_service_status
from sqlalchemy import func, case

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

bp = Blueprint('admin', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            if user.is_admin:
                login_user(user)
                return redirect(url_for('admin.dashboard'))
            else:
                flash('Access denied. Admin privileges required.', 'error')
        flash('Invalid credentials', 'error')
    return render_template('admin/login.html')

@bp.route('/logout')
@admin_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/dashboard')
@admin_required
def dashboard():
    total_suggestions = Suggestion.query.count()
    approved = Suggestion.query.filter_by(status='approved').count()
    pending = Suggestion.query.filter_by(status='pending').count()
    categories = db.session.query(Suggestion.category, func.count(Suggestion.id)).filter(Suggestion.category.isnot(None)).group_by(Suggestion.category).all()
    sentiments = db.session.query(Suggestion.sentiment, func.count(Suggestion.id)).filter(Suggestion.sentiment.isnot(None)).group_by(Suggestion.sentiment).all()
    category_labels = [cat[0] for cat in categories]
    category_data = [cat[1] for cat in categories]
    sentiment_labels = [sent[0] for sent in sentiments]
    sentiment_data = [sent[1] for sent in sentiments]

    # Debugging: print the data being sent to the template
    print("DEBUG: category_labels:", category_labels)
    print("DEBUG: category_data:", category_data)
    print("DEBUG: sentiment_labels:", sentiment_labels)
    print("DEBUG: sentiment_data:", sentiment_data)

    return render_template('admin/dashboard.html', total=total_suggestions, approved=approved, pending=pending, category_labels=category_labels, category_data=category_data, sentiment_labels=sentiment_labels, sentiment_data=sentiment_data)

@bp.route('/analytics')
@admin_required
def analytics():
    from datetime import datetime, timedelta
    from sqlalchemy import func, extract

    # Time-based metrics
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # Basic counts
    total_suggestions = Suggestion.query.count()
    approved_suggestions = Suggestion.query.filter_by(status='approved').count()
    pending_suggestions = Suggestion.query.filter_by(status='pending').count()
    total_users = User.query.count()
    active_users = User.query.filter(User.last_login >= week_ago).count()

    # Category distribution
    category_stats = db.session.query(
        Suggestion.category,
        func.count(Suggestion.id).label('count')
    ).filter_by(status='approved').group_by(Suggestion.category).all()

    # Convert to list of lists for easier template processing
    category_stats = [[cat, count] for cat, count in category_stats]

    # Area distribution - extract area names from location strings and count
    from sqlalchemy import text

    area_stats_query = text("""
        SELECT
            CASE
                WHEN LOCATE(' - ', s.location) > 0
                THEN SUBSTRING(s.location, 1, LOCATE(' - ', s.location) - 1)
                ELSE s.location
            END as area_name,
            COUNT(s.id) as count
        FROM suggestion s
        WHERE s.status = 'approved'
        AND s.location IS NOT NULL
        AND s.location != ''
        GROUP BY area_name
        ORDER BY count DESC
        LIMIT 10
    """)

    area_stats = db.session.execute(area_stats_query).fetchall()
    # Convert to list of lists
    area_stats = [[area[0], area[1]] for area in area_stats]

    # Sentiment distribution
    sentiment_stats = db.session.query(
        Suggestion.sentiment,
        func.count(Suggestion.id).label('count')
    ).filter_by(status='approved').group_by(Suggestion.sentiment).all()

    # Convert to list of lists
    sentiment_stats = [[sent, count] for sent, count in sentiment_stats]

    # Weekly activity (last 7 days)
    weekly_suggestions = Suggestion.query.filter(
        Suggestion.created_at >= week_ago
    ).count()

    weekly_votes = Vote.query.filter(
        Vote.id.in_(
            db.session.query(func.max(Vote.id)).group_by(Vote.suggestion_id, Vote.session_id)
        ),
        Vote.id.in_(
            db.session.query(Vote.id).join(Suggestion).filter(Suggestion.created_at >= week_ago)
        )
    ).count()

    # Monthly trends (last 30 days)
    monthly_data = []
    for i in range(30):
        date = now - timedelta(days=i)
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)

        suggestions = Suggestion.query.filter(
            Suggestion.created_at >= day_start,
            Suggestion.created_at <= day_end
        ).count()

        monthly_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'suggestions': suggestions
        })

    # Sort by date ascending for proper chart display
    monthly_data.sort(key=lambda x: x['date'])

    # Top contributors
    top_contributors = db.session.query(
        User.username,
        User.reputation_score,
        func.count(Suggestion.id).label('suggestions_count')
    ).join(Suggestion, User.id == Suggestion.author_id
    ).filter(Suggestion.status == 'approved'
    ).group_by(User.id, User.username, User.reputation_score
    ).order_by(User.reputation_score.desc()
    ).limit(10).all()

    # Status distribution
    status_stats = db.session.query(
        Suggestion.status,
        func.count(Suggestion.id).label('count')
    ).group_by(Suggestion.status).all()

    # Convert to list of lists
    status_stats = [[stat, count] for stat, count in status_stats]

    # Debug: Print stats for troubleshooting
    print(f"DEBUG Analytics - Total suggestions: {total_suggestions}")
    print(f"DEBUG Analytics - Category stats: {category_stats}")
    print(f"DEBUG Analytics - Sentiment stats: {sentiment_stats}")
    print(f"DEBUG Analytics - Status stats: {status_stats}")
    print(f"DEBUG Analytics - Area stats: {area_stats}")
    print(f"DEBUG Analytics - Top contributors: {top_contributors}")
    print(f"DEBUG Analytics - Weekly data: {weekly_suggestions}, {weekly_votes}")
    print(f"DEBUG Analytics - Monthly data length: {len(monthly_data) if monthly_data else 0}")

    return render_template('admin/analytics.html',
                          total_suggestions=total_suggestions,
                          approved_suggestions=approved_suggestions,
                          pending_suggestions=pending_suggestions,
                          total_users=total_users,
                          active_users=active_users,
                          category_stats=category_stats,
                          area_stats=area_stats,
                          sentiment_stats=sentiment_stats,
                          weekly_suggestions=weekly_suggestions,
                          weekly_votes=weekly_votes,
                          monthly_data=monthly_data,
                          top_contributors=top_contributors,
                          status_stats=status_stats)

@bp.route('/suggestions')
@admin_required
def manage_suggestions():
    status_filter = request.args.get('status', 'all')
    query = Suggestion.query
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    suggestions = query.all()
    return render_template('admin/suggestions.html', suggestions=suggestions, status_filter=status_filter)

@bp.route('/suggestion/<int:id>/status/<status>', methods=['GET', 'POST'])
@admin_required
def change_status(id, status):
    sugg = Suggestion.query.get_or_404(id)

    if request.method == 'POST':
        admin_response = request.form.get('admin_response', '')
        notes = request.form.get('notes', '')

        # Update suggestion status
        old_status = sugg.status
        sugg.status = status

        # Create status history entry
        status_entry = SuggestionStatus(
            suggestion_id=id,
            status=status,
            notes=notes,
            admin_response=admin_response,
            changed_by=current_user.id
        )
        db.session.add(status_entry)

        # If status changed to approved, disable editing
        if status == 'approved' and old_status != 'approved':
            sugg.can_edit = False

        db.session.commit()
        flash(f'Suggestion status changed to {status}', 'success')
        return redirect(url_for('admin.manage_suggestions'))

    return render_template('admin/change_status.html', suggestion=sugg, new_status=status)

@bp.route('/suggestion/<int:id>/merge/<int:target_id>', methods=['POST'])
@admin_required
def merge_suggestions(id, target_id):
    sugg = Suggestion.query.get_or_404(id)
    target = Suggestion.query.get_or_404(target_id)
    target.upvotes += sugg.upvotes
    target.downvotes += sugg.downvotes
    # Move comments
    for comment in sugg.comments:
        comment.suggestion_id = target_id
    db.session.delete(sugg)
    db.session.commit()
    flash('Suggestions merged', 'success')
    return redirect(url_for('admin.manage_suggestions'))

@bp.route('/announcements')
@admin_required
def manage_announcements():
    announcements = Announcement.query.all()
    return render_template('admin/announcements.html', announcements=announcements)

@bp.route('/announcement/new', methods=['GET', 'POST'])
@admin_required
def new_announcement():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        image_url = request.form.get('image_url')
        expires_at = request.form.get('expires_at')
        expires = datetime.fromisoformat(expires_at) if expires_at else None
        ann = Announcement(title=title, content=content, image_url=image_url, expires_at=expires)
        db.session.add(ann)
        db.session.commit()
        flash('Announcement created', 'success')
        return redirect(url_for('admin.manage_announcements'))
    return render_template('admin/announcement_form.html')

@bp.route('/announcement/<int:ann_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_announcement(ann_id):
    ann = Announcement.query.get_or_404(ann_id)
    if request.method == 'POST':
        ann.title = request.form['title']
        ann.content = request.form['content']
        ann.image_url = request.form.get('image_url')
        expires_at = request.form.get('expires_at')
        ann.expires_at = datetime.fromisoformat(expires_at) if expires_at else None
        db.session.commit()
        flash('Announcement updated', 'success')
        return redirect(url_for('admin.manage_announcements'))
    return render_template('admin/announcement_form.html', announcement=ann)

@bp.route('/announcement/<int:ann_id>/delete', methods=['POST'])
@admin_required
def delete_announcement(ann_id):
    ann = Announcement.query.get_or_404(ann_id)
    db.session.delete(ann)
    db.session.commit()
    flash('Announcement deleted', 'success')
    return redirect(url_for('admin.manage_announcements'))

@bp.route('/landmarks')
@admin_required
def manage_landmarks():
    landmarks = LandmarkImage.query.all()
    return render_template('admin/landmarks.html', landmarks=landmarks)

@bp.route('/landmark/new', methods=['GET', 'POST'])
@admin_required
def new_landmark():
    if request.method == 'POST':
        title = request.form['title']
        caption = request.form.get('caption')
        file = request.files['image']
        if file:
            filename = secure_filename(file.filename)
            upload_folder = current_app.config['UPLOAD_FOLDER']
            filepath = os.path.join(upload_folder, filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            file.save(filepath)
            image_url = f'uploads/{filename}'
            lm = LandmarkImage(title=title, image_url=image_url, caption=caption)
            db.session.add(lm)
            db.session.commit()
            flash('Landmark image added', 'success')
            return redirect(url_for('admin.manage_landmarks'))
    return render_template('admin/landmark_form.html')

@bp.route('/landmark/<int:landmark_id>/delete', methods=['POST'])
@admin_required
def delete_landmark(landmark_id):
    landmark = LandmarkImage.query.get_or_404(landmark_id)

    # Delete the physical file if it exists
    if landmark.image_url and landmark.image_url.startswith('uploads/'):
        try:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], landmark.image_url.replace('uploads/', ''))
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file: {e}")

    # Delete from database
    db.session.delete(landmark)
    db.session.commit()
    flash(f'Landmark "{landmark.title}" has been deleted', 'success')
    return redirect(url_for('admin.manage_landmarks'))

@bp.route('/ai-metrics')
@admin_required
def ai_metrics():
    # Get AI metrics data

    # Overall statistics
    total_operations = AIMetrics.query.count()
    successful_operations = AIMetrics.query.filter_by(success=True).count()
    success_rate = (successful_operations / total_operations * 100) if total_operations > 0 else 0

    # Operations by type
    operations_by_type = db.session.query(
        AIMetrics.operation,
        func.count(AIMetrics.id).label('count'),
        func.avg(AIMetrics.response_time).label('avg_time'),
        func.sum(case((AIMetrics.success == True, 1), else_=0)).label('success_count')
    ).group_by(AIMetrics.operation).all()

    # Operations by provider
    operations_by_provider = db.session.query(
        AIMetrics.provider,
        func.count(AIMetrics.id).label('count'),
        func.avg(AIMetrics.response_time).label('avg_time'),
        func.sum(case((AIMetrics.success == True, 1), else_=0)).label('success_count')
    ).group_by(AIMetrics.provider).all()

    # Recent errors
    recent_errors = AIMetrics.query.filter_by(success=False).order_by(AIMetrics.created_at.desc()).limit(10).all()

    # Performance over time (last 7 days)
    from datetime import datetime, timedelta
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    daily_stats = db.session.query(
        func.date(AIMetrics.created_at).label('date'),
        func.count(AIMetrics.id).label('total'),
        func.sum(case((AIMetrics.success == True, 1), else_=0)).label('successful')
    ).filter(AIMetrics.created_at >= seven_days_ago).group_by(func.date(AIMetrics.created_at)).order_by(func.date(AIMetrics.created_at)).all()

    return render_template('admin/ai_metrics.html',
                         total_operations=total_operations,
                         successful_operations=successful_operations,
                         success_rate=success_rate,
                         operations_by_type=operations_by_type,
                         operations_by_provider=operations_by_provider,
                         recent_errors=recent_errors,
                         daily_stats=daily_stats)


@bp.route('/export/<format>')
@admin_required
def export_data(format):
    suggestions = Suggestion.query.all()
    data = [{
        'ID': s.id,
        'Text': s.text,
        'Category': s.category,
        'Summary': s.summary,
        'Sentiment': s.sentiment,
        'Location': s.location,
        'Anonymous': s.is_anonymous,
        'Contact': s.contact_info,
        'Status': s.status,
        'Upvotes': s.upvotes,
        'Downvotes': s.downvotes,
        'Comments': len(s.comments),
        'Created At': s.created_at
    } for s in suggestions]
    df = pd.DataFrame(data)
    if format == 'csv':
        output = BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return send_file(output, mimetype='text/csv', download_name='suggestions.csv', as_attachment=True)
    elif format == 'excel':
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)
        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', download_name='suggestions.xlsx', as_attachment=True)

@bp.route('/system-status')
@admin_required
def system_status():
    ai_status = check_ai_service_status()
    import sys
    return render_template('admin/system_status.html',
                          ai_status=ai_status,
                          python_version=sys.version.split()[0],
                          flask_version='3.1.2')

@bp.route('/areas')
@admin_required
def manage_areas():
    areas = CommunityArea.query.order_by(CommunityArea.name).all()
    return render_template('admin/areas.html', areas=areas)

@bp.route('/areas/new', methods=['GET', 'POST'])
@login_required
def new_area():
    if request.method == 'POST':
        name = request.form['name'].strip()
        description = request.form.get('description', '').strip()

        if not name:
            flash('Area name is required', 'error')
            return redirect(url_for('admin.new_area'))

        # Check if area already exists
        existing = CommunityArea.query.filter_by(name=name).first()
        if existing:
            flash('Area with this name already exists', 'error')
            return redirect(url_for('admin.new_area'))

        area = CommunityArea(name=name, description=description)
        db.session.add(area)
        db.session.commit()
        flash('Community area added successfully!', 'success')
        return redirect(url_for('admin.manage_areas'))

    return render_template('admin/area_form.html')

@bp.route('/areas/<int:area_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_area(area_id):
    area = CommunityArea.query.get_or_404(area_id)

    if request.method == 'POST':
        name = request.form['name'].strip()
        description = request.form.get('description', '').strip()
        is_active = 'is_active' in request.form

        if not name:
            flash('Area name is required', 'error')
            return redirect(url_for('admin.edit_area', area_id=area_id))

        # Check if name conflicts with another area
        existing = CommunityArea.query.filter_by(name=name).filter(CommunityArea.id != area_id).first()
        if existing:
            flash('Area with this name already exists', 'error')
            return redirect(url_for('admin.edit_area', area_id=area_id))

        area.name = name
        area.description = description
        area.is_active = is_active
        db.session.commit()
        flash('Community area updated successfully!', 'success')
        return redirect(url_for('admin.manage_areas'))

    return render_template('admin/area_form.html', area=area)

@bp.route('/areas/<int:area_id>/toggle', methods=['POST'])
@admin_required
def toggle_area(area_id):
    area = CommunityArea.query.get_or_404(area_id)
    area.is_active = not area.is_active
    db.session.commit()
    status = 'activated' if area.is_active else 'deactivated'
    flash(f'Area "{area.name}" has been {status}', 'success')
    return redirect(url_for('admin.manage_areas'))

@bp.route('/areas/<int:area_id>/delete', methods=['POST'])
@admin_required
def delete_area(area_id):
    area = CommunityArea.query.get_or_404(area_id)

    # Check if area is being used by any suggestions
    usage_count = Suggestion.query.filter(Suggestion.location.like(f'{area.name}%')).count()

    if usage_count > 0:
        flash(f'Cannot delete area "{area.name}" - it is being used by {usage_count} suggestion(s)', 'error')
        return redirect(url_for('admin.manage_areas'))

    db.session.delete(area)
    db.session.commit()
    flash(f'Area "{area.name}" has been deleted', 'success')
    return redirect(url_for('admin.manage_areas'))
