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
from flask import jsonify, request 

import mysql.connector
from mysql.connector import Error

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


def get_db_connection():
    """獲取數據庫連接"""
    try:
        conn = mysql.connector.connect(
            host='localhost',
            database='nkust_exercise',
            user='nkust_user',  # 替換為你的數據庫用戶名
            password='1234'   # 替換為你的數據庫密碼
        )
        if conn.is_connected():
            return conn
    except Error as e:
        logger.error(f"數據庫連接失敗: {e}")
        return None





# 初始化遊戲數據庫
def init_game_database():
    """初始化遊戲數據庫"""
    try:
        # 導入遊戲數據庫初始化腳本
        from scripts.init_game_db import create_game_tables, ensure_user_completed_levels_table
        
        # 創建遊戲相關的表格
        if create_game_tables():
            logger.info("遊戲數據庫初始化成功")
        else:
            logger.error("遊戲數據庫初始化失敗")
            
        # 特別確保 user_completed_levels 表結構正確
        if ensure_user_completed_levels_table():
            logger.info("user_completed_levels 表結構檢查成功")
        else:
            logger.error("user_completed_levels 表結構檢查失敗")
    except Exception as e:
        logger.error(f"遊戲數據庫初始化出錯: {str(e)}")
        traceback.print_exc()



