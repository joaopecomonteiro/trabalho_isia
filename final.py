import numpy as np
import os
import re
import ast
import random
import asyncio
import spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.behaviour import FSMBehaviour
from spade.behaviour import State
from spade.behaviour import OneShotBehaviour
from spade.template import Template
from spade.message import Message

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

class Node:
    def __init__(self, parent=None, position=None):
        self.parent=parent
        self.position = position

        self.g = 0
        self.h = 0
        self.f = 0

    def __eq__(self, other):
        return self.position == other.position

class Airport:
    def __init__(self, position, idx, empty=True, airplane=None):
        self.position = position
        self.idx = idx
        self.empty = empty
        self.airplane = airplane

    def is_empty(self):
        return self.empty

    def to_empty(self):
        self.empty = True
        self.airplane = None

    def to_full(self, airplane=None):
        self.empty = False
        #self.airplane = airplane





class Environment:
    def __init__(self, matrix, airports):
        self.matrix = matrix
        self.airports = airports
        self.aircraft_positions = {}


    def build_airports(self):
        for airport in self.airports:
            if airport.is_empty():
                environment_matrix[airport.position[0]][airport.position[1]][airport.position[2]] = 'E'
            else:
                environment_matrix[airport.position[0]][airport.position[1]][airport.position[2]] = 'F'


    def get_empty_airports(self):
        empty_airports = []
        for airport in self.airports:
            if airport.is_empty():
                empty_airports.append(airport)
        return empty_airports

    def get_airports(self):
        return self.airports







    def print_environment(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        for i in range(SIZE):
            line = ""
            for j in range(SIZE):
                line += str(self.matrix[i][j][0]) + " "
            print(line)









class AircraftAgent(Agent):
    def __init__(self, jid, password, environment, idx, start_airport):
        super().__init__(jid, password)
        self.environment = environment
        self.idx = idx
        self.start_airport = start_airport
        self.end_airport = None
        self.position = start_airport.position
        self.path = None

        self.on_land = True
        self.asked_for_path = False


        self.start_airport.to_full(self)

    async def setup(self):

        class Fly(CyclicBehaviour):
            async def run(self):

                if self.agent.on_land:
                    if not self.agent.asked_for_path:
                        empty_airports = self.agent.environment.get_empty_airports()

                        if len(empty_airports) > 0:
                            self.agent.end_airport = random.choice(empty_airports)
                            await self.ask_asm_for_path()

                    else:
                        await self.receive_path()




            async def ask_asm_for_path(self):

                msg = Message(to="asm_agent@localhost")
                msg.set_metadata("performative", "query")
                msg.body = f"0001 {self.agent.start_airport.position} {self.agent.end_airport.position}"

                print(f"{self.agent.idx} - Sending ASM this {msg.body}\n")
                await self.send(msg)

                self.agent.asked_for_path = True

            async def receive_path(self):
                msg_with_path = await self.receive(timeout=15)
                if msg_with_path:
                    self.agent.path = ast.literal_eval(msg_with_path.body)
                    print(f"{self.agent.idx} - Got this path: {self.agent.path}\n")

        self.add_behaviour(Fly())



class AirSpaceManager(Agent):
    def __init__(self, jid, password, environment):
        super().__init__(jid, password)
        self.environment = environment
        self.AA_wait_queue = []
        self.aircraft_data = None

        self.waiting_for_path = False
        self.asked_for_path = False


    async def setup(self):

        class WaitForAAMessages(CyclicBehaviour):

            async def run(self):

                msg = await self.receive(timeout=10)
                if msg and str(msg.sender)[0:8] == "aircraft":

                    separated_text = re.findall(r'\(.*?\)|\w+', msg.body)
                    code = separated_text[0]
                    start_position = separated_text[1]
                    end_position = separated_text[2]
                    self.fill_airport(end_position)

                    if code == "0001":
                        self.agent.AA_wait_queue.append((str(msg.sender), start_position, end_position))
                        print(f"ASM - Added {str(msg.sender)} to the AA wait queue with the start position: {start_position} and end position: {end_position}\n")




            def fill_airport(self, position):

                for airport in self.agent.environment.airports:
                    if airport.position == ast.literal_eval(position):
                        airport.to_full()


        class GetPath(CyclicBehaviour):

            async def run(self):
                if not self.agent.waiting_for_path:
                    if len(self.agent.AA_wait_queue) > 0:
                        #print("ok")
                        self.agent.aircraft_data = self.agent.AA_wait_queue.pop()
                        #print(self.agent.aircraft_data)
                        self.agent.waiting_for_path = True
                else:
                    if not self.agent.asked_for_path:
                        await self.ask_cc_for_path()

                    else:

                        msg = await self.receive()
                        if msg and str(msg.sender) == "cc_agent@localhost":
                            #print(f"ASM - Got this path {msg.body}")

                            msg_with_path = Message(to=self.agent.aircraft_data[0])
                            msg_with_path.set_metadata("performative", "query")
                            msg_with_path.body = msg.body

                            await self.send(msg_with_path)
                            print(f"ASM - Sending this path {msg_with_path.body} to {self.agent.aircraft_data[0]}\n")
                            self.agent.waiting_for_path = False
                            self.agent.asked_for_path = False





            async def ask_cc_for_path(self):

                start_position = self.agent.aircraft_data[1]
                end_position = self.agent.aircraft_data[2]

                msg = Message(to="cc_agent@localhost")
                msg.set_metadata("performative", "query")
                msg.body = f"{start_position} {end_position}"

                print(f"ASM - Asked CC for the path from {start_position} to {end_position}\n")
                await self.send(msg)
                self.agent.asked_for_path = True



        self.add_behaviour(GetPath())
        self.add_behaviour(WaitForAAMessages())




class CentralCoordinationAgent(Agent):
    def __init__(self, jid, password, environment):
        super().__init__(jid, password)
        self.environment = environment
        self.path = None

        self.got_path = False
        self.got_coordinates = False

    async def setup(self):

        class GetPath(CyclicBehaviour):

            async def run(self):
                if not self.agent.got_path:

                    msg = await self.receive(timeout=10)
                    if msg:

                        tuple_strings = msg.body.split()
                        tuples = []

                        for tuple_str in tuple_strings:
                            # Split the tuple string by comma, remove parentheses, and filter out empty strings
                            elements = tuple(filter(None, tuple_str.strip('()').split(',')))
                            # Convert elements to integers and form a tuple
                            elements = tuple(map(int, elements))
                            tuples.append(elements)

                        # Merge adjacent tuples to form combined tuples
                        coordinates = [tuples[i] + tuples[i + 1] + tuples[i + 2] for i in range(0, len(tuples), 3)]

                        path = self.astar(coordinates[0], coordinates[1])

                        msg_with_path = Message(to="asm_agent@localhost")
                        msg_with_path.body = f"{path}"
                        msg_with_path.set_metadata("performative", "query")
                        await self.send(msg_with_path)
                        print(f"CC - Sending ASM the path \n")




            def astar(self, start, end):

                start_node = Node(None, start)
                start_node.g = start_node.h = start_node.f = 0
                end_node = Node(None, end)
                end_node.g = end_node.h = end_node.f = 0

                open_list = []
                closed_list = []

                open_list.append(start_node)

                while (len(open_list) > 0):
                    current_node = open_list[0]
                    current_index = 0

                    for index, item in enumerate(open_list):
                        if item.f < current_node.f:
                            current_node = item
                            current_index = index

                    open_list.pop(current_index)
                    closed_list.append(current_node)
                    #print(len(open_list))
                    #print(current_node.position)
                    #print("-----------------------")

                    # Found the goal
                    if current_node == end_node:
                        path = []
                        current = current_node
                        while current is not None:
                            path.append(current.position)
                            current = current.parent
                        return path[::-1]  # Return reversed path

                    children = []

                    for i in range(-1, 2):
                        for j in range(-1, 2):
                            for k in range(-1, 2):
                                node_position = (
                                current_node.position[0] + i, current_node.position[1] + j, current_node.position[2] + k)

                                if (
                                        node_position[0] > (len(self.agent.environment.matrix) - 1)
                                        or node_position[0] < 0
                                        or node_position[1] > (len(self.agent.environment.matrix[len(self.agent.environment.matrix) - 1]) - 1)
                                        or node_position[1] < 0
                                        or node_position[2] > (len(self.agent.environment.matrix[0][0]) - 1)
                                        or node_position[2] < 0
                                        or node_position == current_node.position
                                ):
                                    continue

                                if (
                                    self.agent.environment.matrix[node_position[0]][node_position[1]][node_position[2]] != '0'
                                    and self.agent.environment.matrix[node_position[0]][node_position[1]][node_position[2]] != 'E'
                                ):
                                    continue

                                new_node = Node(current_node, node_position)

                                children.append(new_node)

                    for child in children:

                        # Child is on the closed list
                        for closed_child in closed_list:
                            if child == closed_child:
                                continue

                        child.g = current_node.g + 1
                        child.h = ((child.position[0] - end_node.position[0]) ** 2) + (
                                (child.position[1] - end_node.position[1]) ** 2) + (
                                          (child.position[2] - end_node.position[2]) ** 2)
                        child.f = child.g + child.h

                        for open_node in open_list:
                            if child == open_node and child.g > open_node.g:
                                continue

                            # Add the child to the open list
                        open_list.append(child)

















        self.add_behaviour(GetPath())





async def main():

    airport_1 = Airport((0, 1, 0), "airport_1")
    airport_3 = Airport((0, 6, 0), "airport_3")
    airport_2 = Airport((6, 0, 0), "airport_2")
    airport_4 = Airport((6, 5, 0), "airport_4")

    environment = Environment(environment_matrix, [airport_1, airport_2, airport_3, airport_4])
    environment.build_airports()

    central_coordination_agent = CentralCoordinationAgent("cc_agent@localhost", "password", environment)
    await central_coordination_agent.start(auto_register=True)

    airspace_manager = AirSpaceManager("asm_agent@localhost", "password", environment)
    await airspace_manager.start(auto_register=True)

    aircraft_agent_1 = AircraftAgent("aircraft_agent_1@localhost", "password", environment, "A1", airport_1)
    await aircraft_agent_1.start(auto_register=True)

    aircraft_agent_2 = AircraftAgent("aircraft_agent_2@localhost", "password", environment, "A2", airport_2)
    await aircraft_agent_2.start(auto_register=True)

    #aircraft_agent_3 = AircraftAgent("aircraft_agent_3@localhost", "password", environment, "A3", airport_3)
    #await aircraft_agent_3.start(auto_register=True)




if __name__ == "__main__":
    spade.run(main())


