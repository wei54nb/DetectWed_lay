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
login_manager.login_view = 'auth.login'
bcrypt = Bcrypt()

# 添加user_loader回调函数
@login_manager.user_loader
def load_user(user_id):
    # 从app.models.user模块导入load_user函数
    from app.models.user import load_user as model_load_user
    return model_load_user(user_id)

def create_app(config_object='app.config.Config'):
    """应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(config_object)


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
    from app.routes.main_routes import main_bp
    app.register_blueprint(main_bp)
    
    from app.routes.exercise_routes import exercise_bp
    app.register_blueprint(exercise_bp)
    
    # 初始化模型
    with app.app_context():  # 添加应用上下文
        from app.services import exercise_service
        exercise_service.init_models()
    
    # 设置错误处理
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500
    
    return app