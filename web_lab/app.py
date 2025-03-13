import eventlet
eventlet.monkey_patch()  # 這行確保 socketIO 可以正確使用 eventlet

# 使用 PyMySQL 代替 MySQLdb（純 Python，不需要編譯 C 擴展）
import pymysql
# 在程式開頭更新日誌配置
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # 使用 stdout 而不是 stderr
        logging.FileHandler('pose_detection.log', encoding='utf-8')  # 指定編碼
    ]
)
logger = logging.getLogger(__name__)


from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from werkzeug.security import generate_password_hash
import mysql.connector
from mysql.connector import Error
from io import BytesIO
import pandas as pd
from flask import send_file
from flask import Flask, request, render_template, redirect, url_for, send_from_directory, Response, jsonify
from flask_socketio import SocketIO
import os
import cv2
import numpy as np
from ultralytics import YOLO
from werkzeug.utils import secure_filename
import torch
import queue
import threading
import time
import mediapipe as mp
from datetime import datetime
from flask_login import UserMixin

# ------------------------------
# 資料庫設定與連線 (使用 PyMySQL)
# ------------------------------
db_config = {
    'host': 'localhost',
    'user': 'nkust_user',
    'password': '1234',
    'database': 'nkust_exercise'
}


# 建立 Flask 應用前先設定資料庫配置到 app.config 中
app = Flask(__name__, static_folder='static')


app.secret_key = "your_secret_key"  # 設定 Flask 的 session key
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(UserMixin):
    def __init__(self, user_id, username, role):
        self.id = str(user_id)  # 🔹 確保 user_id 是字串，避免 session 讀取問題
        self.username = username
        self.role = role


# 自訂一個函式用來取得資料庫連線
def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        if err.errno == mysql.connector.errorcode.ER_ACCESS_DENIED_ERROR:
            app.logger.error("資料庫使用者名稱或密碼錯誤")
        elif err.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:
            app.logger.error("資料庫不存在")
        else:
            app.logger.error(f"資料庫連接錯誤: {err}")
        return None


def user_exists(username):
    """檢查用戶名是否已存在"""
    conn = get_db_connection()
    if not conn:
        raise Exception("無法連接資料庫")

    try:
        cursor = conn.cursor()
        query = "SELECT COUNT(*) FROM users WHERE username = %s"
        cursor.execute(query, (username,))
        count = cursor.fetchone()[0]
        return count > 0
    finally:
        cursor.close()
        conn.close()


def create_user(username, password_hash, role):
    """創建新用戶"""
    conn = get_db_connection()
    if not conn:
        raise Exception("無法連接資料庫")

    try:
        cursor = conn.cursor()
        query = """
        INSERT INTO users (username, password_hash, role)
        VALUES (%s, %s, %s)
        """
        cursor.execute(query, (username, password_hash, role))
        conn.commit()
    except Error as e:
        conn.rollback()
        raise Exception(f"創建用戶錯誤: {e}")
    finally:
        cursor.close()
        conn.close()

def test_db_connection():
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return result[0] == 1
        return False
    except Exception as e:
        print(f"測試連接錯誤: {e}")
        return False

def check_users_table():
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("DESCRIBE users")
            columns = cursor.fetchall()
            cursor.close()
            conn.close()
            return len(columns) > 0
        return False
    except Exception as e:
        print(f"檢查表結構錯誤: {e}")
        return False

# 在啟動應用前測試
if not test_db_connection():
    print("警告: 無法連接到資料庫!")


socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

# ------------------------------
# 其他設定與模型初始化
# ------------------------------
os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # 指定 GPU

# 檢查 GPU
if torch.cuda.is_available():
    device = 'cuda'
    print(f"Using GPU: {torch.cuda.get_device_name(0)}")
else:
    device = 'cpu'
    print("Using CPU")

# 在全局變量區域初始化姿態估計模型
pose_model = YOLO("yolov8n-pose.pt")  # 使用基礎姿態估計模型

