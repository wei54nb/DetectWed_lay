import logging
import mysql.connector
from mysql.connector import Error
from flask import current_app

logger = logging.getLogger(__name__)

def get_db_connection():
    """获取数据库连接"""
    try:
        # 从配置中获取数据库配置
        db_config = {
            'host': 'localhost',
            'user': 'nkust_user',
            'password': '1234',
            'database': 'nkust_exercise'
        }
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        if err.errno == mysql.connector.errorcode.ER_ACCESS_DENIED_ERROR:
            logger.error("数据库用户名或密码错误")
        elif err.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:
            logger.error("数据库不存在")
        else:
            logger.error(f"数据库连接错误: {err}")
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