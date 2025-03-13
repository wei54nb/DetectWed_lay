from flask import Blueprint, render_template, request, jsonify, Response
from flask_socketio import emit
import cv2
import logging
import time
import threading
from app import socketio
from app.services import exercise_service
from app.services.camera_service import get_camera, get_current_frame, release_camera

from datetime import datetime
import queue
from app.services.db_service import get_db_connection



if not hasattr(exercise_service, 'exercise_models') or exercise_service.exercise_models is None:
    exercise_service.init_models()

exercise_bp = Blueprint('exercise', __name__, url_prefix='/exercise')
logger = logging.getLogger(__name__)

frame_buffer = queue.Queue(maxsize=2)
processed_frame_buffer = queue.Queue(maxsize=2)

# 全局变量
processing_active = False
processing_thread = None
detection_active = False

@exercise_bp.route('/video_feed')
def video_feed():
    """视频流路由"""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@exercise_bp.route('/realtime')
def realtime():
    """实时检测页面"""
    return render_template('realtime.html')

def generate_frames():
    """生成视频帧 - 从旧版app.py移植"""
    while True:
        if not processed_frame_buffer.empty():
            # 从处理后的帧缓冲区获取帧
            frame = processed_frame_buffer.get()
            if frame is not None:
                # 编码并发送帧
                _, buffer = cv2.imencode('.jpg', frame)
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        else:
            # 如果缓冲区为空，短暂等待
            time.sleep(0.01)  # 短暂等待，避免CPU过载

def video_capture_thread(camera_index=1):
    """视频捕获线程 - 从旧版app.py移植"""
    global frame_buffer, detection_active
    
    logger.info(f"开始视频捕获线程，使用摄像头索引 {camera_index}")
    
    # 尝试不同的摄像头索引
    for index in [camera_index, 0, 2]:
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            camera_index = index
            logger.info(f"成功打开摄像头索引 {camera_index}")
            break
        cap.release()
    else:
        logger.error("无法打开任何摄像头")
        return
    
    # 设置摄像头参数
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    logger.info("摄像头初始化成功")
    
    while detection_active:
        ret, frame = cap.read()
        if not ret:
            logger.warning("无法读取视频帧")
            time.sleep(0.1)
            continue
        
        # 调整帧大小
        frame = cv2.resize(frame, (480, 480))
        
        # 将帧放入缓冲区
        if not frame_buffer.full():
            frame_buffer.put(frame)
        else:
            # 如果缓冲区满了，移除最旧的帧
            try:
                frame_buffer.get_nowait()
            except queue.Empty:
                pass
            frame_buffer.put(frame)
        
        time.sleep(0.01)  # 控制帧率
    
    # 释放摄像头
    cap.release()
    logger.info("视频捕获线程已停止")

def frame_processing_thread(exercise_type='squat'):
    """帧处理线程 - 从旧版app.py移植"""
    global frame_buffer, processed_frame_buffer, detection_active
    
    logger.info(f"开始帧处理线程，运动类型: {exercise_type}")
    
    while detection_active:
        if not frame_buffer.empty():
            # 从原始帧缓冲区获取帧
            frame = frame_buffer.get()
            
            # 处理帧
            processed_frame = exercise_service.process_frame_realtime(frame, exercise_type)
            
            # 将处理后的帧放入缓冲区
            if not processed_frame_buffer.full():
                processed_frame_buffer.put(processed_frame)
            else:
                # 如果缓冲区满了，移除最旧的帧
                try:
                    processed_frame_buffer.get_nowait()
                except queue.Empty:
                    pass
                processed_frame_buffer.put(processed_frame)
        
        time.sleep(0.01)  # 控制处理速率
    
    logger.info("帧处理线程已停止")

