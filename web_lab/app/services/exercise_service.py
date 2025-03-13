import cv2
import numpy as np
import time
import logging
import os
from ultralytics import YOLO
from app import socketio

# 修改导入方式，避免命名冲突
from app.services.pose_detection import pose_model as imported_pose_model
import threading
import queue
import torch 
from flask import current_app


# 设置日志
logger = logging.getLogger(__name__)

# 全局变量
angles = {}  # 添加这行来解决 'angles' is not defined 错误
detection_active = False
exercise_count = 0
last_pose = None
mid_pose_detected = False
squat_state = "up"
last_squat_time = 0
detection_line_set = False
detection_line_y = 0
knee_line_coords = None
squat_quality_score = 0
detection_line_set_shoulder = False
detection_line_y_shoulder = 0
detection_line_set_bicep = False
elbow_line_coords = None
bicep_quality_score = 0
bicep_state = "down"
last_curl_time = 0
current_exercise_type = 'squat'  # 默认运动类型
target_reps = 10  # 默认目标重复次数
target_sets = 3   # 默认目标组数
current_set = 1   # 当前组数
remaining_sets = 3  # 添加这个变量，它在reset_detection_state中被引用

# 添加帧缓冲区（如果需要）
frame_buffer = queue.Queue(maxsize=2)
processed_frame_buffer = queue.Queue(maxsize=2)


exercise_models = {}
# 确保pose_model有一个初始值
pose_model = imported_pose_model

def init_models():
    """初始化所有模型"""
    global exercise_models, pose_model
    
    try:
        # 确保 exercise_models 已初始化
        exercise_models = {}
        
        # 加载运动分类模型
        load_exercise_models()
        
        # 优先使用从pose_detection导入的模型
        if imported_pose_model is not None:
            pose_model = imported_pose_model
            logger.info("成功使用pose_detection中的姿态检测模型")
        
        # 如果pose_model仍为None，则尝试初始化
        if pose_model is None:
            logger.info("姿态检测模型未初始化，尝试重新初始化...")
            try:
                # 尝试从配置获取模型路径
                base_dir = current_app.config['BASE_DIR']
                pose_path = os.path.join(base_dir, 'static', 'models', 'YOLO_MODLE', 'pose', 'yolov8n-pose.pt')
                
                # 如果文件不存在，使用默认路径
                if not os.path.exists(pose_path):
                    logger.warning(f"姿态检测模型文件不存在: {pose_path}，使用默认模型")
                    pose_model = YOLO('yolov8n-pose.pt')
                else:
                    pose_model = YOLO(pose_path)
                logger.info("姿态检测模型加载完成")
            except Exception as e:
                logger.error(f"加载姿态检测模型时出错: {e}", exc_info=True)
                # 确保有一个默认模型
                try:
                    pose_model = YOLO('yolov8n-pose.pt')
                    logger.info("使用默认模型成功")
                except Exception as e2:
                    logger.error(f"加载默认模型也失败: {e2}", exc_info=True)
                    return False
        
        # 验证模型是否可用
        if pose_model is None:
            logger.error("所有尝试都失败，无法加载姿态检测模型")
            return False
            
        logger.info("所有模型初始化完成")
        return True
    except Exception as e:
        logger.error(f"初始化模型时出错: {e}", exc_info=True)
        return False
def convert_to_serializable(data):
    """将数据转换为可序列化的格式"""
    if isinstance(data, dict):
        return {k: convert_to_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_to_serializable(item) for item in data]
    elif isinstance(data, np.ndarray):
        return data.tolist()
    elif isinstance(data, (np.float32, np.float64)):
        return float(data)
    elif isinstance(data, (np.int32, np.int64)):
        return int(data)
    else:
        return data



def load_exercise_models():
    """加载运动分类模型"""
    global exercise_models
    
    try:
        # 从配置获取模型路径
        model_paths = current_app.config['MODEL_PATHS']
        base_dir = current_app.config['BASE_DIR']
        
        # 确保模型目录存在
        for exercise_type, rel_path in model_paths.items():
            # 构建绝对路径
            abs_path = os.path.join(base_dir, rel_path)
            
            try:
                # 检查文件是否存在
                if not os.path.exists(abs_path):
                    logger.warning(f"模型文件不存在: {abs_path}")
                    continue
                
                # 加载模型
                model = YOLO(abs_path)
                exercise_models[exercise_type] = model
                logger.info(f"YOLO model for {exercise_type} loaded successfully from {abs_path}")
            except Exception as e:
                logger.error(f"加载{exercise_type}模型时出错: {e}")
    except Exception as e:
        logger.error(f"初始化运动分类模型时出错: {e}")

def set_detection_line():
    """设置检测线"""
    global detection_line_set, detection_line_y, knee_line_coords
    
    # 获取当前帧
    from app.routes.exercise_routes import get_current_frame
    frame = get_current_frame()
    
    if frame is None:
        logger.error("无法获取帧来设置检测线")
        return False
    
    # 调整帧大小
    frame = cv2.resize(frame, (480, 480))
    
    # 使用YOLO检测姿势
    results = pose_model(frame)
    
    if not results or len(results) == 0:
        logger.error("无法检测到姿势来设置检测线")
        return False
    
    # 获取关键点
    if results[0].keypoints is not None:
        keypoints = results[0].keypoints.xy.cpu().numpy()[0]
        
        if len(keypoints) >= 17:
            # 获取膝盖关键点
            left_knee = keypoints[13][:2]
            right_knee = keypoints[14][:2]
            
            # 检查关键点有效性
            if not np.isnan(left_knee).any() and not np.isnan(right_knee).any():
                # 设置膝盖线
                knee_line_coords = (
                    (int(left_knee[0]), int(left_knee[1])),
                    (int(right_knee[0]), int(right_knee[1]))
                )
                # 设置检测线Y坐标（膝盖高度）
                detection_line_y = int((left_knee[1] + right_knee[1]) / 2)
                detection_line_set = True
                
                logger.info(f"检测线已设置在 y={detection_line_y}")
                
                # 通知前端
                socketio.emit('detection_line_set', {
                    'success': True,
                    'detection_line_y': float(detection_line_y)  # 确保转换为Python原生类型
                }, namespace='/exercise')
                
                return True
    
    logger.error("无法设置检测线")
    return False


