from flask import Blueprint, render_template, request, jsonify, Response
from flask_socketio import emit
import cv2
import logging
import time
import threading
from app import socketio
from app.services import exercise_service
from app.services.camera_service import get_camera, get_current_frame, release_camera
import base64
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
    
    frame_count = 0
    log_interval = 100  # 每处理100帧记录一次日志
    
    while detection_active:
        if not frame_buffer.empty():
            try:
                # 从原始帧缓冲区获取帧
                frame = frame_buffer.get()
                
                # 处理帧
                processed_frame = exercise_service.process_frame_realtime(frame, exercise_type)
                
                # 将处理后的帧放入缓冲区
                if not processed_frame_buffer.full():
                    processed_frame_buffer.put(processed_frame)
                
                # 编码并发送帧 - 使用更高效的方式减小数据量
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 50]  # 降低JPEG质量到50%
                _, buffer = cv2.imencode('.jpg', processed_frame, encode_param)
                frame_data = buffer.tobytes()
                
                # 使用简短的哈希值代替完整的base64编码，减少日志数据量
                frame_hash = str(hash(frame_data) % 10000000)  # 生成简短哈希值
                frame_base64 = base64.b64encode(frame_data).decode('utf-8')
                
                # 在日志中记录哈希值而不是完整的base64编码
                logger.debug(f"发送视频帧 [哈希值: {frame_hash}]")
                
                # 发送帧到前端 - 前端仍然使用base64解码
                socketio.emit('video_frame', {'frame': frame_base64}, namespace='/exercise')
                
                # 增加帧计数
                frame_count += 1
                
                # 处理运动计数
                try:
                    count = exercise_service.get_current_count()
                    if count > 0:  # 只在計數大於 0 時發送
                        if frame_count % log_interval == 0:  # 只在特定间隔记录日志
                            logger.info(f"發送運動計數: {count}")
                        socketio.emit('exercise_count', {'count': count}, namespace='/exercise')
                except Exception as e:
                    if frame_count % log_interval == 0:  # 减少错误日志频率
                        logger.error(f"獲取運動計數時出錯: {e}")
            except Exception as e:
                logger.error(f"處理幀時出錯: {e}")
                time.sleep(0.1)  # 出错时短暂暂停，避免CPU占用过高
    
    logger.info("帧处理线程已停止")

@socketio.on('start_detection', namespace='/exercise')
def handle_start_detection(data):
    """处理开始检测请求"""
    global detection_active
    
    try:
        logger.info(f'收到开始检测请求: {data}')
        
        # 获取运动类型和其他参数
        exercise_type = data.get('exercise_type', 'squat')
        detection_line = data.get('detection_line', 0.5)
        
        # 可选参数
        weight = data.get('weight')
        reps = data.get('reps')  # 每组次数
        sets = data.get('sets')  # 组数
        student_id = data.get('student_id')
        
        # 如果提供了学生ID和其他参数，记录到数据库
        if all([student_id, weight, reps, sets]):
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
        
        # 如果提供了运动参数，设置它们
        if reps and sets:
            exercise_service.set_exercise_params(int(reps), int(sets))
        
        # 如果提供了检测线，设置它
        if detection_line:
            exercise_service.set_detection_line(detection_line)
        
        # 确保 exercise_service 中的 detection_active 也被设置
        exercise_service.detection_active = True
        
        # 发送初始数据到前端
        emit('exercise_count', {'count': 0})
        
        # 如果有组数信息，发送剩余组数
        if sets:
            emit('remaining_sets_update', {'sets': int(sets)})
        
        # 发送初始品质评分
        emit('pose_quality', {'score': 0})
        
        # 发送初始角度数据
        initial_angles = {
            '左手肘': 0, '右手肘': 0, '左膝蓋': 0, '右膝蓋': 0,
            '左肩膀': 0, '右肩膀': 0, '左髖部': 0, '右髖部': 0
        }
        emit('angle_data', {'angles': initial_angles})
        
        # 发送初始教练提示
        emit('coach_tip', {'tip': f'已開始{exercise_type}運動檢測，請保持正確姿勢'})
        
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
        
        # 发送成功响应
        emit('start_detection_response', {'status': 'success'})
        logger.info("已发送开始检测成功响应")
        
    except Exception as e:
        logger.error(f"启动检测失败: {e}", exc_info=True)
        emit('start_detection_response', {'status': 'error', 'message': str(e)})
        emit('error', {'message': f'启动检测失败: {str(e)}'})


@socketio.on('stop_detection', namespace='/exercise')
def handle_stop_detection():
    """处理停止检测请求"""
    global detection_active
    
    try:
        logger.info('收到停止检测请求')
        detection_active = False
        # 确保 exercise_service 中的 detection_active 也被设置
        exercise_service.detection_active = False
        logger.info("已停止运动检测")
        emit('stop_detection_response', {'status': 'success'})
    except Exception as e:
        logger.error(f"停止检测失败: {e}", exc_info=True)
        emit('stop_detection_response', {'status': 'error', 'message': str(e)})
        emit('error', {'message': f'停止检测失败: {str(e)}'})

@socketio.on('set_detection_line', namespace='/exercise')
def handle_set_detection_line(data):
    """处理设置检测线请求"""
    logger.info(f'收到设置检测线请求: {data}')
    line_position = data.get('line_position', 0.5)
    exercise_service.set_detection_line(line_position)

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