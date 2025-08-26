import os
import json
import hmac
import hashlib
from datetime import datetime
from pathlib import Path
import logging

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///phronisis.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

# Import models after db initialization
from models import User, Progress, Artifact, PeerReview, Event

def load_perspectives():
    """Load all perspectives from JSON files"""
    perspectives = []
    content_dir = Path("content/perspectives")
    
    if not content_dir.exists():
        content_dir.mkdir(parents=True, exist_ok=True)
        return perspectives
    
    for json_file in content_dir.glob("*.json"):
        try:
            with open(json_file, 'r') as f:
                perspective = json.load(f)
                perspectives.append(perspective)
        except Exception as e:
            logging.error(f"Error loading perspective {json_file}: {e}")
    
    # Sort by order field
    perspectives.sort(key=lambda x: x.get('order', 999))
    return perspectives

def get_perspective_by_slug(slug):
    """Get a specific perspective by slug"""
    perspectives = load_perspectives()
    for perspective in perspectives:
        if perspective['slug'] == slug:
            return perspective
    return None

def get_user_progress(user_id, perspective_slug):
    """Get user's progress for a perspective"""
    progress_records = Progress.query.filter_by(
        user_id=user_id, 
        perspective_slug=perspective_slug
    ).all()
    
    progress_dict = {}
    for record in progress_records:
        progress_dict[record.lesson_id] = {
            'status': record.status,
            'score': record.score
        }
    return progress_dict

def calculate_perspective_progress(user_id, perspective):
    """Calculate completion percentage for a perspective"""
    if not perspective.get('lessons'):
        return 0
    
    total_lessons = len(perspective['lessons'])
    completed_lessons = Progress.query.filter_by(
        user_id=user_id,
        perspective_slug=perspective['slug'],
        status='completed'
    ).count()
    
    return int((completed_lessons / total_lessons) * 100) if total_lessons > 0 else 0

def log_event(user_id, event_type, perspective_slug=None, lesson_id=None, meta=None):
    """Log an analytics event"""
    event = Event(
        user_id=user_id,
        type=event_type,
        perspective_slug=perspective_slug,
        lesson_id=lesson_id,
        meta=json.dumps(meta) if meta else None,
        created_at=datetime.utcnow()
    )
    db.session.add(event)
    db.session.commit()

