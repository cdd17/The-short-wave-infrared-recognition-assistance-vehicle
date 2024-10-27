import socket
import cv2
import numpy as np
import torch
import time
import os
from ultralytics import YOLO

# 加载 YOLOv8 模型
model = YOLO("best_1.pt")  # YOLOv8用于人物和瓶子检测

# 设置保存图片的文件夹
output_dir = 'captured_images9'
os.makedirs(output_dir, exist_ok=True)

# 设置 socket 服务器
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('0.0.0.0', 5000))  # 绑定端口 5000
server_socket.listen(1)
print("Waiting for connection...")
conn, addr = server_socket.accept()
print(f"Connected by {addr}")

# 参数设置
target_distance_threshold = 30000 * 18.36  # 人物边界框面积阈值
bottle_distance_threshold = 4000 * 14  # 瓶子边界框面积阈值，用于判断是否接近障碍物
turn_duration = 1  # 小车左转避障持续时间（秒）
right_turn_duration = 2.5  # 小车右转回到原路径的持续时间（秒）
left_turn_duration= 1
turning_left = False  # 向左避障状态
turning_right = False  # 向右避障状态
turn_start_time = time.time()  # 记录转向开始的时间
right_turn_start_time = time.time()  # 记录右转开始的时间
capture_interval = 0.2  # 每5秒拍一张照片
last_capture_time = time.time()  # 记录上次拍照时间

image_count = 0  # 记录保存图片的编号

while True:
    # 接收图像数据
    data = conn.recv(1048576)
    if not data:
        break

    # 将接收到的数据解码为图像
    nparr = np.frombuffer(data, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # 检查是否需要拍照（每隔 capture_interval 秒拍照一次）
    current_time = time.time()
    if current_time - last_capture_time >= capture_interval:
        # 保存图像到指定文件夹
        image_filename = os.path.join(output_dir, f'image_{image_count:04d}.jpg')
        cv2.imwrite(image_filename, image)
        print(f"Image saved: {image_filename}")
        image_count += 1
        last_capture_time = current_time  # 更新拍照时间'''
    cv2.imwrite('output_image.jpg', image)  # 将图像保存为文件
    if image is None or image.size == 0:
        print("Received an empty image!")
        continue  # 跳过本次处理
    
    # 使用 YOLOv8 进行目标检测
    results = model(image)
    detections = results[0].boxes.xyxy.cpu().numpy()  # 获取检测到的边界框 (x1, y1, x2, y2)
    classes = results[0].boxes.cls.cpu().numpy()  # 获取检测的类别

    # 初始化变量
    target_position = None
    bottle_position = None
    target_bbox_area = 0
    bottle_bbox_area = 0
    frame_width = image.shape[1]

    # 遍历检测结果
    for i, cls in enumerate(classes):
        if int(cls) != 0:  # 类别 0 通常表示 "person"
            target_position = detections[i]
            target_bbox_area = (target_position[2] - target_position[0]) * (target_position[3] - target_position[1])
        # 检测所有非人类类别作为障碍物
        elif int(cls) == 0:  # 所有类别不是 "person" 都视为障碍物
            bottle_position = detections[i]
            bottle_bbox_area = (bottle_position[2] - bottle_position[0]) * (bottle_position[3] - bottle_position[1])

    # 小车控制逻辑
    steering = 0.0
    throttle = 0.18  # 默认油门值

    # 如果检测到障碍物
    if bottle_position is not None and bottle_bbox_area >= bottle_distance_threshold:
        # 获取障碍物中心位置
        bottle_center_x = (bottle_position[0] + bottle_position[2]) / 2

        # 如果障碍物在画面中央，触发避障逻辑
        if frame_width * 0.3 < bottle_center_x < frame_width * 0.7:
            # 判断障碍物在左边还是右边
            if bottle_center_x < frame_width / 2:
                # 障碍物在左边，向右避障
                print("Obstacle on the left, avoiding to the right...")
                turning_right = True
                turn_start_time = time.time()
            else:
                # 障碍物在右边，向左避障
                print("Obstacle on the right, avoiding to the left...")
                turning_left = True
                turn_start_time = time.time()

    # 检查向左避障逻辑
    if turning_left:
        if time.time() - turn_start_time < turn_duration:
            steering = -0.5  # 向左转避障
        elif time.time() - turn_start_time < turn_duration + right_turn_duration:
            steering = 0.65  # 避障后右转回归路径
        elif time.time() - turn_start_time < turn_duration + right_turn_duration+left_turn_duration:
            steering=-0.5
        else:
            turning_left = False
            steering = 0.0
            print("Left avoidance completed, driving straight.")

    # 检查向右避障逻辑
    elif turning_right:
        if time.time() - turn_start_time < turn_duration:
            steering = 0.5  # 向右转避障
        elif time.time() - turn_start_time < turn_duration + right_turn_duration:
            steering = -0.65  # 避障后左转回归路径
        elif time.time() - turn_start_time < turn_duration + right_turn_duration+left_turn_duration:
            steering = 0.5
        else:
            turning_right = False
            steering = 0.0
            print("Right avoidance completed, driving straight.")

    # 处理人物追踪逻辑，如果没有在避障
    if not turning_left and not turning_right:
        if target_position is not None:
            target_center_x = (target_position[0] + target_position[2]) / 2
            steering = (target_center_x - frame_width / 2) / (frame_width / 2)  # 基于目标位置计算转向角度

            # 如果人物距离足够近，停止小车
            if target_bbox_area >= target_distance_threshold:
                throttle = 0.0
                print("已到达救援目标附近")#ggggggg
                control_command = f"{steering},{throttle}"
                conn.sendall(control_command.encode()) 
                break

        # 没有检测到人且没有接近障碍物，保持直线行驶
        else:
            steering = 0.0  # 直线行驶
            print("No person detected, driving straight.")

    # 将控制指令发送回 Jetson Nano
    control_command = f"{steering-0.22},{throttle}"
    conn.sendall(control_command.encode())

conn.close()
