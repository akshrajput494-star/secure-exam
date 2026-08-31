from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Center(db.Model):
    __tablename__ = 'centers'
    id = db.Column(db.Integer, primary_key=True)
    center_code = db.Column(db.String(50), unique=True, nullable=False)
    center_name = db.Column(db.String(150), nullable=False)
    address = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='active')
    
    users = db.relationship('User', backref='center', lazy=True)
    activity_logs = db.relationship('ActivityLog', backref='center', lazy=True)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='center') # 'admin' or 'center'
    center_id = db.Column(db.Integer, db.ForeignKey('centers.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    activity_logs = db.relationship('ActivityLog', backref='user', lazy=True)

class Exam(db.Model):
    __tablename__ = 'exams'
    id = db.Column(db.Integer, primary_key=True)
    exam_code = db.Column(db.String(50), unique=True, nullable=False)
    exam_name = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    exam_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    duration = db.Column(db.Integer, nullable=False) # Duration in minutes
    status = db.Column(db.String(20), default='scheduled') # 'scheduled', 'active', 'completed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    exam_papers = db.relationship('ExamPaper', backref='exam', lazy=True)
    activity_logs = db.relationship('ActivityLog', backref='exam', lazy=True)

class ExamPaper(db.Model):
    __tablename__ = 'exam_papers'
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False) # Size in bytes
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    center_id = db.Column(db.Integer, db.ForeignKey('centers.id'), nullable=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=True)
    action = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    status = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Biometric(db.Model):
    __tablename__ = 'biometrics'
    id = db.Column(db.Integer, primary_key=True)
    center_id = db.Column(db.Integer, db.ForeignKey('centers.id'), nullable=False)
    head_name = db.Column(db.String(150), nullable=False)
    designation = db.Column(db.String(100), nullable=True)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')
    
    center = db.relationship('Center', backref=db.backref('biometrics', lazy=True))
