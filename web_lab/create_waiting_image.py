import cv2
import numpy as np
import os

# 创建目录（如果不存在）
os.makedirs('static/img', exist_ok=True)

# 创建一个黑色背景图像
img = np.zeros((480, 480, 3), dtype=np.uint8)

# 添加文字
font = cv2.FONT_HERSHEY_SIMPLEX
cv2.putText(img, 'Loading...', (150, 240), font, 1, (255, 255, 255), 2, cv2.LINE_AA)

# 保存图像
cv2.imwrite('static/img/waiting.jpg', img)

print("等待图片已创建: static/img/waiting.jpg")