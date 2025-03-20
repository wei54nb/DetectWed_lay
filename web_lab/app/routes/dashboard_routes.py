from flask import Blueprint, jsonify, current_app
import mysql.connector
import logging
from datetime import datetime, timedelta

dashboard_bp = Blueprint('dashboard', __name__)
logger = logging.getLogger(__name__)


def get_db_connection():
    """获取数据库连接"""
    try:
        # 使用正确的数据库配置
        db_config = {
            'host': 'localhost',
            'user': 'nkust_user',
            'password': '1234',
            'database': 'nkust_exercise'
        }
        connection = mysql.connector.connect(**db_config)
        return connection
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        return None

@dashboard_bp.route('/api/dashboard_data', methods=['GET'])
def get_dashboard_data():
    """获取仪表盘数据"""
    try:
        # 连接数据库
        connection = get_db_connection()
        if not connection:
            logger.error("无法连接到数据库")
            return jsonify({'success': False, 'message': '数据库连接失败'}), 500
        
        cursor = connection.cursor(dictionary=True)
        
        # 查询exercise_info表中的所有记录
        cursor.execute("""
            SELECT id, student_id, weight, reps, sets, exercise_type, timestamp as date
            FROM exercise_info
            ORDER BY timestamp DESC
        """)
        
        records = cursor.fetchall()
        
        # 转换日期格式，确保JSON可序列化
        for record in records:
            if isinstance(record['date'], datetime):
                record['date'] = record['date'].strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.close()
        connection.close()
        
        logger.info(f"成功获取{len(records)}条运动记录")
        
        # 返回JSON格式的数据
        return jsonify({
            'success': True,
            'records': records
        })
    
    except Exception as e:
        logger.error(f"获取仪表盘数据时出错: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# 添加一个别名路由，以兼容可能的两种API调用方式
@dashboard_bp.route('/api/exercise_data', methods=['GET'])
def get_exercise_data():
    """获取运动数据（别名路由）"""
    return get_dashboard_data()