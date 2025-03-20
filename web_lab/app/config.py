import os

class Config:
    """基本配置类"""
    SECRET_KEY = "your_secret_key"
    
    # 获取项目根目录
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 数据库配置
    DB_CONFIG = {
        'host': 'localhost',
        'user': 'nkust_user',
        'password': '1234',
        'database': 'nkust_exercise'
    }
    @staticmethod
    def init_app(app):
        pass
    
    # 文件上传配置
    UPLOAD_FOLDER = 'uploads'
    OUTPUT_FOLDER = 'output'
    ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    
    # 模型路径配置 - 使用相对路径
    MODEL_PATHS = {
        'squat': os.path.join('static', 'models', 'YOLO_MODLE', 'squat_model', 'best.pt'),
        'bicep-curl': os.path.join('static', 'models', 'YOLO_MODLE', 'bicep_curl', 'best.pt'),
        'shoulder-press': os.path.join('static', 'models', 'YOLO_MODLE', 'shoulder_press', 'best.pt'),
        'push-up': os.path.join('static', 'models', 'YOLO_MODLE', 'push_up', 'best.pt'),
        'pull-up': os.path.join('static', 'models', 'YOLO_MODLE', 'pull_up', 'best.pt'),
        'dumbbell-row': os.path.join('static', 'models', 'YOLO_MODLE', 'dumbbell_row', 'best.pt'),
        'pose': os.path.join('static', 'models', 'YOLO_MODLE', 'pose', 'yolov8n-pose.pt')
    }
    
    # 确保上传目录存在
    @staticmethod
    def init_app(app):
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
        
        # 确保模型目录存在
        models_dir = os.path.join('static', 'models', 'YOLO_MODLE')
        os.makedirs(models_dir, exist_ok=True)
        
        # 确保各个模型子目录存在
        for model_type in ['squat_model', 'bicep_curl', 'shoulder_press', 'push_up', 'pull_up', 'dumbbell_row', 'pose']:
            os.makedirs(os.path.join(models_dir, model_type), exist_ok=True)

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False