def calculate_angle(a, b, c):
    # 將 a, b, c 轉換為 numpy 陣列
    a, b, c = np.array(a), np.array(b), np.array(c)
    # 計算向量 BA 和 BC（即從 b 到 a 以及從 b 到 c 的向量）
    ba = a - b
    bc = c - b
    # 計算向量的點積
    dot_product = np.dot(ba, bc)
    # 計算向量的長度
    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)
    # 防止除以 0 的情況（如果某向量長度為 0，就直接返回 0 度）
    if norm_ba == 0 or norm_bc == 0:
        return 0.0
    # 計算夾角的 cosine 值，並利用 clip 限制範圍在 [-1, 1]
    cos_theta = np.clip(dot_product / (norm_ba * norm_bc), -1.0, 1.0)
    # 利用 arccos 求出角度，再轉換為度數
    angle = np.degrees(np.arccos(cos_theta))
    return angle

def reset_detection_state():
    """重置检测状态"""
    global exercise_count, last_pose, mid_pose_detected, squat_state, detection_line_set
    global detection_line_y, knee_line_coords, squat_quality_score, remaining_sets
    
    exercise_count = 0
    last_pose = None
    mid_pose_detected = False
    squat_state = 'init'
    detection_line_set = False
    detection_line_y = 0
    knee_line_coords = None
    squat_quality_score = 0
    remaining_sets = target_sets

def set_current_exercise_type(exercise_type):
    """设置当前运动类型"""
    global current_exercise_type
    current_exercise_type = exercise_type
    logger.info(f"设置当前运动类型为: {exercise_type}")

def get_current_exercise_type():
    """获取当前运动类型"""
    global current_exercise_type
    return current_exercise_type

def set_exercise_params(reps, sets):
    """设置运动参数"""
    global target_reps, target_sets, remaining_sets
    target_reps = reps
    target_sets = sets
    remaining_sets = sets
    logger.info(f"设置运动参数: {reps}次 x {sets}组")





