import heapq
import numpy as np


SIZE = 7
HEIGHT = 4


environment_matrix = np.zeros((SIZE, SIZE, HEIGHT)).astype(int).astype(str)


for y in range(SIZE): #Proibir o chão
    for x in range(SIZE):
        #print(environment_matrix[y][x][0])
        if environment_matrix[y][x][0] == '0':
            environment_matrix[y][x][0] = 'X'


for y in range(2, 4): #Criar o aeroporto militar
    for x in range(0, 2):
        for z in range(HEIGHT):
            environment_matrix[y][x][z] = 'X'


environment_matrix[0][3][HEIGHT-1] = 'X' #Criar a nuvem
environment_matrix[0][4][HEIGHT-1] = 'X'


for y in range(2, 5): #Criar montanha
    for x in range(4, 7):
        environment_matrix[y][x][1] = 'X'
environment_matrix[2][5][2] = 'X'
environment_matrix[3][4][2] = 'X'
environment_matrix[3][5][2] = 'X'
environment_matrix[3][6][2] = 'X'
environment_matrix[4][5][2] = 'X'
environment_matrix[3][5][3] = 'X'

environment_matrix[0][1][0] = '0'
environment_matrix[0][6][0] = '0'
environment_matrix[6][0][0] = '0'
environment_matrix[6][5][0] = '0'


class Node:
    def __init__(self, parent=None, position=None):
        self.parent=parent
        self.position = position

        self.g = 0
        self.h = 0
        self.f = 0

    def __eq__(self, other):
        return self.position == other.position

def astar(matrix, start, end):

    # Create start and end node
    start_node = Node(None, start)
    start_node.g = start_node.h = start_node.f = 0
    end_node = Node(None, end)
    end_node.g = end_node.h = end_node.f = 0

    open_list = []
    closed_list = []

    open_list.append(start_node)

    while(len(open_list) > 0):

        current_node = open_list[0]
        current_index = 0

        for index, item in enumerate(open_list):
            if item.f < current_node.f:
                current_node = item
                current_index = index

        open_list.pop(current_index)
        closed_list.append(current_node)


        # Found the goal
        if current_node == end_node:
            path = []
            current = current_node
            while current is not None:
                path.append(current.position)
                current = current.parent
            return path[::-1] # Return reversed path

        children = []

        for i in range(-1, 2):
            for j in range(-1, 2):
                for k in range(-1, 2):
                    node_position = (current_node.position[0] + i, current_node.position[1] + j, current_node.position[2] + k)

                    if (
                            node_position[0] > (len(matrix) - 1)
                            or node_position[0] < 0
                            or node_position[1] > (len(matrix[len(matrix) - 1]) - 1)
                            or node_position[1] < 0
                            or node_position[2] > (len(matrix[0][0]) - 1)
                            or node_position[2] < 0
                            or node_position == current_node.position
                    ):
                        continue

                    if matrix[node_position[0]][node_position[1]][node_position[2]] != '0':
                        continue

                    new_node = Node(current_node, node_position)

                    children.append(new_node)

        for child in children:

            # Child is on the closed list
            for closed_child in closed_list:
                if child == closed_child:
                    continue

            child.g = current_node.g + 1
            child.h = ((child.position[0] - end_node.position[0]) ** 2) + ((child.position[1] - end_node.position[1]) ** 2) + ((child.position[2] - end_node.position[2]) ** 2)
            child.f = child.g + child.h

            for open_node in open_list:
                if child == open_node and child.g > open_node.g:
                    continue

                # Add the child to the open list
            open_list.append(child)




path = astar(environment_matrix, (6, 0, 0), (0, 6, 0))
print(path)









