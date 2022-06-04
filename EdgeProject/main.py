from InferenceEngine import InferenceEngine
import cv2 as cv
import threading
import socket
import serial
import os
import numpy as np


class EdgeApp(object):
    def __init__(self, edge_ip, cloud_ip, port, device_number):
        self.edge_ip = edge_ip
        self.cloud_ip = cloud_ip
        self.port = port
        self.device_number = device_number

        self.engine = InferenceEngine(conf_thres=0.5)
        self.capture = cv.VideoCapture(0)
        self.area = 20.0

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.edge_ip, self.port))

        self.human_density = 0.0
        self.smoke_concentration = 0
        self.ser = serial.Serial(
            port='/dev/ttyUSB0',
            baudrate=9600,
            timeout=1,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS
        )

    def monitor(self):
        while True:
            ref, frame = self.capture.read()
            if not ref:
                print("Fail to capture the frame.")
                continue
            result = self.engine.detect(frame)
            n = 0
            for i in result:
                if i['class'] == 'person':
                    n = n + 1
                    position = i['position']
                    cv.rectangle(frame, (position[0], position[1]),
                                 (position[0] + position[2], position[1] + position[3]),
                                 (0, 255, 0), 1, 4)
            self.human_density = n / self.area
            monitor_text = "监测到 {} 人，当前视野内人群密度为 {:.2f} 人/平方米。".format(n, self.human_density)
            print(monitor_text)
            # frame = show_text(frame, monitor_text, (10, 10))
            cv.imshow('PC Camera', frame)

            # 读取烟雾浓度传感器数据
            hex = b'\xfe\x04\x00\x00\x00\x01\x25\xc5'
            self.ser.write(hex)
            data = self.ser.read(8)
            if data == b'':  # 如果没读上数据，继续循环
                continue
            s = str(data)
            a = '0x' + s[16:18] + s[20:22]
            self.smoke_concentration = eval(a)
            print('当前节点烟雾浓度为 {} ppm。'.format(self.smoke_concentration))

            c = cv.waitKey(1) & 0xff
            if c == 27:
                cv.destroyAllWindows()
                break

    def communicate(self):
        request = self.cloud_ip  # 监听中央ip的请求
        request = bytes(request, 'utf-8')
        self.socket.listen()  # 监听，等待与中央计算平台创建连接
        connect, addr = self.socket.accept()  # 与中央计算平台创建连接

        while True:
            data = connect.recv(1024)
            if data == b'quit':
                print('the client has quit.')
                break
            else:
                response = "({},{},'{}')".format(self.human_density, self.smoke_concentration, self.device_number)
                response = bytes(response, 'utf-8')
                print("Request is received.")
                connect.send(response)  # 发送信息
            # self.socket.close()


class ThreadMonitor(threading.Thread):
    def __init__(self, threadname):
        threading.Thread.__init__(self, name=threadname)

    def run(self):
        print("thread {} start".format(self.name))
        global edge_app
        edge_app.monitor()


class ThreadCommunicate(threading.Thread):
    def __init__(self, threadname):
        threading.Thread.__init__(self, name=threadname)

    def run(self):
        print("thread {} start".format(self.name))
        global edge_app
        edge_app.communicate()


if __name__ == "__main__":
    edge_ip = '192.168.1.103'
    cloud_ip = '192.168.1.102'
    port = 8000
    device_number = "0000"

    edge_app = EdgeApp(edge_ip, cloud_ip, port, device_number)

    thread1 = ThreadMonitor('monitor')
    thread2 = ThreadCommunicate('communicate')

    thread1.start()
    thread2.start()



