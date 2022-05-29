import BuildingModel
import socket
from numpy import random
import time
import numpy as np
import pandas as pd


class CloudApp(object):
    def __init__(self, model_name, cloud_ip, edge_ip_list, port_list, devices, number_of_nodes):
        self.cloud_ip = cloud_ip
        self.edge_ip_list = edge_ip_list
        self.port_list = port_list
        self.devices = devices
        self.number_of_nodes = number_of_nodes

        self.model = BuildingModel.Model(model_name)

        self.socket_list = []
        for i in range(len(self.devices)):
            self.socket_list.append(socket.socket(socket.AF_INET, socket.SOCK_STREAM))

        self.optimized_routes = []

    def route_optimization(self):
        # 没有监测的节点，为了进行仿真实验，随机生成楼宇内烟雾、温度人群密度情况。
        # 在应用过程中出现异常，某些节点长时间没更新数据，为安全考虑应当避开该节点，删除相关通路。

        '''通信开始'''
        for i in range(len(self.devices)):
            self.socket_list[i].connect((self.edge_ip_list[i], self.port_list[i]))
        '''通信结束'''

        while True:
            # 除了实验节点，暂未布设其他没有监测的节点，为了进行仿真实验，随机生成楼宇内烟雾、温度人群密度情况。
            monitor_info = monitor_results_generation(self.number_of_nodes, is_random=True)  # 实际生产应用时跳过此步骤

            '''通信开始'''
            # 对于部署了设备的节点，套接字数组内的socket分别与其相对应的设备进行通讯读取，按顺序存入result数组中。
            result = []  # 查询的建筑内信息结果
            # 利用TCP方式通讯。各设备顺序发送并接收信息，存在排队处理效率低的问题；好处就是下一步更新时可以使用顺序查找。
            # 未处理没有收到没更细等情况
            for i in range(len(self.devices)):
                # self.socket_list[i].connect((self.edge_ip_list[i], self.port_list[i]))
                request = bytes(self.cloud_ip, 'utf-8')
                self.socket_list[i].send(request)
                message = self.socket_list[i].recv(1024)
                result.append(eval(str(message, 'utf-8')))
                # self.socket_list[i].close()
            # 更新覆盖原监测数据
            for i in range(len(monitor_info)):
                if len(result) == 0:
                    break
                else:
                    if monitor_info[i][2] == result[0][2]:
                        monitor_info[i] = result[0]
                        del result[0]
            '''通信结束'''

            # 进行路线规划
            self.model.update_monitor_info(monitor_info)
            self.model.generate_evacnet()
            for i in range(self.number_of_nodes):
                route, punished_distance = self.model.calculate_path(i)
                self.optimized_routes.append((route, punished_distance))
            time.sleep(1.0)

        # 再接下来分别把计算结果发送给各边缘端,略。


def monitor_results_generation(node_number, is_random=True):  # 有随机生成和常数生成两种方式
    results = []
    if is_random:
        for i in range(node_number):
            human_density = 5 * random.rand()
            smoke_concentration = random.randint(10000)
            device_number = '{:0>4d}'.format(i)
            results.append((human_density, smoke_concentration, device_number))
    else:
        for i in range(node_number):
            human_density = 2.5
            smoke_concentration = random.randint(1000)
            device_number = '{:0>4d}'.format(i)
            results.append((human_density, smoke_concentration, device_number))
    return results


if __name__ == "__main__":
    cloud_ip = '192.168.10.154'
    edge_ip_list = ['192.168.10.71']
    port_list = [8000]
    devices = {"0000": "疏散优化边缘平台"}
    model_name = "建筑疏散数字孪生虚拟模型-大连理工大学三号实验楼"
    number_of_nodes = 35

    cloud_app = CloudApp(model_name, cloud_ip, edge_ip_list, port_list, devices,number_of_nodes)
    # 接下来构建模型
    data1 = pd.read_excel('L.xlsx',index=True)
    adjacency = np.array(data1).tolist()
    cloud_app.model.set_adjacency(adjacency)

    data2 = pd.read_excel('W.xlsx',index=True)
    width = np.array(data2).tolist()
    cloud_app.model.set_width(width)

    data3 = pd.read_excel('HD.xlsx', index=True)
    height_difference = np.array(data3).tolist()
    cloud_app.model.set_height_difference(height_difference)

    # 设置安全出口节点
    cloud_app.model.exit = [0, 8]

    # 开始进行疏散路线计算服务
    cloud_app.route_optimization()