def process_squat_exercise(frame, annotated_frame, angles, hip_midpoint, detection_line_set, detection_line_y):
    """Handle squat exercise processing logic using original frame for classification"""
    global exercise_count, last_pose, squat_state, last_squat_time, squat_quality_score

    # 使用exercise_models而不是models
    current_model = exercise_models.get("squat")
    if not current_model:
        logger.warning("Squat model not found!")
        return

    # Use squat model for classification on original frame
    squat_results = current_model(frame, conf=0.3, verbose=False)

    if len(squat_results) > 0 and len(squat_results[0].boxes) > 0:
        best_box = squat_results[0].boxes[0]
        class_id = int(best_box.cls)
        conf = float(best_box.conf)
        class_name = current_model.names[class_id]

        # Get bounding box coordinates
        x1, y1, x2, y2 = map(int, best_box.xyxy[0].cpu().numpy())

        # Draw YOLO detection box on annotated frame
        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f'{class_name} {conf:.2f}'
        #cv2.putText(annotated_frame, label, (x1, y1 - 10),
        #            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # If detection line is set and hip midpoint is valid, evaluate squat
        if detection_line_set and hip_midpoint:
            # Get average knee angle
            avg_knee_angle = (angles.get('左膝蓋', 180) + angles.get('右膝蓋', 180)) / 2

            # Improved squat counting and scoring logic
            if last_pose is None:
                last_pose = class_id
            elif last_pose == 0 and class_id == 1:  # From prepare to squat
                squat_state = "down"
                # Check if hip is below baseline
                hip_below_line = hip_midpoint[1] > detection_line_y

                # Score based on knee angle and hip position
                if hip_below_line:
                    if avg_knee_angle < 90:  # Excellent squat standard
                        squat_quality_score = 5  # Perfect score
                    elif avg_knee_angle < 110:  # Good squat standard
                        squat_quality_score = 4
                    elif avg_knee_angle < 130:  # Not deep enough
                        squat_quality_score = 3
                    else:  # Barely squatting
                        squat_quality_score = 2
                else:
                    squat_quality_score = 1  # Hip not below baseline

                # Send score to frontend
                socketio.emit('squat_quality', {'score': squat_quality_score}, namespace='/exercise')
                logger.info(f"深蹲评分: {squat_quality_score}/5")

            elif last_pose == 1 and class_id == 0:  # From squat back to prepare
                current_time = time.time()
                if current_time - last_squat_time > 0.8:  # Time interval to prevent false counts
                    exercise_count += 1
                    last_squat_time = current_time
                    squat_state = "up"
                    logger.info(f"Squat completed, count: {exercise_count}")
                    socketio.emit('exercise_count_update', {'count': exercise_count}, namespace='/exercise')

            last_pose = class_id

            # Display score on frame
            #cv2.putText(annotated_frame, f'Score: {squat_quality_score}/5', (10, 120),
            #            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            # Display average knee angle and current squat state
            #cv2.putText(annotated_frame, f'Knee angle: {avg_knee_angle:.1f}',
            #            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            #cv2.putText(annotated_frame, f'State: {squat_state}',
            #            (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            # Mark hip position relative to baseline
            if hip_midpoint[1] > detection_line_y:
                cv2.putText(annotated_frame, "Hip BELOW line", (200, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            else:
                cv2.putText(annotated_frame, "Hip ABOVE line", (200, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    else:
        logger.warning(f"未检测到深蹲姿势分类! (squat/prepare)")


def process_bicep_curl(frame, annotated_frame, keypoints, angles):
    """Handle bicep curl exercise processing logic using original frame for classification"""
    global exercise_count, last_pose, bicep_quality_score, detection_line_set_bicep, elbow_line_coords, last_curl_time, bicep_state

    # Debug information collection
    debug_info = []
    debug_info.append("Bicep curl detection active")

    if keypoints is None or len(keypoints) < 17:
        logger.warning("Insufficient keypoints for bicep curl detection!")
        return

    current_model = exercise_models.get("bicep-curl")
    if not current_model:
        logger.warning("Bicep curl model not found!")
        return

    # Extract keypoint information regardless of classification model results
    left_shoulder = keypoints[5][:2]
    right_shoulder = keypoints[6][:2]
    left_elbow = keypoints[7][:2]
    right_elbow = keypoints[8][:2]
    left_wrist = keypoints[9][:2]
    right_wrist = keypoints[10][:2]

    # Check keypoint validity
    left_arm_valid = not np.isnan(left_shoulder).any() and not np.isnan(left_elbow).any() and not np.isnan(left_wrist).any()
    right_arm_valid = not np.isnan(right_shoulder).any() and not np.isnan(right_elbow).any() and not np.isnan(right_wrist).any()

    debug_info.append(f"Left arm valid: {left_arm_valid}")
    debug_info.append(f"Right arm valid: {right_arm_valid}")

    # Try to execute classification model
    try:
        bicep_curl_results = current_model(frame, conf=0.3, verbose=False)
        has_classification = len(bicep_curl_results) > 0 and len(bicep_curl_results[0].boxes) > 0
        debug_info.append(f"Classification detected: {has_classification}")
    except Exception as e:
        logger.error(f"Error running bicep curl model: {e}")
        has_classification = False
        debug_info.append(f"Classification error: {str(e)}")

    # Set bicep curl detection line if not already set
    if not detection_line_set_bicep and (left_arm_valid or right_arm_valid):
        if left_arm_valid:
            left_elbow_point = tuple(map(int, left_elbow))
        else:
            left_elbow_point = (int(frame.shape[1] * 0.4), int(frame.shape[0] * 0.5))
        if right_arm_valid:
            right_elbow_point = tuple(map(int, right_elbow))
        else:
            right_elbow_point = (int(frame.shape[1] * 0.6), int(frame.shape[0] * 0.5))
        elbow_line_coords = (left_elbow_point, right_elbow_point)
        detection_line_set_bicep = True
        logger.info("二頭彎舉偵測基準線已設置")

    # Draw detection line if set
    if detection_line_set_bicep and elbow_line_coords:
        cv2.line(annotated_frame, elbow_line_coords[0], elbow_line_coords[1], (255, 0, 255), 2)
        cv2.putText(annotated_frame, "Elbow Reference Line", (elbow_line_coords[0][0], elbow_line_coords[0][1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)

    # Draw and check arm position (left)
    if left_arm_valid:
        left_shoulder_point = tuple(map(int, left_shoulder))
        left_elbow_point = tuple(map(int, left_elbow))
        left_wrist_point = tuple(map(int, left_wrist))
        cv2.circle(annotated_frame, left_shoulder_point, 5, (0, 255, 255), -1)
        cv2.circle(annotated_frame, left_elbow_point, 5, (0, 255, 255), -1)
        cv2.circle(annotated_frame, left_wrist_point, 5, (0, 255, 255), -1)
        cv2.line(annotated_frame, left_shoulder_point, left_elbow_point, (0, 255, 0), 2)
        cv2.line(annotated_frame, left_elbow_point, left_wrist_point, (0, 255, 0), 2)
        angles['左手肘'] = calculate_angle(left_shoulder, left_elbow, left_wrist)
        debug_info.append(f"Left elbow angle: {angles['左手肘']:.1f}°")

    # Draw and check arm position (right)
    if right_arm_valid:
        right_shoulder_point = tuple(map(int, right_shoulder))
        right_elbow_point = tuple(map(int, right_elbow))
        right_wrist_point = tuple(map(int, right_wrist))
        cv2.circle(annotated_frame, right_shoulder_point, 5, (0, 255, 255), -1)
        cv2.circle(annotated_frame, right_elbow_point, 5, (0, 255, 255), -1)
        cv2.circle(annotated_frame, right_wrist_point, 5, (0, 255, 255), -1)
        cv2.line(annotated_frame, right_shoulder_point, right_elbow_point, (0, 255, 0), 2)
        cv2.line(annotated_frame, right_elbow_point, right_wrist_point, (0, 255, 0), 2)
        angles['右手肘'] = calculate_angle(right_shoulder, right_elbow, right_wrist)
        debug_info.append(f"Right elbow angle: {angles['右手肘']:.1f}°")

    # Calculate average elbow angle
    if '左手肘' in angles and '右手肘' in angles:
        avg_elbow_angle = (angles['左手肘'] + angles['右手肘']) / 2
    elif '左手肘' in angles:
        avg_elbow_angle = angles['左手肘']
    elif '右手肘' in angles:
        avg_elbow_angle = angles['右手肘']
    else:
        avg_elbow_angle = 180
        debug_info.append("No elbow angles available")

    # Scoring logic - evaluate form; 此處評分邏輯可依需求保留或調整
    should_score = (left_arm_valid or right_arm_valid) and detection_line_set_bicep

    # === 修改記數邏輯：放下 (無偵測) → 舉 (有偵測) → 放下 (無偵測)才算1下，且1秒內最多只計數一次 ===
    current_time = time.time()
    if has_classification:
        if bicep_state == "down":
            bicep_state = "up"
            debug_info.append("Transition: Down -> Up")
    else:
        if bicep_state == "up":
            # 檢查是否已超過1秒
            if current_time - last_curl_time >= 2.0:
                exercise_count += 1
                last_curl_time = current_time
                socketio.emit('exercise_count_update', {'count': exercise_count}, namespace='/exercise')
                logger.info(f"Bicep curl rep counted, count: {exercise_count}")
                bicep_state = "down"
                debug_info.append("Transition: Up -> Down (rep counted)")
            else:
                debug_info.append("Rep not counted due to 1 sec limit")
        else:
            bicep_state = "down"

    # === 顯示 YOLO 偵測框 ===
    if has_classification:
        best_box = bicep_curl_results[0].boxes[0]
        x1, y1, x2, y2 = map(int, best_box.xyxy[0].cpu().numpy())
        conf = float(best_box.conf)
        class_name = current_model.names[int(best_box.cls)]
        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f'{class_name} {conf:.2f}'
        cv2.putText(annotated_frame, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Perform scoring calculation (保留原有評分邏輯)
    if should_score:
        if avg_elbow_angle < 60:
            bicep_quality_score = 5
        elif avg_elbow_angle < 90:
            bicep_quality_score = 4
        elif avg_elbow_angle < 120:
            bicep_quality_score = 3
        elif avg_elbow_angle < 150:
            bicep_quality_score = 2
        else:
            bicep_quality_score = 1

        shoulder_stability_score = 5  # 預設為最佳
        if left_arm_valid and '左肩膀' in angles:
            shoulder_angle = angles['左肩膀']
            shoulder_deviation = abs(90 - shoulder_angle)
            if shoulder_deviation > 30:
                shoulder_stability_score = 2
            elif shoulder_deviation > 15:
                shoulder_stability_score = 3

        if right_arm_valid and '右肩膀' in angles:
            shoulder_angle = angles['右肩膀']
            shoulder_deviation = abs(90 - shoulder_angle)
            right_stability = 5
            if shoulder_deviation > 30:
                right_stability = 2
            elif shoulder_deviation > 15:
                right_stability = 3
            if right_stability < shoulder_stability_score:
                shoulder_stability_score = right_stability

        combined_score = (bicep_quality_score * 0.7) + (shoulder_stability_score * 0.3)
        final_score = round(combined_score)
        score_description = get_score_description(final_score)

        socketio.emit('bicep_curl_score', {'score': final_score},namespace='/exercise')
        logger.info(f"二頭彎舉評分: {final_score}/5 (肘部: {bicep_quality_score}, 肩穩定性: {shoulder_stability_score})")
        cv2.putText(annotated_frame, f'Score: {final_score}/5 - {score_description}', (10, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        cv2.putText(annotated_frame, f'Elbow: {avg_elbow_angle:.1f}° | Stability: {shoulder_stability_score}/5',
                    (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    else:
        reason = "無法進行評分: "
        if not (left_arm_valid or right_arm_valid):
            reason += "手臂關節點檢測失敗 "
        elif not detection_line_set_bicep:
            reason += "偵測線未設置 "
        cv2.putText(annotated_frame, reason, (10, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        socketio.emit('bicep_curl_score', {'score': 0},namespace='/exercise')
        logger.info(reason)

    # Display debug info
    for i, text in enumerate(debug_info):
        cv2.putText(annotated_frame, text, (10, 200 + i * 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)



def process_squat(frame, keypoints, angles):
    """处理下蹲运动"""
    global exercise_count, squat_state, detection_line_set, detection_line_y, knee_line_coords, mid_pose_detected, remaining_sets, target_reps
    
    annotated_frame = frame.copy()
    
    # 提取关键点信息
    if keypoints is None or len(keypoints) < 17:
        logger.warning("下蹲检测的关键点不足")
        return annotated_frame
    
    # 提取髋部和膝盖关键点
    left_hip = keypoints[11][:2]
    right_hip = keypoints[12][:2]
    left_knee = keypoints[13][:2]
    right_knee = keypoints[14][:2]
    left_ankle = keypoints[15][:2]
    right_ankle = keypoints[16][:2]
    
    # 检查关键点有效性
    knee_valid = not np.isnan(left_knee).any() and not np.isnan(right_knee).any()
    
    # 计算膝盖中点
    if knee_valid:
        knee_midpoint = ((left_knee[0] + right_knee[0]) / 2, (left_knee[1] + right_knee[1]) / 2)
        
        # 设置检测线（如果尚未设置）
        if not detection_line_set:
            detection_line_y = int(knee_midpoint[1])
            knee_line_coords = (
                (int(left_knee[0]), int(left_knee[1])),
                (int(right_knee[0]), int(right_knee[1]))
            )
            detection_line_set = True
            logger.info(f"下蹲检测线已设置在 y={detection_line_y}")
        
        # 绘制检测线
        if detection_line_set and knee_line_coords:
            cv2.line(annotated_frame, knee_line_coords[0], knee_line_coords[1], (0, 255, 255), 2)
            cv2.line(annotated_frame, (0, detection_line_y), (annotated_frame.shape[1], detection_line_y), (0, 0, 255), 2)
            midpoint_x = (knee_line_coords[0][0] + knee_line_coords[1][0]) // 2
            cv2.circle(annotated_frame, (midpoint_x, detection_line_y), 5, (0, 255, 255), -1)
            cv2.putText(annotated_frame, "Detection Line", (midpoint_x - 40, detection_line_y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        
        # 计算膝盖角度
        angles['左膝盖'] = calculate_angle(left_hip, left_knee, left_ankle)
        angles['右膝盖'] = calculate_angle(right_hip, right_knee, right_ankle)
        avg_knee_angle = (angles['左膝盖'] + angles['右膝盖']) / 2
        
        # 下蹲计数逻辑
        if detection_line_set:
            # 检查膝盖是否低于检测线
            if knee_midpoint[1] > detection_line_y:
                # 在下蹲位置
                if squat_state == 'up' or squat_state == 'init':
                    squat_state = 'down'
                    mid_pose_detected = True
                    logger.info("检测到下蹲姿势")
            else:
                # 在站立位置
                if squat_state == 'down' and mid_pose_detected:
                    squat_state = 'up'
                    exercise_count += 1
                    mid_pose_detected = False
                    logger.info(f"完成一次下蹲，计数: {exercise_count}")
                    
                    # 检查是否完成一组
                    if exercise_count >= target_reps:
                        remaining_sets -= 1
                        exercise_count = 0
                        logger.info(f"完成一组下蹲，剩余组数: {remaining_sets}")
                        socketio.emit('set_completed', {
                            'remaining_sets': remaining_sets
                        }, namespace='/exercise')
        
        # 显示膝盖角度
        cv2.putText(annotated_frame, f"膝盖角度: {int(avg_knee_angle)}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    # 显示下蹲次数
    cv2.putText(annotated_frame, f"下蹲次数: {exercise_count}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    # 显示剩余组数
    cv2.putText(annotated_frame, f"剩余组数: {remaining_sets}", (10, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    return annotated_frame



def calculate_shoulder_press_score(avg_elbow_angle, min_angle=90, max_angle=180):
    """Calculate the percentage score for elbow extension in shoulder press"""
    score = (avg_elbow_angle - min_angle) / (max_angle - min_angle) * 100
    score = max(0, min(100, score))
    return score


def convert_percent_to_rating(percent):
    """Convert a percentage score to a 1-5 rating scale"""
    if percent >= 90:
        return 5  # Excellent
    elif percent >= 75:
        return 4  # Good
    elif percent >= 60:
        return 3  # Satisfactory
    elif percent >= 40:
        return 2  # Needs improvement
    else:
        return 1  # Poor


def get_score_description(score):
    """Return a text description for the score"""
    descriptions = {
        5: "Excellent",
        4: "Good",
        3: "Satisfactory",
        2: "Needs Improvement",
        1: "Poor Form"
    }
    return descriptions.get(score, "")



def process_other_exercise(frame, annotated_frame, exercise_type):
    """Handle processing for other exercise types using original frame for classification"""
    global exercise_count, last_pose, mid_pose_detected

    current_model = exercise_models.get(exercise_type)
    if not current_model:
        logger.warning(f"Model for {exercise_type} not found!")
        return

    exercise_results = current_model(frame, conf=0.5, verbose=False)
    logger.info(f"運動分類結果：檢測到 {len(exercise_results[0].boxes)} 個框")

    if len(exercise_results[0].boxes) > 0:
        best_box = exercise_results[0].boxes[0]
        x1, y1, x2, y2 = map(int, best_box.xyxy[0].cpu().numpy())
        conf = float(best_box.conf)
        class_id = int(best_box.cls)
        class_name = current_model.names[class_id]

        # Draw detection box and label on annotated frame
        #cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f'{class_name} {conf:.2f}'
        #cv2.putText(annotated_frame, label, (x1, y1 - 10),
        #            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # Perform classification counting logic
        num_classes = len(current_model.names)
        if num_classes == 1:
            if class_id == 0:
                exercise_count += 1
                socketio.emit('exercise_count_update', {'count': exercise_count},namespace='/exercise')
        elif num_classes == 2:
            if last_pose is not None:
                if last_pose == 0 and class_id == 1:
                    mid_pose_detected = True
                elif last_pose == 1 and class_id == 0 and mid_pose_detected:
                    exercise_count += 1
                    mid_pose_detected = False
                    socketio.emit('exercise_count_update', {'count': exercise_count},namespace='/exercise')
            last_pose = class_id



def set_bicep_detection_line():
    """设置二头弯举检测线"""
    global detection_line_set_bicep, elbow_line_coords
    
    # 获取当前帧
    from app.routes.exercise_routes import get_current_frame
    frame = get_current_frame()
    
    if frame is None:
        logger.error("无法获取帧来设置二头弯举检测线")
        return False
    
    # 调整帧大小
    frame = cv2.resize(frame, (480, 480))
    
    # 使用YOLO检测姿势
    results = pose_model(frame)
    
    if not results or len(results) == 0:
        logger.error("无法检测到姿势来设置二头弯举检测线")
        return False
    
    # 获取关键点
    if results[0].keypoints is not None:
        keypoints = results[0].keypoints.xy.cpu().numpy()[0]
        
        if len(keypoints) >= 17:
            # 获取肘部关键点
            left_elbow = keypoints[7][:2]
            right_elbow = keypoints[8][:2]
            
            # 检查关键点有效性
            if not np.isnan(left_elbow).any() and not np.isnan(right_elbow).any():
                # 设置肘部线
                elbow_line_coords = (
                    (int(left_elbow[0]), int(left_elbow[1])),
                    (int(right_elbow[0]), int(right_elbow[1]))
                )
                detection_line_set_bicep = True
                
                logger.info("二头弯举检测线已设置")
                
                # 通知前端
                socketio.emit('bicep_detection_line_set', {
                    'success': True
                }, namespace='/exercise')
                
                return True
    
    logger.error("无法设置二头弯举检测线")
    return False

def create_error_frame(frame, error_message):
    """创建带有错误信息的帧"""
    if frame is None:
        # 创建一个空白帧
        frame = np.zeros((480, 480, 3), dtype=np.uint8)
    
    # 添加错误信息
    cv2.putText(frame, error_message, (10, 240),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    return frame

def set_shoulder_detection_line():
    """设置肩推检测线"""
    global detection_line_set_shoulder, detection_line_y_shoulder
    
    # 获取当前帧
    from app.routes.exercise_routes import get_current_frame
    frame = get_current_frame()
    
    if frame is None:
        logger.error("无法获取帧来设置肩推检测线")
        return False
    
    # 调整帧大小
    frame = cv2.resize(frame, (480, 480))
    
    # 使用YOLO检测姿势
    results = pose_model(frame)
    
    if not results or len(results) == 0:
        logger.error("无法检测到姿势来设置肩推检测线")
        return False
    
    # 获取关键点
    if results[0].keypoints is not None:
        keypoints = results[0].keypoints.xy.cpu().numpy()[0]
        
        if len(keypoints) >= 17:
            # 获取肩膀关键点
            left_shoulder = keypoints[5][:2]
            right_shoulder = keypoints[6][:2]
            
            # 计算肩膀中点
            shoulder_midpoint = ((left_shoulder[0] + right_shoulder[0]) / 2, 
                                (left_shoulder[1] + right_shoulder[1]) / 2)
            
            # 设置检测线（稍微高于肩膀）
            detection_line_y_shoulder = int(shoulder_midpoint[1]) - 20
            detection_line_set_shoulder = True
            
            logger.info(f"肩推检测线已设置在 y={detection_line_y_shoulder}")
            
            # 通知前端
            socketio.emit('shoulder_detection_line_set', {
                'success': True,
                'detection_line_y': detection_line_y_shoulder
            }, namespace='/exercise')
            
            return True
    
    logger.error("无法设置肩推检测线")
    return False


def process_frame_realtime(frame, exercise_type):
    global exercise_count, last_pose, mid_pose_detected, squat_state, last_squat_time
    global detection_line_set, detection_line_y, knee_line_coords, squat_quality_score
    global detection_line_set_shoulder, detection_line_y_shoulder, pose_model

    try:
        if pose_model is None:
            logger.warning("姿态检测模型未初始化，尝试重新初始化...")
            try:
                pose_model = YOLO('yolov8n-pose.pt')
                logger.info("姿态检测模型重新初始化成功")
            except Exception as e:
                logger.error(f"重新初始化姿态检测模型失败: {e}")
                # 创建一个带有错误信息的帧
                return create_error_frame(frame, "姿态检测模型加载失败")

        frame = cv2.resize(frame, (480, 480))
        annotated_frame = frame.copy()

        # Pose detection
        pose_results = pose_model(frame, conf=0.3, verbose=False)

        # Draw existing detection lines if already set
        if detection_line_set and knee_line_coords:
            # Draw knee line
            cv2.line(annotated_frame, knee_line_coords[0], knee_line_coords[1], (0, 255, 255), 2)
            # Draw horizontal baseline (red)
            cv2.line(annotated_frame, (0, detection_line_y), (annotated_frame.shape[1], detection_line_y),
                     (0, 0, 255), 2)
            # Mark the baseline midpoint
            midpoint_x = (knee_line_coords[0][0] + knee_line_coords[1][0]) // 2
            cv2.circle(annotated_frame, (midpoint_x, detection_line_y), 5, (0, 255, 255), -1)
            cv2.putText(annotated_frame, "Detection Line", (midpoint_x - 40, detection_line_y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        if detection_line_set_shoulder:
            # Draw shoulder press detection line if set
            cv2.line(annotated_frame, (0, detection_line_y_shoulder),
                     (annotated_frame.shape[1], detection_line_y_shoulder), (0, 0, 255), 2)
            cv2.putText(annotated_frame, "Target Line", (10, detection_line_y_shoulder - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        angles = {}
        valid_knee_detection = False
        knee_midpoint = None
        hip_midpoint = None
        keypoints = None  # 初始化keypoints變量

        if not pose_results or len(pose_results) == 0:
            logger.warning("YOLO pose detection returned empty results!")
        else:
            # Process keypoint data
            if pose_results[0].keypoints is not None:
                keypoints = pose_results[0].keypoints.xy.cpu().numpy()[0]
                logger.info(f"取得關鍵點數量: {len(keypoints)}")

                if len(keypoints) >= 17:
                    # Extract keypoints
                    left_shoulder = keypoints[5][:2]
                    right_shoulder = keypoints[6][:2]
                    left_elbow = keypoints[7][:2]
                    right_elbow = keypoints[8][:2]
                    left_wrist = keypoints[9][:2]
                    right_wrist = keypoints[10][:2]
                    left_hip = keypoints[11][:2]
                    right_hip = keypoints[12][:2]
                    left_knee = keypoints[13][:2]
                    right_knee = keypoints[14][:2]
                    left_ankle = keypoints[15][:2]
                    right_ankle = keypoints[16][:2]

                    # Calculate joint angles
                    angles['左手肘'] = calculate_angle(left_shoulder, left_elbow, left_wrist)
                    angles['右手肘'] = calculate_angle(right_shoulder, right_elbow, right_wrist)
                    angles['左膝蓋'] = calculate_angle(left_hip, left_knee, left_ankle)
                    angles['右膝蓋'] = calculate_angle(right_hip, right_knee, right_ankle)
                    avg_knee_angle = (angles['左膝蓋'] + angles['右膝蓋']) / 2
                    angles['左肩膀'] = calculate_angle(left_hip, left_shoulder, left_elbow)
                    angles['右肩膀'] = calculate_angle(right_hip, right_shoulder, right_elbow)
                    angles['左髖部'] = calculate_angle(left_shoulder, left_hip, left_knee)
                    angles['右髖部'] = calculate_angle(right_shoulder, right_hip, right_knee)

                    # Send angle data to frontend
                    socketio.emit('angle_data', angles, namespace='/exercise')

                    # Calculate hip midpoint
                    if not np.isnan(left_hip).any() and not np.isnan(right_hip).any():
                        hip_midpoint = ((int(left_hip[0]) + int(right_hip[0])) // 2,
                                        (int(left_hip[1]) + int(right_hip[1])) // 2)
                        # Draw hip midpoint
                        cv2.circle(annotated_frame, hip_midpoint, 5, (255, 0, 255), -1)

                    # Process knee coordinates and set detection line for squats (only once)
                    if not np.isnan(left_knee).any() and not np.isnan(right_knee).any():
                        l_knee = tuple(map(int, left_knee))
                        r_knee = tuple(map(int, right_knee))

                        # Calculate knee midpoint
                        knee_midpoint = ((l_knee[0] + r_knee[0]) // 2, (l_knee[1] + r_knee[1]) // 2)

                        # Set squat detection line only once if not already set
                        if not detection_line_set and knee_midpoint and exercise_type == "squat":
                            knee_line_coords = (l_knee, r_knee)
                            detection_line_y = int(knee_midpoint[1] * 0.8)
                            detection_line_set = True
                            logger.info(f"深蹲检测基准线已设置在Y={detection_line_y}位置")

                            # Draw the initial detection line
                            cv2.line(annotated_frame, knee_line_coords[0], knee_line_coords[1], (0, 255, 255), 2)
                            cv2.line(annotated_frame, (0, detection_line_y),
                                     (annotated_frame.shape[1], detection_line_y), (0, 0, 255), 2)
                            cv2.circle(annotated_frame, knee_midpoint, 5, (0, 255, 255), -1)
                            cv2.putText(annotated_frame, "Detection Line Set",
                                        (knee_midpoint[0] - 60, knee_midpoint[1] - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

                        valid_knee_detection = True

                    # Set shoulder press detection line only once if not already set
                    if exercise_type == "shoulder-press" and not detection_line_set_shoulder:
                        if not np.isnan(left_shoulder).any() and not np.isnan(right_shoulder).any():
                            # Convert to integers for drawing
                            left_shoulder_point = (int(left_shoulder[0]), int(left_shoulder[1]))
                            right_shoulder_point = (int(right_shoulder[0]), int(right_shoulder[1]))

                            # Draw shoulder connection line
                            cv2.line(annotated_frame, left_shoulder_point, right_shoulder_point, (255, 255, 0), 2)

                            # Calculate target line height (above shoulders)
                            shoulder_midpoint_y = (left_shoulder[1] + right_shoulder[1]) / 2
                            shoulder_to_head_distance = frame.shape[0] * 0.15 * 1.2  # Adjusted factor

                            # Set detection line above shoulders
                            detection_line_y_shoulder = max(int(shoulder_midpoint_y - shoulder_to_head_distance),
                                                            int(frame.shape[0] * 0.1))  # Minimum 10% from top

                            # Set shoulder detection flag
                            detection_line_set_shoulder = True
                            logger.info(f"肩推检测基准线已设置在Y={detection_line_y_shoulder}位置")

        # Exercise-specific processing with original frame for classification
        if exercise_type == "squat":
            process_squat_exercise(frame, annotated_frame, angles, hip_midpoint, detection_line_set, detection_line_y)
            

        elif exercise_type == "shoulder-press":
            process_shoulder_press(frame, annotated_frame, keypoints, angles, detection_line_y_shoulder)
            

        elif exercise_type == "bicep-curl":
            process_bicep_curl(frame, annotated_frame, keypoints, angles)
            
        else:
            process_other_exercise(frame, annotated_frame, exercise_type)
            

        # Display exercise count
        cv2.putText(annotated_frame, f'Count: {exercise_count}', (10, annotated_frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Add status indicators for debugging
        status_text = []
        status_text.append(f"Squat Line: {'Yes' if detection_line_set else 'No'}")
        status_text.append(f"Shoulder Line: {'Yes' if detection_line_set_shoulder else 'No'}")
        status_text.append(f"Exercise: {exercise_type}")
        status_text.append(f"Frame: {annotated_frame.shape}")

        for i, text in enumerate(status_text):
            cv2.putText(annotated_frame, text, (10, 20 + i * 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        return annotated_frame

    except Exception as e:
        logger.error(f"Error in process_frame_realtime: {e}", exc_info=True)
        # Display error on frame
        if 'frame' in locals():
            error_frame = frame.copy() if frame is not None else np.zeros((480, 480, 3), dtype=np.uint8)
            cv2.putText(error_frame, f"Error: {str(e)}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            return error_frame
        return np.zeros((480, 480, 3), dtype=np.uint8)  # Return black frame on complete failure


def process_shoulder_press(frame, annotated_frame, keypoints, angles, detection_line_y_shoulder):
    """Handle shoulder press exercise processing logic using original frame for classification"""
    global exercise_count, last_pose

    # 添加除錯資訊收集
    debug_info = []
    debug_info.append(f"Detection line Y: {detection_line_y_shoulder}")

    # 檢查關鍵點是否足夠
    if keypoints is None or len(keypoints) < 17:
        logger.warning("Insufficient keypoints for shoulder press detection!")
        return

    current_model = exercise_models.get("shoulder-press")
    if not current_model:
        logger.warning("Shoulder press model not found!")
        return

    # 定義骨架連接（基於COCO 17個關鍵點）
    skeleton_connections = [
        (5, 7), (7, 9),    # 左肩-左肘-左手腕
        (6, 8), (8, 10),   # 右肩-右肘-右手腕
        (5, 6),            # 左肩-右肩
        (11, 12),          # 左髖-右髖
        (5, 11), (6, 12),  # 肩-髖
        (11, 13), (13, 15), # 左髖-左膝-左踝
        (12, 14), (14, 16), # 右髖-右膝-右踝
    ]

    # 繪製骨架連接線
    for connection in skeleton_connections:
        pt1 = tuple(map(int, keypoints[connection[0]][:2]))
        pt2 = tuple(map(int, keypoints[connection[1]][:2]))
        if not (np.isnan(pt1).any() or np.isnan(pt2).any()):
            cv2.line(annotated_frame, pt1, pt2, (0, 255, 0), 2)  # 綠色連線

    # 繪製關鍵點
    for kp in keypoints:
        if not np.isnan(kp).any():
            cv2.circle(annotated_frame, tuple(map(int, kp[:2])), 5, (0, 0, 255), -1)  # 紅色圓點

    # 提取關鍵點資訊
    left_shoulder = keypoints[5][:2]
    right_shoulder = keypoints[6][:2]
    left_elbow = keypoints[7][:2]
    right_elbow = keypoints[8][:2]
    left_wrist = keypoints[9][:2]
    right_wrist = keypoints[10][:2]

    # 檢查關鍵點有效性
    left_shoulder_valid = not np.isnan(left_shoulder).any()
    right_shoulder_valid = not np.isnan(right_shoulder).any()
    left_wrist_valid = not np.isnan(left_wrist).any()
    right_wrist_valid = not np.isnan(right_wrist).any()

    debug_info.append(f"Shoulder L/R valid: {left_shoulder_valid}/{right_shoulder_valid}")
    debug_info.append(f"Wrist L/R valid: {left_wrist_valid}/{right_wrist_valid}")

    # 嘗試執行分類模型
    try:
        shoulder_press_results = current_model(frame, conf=0.3, verbose=False)
        has_classification = len(shoulder_press_results) > 0 and len(shoulder_press_results[0].boxes) > 0
        debug_info.append(f"Classification detected: {has_classification}")
    except Exception as e:
        logger.error(f"Error running shoulder press model: {e}")
        has_classification = False
        debug_info.append(f"Classification error: {str(e)}")

    # 繪製肩膀連線
    if left_shoulder_valid and right_shoulder_valid:
        left_shoulder_point = (int(left_shoulder[0]), int(left_shoulder[1]))
        right_shoulder_point = (int(right_shoulder[0]), int(right_shoulder[1]))
        cv2.line(annotated_frame, left_shoulder_point, right_shoulder_point, (255, 255, 0), 2)

    # 檢測線邏輯
    if detection_line_y_shoulder is None or detection_line_y_shoulder <= 0:
        if left_shoulder_valid and right_shoulder_valid:
            shoulder_midpoint_y = (left_shoulder[1] + right_shoulder[1]) / 2
            shoulder_to_head_distance = frame.shape[0] * 0.15 * 1.2
            detection_line_y_shoulder = max(int(shoulder_midpoint_y - shoulder_to_head_distance),
                                            int(frame.shape[0] * 0.1))
            logger.info(f"自動設置肩推檢測線在Y={detection_line_y_shoulder}位置")
        else:
            detection_line_y_shoulder = int(frame.shape[0] * 0.2)
            logger.info(f"使用預設檢測線在Y={detection_line_y_shoulder}位置")

    # 繪製檢測線
    cv2.line(annotated_frame, (0, detection_line_y_shoulder),
             (annotated_frame.shape[1], detection_line_y_shoulder), (0, 0, 255), 2)
    cv2.putText(annotated_frame, "Target Line", (10, detection_line_y_shoulder - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    # 繪製和檢查手腕位置
    left_wrist_below = False
    right_wrist_below = False

    if left_wrist_valid:
        left_wrist_point = (int(left_wrist[0]), int(left_wrist[1]))
        left_wrist_below = left_wrist[1] < detection_line_y_shoulder
        wrist_color_left = (0, 255, 0) if left_wrist_below else (0, 0, 255)
        cv2.circle(annotated_frame, left_wrist_point, 5, wrist_color_left, -1)
        debug_info.append(f"Left wrist Y: {left_wrist[1]} (Below line: {left_wrist_below})")

    if right_wrist_valid:
        right_wrist_point = (int(right_wrist[0]), int(right_wrist[1]))
        right_wrist_below = right_wrist[1] < detection_line_y_shoulder
        wrist_color_right = (0, 255, 0) if right_wrist_below else (0, 0, 255)
        cv2.circle(annotated_frame, right_wrist_point, 5, wrist_color_right, -1)
        debug_info.append(f"Right wrist Y: {right_wrist[1]} (Below line: {right_wrist_below})")

    # 計算肘部角度
    if '左手肘' in angles and '右手肘' in angles:
        avg_elbow_angle = (angles.get('左手肘', 180) + angles.get('右手肘', 180)) / 2.0
        debug_info.append(f"Avg elbow angle: {avg_elbow_angle:.1f}°")
    else:
        avg_elbow_angle = 180
        debug_info.append("Elbow angles not available")

    # 評分邏輯
    should_score = False
    if (left_wrist_valid and left_wrist_below) or (right_wrist_valid and right_wrist_below):
        should_score = True

    if has_classification:
        best_box = shoulder_press_results[0].boxes[0]
        class_id = int(best_box.cls)
        conf = float(best_box.conf)
        class_name = current_model.names[class_id]
        x1, y1, x2, y2 = map(int, best_box.xyxy[0].cpu().numpy())
        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        label = f'{class_name} {conf:.2f}'
        cv2.putText(annotated_frame, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    else:
        debug_info.append("No classification, using pose data only")

    if should_score and (left_shoulder_valid and right_shoulder_valid) and (left_wrist_valid or right_wrist_valid):
        alignment_percent = 0
        if left_wrist_valid and left_shoulder_valid:
            left_wrist_shoulder_diff = abs(left_wrist[0] - left_shoulder[0])
            max_allowed_diff = frame.shape[1] * 0.2
            left_alignment = min(100, max(0, 100 - (left_wrist_shoulder_diff / max_allowed_diff * 100)))
            alignment_percent = left_alignment

        if right_wrist_valid and right_shoulder_valid:
            right_wrist_shoulder_diff = abs(right_wrist[0] - right_shoulder[0])
            max_allowed_diff = frame.shape[1] * 0.2
            right_alignment = min(100, max(0, 100 - (right_wrist_shoulder_diff / max_allowed_diff * 100)))
            if left_wrist_valid:
                alignment_percent = (alignment_percent + right_alignment) / 2
            else:
                alignment_percent = right_alignment

        elbow_extension_percent = calculate_shoulder_press_score(avg_elbow_angle)
        total_percent = (elbow_extension_percent + alignment_percent) / 2
        shoulder_press_quality_score = convert_percent_to_rating(total_percent)
        score_description = get_score_description(shoulder_press_quality_score)

        socketio.emit('shoulder_press_score', {'score': shoulder_quality_score}, namespace='/exercise')
        logger.info(f"肩推評分: {shoulder_press_quality_score}/5 ({int(total_percent)}%)")
        socketio.emit('exercise_count_update', {'count': exercise_count}, namespace='/exercise')
    else:
        reason = "無法進行評分: "
        if not (left_shoulder_valid and right_shoulder_valid):
            reason += "肩膀檢測失敗 "
        elif not (left_wrist_valid or right_wrist_valid):
            reason += "手腕檢測失敗 "
        elif not ((left_wrist_valid and left_wrist_below) or (right_wrist_valid and right_wrist_below)):
            reason += "請將手腕舉高超過目標線 "
        socketio.emit('shoulder_press_score', {'score': 0})
        logger.info(reason)

    # 顯示除錯資訊（可選）
    # for i, text in enumerate(debug_info):
    #     cv2.putText(annotated_frame, text, (10, 200 + i * 20),
    #                 cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)


def reset_detection_state_complete():
    """完整重置所有检测状态"""
    global exercise_count, last_pose, mid_pose_detected, squat_state, detection_line_set
    global detection_line_y, knee_line_coords, squat_quality_score, remaining_sets
    global detection_line_set_shoulder, detection_line_y_shoulder
    global detection_line_set_bicep, elbow_line_coords, bicep_state, shoulder_state
    global bicep_quality_score, last_curl_time
    
    # 重置基本状态
    exercise_count = 0
    last_pose = None
    mid_pose_detected = False
    
    # 重置下蹲相关状态
    squat_state = 'init'
    detection_line_set = False
    detection_line_y = 0
    knee_line_coords = None
    squat_quality_score = 0
    
    # 重置肩推相关状态
    shoulder_state = 'init'
    detection_line_set_shoulder = False
    detection_line_y_shoulder = 0
    
    # 重置二头弯举相关状态
    bicep_state = 'init'
    detection_line_set_bicep = False
    elbow_line_coords = None
    bicep_quality_score = 0
    last_curl_time = 0
    
    # 重置组数
    remaining_sets = target_sets
    
    logger.info("所有检测状态已重置")



def get_current_angles():
    """获取当前角度数据"""
    global current_angles
    if not hasattr(get_current_angles, 'current_angles'):
        get_current_angles.current_angles = {
            '左手肘': 0, '右手肘': 0, '左膝蓋': 0, '右膝蓋': 0,
            '左肩膀': 0, '右肩膀': 0, '左髖部': 0, '右髖部': 0
        }
    return get_current_angles.current_angles


def get_current_quality_score():
    """获取当前品质评分"""
    global squat_quality_score, bicep_quality_score
    exercise_type = get_current_exercise_type()
    
    if exercise_type == 'squat':
        return squat_quality_score
    elif exercise_type == 'bicep-curl':
        return bicep_quality_score
    elif exercise_type == 'shoulder-press':
        return shoulder_quality_score
    return 0

def get_current_coach_tip():
    """获取当前教练提示"""
    global current_coach_tip
    if not hasattr(get_current_coach_tip, 'current_coach_tip'):
        get_current_coach_tip.current_coach_tip = "請保持正確姿勢，開始運動"
    return get_current_coach_tip.current_coach_tip

def update_coach_tip(tip):
    """更新教练提示"""
    get_current_coach_tip.current_coach_tip = tip
    # 发送到前端
    socketio.emit('coach_tip', {'tip': tip}, namespace='/exercise')    