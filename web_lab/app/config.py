import os

class Config:
    """基本配置类"""
    SECRET_KEY = "your_secret_key"
    
    # 数据库配置
    DB_CONFIG = {
        'host': 'localhost',
        'user': 'nkust_user',
        'password': '1234',
        'database': 'nkust_exercise'
    }
    
    # 文件上传配置
    UPLOAD_FOLDER = 'uploads'
    OUTPUT_FOLDER = 'output'
    ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
    # 模型路径配置
    MODEL_PATHS = {
        'squat': 'D:\\project_Main\\modles\\yolov8_squat_model\\weights\\best.pt',
        'bicep-curl': 'D:\\project_Main\\modles\\best_bicep.pt',
        'shoulder-press': 'D:\\project_Main\\modles\\yolov8_shoulder_model\\weights\\best.pt',
        'push-up': 'D:\\project_Main\\modles\\push-up_model\\weights\\pushup_best.pt',
        'pull-up': 'D:\\project_Main\\modles\\best_pullup.pt',
        'dumbbell-row':'D:\\project_Main\\modles\\dumbbellrow_train\\weights\\best.pt'
    }
    
    # 确保上传目录存在
    @staticmethod
    def init_app(app):
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
        os.makedirs('static/models', exist_ok=True)

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False