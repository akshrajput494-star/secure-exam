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

app = create_app()

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

