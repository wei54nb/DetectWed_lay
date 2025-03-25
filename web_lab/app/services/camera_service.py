import cv2
import logging
import threading
import time
import queue

logger = logging.getLogger(__name__)

# 全局变量
camera = None
frame_buffer = None
frame_available = threading.Event()
camera_lock = threading.Lock()
frame_buffer = queue.Queue(maxsize=2)

def get_camera():
    """获取摄像头实例"""
    global camera
    
    with camera_lock:
        if camera is None:
            try:
                camera = cv2.VideoCapture(1)
                if not camera.isOpened():
                    logger.error("无法打开摄像头")
                    return None
                
                # 设置摄像头参数
                camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                camera.set(cv2.CAP_PROP_FPS, 30)
                
                # 启动帧获取线程
                threading.Thread(target=capture_frames, daemon=True).start()
                logger.info("摄像头初始化成功")
            except Exception as e:
                logger.error(f"初始化摄像头时出错: {e}")
                return None
    
    return camera

def capture_frames():
    """持续捕获帧的线程函数"""
    global camera, frame_buffer
    
    logger.info("开始捕获视频帧")
    
    while True:
        if camera is None or not camera.isOpened():
            logger.warning("摄像头未打开，尝试重新打开")
            with camera_lock:
                try:
                    if camera is not None:
                        camera.release()
                    camera = cv2.VideoCapture(1)
                    if not camera.isOpened():
                        logger.error("无法重新打开摄像头")
                        time.sleep(1)
                        continue
                except Exception as e:
                    logger.error(f"重新打开摄像头时出错: {e}")
                    time.sleep(1)
                    continue
        
        try:
            ret, frame = camera.read()
            if not ret:
                logger.warning("无法读取帧")
                time.sleep(0.1)
                continue
            
            # 更新帧缓冲
            frame_buffer = frame.copy()
            
            # 通知等待的线程有新帧可用
            frame_available.set()
            
            # 控制帧率
            time.sleep(0.01)
        except Exception as e:
            logger.error(f"捕获帧时出错: {e}")
            time.sleep(0.1)

def get_current_frame():
    """获取当前帧"""
    global frame_buffer
    
    if frame_buffer is None:
        # 等待帧可用
        if not frame_available.wait(timeout=1.0):
            logger.warning("等待帧超时")
            return None
        frame_available.clear()
    
    return frame_buffer.copy() if frame_buffer is not None else None

def wait_for_frame(timeout=1.0):
    """等待新帧可用"""
    frame_available.wait(timeout)
    frame_available.clear()

def release_camera():
    """释放摄像头资源"""
    global camera
    
    with camera_lock:
        if camera is not None and camera.isOpened():
            camera.release()
            camera = None
            logger.info("摄像头资源已释放")