# 全局變數用於控制偵測狀態
detection_active = False
current_exercise_type = 'squat'
frame_buffer = queue.Queue(maxsize=2)
processed_frame_buffer = queue.Queue(maxsize=2)
exercise_count = 0
last_pose = None
mid_pose_detected = False

# 日誌設定（若重複設定則可略過）
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MediaPipe setup
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_pose = mp.solutions.pose

# 文件儲存設定
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024




# 模型位置設定
MODEL_PATHS = {
    'squat': 'D:\\project_Main\\modles\\yolov8_squat_model\\weights\\best.pt',
    'bicep-curl': 'D:\\project_Main\\modles\\best_bicep.pt',
    'shoulder-press': 'D:\\project_Main\\modles\\yolov8_shoulder_model\\weights\\best.pt',
    'push-up': 'D:\\project_Main\\modles\\push-up_model\\weights\\pushup_best.pt',
    'pull-up': 'D:\\project_Main\\modles\\best_pullup.pt',
    'dumbbell-row':'D:\\project_Main\\modles\\dumbbellrow_train\\weights\\best.pt'

}

# 加載運動分類模型
with app.app_context():
    models = {}
    for exercise_type, model_path in MODEL_PATHS.items():
        try:
            if torch.cuda.is_available():
                exercise_model = YOLO(model_path).to('cuda')
            else:
                exercise_model = YOLO(model_path)
            models[exercise_type] = exercise_model
            logger.info(f"YOLO model for {exercise_type} loaded successfully from {model_path}")
        except Exception as e:
            logger.error(f"Error loading YOLO model for {exercise_type}: {e}")

# 工具函數
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

def get_pose_angles(keypoints):
    angles = {}
    try:
        logger.info("get_pose_angles function called")  # 添加這行
        # Check if enough keypoints are detected
        if len(keypoints) < 17:
            logger.warning("Not enough keypoints detected to calculate angles.")
            return angles  # Return empty dictionary if not enough keypoints

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

        # 檢查關鍵點座標是否有效
        if any(np.isnan(kp).any() for kp in [left_shoulder, right_shoulder, left_elbow, right_elbow, left_wrist, right_wrist, left_hip, right_hip, left_knee, right_knee, left_ankle, right_ankle]):
            logger.warning("Invalid keypoint coordinates detected.")
            return angles

        # 計算基本角度
        try:
            angles['左手肘'] = calculate_angle(left_shoulder, left_elbow, left_wrist)
            angles['右手肘'] = calculate_angle(right_shoulder, right_elbow, right_wrist)
            angles['左膝蓋'] = calculate_angle(left_hip, left_knee, left_ankle)
            angles['右膝蓋'] = calculate_angle(right_hip, right_knee, right_ankle)
            angles['左肩膀'] = calculate_angle(left_hip, left_shoulder, left_elbow)
            angles['右肩膀'] = calculate_angle(right_hip, right_shoulder, right_elbow)
            angles['左髖部'] = calculate_angle(left_shoulder, left_hip, left_knee)
            angles['右髖部'] = calculate_angle(right_shoulder, right_hip, right_knee)
        except Exception as e:
            logger.error(f"Error calculating angles: {e}")

        logger.info(f"Calculated angles: {angles}")  # 添加這行
    except Exception as e:
        logging.error(f"計算角度時發生錯誤: {e}")
    logger.info(f"Angles calculated: {angles}")
    return angles

def process_frame(frame):
    frame = cv2.resize(frame, (480, 480))
    results = pose_model(frame)  # 改為使用 pose_model
    annotated_frame = frame.copy()

    for result in results:
        if result.keypoints is not None:
            keypoints = result.keypoints.xy.cpu().numpy()[0]  # 獲取關鍵點座標
            angles = get_pose_angles(keypoints)
            socketio.emit('angle_data', angles)
            for kp in keypoints:
                x, y = int(kp[0]), int(kp[1])
                cv2.circle(annotated_frame, (x, y), 5, (0, 255, 0), -1)
    return annotated_frame