@exercise_bp.route('/start_detection', methods=['POST'])
def start_detection():
    """启动运动检测 - 从旧版app.py移植"""
    global detection_active
    
    try:
        data = request.json
        exercise_type = request.args.get('exercise_type', 'squat')
        
        weight = data.get('weight')
        reps = data.get('reps')  # 每组次数
        sets = data.get('sets')  # 组数
        student_id = data.get('student_id')
        
        if not all([student_id, weight, reps, sets]):
            return jsonify({'success': False, 'error': '请完整填写所有输入栏位'}), 400
            
        # 记录到数据库
        connection = get_db_connection()
        if connection:
            cursor = connection.cursor()
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                INSERT INTO exercise_info (student_id, weight, reps, sets, exercise_type, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (student_id, weight, reps, sets, exercise_type, timestamp))
            connection.commit()
            cursor.close()
            connection.close()
        
        # 重置计数和状态
        exercise_service.reset_detection_state_complete()  # 使用完整的重置函數
        exercise_service.set_current_exercise_type(exercise_type)
        exercise_service.set_exercise_params(int(reps), int(sets))
        
        # 确保 exercise_service 中的 detection_active 也被设置
        exercise_service.detection_active = True
        
        # 发送初始数据到前端
        socketio.emit('exercise_count_update', {'count': 0}, namespace='/exercise')
        socketio.emit('remaining_sets_update', {'sets': int(sets)}, namespace='/exercise')
        
        # 根据运动类型发送初始品质评分
        if exercise_type == 'squat':
            socketio.emit('squat_quality', {'score': 0}, namespace='/exercise')
        elif exercise_type == 'shoulder-press':
            socketio.emit('shoulder_press_score', {'score': 0}, namespace='/exercise')
        elif exercise_type == 'bicep-curl':
            socketio.emit('bicep_curl_score', {'score': 0}, namespace='/exercise')
        
        # 发送初始角度数据
        initial_angles = {
            '左手肘': 0, '右手肘': 0, '左膝蓋': 0, '右膝蓋': 0,
            '左肩膀': 0, '右肩膀': 0, '左髖部': 0, '右髖部': 0
        }
        socketio.emit('angle_data', initial_angles, namespace='/exercise')
        
        # 发送初始教练提示
        socketio.emit('coach_tip', {'tip': f'已開始{exercise_type}運動檢測，請保持正確姿勢'}, namespace='/exercise')
        
        # 启动检测线程
        if not detection_active:
            detection_active = True
            
            # 启动线程
            video_thread = threading.Thread(target=video_capture_thread, args=(1,), name="VideoCapture")
            video_thread.daemon = True  # 设置为守护线程
            video_thread.start()
            
            process_thread = threading.Thread(target=frame_processing_thread, args=(exercise_type,), name="FrameProcessing")
            process_thread.daemon = True  # 设置为守护线程
            process_thread.start()
            
            logger.info(f"已启动{exercise_type}运动检测")
            
            # 记录活跃线程
            active_threads = threading.enumerate()
            logger.info(f"活跃线程: {[t.name for t in active_threads]}")
            
            return jsonify({'success': True})
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"启动检测失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@exercise_bp.route('/stop_detection', methods=['POST'])
def stop_detection():
    """停止运动检测 - 从旧版app.py移植"""
    global detection_active
    
    try:
        detection_active = False
        # 确保 exercise_service 中的 detection_active 也被设置
        exercise_service.detection_active = False
        logger.info("已停止运动检测")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"停止检测失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@socketio.on('set_detection_line', namespace='/exercise')
def handle_set_detection_line():
    """处理设置检测线请求"""
    logger.info('收到设置检测线请求')
    exercise_service.set_detection_line()

@socketio.on('connect', namespace='/exercise')
def handle_connect():
    """处理客户端连接"""
    logger.info('客户端已连接')

# 确保以下函数在 exercise_routes.py 中正确实现

def get_current_frame():
    """从 frame_buffer 取得最新影像"""
    timeout = 5  # 等待 5 秒
    start_time = time.time()
    while frame_buffer.empty():
        if time.time() - start_time > timeout:
            logger.error("等待影像超时，队列仍为空")
            return None
        time.sleep(0.1)
    return frame_buffer.get()

# 在文件末尾添加以下代码

@socketio.on('request_angle_data', namespace='/exercise')
def handle_request_angle_data():
    """处理请求角度数据"""
    logger.info('收到请求角度数据')
    # 从 exercise_service 获取当前角度数据
    angles = exercise_service.get_current_angles()
    emit('angle_data', angles)

@socketio.on('request_quality_score', namespace='/exercise')
def handle_request_quality_score():
    """处理请求品质评分"""
    logger.info('收到请求品质评分')
    exercise_type = exercise_service.get_current_exercise_type()
    score = exercise_service.get_current_quality_score()
    
    if exercise_type == 'squat':
        emit('squat_quality', {'score': score})
    elif exercise_type == 'shoulder-press':
        emit('shoulder_press_score', {'score': score})
    elif exercise_type == 'bicep-curl':
        emit('bicep_curl_score', {'score': score})

@socketio.on('request_coach_tip', namespace='/exercise')
def handle_request_coach_tip():
    """处理请求教练提示"""
    logger.info('收到请求教练提示')
    tip = exercise_service.get_current_coach_tip()
    emit('coach_tip', {'tip': tip})