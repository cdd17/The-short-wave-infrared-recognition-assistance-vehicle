import socket
import cv2
import os
import time
from jetracer.nvidia_racecar import NvidiaRacecar

# 设置保存图片的文件夹
output_dir = 'captured_images0'
os.makedirs(output_dir, exist_ok=True)

# 使用 OpenCV 读取 USB 摄像头
camera = cv2.VideoCapture(0)

# 设置更高的摄像头分辨率，例如 1280x720
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# 初始化小车
car = NvidiaRacecar()

# 设置 socket 连接到服务器
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(('172.20.10.4', 5000))  # 替换为服务器的实际IP地址

# 定义拍照间隔（秒）
capture_interval = 5  # 每5秒拍一张照片
image_count = 0

while True:
    # 读取 USB 摄像头数据
    ret, image = camera.read()
    if not ret:
        print("Failed to grab frame from USB camera")
        break
    
    
    # 生成图片文件名
    image_path = os.path.join(output_dir, f'image_{image_count:04d}.jpg')

    # 保存图片
    cv2.imwrite(image_path, frame)
    print(f"Image saved: {image_path}")

    # 等待下一个拍照时间
    time.sleep(capture_interval)

    # 更新图片编号
    image_count += 1

    
    # 直接使用高分辨率的图像，不再调整到 224x224
    # 将图像编码为JPEG格式
    _, buffer = cv2.imencode('.jpg', image)
    buffer = buffer.tobytes()

    # 发送图像数据
    client_socket.sendall(buffer)

    # 接收服务器返回的控制指令
    response = client_socket.recv(1024).decode()  # 读取指令
    if not response:
        print("Lost connection to server")
        break

    steering, throttle = map(float, response.split(','))  # 将指令分解成转向和油门
    print(steering, '  ~~~  ', throttle)
    # 控制小车
    car.steering = steering
    car.throttle = throttle

# 释放摄像头和关闭socket
camera.release()
client_socket.close()

