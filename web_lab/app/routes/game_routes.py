from flask import Blueprint, render_template, jsonify, request, current_app
import mysql.connector
import logging
from datetime import datetime

game_bp = Blueprint('game', __name__)
logger = logging.getLogger(__name__)

def get_db_connection():
    """获取数据库连接"""
    try:
        # 使用与其他模块相同的数据库配置
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

@game_bp.route('/game/map')
def game_map():
    """游戏地图页面"""
    # 从会话中获取用户名，如果没有则使用默认值
    username = request.args.get('username', '测试用户')
    return render_template('game_map.html', username=username)

@game_bp.route('/game/level/<int:level_id>')
def game_level(level_id):
    """游戏关卡页面"""
    return render_template('game_level.html', level_id=level_id)

@game_bp.route('/api/game/levels')
def get_levels():
    """获取所有关卡信息"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})
        
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT level_id, level_name, description, monster_count, monster_hp, exp_reward, image_url
            FROM game_levels
            ORDER BY level_id
        """)
        
        levels = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'levels': levels
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@game_bp.route('/api/game/user_progress')
def get_user_progress():
    """获取用户游戏进度"""
    user_id = request.args.get('user_id', '')
    
    if not user_id:
        return jsonify({'success': False, 'message': '缺少用户ID'})
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})
        
        cursor = conn.cursor(dictionary=True)
        
        # 获取用户进度
        cursor.execute("""
            SELECT current_level, total_exp
            FROM user_progress
            WHERE user_id = %s
        """, (user_id,))
        
        progress = cursor.fetchone()
        
        if not progress:
            # 如果没有记录，创建新记录
            cursor.execute("""
                INSERT INTO user_progress (user_id, current_level, total_exp)
                VALUES (%s, 1, 0)
            """, (user_id,))
            conn.commit()
            progress = {'current_level': 1, 'total_exp': 0}
        
        # 获取当前等级信息
        cursor.execute("""
            SELECT level_id, level_name, required_exp
            FROM game_levels
            WHERE level_id = %s
        """, (progress['current_level'],))
        
        current_level = cursor.fetchone()
        
        # 获取用户成就
        cursor.execute("""
            SELECT a.achievement_id, a.achievement_name, a.achievement_description, ua.unlocked_at
            FROM user_achievements ua
            JOIN achievements a ON ua.achievement_id = a.achievement_id
            WHERE ua.user_id = %s
            ORDER BY ua.unlocked_at DESC
        """, (user_id,))
        
        achievements = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'progress': progress,
            'current_level': current_level,
            'achievements': achievements
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@game_bp.route('/api/game/update_progress', methods=['POST'])
def update_progress():
    """更新用户游戏进度"""
    data = request.json
    user_id = data.get('user_id')
    exercise_type = data.get('exercise_type')
    reps = data.get('reps', 0)
    sets = data.get('sets', 0)
    
    if not user_id or not exercise_type:
        return jsonify({'success': False, 'message': '缺少必要参数'}), 400
        
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'}), 500
            
        cursor = conn.cursor(dictionary=True)
        
        # 计算获得的经验值 (简单公式: 重复次数 * 组数)
        exp_gained = reps * sets
        
        # 更新用户进度
        cursor.execute(
            """
            UPDATE user_game_progress 
            SET total_exp = total_exp + %s, 
                last_played = NOW() 
            WHERE user_id = %s
            """,
            (exp_gained, user_id)
        )
        
        # 获取更新后的用户进度
        cursor.execute("SELECT * FROM user_game_progress WHERE user_id = %s", (user_id,))
        progress = cursor.fetchone()
        
        # 检查是否可以升级
        cursor.execute(
            """
            SELECT * FROM game_levels 
            WHERE level_id > %s 
            ORDER BY level_id ASC 
            LIMIT 1
            """,
            (progress['current_level'],)
        )
        next_level = cursor.fetchone()
        
        level_up = False
        new_achievements = []
        
        if next_level and progress['total_exp'] >= next_level['required_exp']:
            # 升级到下一关
            cursor.execute(
                "UPDATE user_game_progress SET current_level = %s WHERE user_id = %s",
                (next_level['level_id'], user_id)
            )
            level_up = True
            
            # 添加升级成就
            achievement_name = f"解锁关卡: {next_level['level_name']}"
            cursor.execute(
                """
                INSERT INTO user_achievements 
                (user_id, achievement_name, achievement_description, unlocked_at, icon_path)
                VALUES (%s, %s, %s, NOW(), %s)
                """,
                (
                    user_id, 
                    achievement_name, 
                    f"成功解锁第{next_level['level_id']}关: {next_level['level_name']}",
                    f"/static/img/achievements/level_{next_level['level_id']}.png"
                )
            )
            
            new_achievements.append({
                'name': achievement_name,
                'description': f"成功解锁第{next_level['level_id']}关: {next_level['level_name']}"
            })
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'exp_gained': exp_gained,
            'level_up': level_up,
            'next_level': next_level if level_up else None,
            'new_achievements': new_achievements
        })
    except Exception as e:
        logger.error(f"更新用户进度时出错: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@game_bp.route('/complete_level', methods=['POST'])
def complete_level():
    """完成關卡"""
    data = request.json
    user_id = data.get('user_id', 'C111151146')
    level_id = data.get('level_id', 1)
    
    try:
        # 從文件讀取關卡數據
        with open(LEVELS_FILE, 'r', encoding='utf-8') as f:
            levels_data = json.load(f)
        
        # 查找指定ID的關卡
        level = next((level for level in levels_data if level['level_id'] == level_id), None)
        
        if not level:
            return jsonify({'success': False, 'error': f'關卡 {level_id} 不存在'})
        
        # 從文件讀取用戶進度數據
        with open(USER_PROGRESS_FILE, 'r', encoding='utf-8') as f:
            user_progress_data = json.load(f)
        
        # 如果用戶不存在，創建默認進度
        if user_id not in user_progress_data:
            user_progress_data[user_id] = {
                'current_level': 1,
                'total_exp': 0,
                'level': 1,
                'next_level_exp': 100,
                'achievements': []
            }
        
        # 獲取用戶當前進度
        user_progress = user_progress_data[user_id]
        
        # 增加經驗值
        exp_reward = level.get('exp_reward', 50)
        user_progress['total_exp'] += exp_reward
        
        # 計算等級
        level_thresholds = [0, 100, 250, 450, 700, 1000, 1350, 1750, 2200, 2700, 3250]  # 每級所需經驗值
        user_level = 1
        for i, threshold in enumerate(level_thresholds):
            if user_progress['total_exp'] >= threshold:
                user_level = i + 1
        
        user_progress['level'] = user_level
        
        # 設置下一級所需經驗值
        if user_level < len(level_thresholds):
            user_progress['next_level_exp'] = level_thresholds[user_level]
        else:
            user_progress['next_level_exp'] = level_thresholds[-1] + 500 * (user_level - len(level_thresholds) + 1)
        
        # 解鎖下一關卡 - 無條件解鎖，只要當前關卡完成
        next_level_id = level_id + 1
        if next_level_id <= len(levels_data):
            user_progress['current_level'] = next_level_id
            print(f"用戶 {user_id} 已解鎖關卡 {next_level_id}")
        
        # 檢查是否解鎖新成就
        achievements = []
        
        # 成就1: 完成第一個關卡
        if level_id == 1 and not any(a.get('achievement_id') == 1 for a in user_progress.get('achievements', [])):
            achievements.append({
                'achievement_id': 1,
                'achievement_name': '初出茅廬',
                'achievement_description': '完成第一個關卡',
                'unlocked_at': datetime.now().isoformat()
            })
        
        # 成就2: 完成5個關卡
        completed_levels = sum(1 for l in levels_data if l['level_id'] <= user_progress['current_level'] - 1)
        if completed_levels >= 5 and not any(a.get('achievement_id') == 2 for a in user_progress.get('achievements', [])):
            achievements.append({
                'achievement_id': 2,
                'achievement_name': '初級冒險家',
                'achievement_description': '完成5個關卡',
                'unlocked_at': datetime.now().isoformat()
            })
        
        # 成就3: 達到3級
        if user_level >= 3 and not any(a.get('achievement_id') == 3 for a in user_progress.get('achievements', [])):
            achievements.append({
                'achievement_id': 3,
                'achievement_name': '成長之路',
                'achievement_description': '達到3級',
                'unlocked_at': datetime.now().isoformat()
            })
        
        # 添加新解鎖的成就
        if 'achievements' not in user_progress:
            user_progress['achievements'] = []
        
        user_progress['achievements'].extend(achievements)
        
        # 保存到文件
        with open(USER_PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_progress_data, f, ensure_ascii=False, indent=4)
        
        return jsonify({
            'success': True, 
            'message': f'成功完成關卡 {level_id}',
            'user_data': user_progress,
            'achievements': achievements
        })
    except Exception as e:
        print(f"完成關卡時出錯: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@game_bp.route('/api/game/defeat_monster', methods=['POST'])
def defeat_monster():
    """记录击败怪物"""
    data = request.json
    user_id = data.get('user_id')
    monster_id = data.get('monster_id')
    
    if not user_id or not monster_id:
        return jsonify({'success': False, 'message': '缺少必要参数'}), 400
        
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'}), 500
            
        cursor = conn.cursor(dictionary=True)
        
        # 更新击败怪物数量
        cursor.execute(
            "UPDATE user_game_progress SET monsters_defeated = monsters_defeated + 1 WHERE user_id = %s",
            (user_id,)
        )
        
        # 获取更新后的用户进度
        cursor.execute("SELECT * FROM user_game_progress WHERE user_id = %s", (user_id,))
        progress = cursor.fetchone()
        
        # 检查是否达成成就
        new_achievements = []
        
        # 示例: 击败10个怪物的成就
        if progress['monsters_defeated'] == 10:
            achievement_name = "怪物猎人初级"
            cursor.execute(
                """
                INSERT INTO user_achievements 
                (user_id, achievement_name, achievement_description, unlocked_at, icon_path)
                VALUES (%s, %s, %s, NOW(), %s)
                """,
                (
                    user_id, 
                    achievement_name, 
                    "击败10个怪物",
                    "/static/img/achievements/monster_hunter_1.png"
                )
            )
            
            new_achievements.append({
                'name': achievement_name,
                'description': "击败10个怪物"
            })
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'monsters_defeated': progress['monsters_defeated'],
            'new_achievements': new_achievements
        })
    except Exception as e:
        logger.error(f"记录击败怪物时出错: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@game_bp.route('/api/game/achievements')
def get_achievements():
    """获取用户成就"""
    user_id = request.args.get('user_id', '')
    
    if not user_id:
        return jsonify({'success': False, 'message': '缺少用户ID'})
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})
        
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT a.achievement_id, a.achievement_name, a.achievement_description, a.icon, ua.unlocked_at
            FROM user_achievements ua
            JOIN achievements a ON ua.achievement_id = a.achievement_id
            WHERE ua.user_id = %s
            ORDER BY ua.unlocked_at DESC
        """, (user_id,))
        
        achievements = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'achievements': achievements
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@game_bp.route('/api/game/add_exp', methods=['POST'])
def add_exp():
    """增加用户经验值"""
    data = request.json
    user_id = data.get('user_id', '')
    exp = data.get('exp', 0)
    
    if not user_id or exp <= 0:
        return jsonify({'success': False, 'message': '参数错误'})
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'})
        
        cursor = conn.cursor(dictionary=True)
        
        # 获取用户当前进度
        cursor.execute("""
            SELECT current_level, total_exp
            FROM user_progress
            WHERE user_id = %s
        """, (user_id,))
        
        progress = cursor.fetchone()
        
        if not progress:
            # 如果没有记录，创建新记录
            cursor.execute("""
                INSERT INTO user_progress (user_id, current_level, total_exp)
                VALUES (%s, 1, %s)
            """, (user_id, exp))
            conn.commit()
            
            new_total_exp = exp
            new_level = 1
        else:
            # 更新经验值
            new_total_exp = progress['total_exp'] + exp
            
            # 检查是否升级
            cursor.execute("""
                SELECT level_id, required_exp
                FROM game_levels
                WHERE level_id > %s
                ORDER BY level_id
                LIMIT 1
            """, (progress['current_level'],))
            
            next_level = cursor.fetchone()
            
            if next_level and new_total_exp >= next_level['required_exp']:
                # 升级
                new_level = next_level['level_id']
                
                # 检查是否解锁成就
                check_and_unlock_achievements(cursor, user_id, new_level, new_total_exp)
            else:
                new_level = progress['current_level']
            
            # 更新用户进度
            cursor.execute("""
                UPDATE user_progress
                SET current_level = %s, total_exp = %s
                WHERE user_id = %s
            """, (new_level, new_total_exp, user_id))
            
            conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'new_exp': new_total_exp,
            'new_level': new_level,
            'exp_gained': exp
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})



def check_and_unlock_achievements(cursor, user_id, level, total_exp):
    """检查并解锁成就"""
    # 检查等级成就
    cursor.execute("""
        SELECT achievement_id
        FROM achievements
        WHERE achievement_type = 'level' AND requirement <= %s
        AND achievement_id NOT IN (
            SELECT achievement_id
            FROM user_achievements
            WHERE user_id = %s
        )
    """, (level, user_id))
    
    level_achievements = cursor.fetchall()
    
    # 检查经验值成就
    cursor.execute("""
        SELECT achievement_id
        FROM achievements
        WHERE achievement_type = 'exp' AND requirement <= %s
        AND achievement_id NOT IN (
            SELECT achievement_id
            FROM user_achievements
            WHERE user_id = %s
        )
    """, (total_exp, user_id))
    
    exp_achievements = cursor.fetchall()
    
    # 解锁成就
    for achievement in level_achievements + exp_achievements:
        cursor.execute("""
            INSERT INTO user_achievements (user_id, achievement_id, unlocked_at)
            VALUES (%s, %s, NOW())
        """, (user_id, achievement['achievement_id']))