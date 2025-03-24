# 修改导入语句，确保从正确的模块导入
from app import create_app
from app import socketio
import logging
import sys
import threading
import time
import traceback
import os
import base64  # 添加base64模块导入

# 创建自定义日志过滤器，更严格地过滤掉图像编码数据
class ImageDataFilter(logging.Filter):
    def filter(self, record):
        # 检查日志消息是否包含大量的编码数据
        if record.msg and isinstance(record.msg, str):
            # 检查是否包含base64编码特征
            if 'data:image' in record.msg or '/9j/' in record.msg:
                # 提取哈希值（如果存在）
                import re
                hash_match = re.search(r'\[哈希值: (\d+)\]', record.msg)
                if hash_match:
                    record.msg = f"[图像数据已过滤，哈希值: {hash_match.group(1)}]"
                else:
                    record.msg = "[图像数据已过滤]"
                return True
                
            # 检测base64字符串特征
            if len(record.msg) > 100 and any(c in record.msg for c in '+/='):
                # 计算base64特征字符的比例
                base64_chars = set('+/=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789')
                base64_ratio = sum(1 for c in record.msg if c in base64_chars) / len(record.msg)
                
                if base64_ratio > 0.6:  # 如果base64特征字符比例高
                    record.msg = "[可能的编码数据已过滤]"
                    return True
            
            # 检测非常长的消息
            if len(record.msg) > 500:
                # 如果消息过长，保留前100个字符
                record.msg = record.msg[:100] + "... [长消息已截断]"
                return True
                
        # 始终返回True，允许所有日志记录通过
        return True

# 配置日志 - 修改为更详细的配置，但不生成日志文件
logging.basicConfig(
    level=logging.INFO,  # 改为INFO級別以減少不必要的日誌
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # 只输出到控制台，不生成日志文件
    ]
)

# 添加自定义过滤器到根日志记录器
root_logger = logging.getLogger()
root_logger.addFilter(ImageDataFilter())

# 添加启动信息
print("正在啟動應用...")
logger = logging.getLogger(__name__)

# 設置某些模塊的日誌級別為更高級別，減少不必要的輸出
logging.getLogger('engineio').setLevel(logging.ERROR)  # 從WARNING提高到ERROR
logging.getLogger('socketio').setLevel(logging.ERROR)  # 從WARNING提高到ERROR
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logger.info("正在初始化Flask應用")

# 確保這些模塊也應用了圖像過濾器
for logger_name in ['engineio', 'socketio', 'werkzeug']:
    logger = logging.getLogger(logger_name)
    logger.addFilter(ImageDataFilter())

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
        # 移除 cors_allowed_origins 參數，它應該在 SocketIO 初始化時設置
        socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
    except Exception as e:
        logger.error(f"應用啟動失敗: {str(e)}")
        traceback.print_exc()