from datetime import datetime
from app import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    progress = db.relationship('Progress', backref='user', lazy=True, cascade='all, delete-orphan')
    artifacts = db.relationship('Artifact', backref='user', lazy=True, cascade='all, delete-orphan')
    peer_reviews = db.relationship('PeerReview', backref='reviewer', lazy=True, cascade='all, delete-orphan')
    events = db.relationship('Event', backref='user', lazy=True, cascade='all, delete-orphan')

class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    perspective_slug = db.Column(db.String(100), nullable=False)
    lesson_id = db.Column(db.String(100), nullable=False)
    status = db.Column(db.Enum('not_started', 'started', 'completed', name='progress_status'), 
                      default='not_started', nullable=False)
    score = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Ensure unique progress per user, perspective, lesson
    __table_args__ = (db.UniqueConstraint('user_id', 'perspective_slug', 'lesson_id'),)

class Artifact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    perspective_slug = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    body_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    peer_reviews = db.relationship('PeerReview', backref='artifact', lazy=True, cascade='all, delete-orphan')

class PeerReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    artifact_id = db.Column(db.Integer, db.ForeignKey('artifact.id'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    clarity = db.Column(db.Integer, nullable=False)  # 1-5 scale
    logic = db.Column(db.Integer, nullable=False)    # 1-5 scale
    fairness = db.Column(db.Integer, nullable=False) # 1-5 scale
    comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Ensure one review per reviewer per artifact
    __table_args__ = (db.UniqueConstraint('artifact_id', 'reviewer_id'),)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # lesson_started, lesson_completed, etc.
    perspective_slug = db.Column(db.String(100))
    lesson_id = db.Column(db.String(100))
    meta = db.Column(db.Text)  # JSON string for additional data
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
