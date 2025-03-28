from flask import Blueprint, jsonify, request, session
from app.database import get_db_connection
import logging
from datetime import datetime, timedelta
import math

fitness_bp = Blueprint('fitness', __name__)
logger = logging.getLogger(__name__)

# 運動類型與肌肉群對應關係
EXERCISE_MUSCLE_MAP = {
    'squat': {
        'primary': ['quadriceps', 'glutes'],
        'secondary': ['lower_back', 'core'],
        'base_calorie': 0.5
    },
    'push-up': {
        'primary': ['chest', 'triceps'],
        'secondary': ['shoulders', 'core'],
        'base_calorie': 0.3
    },
    'bicep-curl': {
        'primary': ['biceps'],
        'secondary': ['forearms'],
        'base_calorie': 0.2
    },
    'shoulder-press': {
        'primary': ['deltoids'],
        'secondary': ['triceps', 'trapezius'],
        'base_calorie': 0.25
    },
    'dumbbell-row': {
        'primary': ['latissimus', 'rhomboids'],
        'secondary': ['biceps', 'forearms'],
        'base_calorie': 0.3
    }
}

# 肌肉群最佳訓練頻率（每週次數）
MUSCLE_OPTIMAL_FREQUENCY = {
    'quadriceps': 2, 'glutes': 2, 'lower_back': 2, 'core': 3,
    'chest': 2, 'triceps': 3, 'shoulders': 3, 'biceps': 3,
    'forearms': 3, 'deltoids': 3, 'trapezius': 2, 'latissimus': 2,
    'rhomboids': 2
}

@fitness_bp.route('/api/fitness/dashboard', methods=['GET'])
def get_fitness_dashboard():
    """獲取用戶健身儀表板數據"""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': '未提供用戶ID'}), 400
    
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("無法連接到數據庫")
            return jsonify({'success': False, 'message': '數據庫連接失敗'}), 500
            
        cursor = conn.cursor(dictionary=True)
        
        # 1. 計算總消耗熱量
        cursor.execute("""
            SELECT SUM(calories_burned) as total_calories
            FROM exercise_info
            WHERE student_id = %s
        """, (user_id,))
        total_calories = cursor.fetchone()['total_calories'] or 0
        
        # 2. 計算總訓練時間 (假設每次訓練平均10分鐘)
        cursor.execute("""
            SELECT COUNT(*) as session_count
            FROM exercise_info
            WHERE student_id = %s
        """, (user_id,))
        session_count = cursor.fetchone()['session_count']
        total_training_time = session_count * 10  # 每次訓練10分鐘
        
        # 3. 計算訓練頻率 (過去7天訓練次數)
        cursor.execute("""
            SELECT COUNT(DISTINCT DATE(timestamp)) as training_days
            FROM exercise_info
            WHERE student_id = %s AND timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """, (user_id,))
        training_frequency = cursor.fetchone()['training_days'] or 0
        
        # 4. 獲取熱量消耗趨勢 (最近7天)
        cursor.execute("""
            SELECT DATE(timestamp) as date, SUM(calories_burned) as daily_calories
            FROM exercise_info
            WHERE student_id = %s AND timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY DATE(timestamp)
            ORDER BY date
        """, (user_id,))
        calories_trend = [row['daily_calories'] for row in cursor.fetchall()]
        
        # 5. 計算肌肉群發展 (根據運動類型)
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
        
        return jsonify({
            'success': True,
            'total_calories': total_calories,
            'total_training_time': total_training_time,
            'training_frequency': training_frequency,
            'calories_trend': calories_trend,
            'muscle_growth': muscle_growth,
            'exercise_stats': exercise_stats,
            'recent_exercises': recent_exercises
        })
        
    except Exception as e:
        logger.error(f"獲取健身儀表板數據失敗: {e}")
        return jsonify({'success': False, 'message': '獲取數據失敗'}), 500




@fitness_bp.route('/api/fitness/recommendations', methods=['GET'])
def get_fitness_recommendations():
    """獲取用戶健身建議"""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': '未提供用戶ID'}), 400
    
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("無法連接到數據庫")
            return jsonify({'success': False, 'message': '數據庫連接失敗'}), 500
            
        cursor = conn.cursor(dictionary=True)
        
        # 獲取用戶運動記錄
        cursor.execute("""
            SELECT exercise_type, COUNT(*) as count, 
                   AVG(weight) as avg_weight, AVG(reps) as avg_reps, AVG(sets) as avg_sets
            FROM exercise_info 
            WHERE student_id = %s 
            GROUP BY exercise_type
        """, (user_id,))
        
        exercise_summary = cursor.fetchall()
        
        # 分析訓練不平衡
        muscle_training_count = {}
        for exercise in exercise_summary:
            exercise_type = exercise['exercise_type']
            if exercise_type in EXERCISE_MUSCLE_MAP:
                for muscle in EXERCISE_MUSCLE_MAP[exercise_type]['primary']:
                    if muscle not in muscle_training_count:
                        muscle_training_count[muscle] = 0
                    muscle_training_count[muscle] += exercise['count']
        
        # 找出訓練最少的肌肉群
        least_trained_muscles = []
        if muscle_training_count:
            min_count = min(muscle_training_count.values())
            least_trained_muscles = [muscle for muscle, count in muscle_training_count.items() if count <= min_count * 1.2]
        
        # 生成訓練建議
        recommendations = []
        
        # 1. 訓練不平衡建議
        if least_trained_muscles:
            recommended_exercises = []
            for muscle in least_trained_muscles:
                for exercise_type, info in EXERCISE_MUSCLE_MAP.items():
                    if muscle in info['primary'] and exercise_type not in recommended_exercises:
                        recommended_exercises.append(exercise_type)
            
            if recommended_exercises:
                recommendations.append({
                    'type': 'balance',
                    'message': f'您的{", ".join(least_trained_muscles)}肌群訓練較少，建議增加以下運動：{", ".join(recommended_exercises)}'
                })
        
        # 2. 進階訓練建議
        for exercise in exercise_summary:
            exercise_type = exercise['exercise_type']
            avg_weight = exercise['avg_weight']
            avg_reps = exercise['avg_reps']
            
            if avg_reps > 12:
                recommendations.append({
                    'type': 'progression',
                    'message': f'您的{exercise_type}平均次數已達{round(avg_reps, 1)}次，建議增加重量並減少次數到8-10次/組'
                })
            elif avg_weight > 0 and exercise['count'] > 10:
                recommendations.append({
                    'type': 'progression',
                    'message': f'您已完成{exercise["count"]}次{exercise_type}訓練，可以嘗試將重量從{round(avg_weight, 1)}kg提高5-10%'
                })
        
        # 關閉資源
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'recommendations': recommendations,
                'least_trained_muscles': least_trained_muscles,
                'exercise_summary': exercise_summary
            }
        })
        
    except Exception as e:
        logger.error(f"獲取健身建議時出錯: {e}")
        if conn:
            cursor.close()
            conn.close()
        return jsonify({'success': False, 'message': str(e)}), 500