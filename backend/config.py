import os

basedir = os.path.abspath(os.path.dirname(__file__))
db_dir = os.path.abspath(os.path.join(basedir, '..', 'database'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'super-secret-exam-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f'sqlite:///{os.path.join(db_dir, "secure_exam.db")}')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