def get_exercise_angles(landmarks, exercise_type='squat'):
    angles = {}
    try:
        # 基本姿勢點
        left_shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,
                         landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
        right_shoulder = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x,
                          landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
        left_elbow = [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x,
                      landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
        right_elbow = [landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x,
                       landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y]
        left_wrist = [landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].x,
                      landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y]
        right_wrist = [landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].x,
                       landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value].y]
        left_hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x,
                    landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y]
        right_hip = [landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].x,
                     landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value].y]
        left_knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x,
                     landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
        right_knee = [landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].x,
                      landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value].y]
        left_ankle = [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x,
                      landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
        right_ankle = [landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x,
                       landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y]

        # 計算基本角度
        angles['左手肘'] = calculate_angle(left_shoulder, left_elbow, left_wrist)
        angles['右手肘'] = calculate_angle(right_shoulder, right_elbow, right_wrist)
        angles['左膝蓋'] = calculate_angle(left_hip, left_knee, left_ankle)
        angles['右膝蓋'] = calculate_angle(right_hip, right_knee, right_ankle)
        angles['左肩膀'] = calculate_angle(left_hip, left_shoulder, left_elbow)
        angles['右肩膀'] = calculate_angle(right_hip, right_shoulder, right_elbow)
        angles['左髖部'] = calculate_angle(left_shoulder, left_hip, left_knee)
        angles['右髖部'] = calculate_angle(right_shoulder, right_hip, right_knee)

        # 引體向上專用角度計算
        if exercise_type == 'pull-up':
            # 計算手臂與垂直線的夾角
            # 創建垂直參考點 (與肩同x,但y較小)
            left_vertical = [left_shoulder[0], left_shoulder[1] - 0.2]
            right_vertical = [right_shoulder[0], right_shoulder[1] - 0.2]

            angles['左手臂懸垂角度'] = calculate_angle(left_vertical, left_shoulder, left_elbow)
            angles['右手臂懸垂角度'] = calculate_angle(right_vertical, right_shoulder, right_elbow)

            # 計算身體傾斜角度
            # 創建垂直參考點 (與髖部同x,但y較小)
            hip_vertical = [left_hip[0], left_hip[1] - 0.2]
            angles['身體傾斜度'] = calculate_angle(hip_vertical, left_hip, left_shoulder)

            # 計算肘部彎曲程度
            angles['引體向上深度'] = min(angles['左手肘'], angles['右手肘'])

    except Exception as e:
        logger.error(f"Error calculating angles: {e}")

    return angles



detection_line_set_shoulder = False
detection_line_y_shoulder = 0

exercise_count = 0
squat_state = "up"  # 深蹲初始狀態：站立（"up"）
last_squat_time = 0  # 記錄上一次成功計數的時間（秒）
last_pose = None
mid_pose_detected = False


detection_line_set = False  # 标记检测线是否已设置
detection_line_y = 0  # 基准线的Y坐标
knee_line_coords = None  # 存储膝盖连线的两端坐标
squat_quality_score = 0  # 深蹲质量评分

detection_line_set_bicep = False
elbow_line_coords = None
last_curl_time = 0
bicep_quality_score = 0


def process_frame_realtime(frame, exercise_type):
    global exercise_count, last_pose, mid_pose_detected, squat_state, last_squat_time
    global detection_line_set, detection_line_y, knee_line_coords, squat_quality_score
    global detection_line_set_shoulder, detection_line_y_shoulder

    try:
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
                    socketio.emit('angle_data', angles)

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

    current_model = models.get("shoulder-press")
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

        socketio.emit('shoulder_press_score', {'score': int(shoulder_press_quality_score)})
        logger.info(f"肩推評分: {shoulder_press_quality_score}/5 ({int(total_percent)}%)")
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

def process_squat_exercise(frame, annotated_frame, angles, hip_midpoint, detection_line_set, detection_line_y):
    """Handle squat exercise processing logic using original frame for classification"""
    global exercise_count, last_pose, squat_state, last_squat_time, squat_quality_score

    current_model = models.get("squat")
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
                socketio.emit('squat_quality', {'score': squat_quality_score})
                logger.info(f"深蹲评分: {squat_quality_score}/5")

            elif last_pose == 1 and class_id == 0:  # From squat back to prepare
                current_time = time.time()
                if current_time - last_squat_time > 0.8:  # Time interval to prevent false counts
                    exercise_count += 1
                    last_squat_time = current_time
                    squat_state = "up"
                    logger.info(f"Squat completed, count: {exercise_count}")
                    socketio.emit('exercise_count_update', {'count': exercise_count})

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

bicep_state = "down"
last_curl_time = 0
def process_bicep_curl(frame, annotated_frame, keypoints, angles):
    """Handle bicep curl exercise processing logic using original frame for classification"""
    global exercise_count, last_pose, bicep_quality_score, detection_line_set_bicep, elbow_line_coords, last_curl_time, bicep_state

    # Debug information collection
    debug_info = []
    debug_info.append("Bicep curl detection active")

    if keypoints is None or len(keypoints) < 17:
        logger.warning("Insufficient keypoints for bicep curl detection!")
        return

    current_model = models.get("bicep-curl")
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
                socketio.emit('exercise_count_update', {'count': exercise_count})
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

        socketio.emit('bicep_curl_score', {'score': final_score})
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
        socketio.emit('bicep_curl_score', {'score': 0})
        logger.info(reason)

    # Display debug info
    for i, text in enumerate(debug_info):
        cv2.putText(annotated_frame, text, (10, 200 + i * 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)


def process_other_exercise(frame, annotated_frame, exercise_type):
    """Handle processing for other exercise types using original frame for classification"""
    global exercise_count, last_pose, mid_pose_detected

    current_model = models.get(exercise_type)
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
                socketio.emit('exercise_count_update', {'count': exercise_count})
        elif num_classes == 2:
            if last_pose is not None:
                if last_pose == 0 and class_id == 1:
                    mid_pose_detected = True
                elif last_pose == 1 and class_id == 0 and mid_pose_detected:
                    exercise_count += 1
                    mid_pose_detected = False
                    socketio.emit('exercise_count_update', {'count': exercise_count})
            last_pose = class_id


def reset_detection_state():
    global detection_line_set, detection_line_y, knee_line_coords, squat_quality_score
    global detection_line_set_shoulder, detection_line_y_shoulder
    detection_line_set = False
    detection_line_y = 0
    knee_line_coords = None
    squat_quality_score = 0
    detection_line_set_shoulder = False
    detection_line_y_shoulder = 0


def video_capture_thread(camera_index=1):
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        logger.error(f"無法開啟攝像頭 {camera_index}")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 360)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
    cap.set(cv2.CAP_PROP_FPS, 20)

    while detection_active:
        ret, frame = cap.read()
        if not ret:
            logger.error("無法讀取影像幀")
            break
        frame = cv2.resize(frame, (360, 360))

        if not frame_buffer.full():
            frame_buffer.put(frame)
            logger.info("成功將影像幀放入 frame_buffer")
        else:
            try:
                frame_buffer.get_nowait()
            except queue.Empty:
                pass
            frame_buffer.put(frame)
            logger.info("隊列已滿，清空後放入新影像幀")
        time.sleep(0.01)

    cap.release()
    logger.info("攝像頭執行緒已正常停止")

def frame_processing_thread(exercise_type='squat'):
    while detection_active:
        if not frame_buffer.empty():
            frame = frame_buffer.get()
            processed_frame = process_frame_realtime(frame, exercise_type)
            if not processed_frame_buffer.full():
                processed_frame_buffer.put(processed_frame)
        time.sleep(0.001)
    logger.info("畫面處理執行緒已停止")

def generate_frames():
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = process_frame(frame)
        ret, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    cap.release()

def cleanup_buffers():
    """定期清理緩衝區"""
    while True:
        if frame_buffer.qsize() > 1:
            try:
                frame_buffer.get_nowait()
            except queue.Empty:
                pass
        time.sleep(0.1)

def check_thread_status():
    """檢查執行緒狀態"""
    while True:
        active_threads = threading.enumerate()
        logger.info(f"Active threads: {[t.name for t in active_threads]}")
        time.sleep(5)  # 每5秒檢查一次

def setup_gpu():
    try:
        if torch.cuda.is_available():
            print(f"PyTorch 可以使用 GPU: {torch.cuda.get_device_name(0)}")
            torch.cuda.empty_cache()  # 清空 GPU 緩存
        else:
            print("PyTorch 無法使用 GPU，將使用 CPU")
    except Exception as e:
        print(f"GPU 配置時發生錯誤：{e}")
        print("將使用 CPU 運行")


def get_current_frame():
    """從 frame_buffer 取得最新影像"""
    timeout = 5  # 等待 5 秒
    start_time = time.time()
    while frame_buffer.empty():
        if time.time() - start_time > timeout:
            logger.error("等待影像超時，隊列仍為空")
            return None
        time.sleep(0.1)
    return frame_buffer.get()


@login_manager.user_loader
def load_user(user_id):
    print(f"🔍 嘗試加載用戶 ID: {user_id}")  # Debug

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    connection.close()

    print(f"📝 查詢結果: {user}")  # Debug

    if user:
        return User(user["user_id"], user["username"], user["role"])
    else:
        print("⚠️ 找不到用戶，回傳 None")
        return None  # 確保找不到用戶時回傳 None

@app.route('/')
def index():
    return render_template('index.html', current_user=current_user)

@app.route('/realtime')
def realtime():
    return render_template('realtime.html')

@app.route('/Equipment_Introduction')
def Equipment_Introduction():
    return render_template('Equipment Introduction Page.html')

@app.route('/Exercise_Knowledge')
def Exercise_Knowledge():
    return render_template('Exercise Knowledge Page.html')

@app.route('/page1')
def Recommended_Setup_Page():
    return render_template('Recommended_Setup_Page.html')

@app.route('/page2')
def Technologies_Page():
    return render_template('Technologies_Page.html')

@app.route('/start_detection', methods=['POST'])
def start_detection():
    global detection_active, current_exercise_type, exercise_count, last_pose, mid_pose_detected, remaining_sets

    try:
        exercise_type = request.args.get('exercise_type', 'squat')

        data = request.get_json() or {}
        weight = data.get('weight')
        reps = data.get('reps')  # 每組次數
        sets = data.get('sets')  # 組數
        student_id = data.get('student_id')

        if not all([student_id, weight, reps, sets]):
            return jsonify({'success': False, 'error': '請完整填寫所有輸入欄位'}), 400

        connection = get_db_connection()
        cursor = connection.cursor()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            INSERT INTO exercise_info (student_id, weight, reps, sets, exercise_type, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (student_id, weight, reps, sets, exercise_type, timestamp))
        connection.commit()
        cursor.close()
        connection.close()

        current_exercise_type = exercise_type
        exercise_count = 0
        last_pose = None
        mid_pose_detected = False

        remaining_sets = int(sets)  # 記錄剩餘組數
        socketio.emit('remaining_sets_update', {'remaining_sets': remaining_sets})  # 傳送剩餘組數到前端

        if not detection_active:
            detection_active = True
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                cap.release()
                return jsonify({'success': False, 'error': '無法開啟攝像頭'}), 400
            cap.release()
            threading.Thread(target=video_capture_thread, name="VideoCapture").start()
            threading.Thread(target=frame_processing_thread, args=(exercise_type,), name="FrameProcessing").start()
            return jsonify({'success': True})

    except Exception as e:
        logger.error(f"啟動偵測時發生錯誤: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/stop_detection', methods=['POST'])
def stop_detection():
    global detection_active
    detection_active = False
    reset_detection_state()
    logger.info("停止即時偵測執行緒")
    return jsonify({'success': True})

@app.route('/video_feed')
def video_feed():
    def generate():
        while True:
            if not processed_frame_buffer.empty():
                frame = processed_frame_buffer.get()
                if frame is not None:
                    ret, buffer = cv2.imencode('.jpg', frame)
                    if ret:
                        frame_bytes = buffer.tobytes()
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                time.sleep(0.01)
    return Response(generate(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/static/models/<path:filename>')
def serve_model(filename):
    return send_from_directory('static/models', filename)



@app.route('/export_excel', methods=['GET'])
def export_excel():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            SELECT student_id, weight, reps, sets, exercise_type, timestamp
            FROM exercise_info
            ORDER BY timestamp DESC
        """)

        records = cursor.fetchall()
        if not records:
            return jsonify({'error': '沒有找到運動記錄'}), 404

        df = pd.DataFrame(records)
        df.columns = ['學號', '重量(Kg)', '每組次數', '組數', '運動類型', '紀錄時間']
        df['紀錄時間'] = pd.to_datetime(df['紀錄時間']).dt.strftime('%Y-%m-%d %H:%M:%S')

        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='運動紀錄')

            workbook = writer.book
            worksheet = writer.sheets['運動紀錄']
            worksheet.set_column('A:A', 15)
            worksheet.set_column('B:B', 10)
            worksheet.set_column('C:C', 15)
            worksheet.set_column('D:D', 10)
            worksheet.set_column('E:E', 15)
            worksheet.set_column('F:F', 20)

            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#00BCD4',
                'font_color': 'white',
                'align': 'center',
                'valign': 'vcenter',
                'border': 1
            })
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)

            worksheet.freeze_panes(1, 0)

        output.seek(0)
        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True, download_name=f"運動紀錄_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")

    except Exception as e:
        return jsonify({'error': f'匯出記錄失敗: {str(e)}'}), 500

@app.route('/update_monster_count', methods=['POST'])
def update_monster_count():
    try:
        data = request.json
        count = data.get('count')
        exercise_type = data.get('exercise_type')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO exercise_records (monster_count, exercise_type, timestamp)
            VALUES (%s, %s, %s)
        """, (count, exercise_type, timestamp))
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"更新紀錄發生錯誤: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/test_db')
def test_db():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute('SELECT 1')
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        return jsonify({'message': '數據庫連接成功！', 'result': result})
    except Exception as e:
        return jsonify({'error': f'數據庫連接失敗: {str(e)}'})

#討論區==========================================
@app.route('/classroom')
@login_required  # 確保用戶已登入
def classroom():
    return render_template('classroom.html')


@app.route('/api/discussions', methods=['GET'])
def get_discussions():
    try:
        course_id = request.args.get('course_id')
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)  # 使用 dictionary cursor 讓結果更容易處理

        cursor.execute("""
            SELECT d.*, c.course_name,
                   COALESCE(u_student.username, '') as student_username,
                   COALESCE(u_teacher.username, '') as teacher_username,
                   (SELECT COUNT(*) FROM responses WHERE discussion_id = d.discussion_id) as response_count
            FROM discussions d
            JOIN courses c ON d.course_id = c.course_id
            LEFT JOIN users u_student ON d.student_id = u_student.user_id
            LEFT JOIN users u_teacher ON d.teacher_id = u_teacher.user_id
            WHERE d.course_id = %s
            ORDER BY d.created_at DESC
        """, (course_id,))

        discussions = cursor.fetchall()
        cursor.close()
        connection.close()

        # 確保所有數據欄位格式正確
        for d in discussions:
            d['created_at'] = d['created_at'].isoformat() if d['created_at'] else None
            # 判斷發布者是教師還是學生
            if d['teacher_id']:
                d['publisher_id'] = d['teacher_id']
                d['publisher_name'] = d['teacher_username']
                d['is_teacher_post'] = True
            else:
                d['publisher_id'] = d['student_id']
                d['publisher_name'] = d['student_username']
                d['is_teacher_post'] = False

        return jsonify({'success': True, 'discussions': discussions})
    except Exception as e:
        logger.error(f"獲取討論列表失敗: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/discussions', methods=['POST'])
@login_required
def create_discussion():
    try:
        data = request.json
        course_id = data.get('course_id')
        title = data.get('title')
        content = data.get('content')

        if not all([course_id, title, content]):
            return jsonify({'success': False, 'error': '缺少必要資料'}), 400

        connection = get_db_connection()
        cursor = connection.cursor()

        if current_user.role == 'teacher':

            cursor.execute("""
                INSERT INTO discussions (course_id, teacher_id, student_id, title, content)
                VALUES (%s, %s, %s, %s, %s)
            """, (course_id, current_user.id, None, title, content))

        else:
            # 學生發文時，teacher_id 設為 NULL
            cursor.execute("""
                INSERT INTO discussions (course_id, teacher_id, student_id, title, content)
                VALUES (%s, NULL, %s, %s, %s)
            """, (course_id, current_user.id, title, content))

        connection.commit()
        cursor.close()
        connection.close()

        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"創建討論失敗: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/responses', methods=['GET'])
def get_responses():
    try:
        discussion_id = request.args.get('discussion_id')
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)  # 使用 dictionary cursor

        cursor.execute("""
            SELECT r.*,
                   CASE 
                     WHEN r.is_teacher = 1 THEN (SELECT username FROM users WHERE user_id = r.user_id)
                     ELSE (SELECT username FROM users WHERE user_id = r.user_id)
                   END as username
            FROM responses r
            WHERE r.discussion_id = %s
            ORDER BY r.created_at ASC
        """, (discussion_id,))

        responses = cursor.fetchall()
        cursor.close()
        connection.close()

        # 確保創建時間的格式正確
        for r in responses:
            r['created_at'] = r['created_at'].isoformat() if r['created_at'] else None

        return jsonify({'success': True, 'responses': responses})
    except Exception as e:
        logger.error(f"獲取回覆失敗: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/responses', methods=['POST'])
@login_required
def create_response():
    try:
        data = request.json
        discussion_id = data.get('discussion_id')
        content = data.get('content')
        user_id = current_user.id

        # 根據當前使用者的角色自動設定 is_teacher
        is_teacher = True if current_user.role == 'teacher' else False

        if not all([discussion_id, user_id, content]):
            return jsonify({'success': False, 'error': '缺少必要資料'}), 400

        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO responses (discussion_id, user_id, content, is_teacher)
            VALUES (%s, %s, %s, %s)
        """, (discussion_id, user_id, content, is_teacher))

        connection.commit()
        cursor.close()
        connection.close()

        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"創建回覆失敗: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/discussions/<int:discussion_id>', methods=['DELETE'])
@login_required  # 確保用戶已登入
def delete_discussion(discussion_id):
    try:
        # 檢查當前用戶是否為教師
        if current_user.role != 'teacher':
            return jsonify({'success': False, 'error': '只有老師可以刪除討論'}), 403

        connection = get_db_connection()
        cursor = connection.cursor()

        # 首先檢查討論是否存在
        cursor.execute("SELECT course_id FROM discussions WHERE discussion_id = %s", (discussion_id,))
        discussion = cursor.fetchone()

        if not discussion:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'error': '討論不存在'}), 404

        # 刪除相關的回覆
        cursor.execute("DELETE FROM responses WHERE discussion_id = %s", (discussion_id,))

        # 刪除討論
        cursor.execute("DELETE FROM discussions WHERE discussion_id = %s", (discussion_id,))

        connection.commit()
        cursor.close()
        connection.close()

        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"刪除討論失敗: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/responses/<int:response_id>', methods=['DELETE'])
@login_required  # 確保用戶已登入
def delete_response(response_id):
    try:
        # 檢查當前用戶是否為教師
        if current_user.role != 'teacher':
            return jsonify({'success': False, 'error': '只有老師可以刪除回覆'}), 403

        connection = get_db_connection()
        cursor = connection.cursor()

        # 首先檢查回覆是否存在
        cursor.execute("SELECT discussion_id FROM responses WHERE response_id = %s", (response_id,))
        response = cursor.fetchone()

        if not response:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'error': '回覆不存在'}), 404

        # 刪除回覆
        cursor.execute("DELETE FROM responses WHERE response_id = %s", (response_id,))

        connection.commit()
        cursor.close()
        connection.close()

        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"刪除回覆失敗: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

#登入系統=============================================

@app.route('/api/user/status')
@login_required
def get_user_status():
    return jsonify({
        'success': True,
        'role': current_user.role,
        'username': current_user.username,
        'user_id': current_user.id
    })

@app.route('/register', methods=['GET'])
def register_page():
    return render_template('register.html')

from flask_bcrypt import Bcrypt

bcrypt = Bcrypt(app)

@app.route('/register', methods=['POST'])
def handle_register():
    try:
        data = request.get_json()
        username = data['username']
        password = data['password']
        role = data['role']

        if user_exists(username):
            return jsonify({'success': False, 'error': '用戶名已存在'}), 409

        # 確保使用 Flask-Bcrypt 來加密密碼
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        create_user(username, hashed_password, role)
        return jsonify({'success': True, 'message': '註冊成功'}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    connection.close()

    if user and bcrypt.check_password_hash(user["password_hash"], password):
        user_obj = User(user["user_id"], user["username"], user["role"])
        login_user(user_obj)

        # 🔹 如果 `next` 參數存在，跳轉回原本的頁面，否則跳轉到首頁
        next_page = request.args.get('next')
        return jsonify({'success': True, 'message': '登入成功', 'role': user["role"], 'next': next_page or '/'})
    else:
        return jsonify({'success': False, 'error': '帳號或密碼錯誤'})

@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))  # 確保'index'是你的首頁路由名稱

#圖表工作=============================================

@app.route('/api/dashboard_data', methods=['GET'])
@login_required
def dashboard_data():
    try:
        user_id = current_user.id  # 只抓取當前使用者的紀錄
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # 取得該使用者的所有運動紀錄
        cursor.execute("""
            SELECT timestamp, weight, reps, sets, exercise_type
            FROM exercise_info
            WHERE student_id = %s
            ORDER BY timestamp ASC
        """, (user_id,))
        records = cursor.fetchall()

        cursor.close()
        connection.close()

        # 可在這裡進一步聚合數據，例：
        # - 依照日期統計運動次數或總重量
        # - 根據目標數據計算完成百分比
        # 此處範例直接回傳原始紀錄，由前端或後端後續處理
        return jsonify({'success': True, 'records': records})
    except Exception as e:
        logger.error(f"取得儀表板數據失敗: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/exercise_data', methods=['GET'])
@login_required  # 確保用戶已登入
def get_exercise_data():
    student_id = current_user.username  # 使用登入者的學號
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT exercise_type, timestamp, reps, sets, weight
            FROM exercise_info
            WHERE student_id = %s
            ORDER BY timestamp ASC
        """
        cursor.execute(query, (student_id,))
        records = cursor.fetchall()

        cursor.close()
        connection.close()

        if not records:
            return jsonify({'success': False, 'message': '無運動數據'})

        return jsonify({'success': True, 'data': records})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})




if __name__ == '__main__':
    setup_gpu()
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    os.makedirs('static/models', exist_ok=True)
    while not frame_buffer.empty():
        frame_buffer.get()
    while not processed_frame_buffer.empty():
        processed_frame_buffer.get()
    threading.Thread(target=check_thread_status, daemon=True, name="ThreadMonitor").start()
    app.logger.info("🚀 Flask 伺服器啟動: http://127.0.0.1:5000")
    socketio.run(app, host='127.0.0.1', port=5000, debug=False)