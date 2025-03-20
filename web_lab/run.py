# 修改导入语句，确保从正确的模块导入
from app import create_app
from app import socketio
import logging
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
print("正在啟動應用...")
logger = logging.getLogger(__name__)
logger.info("正在初始化Flask應用")

# 创建Flask应用实例
app = create_app()

# 確保靜態文件路徑設置正確
app.static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
app.static_url_path = '/static'

# 添加日誌以檢查靜態文件路徑
logger.info(f"靜態文件路徑: {app.static_folder}")
logger.info(f"靜態URL路徑: {app.static_url_path}")

# 初始化遊戲數據庫
def init_game_database():
    """初始化遊戲數據庫"""
    try:
        # 導入遊戲數據庫初始化腳本
        from scripts.init_game_db import create_game_tables
        
        # 創建遊戲相關的表格
        if create_game_tables():
            logger.info("遊戲數據庫初始化成功")
        else:
            logger.error("遊戲數據庫初始化失敗")
    except Exception as e:
        logger.error(f"遊戲數據庫初始化出錯: {str(e)}")
        traceback.print_exc()

# 在應用啟動前初始化遊戲數據庫
init_game_database()

if __name__ == '__main__':
    try:
        logger.info("正在啟動Flask應用")
        socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
    except Exception as e:
        logger.error(f"應用啟動失敗: {str(e)}")
        traceback.print_exc()