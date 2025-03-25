import mysql.connector
import logging
from mysql.connector import Error

logger = logging.getLogger(__name__)


def get_db_connection():
    """获取数据库连接"""
    try:
        # 数据库连接配置
        db_config = {
            'host': 'localhost',
            'user': 'nkust_user',
            'password': '1234',
            'database': 'nkust_exercise'
        }
        
        logger.info(f"嘗試連接到數據庫: {db_config['host']}/{db_config['database']}")
        conn = mysql.connector.connect(**db_config)
        
        if conn.is_connected():
            logger.info(f"成功連接到數據庫: {db_config['host']}/{db_config['database']}")
            return conn
        else:
            logger.error("數據庫連接失敗")
            return None
    except Error as e:
        logger.error(f"數據庫連接錯誤: {e}")
        return None
    except Exception as e:
        logger.error(f"獲取數據庫連接時出錯: {e}")
        return None

def test_db_connection():
    """测试数据库连接"""
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return result[0] == 1
        return False
    except Exception as e:
        logger.error(f"测试连接错误: {e}")
        return False

def check_users_table():
    """检查用户表是否存在"""
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("DESCRIBE users")
            columns = cursor.fetchall()
            cursor.close()
            conn.close()
            return len(columns) > 0
        return False
    except Exception as e:
        logger.error(f"检查表结构错误: {e}")
        return False