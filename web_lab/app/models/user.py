import logging
from flask_login import UserMixin
from flask import current_app
from app.services.db_service import get_db_connection

logger = logging.getLogger(__name__)

class User(UserMixin):
    """用户模型类"""
    
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role
    
    def get_id(self):
        return str(self.id)
        return None

def load_user(user_id):
    """加载用户的回调函数，供Flask-Login使用"""
    try:
        logger.debug(f"尝试加载用户ID: {user_id}")
        conn = get_db_connection()
        if not conn:
            logger.error("无法连接数据库")
            return None
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user_data:
            logger.debug(f"成功加载用户: {user_data['username']}")
            return User(user_data['user_id'], user_data['username'], user_data['role'])
        else:
            logger.warning(f"未找到用户ID: {user_id}")
            return None
    except Exception as e:
        logger.error(f"加载用户时出错: {e}")
        return None

def user_exists(username):
    """检查用户名是否已存在"""
    conn = get_db_connection()
    if not conn:
        raise Exception("无法连接数据库")

    try:
        cursor = conn.cursor()
        query = "SELECT COUNT(*) FROM users WHERE username = %s"
        cursor.execute(query, (username,))
        count = cursor.fetchone()[0]
        return count > 0
    finally:
        cursor.close()
        conn.close()

def create_user(username, password_hash, role):
    """创建新用户"""
    conn = get_db_connection()
    if not conn:
        raise Exception("无法连接数据库")

    try:
        cursor = conn.cursor()
        query = """
        INSERT INTO users (username, password_hash, role)
        VALUES (%s, %s, %s)
        """
        cursor.execute(query, (username, password_hash, role))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise Exception(f"创建用户错误: {e}")
    finally:
        cursor.close()
        conn.close()