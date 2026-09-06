from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from config import Config
from models import db, Center, Exam, ExamPaper, ActivityLog, User
from routes.auth import auth_bp
from routes.exams import exams_bp
from routes.centers import centers_bp
from routes.logs import logs_bp
from routes.users import users_bp
from routes.biometrics import biometrics_bp
import os
from datetime import datetime, date

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    CORS(app)
    db.init_app(app)
    
    # Ensure upload directory exists
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(exams_bp, url_prefix='/api/exams')
    app.register_blueprint(centers_bp, url_prefix='/api/centers')
    app.register_blueprint(logs_bp, url_prefix='/api/logs')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(biometrics_bp, url_prefix='/api/biometrics')
    
    # Serve Frontend static files
    @app.route('/')
    def serve_index():
        return send_from_directory('../frontend', 'index.html')
        
    @app.route('/<path:path>')
    def serve_static(path):
        if os.path.exists(os.path.join('../frontend', path)):
            return send_from_directory('../frontend', path)
        else:
            return send_from_directory('../frontend', 'index.html')

    @app.route('/api/dashboard/stats', methods=['GET'])
    def get_dashboard_stats():
        total_centers = Center.query.count()
        scheduled_exams = Exam.query.filter_by(status='scheduled').count()
        total_papers = ExamPaper.query.count()
        downloads_count = ActivityLog.query.filter_by(action='Paper Downloaded').count()
        
        recent_activity_logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(5).all()
        recent_activity = []
        for log in recent_activity_logs:
            user_info = log.user.username if log.user else 'Unknown'
            recent_activity.append({
                'action': log.action,
                'timestamp': log.timestamp.isoformat(),
                'user': user_info
            })
            
        upcoming_exams_data = Exam.query.filter(Exam.exam_date >= date.today()).order_by(Exam.exam_date.asc(), Exam.start_time.asc()).limit(5).all()
        upcoming_exams = [{
            'id': e.id,
            'exam_code': e.exam_code,
            'exam_name': e.exam_name,
            'date': e.exam_date.isoformat(),
            'time': e.start_time.isoformat()
        } for e in upcoming_exams_data]
        
        return jsonify({
            'total_centers': total_centers,
            'scheduled_exams': scheduled_exams,
            'total_papers': total_papers,
            'downloads_count': downloads_count,
            'recent_activity': recent_activity,
            'upcoming_exams': upcoming_exams
        })

    @app.route('/api/dashboard/center-stats/<int:center_id>', methods=['GET'])
    def get_center_dashboard_stats(center_id):
        # Simply return stats for a center
        scheduled_exams = Exam.query.filter_by(status='scheduled').count()
        recent_activity_logs = ActivityLog.query.filter_by(center_id=center_id).order_by(ActivityLog.timestamp.desc()).limit(5).all()
        recent_activity = []
        for log in recent_activity_logs:
            user_info = log.user.username if log.user else 'Unknown'
            recent_activity.append({
                'action': log.action,
                'timestamp': log.timestamp.isoformat(),
                'user': user_info
            })
            
        upcoming_exams_data = Exam.query.filter(Exam.exam_date >= date.today()).order_by(Exam.exam_date.asc(), Exam.start_time.asc()).limit(5).all()
        upcoming_exams = [{
            'id': e.id,
            'exam_code': e.exam_code,
            'exam_name': e.exam_name,
            'date': e.exam_date.isoformat(),
            'time': e.start_time.isoformat()
        } for e in upcoming_exams_data]
        
        return jsonify({
            'scheduled_exams': scheduled_exams,
            'recent_activity': recent_activity,
            'upcoming_exams': upcoming_exams
        })

    return app

def seed_initial_data(app):
    from models import db, User, Center, Exam, ActivityLog
    from flask_bcrypt import Bcrypt
    from datetime import date, time, timedelta

    bcrypt = Bcrypt(app)
    if not User.query.filter_by(username='admin').first():
        print("Auto-seeding initial database data...")
        try:
            # 1. Admin user
            hashed_pw = bcrypt.generate_password_hash('admin123').decode('utf-8')
            admin = User(username='admin', password_hash=hashed_pw, role='admin')
            db.session.add(admin)

            # 2. Centers
            c1 = Center(center_code='C001', center_name='Main Test Center', address='123 Education Blvd')
            c2 = Center(center_code='C002', center_name='City Exam Hall', address='456 University Ave')
            c3 = Center(center_code='C003', center_name='District Center', address='789 School Road')
            db.session.add_all([c1, c2, c3])
            db.session.commit()

            # 3. Center Users
            hashed_pw_c = bcrypt.generate_password_hash('center123').decode('utf-8')
            u1 = User(username='center_C001', password_hash=hashed_pw_c, role='center', center_id=c1.id)
            u2 = User(username='center_C002', password_hash=hashed_pw_c, role='center', center_id=c2.id)
            u3 = User(username='center_C003', password_hash=hashed_pw_c, role='center', center_id=c3.id)
            db.session.add_all([u1, u2, u3])
            db.session.commit()

            # 4. Sample Exams
            today = date.today()
            e1 = Exam(
                exam_code='MATH101', 
                exam_name='Mathematics Advanced', 
                subject='Mathematics', 
                exam_date=today + timedelta(days=7),
                start_time=time(9, 0),
                duration=180
            )
            e2 = Exam(
                exam_code='PHYS201', 
                exam_name='Physics Fundamentals', 
                subject='Physics', 
                exam_date=today + timedelta(days=14),
                start_time=time(14, 0),
                duration=120
            )
            e3 = Exam(
                exam_code='CHEM301', 
                exam_name='Organic Chemistry', 
                subject='Chemistry', 
                exam_date=today + timedelta(days=21),
                start_time=time(10, 30),
                duration=150
            )
            db.session.add_all([e1, e2, e3])
            db.session.commit()

            l1 = ActivityLog(user_id=admin.id, action='System Initialized', status='Success')
            db.session.add(l1)
            db.session.commit()
            print("Auto-seeding completed successfully.")
        except Exception as err:
            db.session.rollback()
            print(f"Error during auto-seeding: {err}")

app = create_app()

with app.app_context():
    db.create_all()
    seed_initial_data(app)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

