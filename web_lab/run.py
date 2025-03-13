# 修改导入语句，确保从正确的模块导入
from app import create_app
from app import socketio
import logging  # 添加这一行导入logging模块
import sys
import threading
import time
import traceback
import os


# 配置日志 - 修改为更详细的配置
logging.basicConfig(
    level=logging.DEBUG,  # 改为DEBUG级别以显示更多信息
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # 确保日志输出到控制台
        logging.FileHandler('app.log', encoding='utf-8')
    ]
)

# 添加启动信息
print("正在启动应用...")#還是不行還是不行
logger = logging.getLogger(__name__)
logger.info("正在初始化Flask应用")

# 创建Flask应用实例
app = create_app()

app.static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
app.static_url_path = '/static'

# 添加心跳函数定义
def heartbeat():
    """发送心跳信号以保持服务器活跃"""
    logger.info("心跳线程已启动")
    while True:
        try:
            # 每30秒记录一次心跳信息
            logger.debug("服务器心跳正常")
            time.sleep(30)
        except Exception as e:
            logger.error(f"心跳线程出错: {e}")
            time.sleep(5)  # 出错后等待5秒再继续

# 添加资源清理函数
def cleanup_resources():
    """清理应用资源"""
    try:
        # 导入exercise_routes模块
        from app.routes.exercise_routes import detection_active
        from app.routes import exercise_routes
        # 停止检测线程
        if detection_active:
            logger.info("正在停止检测线程...")
            exercise_routes.detection_active = False  # 直接修改模塊中的變量
            time.sleep(1)  # 给线程一些时间停止
        
        # 清理摄像头资源
        from app.services.camera_service import release_camera
        release_camera()
        
        logger.info("资源清理完成")
    except Exception as e:
        logger.error(f"清理资源时出错: {e}")

if __name__ == '__main__':
    # 添加更多启动信息
    print(f"应用已初始化，正在启动服务器在 http://localhost:5000")
    logger.info("服务器正在启动...")
    
    # 启动心跳线程
    heartbeat_thread = threading.Thread(target=heartbeat, daemon=True)
    heartbeat_thread.start()
    
    # 使用socketio启动应用而不是app.run()
    print("服务器已启动，等待连接...")
    try:
        # 尝试使用不同的参数启动socketio
        socketio.run(
            app, 
            host='0.0.0.0', 
            port=5000, 
            debug=True, 
            allow_unsafe_werkzeug=True,
            use_reloader=False  # 禁用重载器，可能导致问题
        )
    except Exception as e:
        logger.error(f"启动服务器时出错: {e}")
        logger.error(traceback.format_exc())
    finally:
        # 清理资源
        cleanup_resources()
        
        # 这行代码通常不会执行，除非socketio.run()返回
        logger.warning("socketio.run() 已返回，服务器可能已停止")
        # 保持程序运行，不让它立即退出
        print("服务器已停止，按Ctrl+C退出程序...")
        try:
            # 防止程序立即退出
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("程序已手动停止")