import numpy as np


class NumberOfFloors(object):  # 只存储总数，不存储细节
    def __init__(self):
        self.__aboveground = 0
        self.__underground = 0
        self.__total = 0

    def add_floor(self, above=True):
        if above:
            self.__aboveground=self.__aboveground+1
        else:
            self.__underground=self.__underground+1
        self.__total=self.__total+1

    def delete_floor(self, above=True):
        if above:
            self.__aboveground=self.__aboveground-1
        else:
            self.__underground=self.__underground-1
        self.__total=self.__total-1

    def show_details(self):
        return {"above ground": self.__aboveground,
                "under ground": self.__underground,
                "total": self.__aboveground+self.__underground}


class Model(object):
    def __init__(self, model_name):
        self.name = model_name  # 存储模型名字
        self.number_of_floors = NumberOfFloors()  # 楼层数
        self.__adjacency = None   # 存储邻接矩阵
        self.__height_difference = None
        self.__width = None  # 边(路)的宽度矩阵
        self.__monitor_info = None

        self.__smoke = None  # 边的烟雾浓度矩阵
        self.__population_density = None  # 人群密度矩阵

        self.__current_floor = 0  # 被选中的当前层, 0表示未选中
        self.__current_path = (0, 0)  # 被选中的node
        self.__current_position = 0

        self.evacnet = None
        self.exit = []
        self.current_node = None

        self.max = 999999

    # 进行虚拟模型管理

    def set_adjacency(self, adjacency_array):
        self.__adjacency = adjacency_array  # 仅算水平步行距离，楼梯要细算

    def set_width(self, width_array):  # 节点间路径最小宽度
        self.__width = width_array

    def set_height_difference(self, height_difference_array):
        self.__height_difference = height_difference_array  # 由行到列检索，若上升为正，下降为负

    def update_monitor_info(self,monitor_info):
        self.__monitor_info = monitor_info

    # 状态管理服务

    def set_current_floor(self, number):
        if number == 0:
            print("Failed to choose the floor. 0 is an invalid floor number.")
            self.current_floor()
        elif number > self.number_of_floors.show_details()["above ground"]:
            print("Failed to choose the floor. The top floor is {}".
                  format(self.number_of_floors.show_details()["above ground"]))
            self.current_floor()
        elif number < -self.number_of_floors.show_details()["under ground"]:
            print("Failed to choose the floor. The bottom floor is -{}".
                  format(self.number_of_floors.show_details()["under ground"]))
            self.current_floor()
        else:
            self.__current_floor = number
            print("Successfully chose floor {}.".format(self.__current_floor))
            self.current_floor()

    def current_floor(self):
        if self.__current_floor == 0:
            print("You haven't chosen any floor")
        else:
            print("==== Current Floor is {} ====".format(self.__current_floor))
            return self.__current_floor

    # 路径规划服务
    def generate_evacnet(self):  # 生成带惩罚信息的逃生网络
        import copy
        max = self.max
        adjacency = self.__adjacency
        width = self.__width
        height_difference = self.__height_difference
        monitor_info = self.__monitor_info

        physical_model = copy.deepcopy(adjacency)
        evacnet = copy.deepcopy(adjacency)
        w = 0
        k = max
        Rd = 0
        Rc = 0

        for i in range(len(physical_model)):
            for j in range(len(physical_model)):
                if adjacency[i][j] < max-1:  # 如果有通路
                    # 计算节点i，j间宽度惩罚系数
                    if width[i][j] >= 5.0:
                        w = 1.0
                    elif 2 <= width[i][j] < 5:
                        w = -0.167*width[i][j]+1.833
                    elif width[i][j] < 2:
                        w = 2
                    else:
                        print('节点{}至节点{}宽度惩罚出现异常'.format(i,j))
                    # 计算节点i，j间上下楼惩罚系数
                    if height_difference[i][j] >= 0:
                        k = 1.5
                    elif height_difference[i][j] < 0:
                        k = 0.9
                    else:
                        print('节点{}至节点{}上下楼惩罚出现异常'.format(i, j))
                    physical_model[i][j] = w*(k*abs(height_difference[i][j]+adjacency[i][j]))
                    # 计算i，j节点间人群密度惩罚系数
                    density = min(monitor_info[i][0],monitor_info[j][0])
                    if density <= 0.75:
                        Rd = 1000
                    elif 0.75 < density <= 4.2:
                        Rd = 1400/(0.0412*density**2-0.59*density+1.867)
                    elif density > 4.2:
                        Rd = 14000
                    # 计算i，j节点间烟雾浓度惩罚系数
                    concentration = min(monitor_info[i][1], monitor_info[j][1])
                    Rc = 1200 / (1 + 15*np.e ** (-0.0016 * (concentration - 1500)))
                    # 最终惩罚逃生网络
                    evacnet[i][j]=(1+0.0005*Rd+0.005*Rc)*physical_model[i][j]

        self.evacnet = copy.deepcopy(evacnet)
        print('惩罚逃生网络：',evacnet)

    def calculate_path(self,start_node):
        # 基于Dijkstra算法进行最短路优化
        number_of_node = len(self.evacnet)
        max = self.max
        matrix = self.evacnet
        # matrix = self.__adjacency  # 可与直接考虑水平距离比较
        exit_list = self.exit

        shortest_distance = []
        Set = []  # 存路线
        undetermined_node = []

        for i in range(number_of_node):
            shortest_distance.append(max)
            undetermined_node.append(i)
            Set.append(-1)

        Set[start_node]=start_node
        undetermined_node.remove(start_node)
        min_node = start_node
        new_added = [start_node]
        shortest_distance[start_node] = 0

        for i in undetermined_node:
            if shortest_distance[new_added[-1]] + matrix[new_added[-1]][i] < shortest_distance[i]:
                shortest_distance[i] = shortest_distance[new_added[-1]] + matrix[new_added[-1]][i]
                Set[i] = (new_added[-1])

        while len(undetermined_node) > 0:
            min = max
            for i in undetermined_node:
                if shortest_distance[i] < min:
                    min = shortest_distance[i]
                    min_node = i

            if min < max-0.0001:
                undetermined_node.remove(min_node)
                new_added.append(min_node)
                for i in undetermined_node:
                    if shortest_distance[new_added[-1]] + matrix[new_added[-1]][i] < shortest_distance[i]:
                        shortest_distance[i] = shortest_distance[new_added[-1]] + matrix[new_added[-1]][i]
                        Set[i] = (new_added[-1])

            else:
                if len(new_added) == 1:
                    print("警告，节点{}无法生成有效路径，请进行救援".format(start_node))
                    return None, None
                else:
                    new_added.pop()

        min_distance = max
        best_exit = exit_list[0]
        for i in exit_list:
            if shortest_distance[i] < min_distance-0.001:
                min_distance = shortest_distance[i]
                best_exit = i
        i = best_exit
        route = [i]
        while i != start_node:
            i = Set[i]
            route.insert(0,i)
        print("===========================================")
        print("当前最优逃生路径与相应惩罚距离分别是")
        print(route, shortest_distance[best_exit])

        return route, shortest_distance[best_exit]

