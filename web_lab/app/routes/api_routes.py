from flask import Blueprint, jsonify, request, current_app
from flask_login import current_user, login_required
from app.services.db_service import get_db_connection
import logging

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/user/status', methods=['GET'])
def get_user_status():
    """获取当前用户状态"""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'username': current_user.username,
            'role': current_user.role,
            'userId': current_user.id
        })
    else:
        return jsonify({
            'authenticated': False
        })

@api_bp.route('/discussions', methods=['GET'])
def get_discussions():
    """获取课程讨论列表"""
    course_id = request.args.get('course_id', type=int)
    
    if not course_id:
        return jsonify({'success': False, 'error': '缺少课程ID'})
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': '数据库连接失败'})
            
        cursor = conn.cursor(dictionary=True)
        
        # 首先检查表结构
        cursor.execute("SHOW COLUMNS FROM discussions")
        columns = [column['Field'] for column in cursor.fetchall()]
        logger.info(f"discussions表的列: {columns}")
        
        # 根据实际表结构调整查询 - 使用LEFT JOIN同时处理学生和教师发布的讨论
        query = """
        SELECT d.*, 
               COALESCE(s.username, t.username) as author_name,
               CASE 
                   WHEN d.teacher_id IS NOT NULL THEN 'teacher'
                   ELSE 'student'
               END as author_role
        FROM discussions d
        LEFT JOIN users s ON d.student_id = s.user_id
        LEFT JOIN users t ON d.teacher_id = t.user_id
        WHERE d.course_id = %s
        ORDER BY d.created_at DESC
        """
        
        cursor.execute(query, (course_id,))
        discussions = cursor.fetchall()
        
        # 处理日期格式
        for discussion in discussions:
            if 'created_at' in discussion and discussion['created_at']:
                discussion['created_at'] = discussion['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'discussions': discussions})
    
    except Exception as e:
        logger.error(f"获取讨论列表时出错: {e}")
        return jsonify({'success': False, 'error': f'获取讨论列表失败: {str(e)}'})

@api_bp.route('/responses', methods=['GET'])
def get_responses():
    """获取讨论回复列表"""
    discussion_id = request.args.get('discussion_id', type=int)
    
    if not discussion_id:
        return jsonify({'success': False, 'error': '缺少讨论ID'})
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': '数据库连接失败'})
            
        cursor = conn.cursor(dictionary=True)
        
        # 首先检查表结构
        cursor.execute("SHOW COLUMNS FROM responses")
        columns = [column['Field'] for column in cursor.fetchall()]
        logger.info(f"responses表的列: {columns}")
        
        # 检查users表结构
        cursor.execute("SHOW COLUMNS FROM users")
        user_columns = [column['Field'] for column in cursor.fetchall()]
        logger.info(f"users表的列: {user_columns}")
        
        # 获取所有回复
        cursor.execute(
            """
            SELECT r.*, u.username as author_name
            FROM responses r
            LEFT JOIN users u ON r.user_id = u.user_id
            WHERE r.discussion_id = %s
            ORDER BY r.created_at ASC
            """, 
            (discussion_id,)
        )
        responses = cursor.fetchall()
        logger.info(f"获取到 {len(responses)} 条回复")
        
        # 处理日期格式和确保author_name有值
        for response in responses:
            if 'created_at' in response and response['created_at']:
                response['created_at'] = response['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            
            # 确保author_name有值
            if not response.get('author_name'):
                # 尝试单独查询用户名
                cursor.execute("SELECT username FROM users WHERE user_id = %s", (response['user_id'],))
                user = cursor.fetchone()
                if user and user['username']:
                    response['author_name'] = user['username']
                else:
                    response['author_name'] = f"用户{response['user_id']}"
            
            # 添加角色信息
            response['author_role'] = 'teacher' if response.get('is_teacher') == 1 else 'student'
        
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'responses': responses})
    
    except Exception as e:
        logger.error(f"获取回复列表时出错: {e}")
        return jsonify({'success': False, 'error': f'获取回复列表失败: {str(e)}'})




