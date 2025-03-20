from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
import logging
import mysql.connector
from app.models.user import User

# 创建蓝图
user_bp = Blueprint('user', __name__)
logger = logging.getLogger(__name__)

# 数据库连接函数
def get_db_connection():
    """获取数据库连接"""
    try:
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

@user_bp.route('/profile')
@login_required
def profile():
    """用户个人资料页面"""
    return render_template('user/profile.html', user=current_user)

@user_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """编辑用户个人资料"""
    if request.method == 'POST':
        # 获取表单数据
        name = request.form.get('name')
        email = request.form.get('email')
        
        try:
            # 更新用户信息
            conn = get_db_connection()
            if not conn:
                flash('数据库连接失败', 'danger')
                return redirect(url_for('user.profile'))
                
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET name = %s, email = %s WHERE id = %s",
                (name, email, current_user.id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            
            flash('个人资料更新成功', 'success')
            return redirect(url_for('user.profile'))
        except Exception as e:
            logger.error(f"更新用户资料失败: {e}")
            flash('更新个人资料失败', 'danger')
            return redirect(url_for('user.edit_profile'))
    
    return render_template('user/edit_profile.html', user=current_user)

@user_bp.route('/exercise/history')
@login_required
def exercise_history():
    """用户运动历史记录"""
    try:
        conn = get_db_connection()
        if not conn:
            flash('数据库连接失败', 'danger')
            return render_template('user/exercise_history.html', records=[])
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT * FROM exercise_records 
            WHERE user_id = %s 
            ORDER BY date DESC
            """,
            (current_user.id,)
        )
        records = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return render_template('user/exercise_history.html', records=records)
    except Exception as e:
        logger.error(f"获取运动历史记录失败: {e}")
        flash('获取运动历史记录失败', 'danger')
        return render_template('user/exercise_history.html', records=[])

@user_bp.route('/api/user/stats')
@login_required
def user_stats():
    """获取用户统计数据"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'message': '数据库连接失败'}), 500
            
        cursor = conn.cursor(dictionary=True)
        
        # 获取总运动次数
        cursor.execute(
            "SELECT COUNT(*) as total FROM exercise_records WHERE user_id = %s",
            (current_user.id,)
        )
        total_count = cursor.fetchone()['total']
        
        # 获取总运动时间
        cursor.execute(
            "SELECT SUM(duration) as total_duration FROM exercise_records WHERE user_id = %s",
            (current_user.id,)
        )
        result = cursor.fetchone()
        total_duration = result['total_duration'] if result['total_duration'] else 0
        
        # 获取各类运动的次数
        cursor.execute(
            """
            SELECT exercise_type, COUNT(*) as count 
            FROM exercise_records 
            WHERE user_id = %s 
            GROUP BY exercise_type
            """,
            (current_user.id,)
        )
        exercise_counts = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_count': total_count,
                'total_duration': total_duration,
                'exercise_counts': exercise_counts
            }
        })
    except Exception as e:
        logger.error(f"获取用户统计数据失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@user_bp.route('/settings')
@login_required
def settings():
    """用户设置页面"""
    return render_template('user/settings.html', user=current_user)

@user_bp.route('/settings/change-password', methods=['POST'])
@login_required
def change_password():
    """修改用户密码"""
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # 验证新密码
    if new_password != confirm_password:
        flash('新密码和确认密码不匹配', 'danger')
        return redirect(url_for('user.settings'))
    
    # 验证当前密码
    from app import bcrypt
    if not bcrypt.check_password_hash(current_user.password, current_password):
        flash('当前密码不正确', 'danger')
        return redirect(url_for('user.settings'))
    
    try:
        # 更新密码
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        
        conn = get_db_connection()
        if not conn:
            flash('数据库连接失败', 'danger')
            return redirect(url_for('user.settings'))
            
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password = %s WHERE id = %s",
            (hashed_password, current_user.id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('密码修改成功', 'success')
        return redirect(url_for('user.settings'))
    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        flash('修改密码失败', 'danger')
        return redirect(url_for('user.settings'))