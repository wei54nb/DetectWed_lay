import cv2
import numpy as np
import logging
import torch
from ultralytics import YOLO
from flask import current_app
from app import socketio
import os

logger = logging.getLogger(__name__)

# 全局变量
models = {}  # 這個字典只用於存其他辅助模型
pose_model = None  # 專門用於姿態檢測的模型

# 修改 setup_models 函数，不依赖 current_app
def setup_models():
    """设置模型"""
    global models
    
    try:
        # 使用硬编码的模型路径，而不是从 current_app.config 获取
        model_paths = {
            'pose': 'yolov8n-pose.pt',
            # 其他模型...
        }
        
        # 检查本地模型文件
        for model_name, model_path in model_paths.items():
            # 尝试加载本地模型文件
            local_path = os.path.join(os.path.dirname(__file__), '..', '..', model_path)
            if os.path.exists(local_path):
                models[model_name] = YOLO(local_path)
                logger.info(f"已加载本地模型: {model_name} 从 {local_path}")
            else:
                # 如果本地文件不存在，从网络下载
                models[model_name] = YOLO(model_path)
                logger.info(f"已从网络加载模型: {model_name}")
        
        return True
    except Exception as e:
        logger.error(f"设置模型时出错: {e}", exc_info=True)
        return False

def calculate_angle(a, b, c):
    """计算三点之间的角度"""
    # 将 a, b, c 转换为 numpy 数组
    a, b, c = np.array(a), np.array(b), np.array(c)

    # 计算向量 BA 和 BC（即从 b 到 a 以及从 b 到 c 的向量）
    ba = a - b
    bc = c - b

    # 计算向量的点积
    dot_product = np.dot(ba, bc)

    # 计算向量的长度
    norm_ba = np.linalg.norm(ba)
    norm_bc = np.linalg.norm(bc)

    # 防止除以 0 的情况（如果某向量长度为 0，就直接返回 0 度）
    if norm_ba == 0 or norm_bc == 0:
        return 0.0

    # 计算夹角的 cosine 值，并利用 clip 限制范围在 [-1, 1]
    cos_theta = np.clip(dot_product / (norm_ba * norm_bc), -1.0, 1.0)

    # 利用 arccos 求出角度，再转换为度数
    angle = np.degrees(np.arccos(cos_theta))

    return angle

def get_pose_angles(keypoints):
    """计算姿态关键点的角度"""
    angles = {}
    try:
        logger.info("get_pose_angles function called")
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

        # 检查关键点坐标是否有效
        if any(np.isnan(kp).any() for kp in [left_shoulder, right_shoulder, left_elbow, right_elbow, left_wrist, right_wrist, left_hip, right_hip, left_knee, right_knee, left_ankle, right_ankle]):
            logger.warning("Invalid keypoint coordinates detected.")
            return angles

        # 计算基本角度
        try:
            angles['左手肘'] = calculate_angle(left_shoulder, left_elbow, left_wrist)
            angles['右手肘'] = calculate_angle(right_shoulder, right_elbow, right_wrist)
            angles['左膝盖'] = calculate_angle(left_hip, left_knee, left_ankle)
            angles['右膝盖'] = calculate_angle(right_hip, right_knee, right_ankle)
            angles['左肩膀'] = calculate_angle(left_hip, left_shoulder, left_elbow)
            angles['右肩膀'] = calculate_angle(right_hip, right_shoulder, right_elbow)
            angles['左髋部'] = calculate_angle(left_shoulder, left_hip, left_knee)
            angles['右髋部'] = calculate_angle(right_shoulder, right_hip, right_knee)
        except Exception as e:
            logger.error(f"Error calculating angles: {e}")

    except Exception as e:
        logger.error(f"Error in get_pose_angles: {e}")
    return angles

def load_models():
    """加载姿态检测模型"""
    global pose_model
    
    try:
        # 从配置獲取模型路徑
        base_dir = current_app.config['BASE_DIR']
        
        # 加载姿態檢測模型模型
        logger.info("正在加载姿态检测模型...")
        pose_path = os.path.join(base_dir, 'static', 'models', 'YOLO_MODLE', 'pose', 'yolov8n-pose.pt')
        
        # 如果文件不存在，使用默認路徑
        if not os.path.exists(pose_path):
            logger.warning(f"姿态检测模型文件不存在: {pose_path}，使用默认模型")
            pose_model = YOLO('yolov8n-pose.pt')
        else:
            pose_model = YOLO(pose_path)
        
        logger.info("姿态检测模型加载完成")
        
       
        
    except Exception as e:
        logger.error(f"加载模型时出错: {e}", exc_info=True)
        raise