@api_bp.route('/discussions', methods=['POST'])
@login_required
def create_discussion():
    """创建新讨论"""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': '无效的请求数据'})
    
    course_id = data.get('course_id')
    title = data.get('title')
    content = data.get('content')
    
    if not all([course_id, title, content]):
        return jsonify({'success': False, 'error': '缺少必要字段'})
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': '数据库连接失败'})
            
        cursor = conn.cursor()
        
        # 根据用户角色决定使用哪个字段
        if current_user.role == 'teacher':
            query = """
            INSERT INTO discussions (course_id, teacher_id, title, content)
            VALUES (%s, %s, %s, %s)
            """
        else:
            query = """
            INSERT INTO discussions (course_id, student_id, title, content)
            VALUES (%s, %s, %s, %s)
            """
        
        cursor.execute(query, (course_id, current_user.id, title, content))
        discussion_id = cursor.lastrowid
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'discussion_id': discussion_id})
    
    except Exception as e:
        logger.error(f"创建讨论时出错: {e}")
        return jsonify({'success': False, 'error': f'创建讨论失败: {str(e)}'})

# ... 現有代碼 ...

@api_bp.route('/discussions/<int:discussion_id>', methods=['DELETE'])
@login_required
def delete_discussion(discussion_id):
    """删除讨论"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': '数据库连接失败'})
            
        cursor = conn.cursor(dictionary=True)
        
        # 检查讨论是否存在
        cursor.execute("SELECT * FROM discussions WHERE discussion_id = %s", (discussion_id,))
        discussion = cursor.fetchone()
        
        if not discussion:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': '讨论不存在'})
        
        # 修改这里：使用正确的字段名检查权限
        # 检查当前用户是否有权限删除（只有教师或讨论创建者可以删除）
        if current_user.role != 'teacher' and (
            (discussion.get('teacher_id') and discussion['teacher_id'] != current_user.username) and
            (discussion.get('student_id') and discussion['student_id'] != current_user.username)
        ):
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': '无权限删除此讨论'}), 403
        
        # 先删除与讨论相关的所有回复
        cursor.execute("DELETE FROM responses WHERE discussion_id = %s", (discussion_id,))
        
        # 然后删除讨论
        cursor.execute("DELETE FROM discussions WHERE discussion_id = %s", (discussion_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True})
    
    except Exception as e:
        logger.error(f"删除讨论时出错: {e}")
        return jsonify({'success': False, 'error': f'删除讨论失败: {str(e)}'})

# ... 現有代碼 ...

@api_bp.route('/responses', methods=['POST'])
@login_required
def create_response():
    """创建新回复"""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'error': '无效的请求数据'})
    
    discussion_id = data.get('discussion_id')
    content = data.get('content')
    
    if not all([discussion_id, content]):
        return jsonify({'success': False, 'error': '缺少必要字段'})
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': '数据库连接失败'})
            
        cursor = conn.cursor()
        
        # 设置is_teacher字段
        is_teacher = 1 if current_user.role == 'teacher' else 0
        
        # 使用用户名而不是用户ID
        user_name = current_user.username
        
        query = """
        INSERT INTO responses (discussion_id, user_id, content, is_teacher)
        VALUES (%s, %s, %s, %s)
        """
        
        cursor.execute(query, (discussion_id, user_name, content, is_teacher))
        response_id = cursor.lastrowid
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'response_id': response_id})
    
    except Exception as e:
        logger.error(f"创建回复时出错: {e}")
        return jsonify({'success': False, 'error': f'创建回复失败: {str(e)}'})

@api_bp.route('/responses/<int:response_id>', methods=['DELETE'])
@login_required
def delete_response(response_id):
    """删除回复"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'success': False, 'error': '数据库连接失败'})
            
        cursor = conn.cursor(dictionary=True)
        
        # 检查回复是否存在且用户是否有权限删除
        cursor.execute("SELECT user_id, is_teacher FROM responses WHERE response_id = %s", (response_id,))
        response = cursor.fetchone()
        
        if not response:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': '回复不存在'})
        
        # 只有回复作者或教师可以删除
        if response['user_id'] != current_user.username and current_user.role != 'teacher':
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': '无权限删除此回复'}), 403
        
        # 删除回复
        cursor.execute("DELETE FROM responses WHERE response_id = %s", (response_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True})
    
    except Exception as e:
        logger.error(f"删除回复时出错: {e}")
        return jsonify({'success': False, 'error': f'删除回复失败: {str(e)}'})