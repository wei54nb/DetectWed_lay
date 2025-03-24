from flask import Blueprint, jsonify, request, render_template
from flask_login import current_user, login_required
import mysql.connector
import logging
from datetime import datetime

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


@dashboard_bp.route('/api/exercise_data', methods=['GET'])
def get_exercise_data():
    """获取运动数据，专门为前端图表设计"""
    try:
        # 获取用户ID参数
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': '未提供用户ID'}), 400
            
        # 连接数据库
        connection = get_db_connection()
        if not connection:
            logger.error("无法连接到数据库")
            return jsonify({'success': False, 'message': '数据库连接失败'}), 500
        
        cursor = connection.cursor(dictionary=True)
        
        # 查询exercise_info表中的数据，按日期分组，并根据用户ID过滤
        cursor.execute("""
            SELECT 
                DATE(timestamp) as date,
                exercise_type,
                SUM(sets) as total_sets,
                SUM(reps) as total_reps
            FROM exercise_info
            WHERE student_id = %s
            GROUP BY DATE(timestamp), exercise_type
            ORDER BY date DESC
            LIMIT 30
        """, (user_id,))
        
        records = cursor.fetchall()
        
        # 转换日期格式，确保JSON可序列化
        for record in records:
            if isinstance(record['date'], datetime):
                record['date'] = record['date'].strftime('%Y-%m-%d')
        
        cursor.close()
        connection.close()
        
        logger.info(f"成功获取用户 {user_id} 的 {len(records)} 条运动记录(按日期分组)")
        
        # 返回JSON格式的数据
        return jsonify({
            'success': True,
            'data': records
        })
    
    except Exception as e:
        logger.error(f"获取运动数据时出错: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500