def require_auth(f):
    """Decorator to require authentication"""
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def require_admin(f):
    """Decorator to require admin privileges"""
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash('Admin access required')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        display_name = request.form['display_name'].strip()
        
        if not email or not password or not display_name:
            flash('All fields are required')
            return render_template('register.html')
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return render_template('register.html')
        
        # Create new user
        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            display_name=display_name,
            is_admin=False,
            created_at=datetime.utcnow()
        )
        
        db.session.add(user)
        db.session.commit()
        
        session['user_id'] = user.id
        flash('Registration successful!')
        return redirect(url_for('dashboard'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully')
    return redirect(url_for('login'))

@app.route('/dashboard')
@require_auth
def dashboard():
    user = User.query.get(session['user_id'])
    perspectives = load_perspectives()
    
    # Add progress info to each perspective
    for perspective in perspectives:
        perspective['progress'] = calculate_perspective_progress(user.id, perspective)
    
    # Calculate streak (simplified - days with events in last week)
    recent_events = Event.query.filter_by(user_id=user.id).filter(
        Event.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    ).count()
    
    streak = min(recent_events, 7)  # Simple streak calculation
    
    return render_template('dashboard.html', 
                         user=user, 
                         perspectives=perspectives, 
                         streak=streak)

@app.route('/perspectives/<slug>')
@require_auth
def perspective_detail(slug):
    user = User.query.get(session['user_id'])
    perspective = get_perspective_by_slug(slug)
    
    if not perspective:
        flash('Perspective not found')
        return redirect(url_for('dashboard'))
    
    # Get user's progress for this perspective
    progress = get_user_progress(user.id, slug)
    
    # Add progress info to lessons
    for lesson in perspective.get('lessons', []):
        lesson_progress = progress.get(lesson['id'], {})
        lesson['status'] = lesson_progress.get('status', 'not_started')
        lesson['score'] = lesson_progress.get('score')
    
    return render_template('perspective.html', 
                         user=user, 
                         perspective=perspective)

@app.route('/lesson/<slug>/<lesson_id>', methods=['GET', 'POST'])
@require_auth
def lesson_detail(slug, lesson_id):
    user = User.query.get(session['user_id'])
    perspective = get_perspective_by_slug(slug)
    
    if not perspective:
        flash('Perspective not found')
        return redirect(url_for('dashboard'))
    
    # Find the lesson
    lesson = None
    for l in perspective.get('lessons', []):
        if l['id'] == lesson_id:
            lesson = l
            break
    
    if not lesson:
        flash('Lesson not found')
        return redirect(url_for('perspective_detail', slug=slug))
    
    # Get current progress
    progress = Progress.query.filter_by(
        user_id=user.id,
        perspective_slug=slug,
        lesson_id=lesson_id
    ).first()
    
    if not progress:
        # Create new progress record
        progress = Progress(
            user_id=user.id,
            perspective_slug=slug,
            lesson_id=lesson_id,
            status='started',
            score=0,
            updated_at=datetime.utcnow()
        )
        db.session.add(progress)
        db.session.commit()
        
        # Log lesson started event
        log_event(user.id, 'lesson_started', slug, lesson_id)
    
    quiz_result = None
    minigame_result = None
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'submit_quiz':
            # Handle quiz submission
            selected_answer = int(request.form.get('answer', -1))
            quick_check = lesson.get('quick_checks', [{}])[0]  # Assuming one quick check per lesson
            correct_answer = quick_check.get('answer_index', 0)
            
            is_correct = selected_answer == correct_answer
            score = 100 if is_correct else 0
            
            # Update progress
            progress.score = max(progress.score, score)
            progress.updated_at = datetime.utcnow()
            db.session.commit()
            
            # Log event
            log_event(user.id, 'quiz_attempted', slug, lesson_id, {
                'correct': is_correct,
                'score': score
            })
            
            quiz_result = {
                'correct': is_correct,
                'selected': selected_answer,
                'correct_answer': correct_answer,
                'feedback': quick_check.get('feedback', [])
            }
        
        elif action == 'submit_minigame':
            # Handle minigame submission
            selected_option = request.form.get('minigame_choice')
            minigame = lesson.get('minigame', {})
            correct_option = minigame.get('correct_option')
            
            is_correct = selected_option == correct_option
            
            # Log event
            log_event(user.id, 'minigame_played', slug, lesson_id, {
                'game_type': minigame.get('type'),
                'correct': is_correct,
                'selected': selected_option
            })
            
            minigame_result = {
                'correct': is_correct,
                'selected': selected_option,
                'explanation': minigame.get('explanation', '')
            }
        
        elif action == 'mark_complete':
            # Mark lesson as completed
            progress.status = 'completed'
            progress.updated_at = datetime.utcnow()
            db.session.commit()
            
            # Log completion event
            log_event(user.id, 'lesson_completed', slug, lesson_id)
            
            flash('Lesson completed!')
            return redirect(url_for('perspective_detail', slug=slug))
    
    return render_template('lesson.html', 
                         user=user, 
                         perspective=perspective, 
                         lesson=lesson,
                         progress=progress,
                         quiz_result=quiz_result,
                         minigame_result=minigame_result)

@app.route('/creator/<slug>', methods=['GET', 'POST'])
@require_auth
def creator_challenge(slug):
    user = User.query.get(session['user_id'])
    perspective = get_perspective_by_slug(slug)
    
    if not perspective:
        flash('Perspective not found')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        body_text = request.form.get('body_text', '').strip()
        
        if not title or not body_text:
            flash('Both title and content are required')
            return render_template('creator.html', user=user, perspective=perspective)
        
        # Create artifact
        artifact = Artifact(
            user_id=user.id,
            perspective_slug=slug,
            title=title,
            body_text=body_text,
            created_at=datetime.utcnow()
        )
        
        db.session.add(artifact)
        db.session.commit()
        
        # Log event
        log_event(user.id, 'artifact_submitted', slug)
        
        flash('Artifact submitted successfully!')
        return redirect(url_for('perspective_detail', slug=slug))
    
    return render_template('creator.html', user=user, perspective=perspective)

@app.route('/peer-review/queue', methods=['GET', 'POST'])
@require_auth
def peer_review_queue():
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        action = request.form.get('action')
        artifact_id = request.form.get('artifact_id')
        
        if action == 'submit_review':
            # Handle review submission
            clarity = int(request.form.get('clarity', 1))
            logic = int(request.form.get('logic', 1))
            fairness = int(request.form.get('fairness', 1))
            comments = request.form.get('comments', '').strip()
            
            review = PeerReview(
                artifact_id=artifact_id,
                reviewer_id=user.id,
                clarity=clarity,
                logic=logic,
                fairness=fairness,
                comments=comments,
                created_at=datetime.utcnow()
            )
            
            db.session.add(review)
            db.session.commit()
            
            # Log event
            log_event(user.id, 'peer_review_completed')
            
            flash('Review submitted successfully!')
            return redirect(url_for('peer_review_queue'))
        
        elif action == 'report':
            # Handle report (just log event)
            log_event(user.id, 'artifact_reported', meta={'artifact_id': artifact_id})
            flash('Artifact reported. Thank you for your feedback.')
            return redirect(url_for('peer_review_queue'))
    
    # Find next artifact to review (not authored by current user, not already reviewed)
    reviewed_artifact_ids = db.session.query(PeerReview.artifact_id).filter_by(reviewer_id=user.id).subquery()
    
    next_artifact = Artifact.query.filter(
        Artifact.user_id != user.id,
        ~Artifact.id.in_(reviewed_artifact_ids)
    ).first()
    
    return render_template('peer_review.html', user=user, artifact=next_artifact)

@app.route('/profile')
@require_auth
def profile():
    user = User.query.get(session['user_id'])
    
    # Get user's progress by perspective
    perspectives = load_perspectives()
    progress_by_perspective = {}
    
    for perspective in perspectives:
        progress_by_perspective[perspective['slug']] = {
            'title': perspective['title'],
            'progress': calculate_perspective_progress(user.id, perspective)
        }
    
    # Get user's artifacts
    artifacts = Artifact.query.filter_by(user_id=user.id).order_by(Artifact.created_at.desc()).all()
    
    # Get reviews received on user's artifacts
    reviews_received = db.session.query(PeerReview).join(Artifact).filter(
        Artifact.user_id == user.id
    ).order_by(PeerReview.created_at.desc()).all()
    
    return render_template('profile.html', 
                         user=user, 
                         progress_by_perspective=progress_by_perspective,
                         artifacts=artifacts,
                         reviews_received=reviews_received)

@app.route('/admin/upload', methods=['GET', 'POST'])
def admin_upload():
    # Check admin access
    admin_authenticated = False
    
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user and user.is_admin:
            admin_authenticated = True
    
    # Handle admin code authentication
    if request.method == 'POST' and request.form.get('action') == 'authenticate':
        admin_code = request.form.get('admin_code', '')
        expected_code = os.environ.get('ADMIN_CODE', 'letmein')
        
        if hmac.compare_digest(admin_code, expected_code):
            session['admin_authenticated'] = True
            admin_authenticated = True
        else:
            flash('Invalid admin code')
    
    if 'admin_authenticated' in session:
        admin_authenticated = True
    
    if not admin_authenticated:
        return render_template('admin_upload.html', 
                             authenticated=False, 
                             user=User.query.get(session.get('user_id')))
    
    if request.method == 'POST' and request.form.get('action') == 'upload':
        if 'json_file' not in request.files:
            flash('No file selected')
            return redirect(request.url)
        
        file = request.files['json_file']
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        
        if file and file.filename.lower().endswith('.json'):
            try:
                # Parse and validate JSON
                content = json.loads(file.read().decode('utf-8'))
                
                # Basic validation
                required_fields = ['slug', 'title', 'summary', 'order', 'lessons']
                for field in required_fields:
                    if field not in content:
                        flash(f'Missing required field: {field}')
                        return redirect(request.url)
                
                # Save file
                filename = secure_filename(f"{content['slug']}.json")
                content_dir = Path("content/perspectives")
                content_dir.mkdir(parents=True, exist_ok=True)
                
                filepath = content_dir / filename
                with open(filepath, 'w') as f:
                    json.dump(content, f, indent=2)
                
                flash(f'Perspective "{content["title"]}" uploaded successfully!')
                
            except json.JSONDecodeError:
                flash('Invalid JSON file')
            except Exception as e:
                flash(f'Error uploading file: {str(e)}')
        else:
            flash('Please upload a JSON file')
    
    return render_template('admin_upload.html', 
                         authenticated=True, 
                         user=User.query.get(session.get('user_id')))

@app.route('/debug/events')
@require_admin
def debug_events():
    user = User.query.get(session['user_id'])
    events = Event.query.order_by(Event.created_at.desc()).limit(100).all()
    
    return render_template('debug_events.html', user=user, events=events)

# Create tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
