import socket
import cv2
from jetracer.nvidia_racecar import NvidiaRacecar


# 使用 OpenCV 读取 USB 摄像头
camera = cv2.VideoCapture(0)

# 初始化小车
car = NvidiaRacecar()

# 强制使用 MJPG 格式
#camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

# 设置接近的摄像头分辨率，比如 320x240 或 640x480
#camera.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
#camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

# 设置socket连接到服务器
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(('172.20.10.4', 5000))  # 替换为服务器的实际IP地址

while True:
    # 读取 USB 摄像头数据
    ret, image = camera.read()
    if not ret:
        print("Failed to grab frame from USB camera")
        break
    
    # 将图像调整到 224x224 分辨率
    resized_image = cv2.resize(image, (224, 224))
    cv2.imwrite('jetracer/notebooks/01.png',resized_image)
    # 将图像编码为JPEG格式
    _, buffer = cv2.imencode('.jpg', resized_image)
    buffer = buffer.tobytes()

    # 先发送图像大小
    #size = len(buffer)
    #client_socket.sendall(size.to_bytes(4, 'big'))  # 发送4字节的图像大小

    # 发送图像数据
    client_socket.sendall(buffer)

    # 接收服务器返回的控制指令
    response = client_socket.recv(1024).decode()  # 读取指令
    if not response:
        print("Lost connection to server")
        break

    steering, throttle = map(float, response.split(','))  # 将指令分解成转向和油门
    print(steering,'  ~~~  ',throttle)
    # 控制小车
    car.steering = steering
    car.throttle = throttle

# 释放摄像头和关闭socket
camera.release()
client_socket.close()