@app.route('/api/fitness/dashboard', methods=['GET'])
def fitness_dashboard():
    conn = None
    cursor = None
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'message': '未提供用戶ID'}), 400
        
        # 添加詳細日誌記錄
        logger.info(f"API接收到用戶ID: {user_id} (類型: {type(user_id)})")
        
        # 確保user_id是字符串類型
        user_id = str(user_id).strip()
        
        conn = get_db_connection()
        if not conn:
            logger.error(f"用戶 {user_id} 的數據庫連接失敗")
            return jsonify({'success': False, 'message': '數據庫連接失敗'}), 500
            
        cursor = conn.cursor(dictionary=True)
        
        # 1. 檢查是否有數據
        cursor.execute("SELECT COUNT(*) as count FROM exercise_info WHERE student_id = %s", (user_id,))
        count_result = cursor.fetchone()
        record_count = count_result['count'] if count_result else 0
        logger.info(f"用戶 {user_id} 的運動記錄數量: {record_count}")
        
        # 如果沒有數據，返回空結果但仍然成功
        if record_count == 0:
            logger.warning(f"用戶 {user_id} 沒有運動記錄")
            return jsonify({
                'success': True,
                'total_weight': 0,
                'total_calories': 0,
                'total_training_time': 0,
                'training_frequency': 0,
                'calories_trend': [],
                'muscle_growth': {
                    'arms': 0, 'chest': 0, 'core': 0, 'legs': 0, 'shoulders': 0
                },
                'exercise_stats': [],
                'recent_exercises': []
            })
        
        # 2. 計算總重量
        cursor.execute("""
            SELECT SUM(weight) as total_weight
            FROM exercise_info
            WHERE student_id = %s
        """, (user_id,))
        total_weight = cursor.fetchone()['total_weight'] or 0
        logger.info(f"用戶 {user_id} 的總重量計算結果: {total_weight}")
        
        # 2. 計算總卡路里
        cursor.execute("""
            SELECT SUM(weight * reps * sets * 0.1) as total_calories
            FROM exercise_info
            WHERE student_id = %s
        """, (user_id,))
        total_calories = cursor.fetchone()['total_calories'] or 0

        # 3. 計算總訓練時間
        cursor.execute("""
            SELECT TIMESTAMPDIFF(MINUTE, MIN(timestamp), MAX(timestamp)) as total_duration
            FROM exercise_info
            WHERE student_id = %s
        """, (user_id,))
        total_training_time = cursor.fetchone()['total_duration'] or 0
        
        # 4. 計算訓練頻率
        cursor.execute("""
            SELECT COUNT(DISTINCT DATE(timestamp)) as training_days
            FROM exercise_info
            WHERE student_id = %s AND timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """, (user_id,))
        training_frequency = cursor.fetchone()['training_days'] or 0
        
        # 5. 計算熱量消耗趨勢
        cursor.execute("""
            SELECT DATE(timestamp) as date, 
                   SUM(weight * reps * sets * 0.1) as daily_calories
            FROM exercise_info
            WHERE student_id = %s AND timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY DATE(timestamp)
            ORDER BY date
        """, (user_id,))
        
        calories_result = cursor.fetchall()
        logger.info(f"用戶 {user_id} 的熱量趨勢查詢結果: {calories_result}")

        # 確保至少有一個數據點
        if not calories_result:
            logger.warning(f"用戶 {user_id} 沒有熱量消耗記錄，將使用默認值")
            calories_trend = [0]  # 至少提供一個默認值
        else:
            calories_trend = [float(row['daily_calories'] or 0) for row in calories_result]
        
        logger.info(f"用戶 {user_id} 的熱量趨勢數據: {calories_trend}")
        


        # 6. 計算肌肉群發展
        cursor.execute("""
            SELECT exercise_type, COUNT(*) as count
            FROM exercise_info
            WHERE student_id = %s
            GROUP BY exercise_type
        """, (user_id,))
        
        muscle_growth = {'arms': 0, 'chest': 0, 'legs': 0, 'shoulders': 0, 'core': 0}
        for row in cursor.fetchall():
            exercise_type = row['exercise_type']
            count = row['count']
            
            # 根據運動類型映射到肌肉群
            if exercise_type in ['bicep-curl', 'tricep-extension']:
                muscle_growth['arms'] += count * 2
            elif exercise_type in ['push-up', 'bench-press']:
                muscle_growth['chest'] += count * 3
            elif exercise_type in ['squat', 'lunge']:
                muscle_growth['legs'] += count * 4
            elif exercise_type in ['shoulder-press']:
                muscle_growth['shoulders'] += count * 3
            else:
                muscle_growth['core'] += count * 1
        
        # 6. 獲取運動類型統計
        cursor.execute("""
            SELECT exercise_type, COUNT(*) as count
            FROM exercise_info
            WHERE student_id = %s
            GROUP BY exercise_type
            ORDER BY count DESC
            LIMIT 5
        """, (user_id,))
        exercise_stats = [{'name': row['exercise_type'], 'count': row['count']} 
                         for row in cursor.fetchall()]
        
        # 7. 獲取最近訓練記錄
        cursor.execute("""
            SELECT exercise_type, timestamp as date, reps, sets
            FROM exercise_info
            WHERE student_id = %s
            ORDER BY timestamp DESC
            LIMIT 5
        """, (user_id,))
        recent_exercises = [{
            'date': row['date'].strftime('%Y-%m-%d'),
            'exercise': row['exercise_type'],
            'reps': row['reps']
        } for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        # 返回結果前記錄
        logger.info(f"成功獲取用戶 {user_id} 的健身數據，calories_trend={calories_trend}")
        
        return jsonify({
            'success': True,
            'total_weight': float(total_weight),
            'total_calories': float(total_calories),
            'total_training_time': int(total_training_time),
            'training_frequency': int(training_frequency),
            'calories_trend': [float(x) for x in calories_trend],
            'muscle_growth': {
                'arms': int(muscle_growth['arms']),
                'chest': int(muscle_growth['chest']),
                'core': int(muscle_growth['core']),
                'legs': int(muscle_growth['legs']),
                'shoulders': int(muscle_growth['shoulders'])
            },
            'exercise_stats': exercise_stats,
            'recent_exercises': recent_exercises
        })
        
    except Exception as e:
        logger.error(f"獲取用戶 {user_id if 'user_id' in locals() else '未知'} 的健身數據失敗: {str(e)}")
        return jsonify({'success': False, 'message': f'獲取數據失敗: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


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