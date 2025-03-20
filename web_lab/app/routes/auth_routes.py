from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app.services.db_service import get_db_connection
from app import bcrypt
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    # 获取JSON数据
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    try:
        # 连接数据库验证用户
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': '数据库连接失败'})
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user_data and bcrypt.check_password_hash(user_data['password_hash'], password):
            # 登录成功
            user = User(user_data['user_id'], user_data['username'], user_data['role'])
            login_user(user)
            return jsonify({
                'success': True, 
                'role': user_data['role'],
                'userId': user_data['user_id'],
                'next': '/classroom'
            })
        else:
            # 登录失败
            return jsonify({'success': False, 'error': '用户名或密码错误'})
            
    except Exception as e:
        logger.error(f"登录时出错: {e}")
        return jsonify({'success': False, 'error': f'登录处理错误: {str(e)}'})
    
    # GET请求返回登录页面
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    # 添加日志记录
    logger.info(f"用户 {current_user.username} 正在登出")
    logout_user()
    # 清除会话
    session.clear()
    # 添加闪现消息
    flash('您已成功登出')
    return redirect(url_for('main.index'))