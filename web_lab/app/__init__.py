import logging
import sys
import os
from flask import Flask, render_template
from flask_socketio import SocketIO
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

# 初始化扩展，但不绑定到应用实例
socketio = SocketIO(
    async_mode='threading',  # 使用threading模式
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True
)

login_manager = LoginManager()
# 設置登入視圖，需要在初始化後設置
setattr(login_manager, 'login_view', 'auth.login')  # 使用setattr動態設置屬性
bcrypt = Bcrypt()

# 添加user_loader回调函数
@login_manager.user_loader
def load_user(user_id):
    # 从app.models.user模块导入load_user函数
    from app.models.user import load_user as model_load_user
    return model_load_user(user_id)

def create_app(config_name='development'):
    """应用工厂函数"""
    app = Flask(__name__)
    
    # 根据环境选择配置
    if config_name == 'production':
        app.config.from_object('app.config.ProductionConfig')
    else:
        app.config.from_object('app.config.DevelopmentConfig')
    
    # 初始化应用
    from app.config import Config
    Config.init_app(app)

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('app.log', encoding='utf-8')
        ]
    )
    
    # 初始化扩展
    socketio.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    
    # 注册蓝图
    from app.routes.auth_routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.routes.main_routes import main_bp
    app.register_blueprint(main_bp)

    from app.routes.exercise_routes import exercise_bp
    app.register_blueprint(exercise_bp)

    from app.routes.api_routes import api_bp
    app.register_blueprint(api_bp)

    from app.routes.dashboard_routes import dashboard_bp  
    app.register_blueprint(dashboard_bp)  


    
    
    from app.routes.user_routes import user_bp
    from app.routes.game_routes import game_bp  # 添加游戏蓝图导入
    
   
    app.register_blueprint(user_bp)
    app.register_blueprint(game_bp)  # 注册游戏蓝图

    
    
    # 初始化模型
# 在應用上下文中執行模型加載

    with app.app_context():
        # 先加载姿态检测模型
        from app.services.pose_detection import load_models
        try:
            load_models()
            app.logger.info("姿态检测模型加载成功")
        except Exception as e:
            app.logger.error(f"加载姿态检测模型失败: {e}")
        
        # 再加载运动分类模型 - 确保在应用上下文中
        from app.services import exercise_service
        try:
            if hasattr(exercise_service, 'init_models'):
                exercise_service.init_models()
                app.logger.info("运动检测模型加载成功")
            else:
                exercise_service.load_exercise_models()
                app.logger.info("运动检测模型加载成功")
        except Exception as e:
            app.logger.error(f"加载运动检测模型失败: {e}")
        
        # 再加载運動分類模型
        from app.services import exercise_service
        try:
            if hasattr(exercise_service, 'init_models'):
                exercise_service.init_models()
                app.logger.info("运动检测模型加载成功")
            else:
                exercise_service.load_exercise_models()
                app.logger.info("运动检测模型加载成功")
        except Exception as e:
            app.logger.error(f"加载运动检测模型失败: {e}")
        
        # 設置錯誤處理
        @app.errorhandler(404)
        def page_not_found(e):
            return render_template('404.html'), 404
        
        @app.errorhandler(500)
        def internal_server_error(e):
            return render_template('500.html'), 500
        
        return app