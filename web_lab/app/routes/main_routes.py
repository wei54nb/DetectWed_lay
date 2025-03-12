from flask import Blueprint, render_template

# 创建蓝图
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """主页"""
    return render_template('index.html')


# 添加realtime路由
@main_bp.route('/realtime')
def realtime():
    return render_template('realtime.html')    

@main_bp.route('/equipment_introduction')
def Equipment_Introduction():
    return render_template('Equipment Introduction Page.html')

@main_bp.route('/exercise_knowledge')
def Exercise_Knowledge():
    return render_template('Exercise Knowledge Page.html')

@main_bp.route('/classroom')
def classroom():
    return render_template('classroom.html')

@main_bp.route('/login')
def login():
    return render_template('login.html')

@main_bp.route('/logout')
def logout():
    # 实现登出逻辑
    # ...
    return redirect(url_for('main.index'))