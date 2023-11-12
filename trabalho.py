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
        self.airplane = None

    def is_empty(self):
        return self.empty

    def to_empty(self):
        self.empty = True
        self.airplane = None

    def to_full(self, airplane):
        self.empty = False
        self.airplane = airplane





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








    def print_environment(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        for i in range(SIZE):
            line = ""
            for j in range(SIZE):
                line += str(self.matrix[i][j][0]) + " "
            print(line)






class AircraftAgent(Agent):
    def __init__(self, jid, password, environment, idx, start_airport, position, end_airport=None, sent_msg=False):
        super().__init__(jid, password)
        self.environment = environment
        self.idx = idx
        self.start_airport = start_airport
        self.position = position
        self.on_land = True
        self.end_airport = end_airport
        self.sent_msg = sent_msg

        self.start_airport.to_full(self)


    async def setup(self):

        class Fly(CyclicBehaviour):
            async def run(self):
                if self.agent.on_land:
                    if not self.agent.sent_msg:
                        empty_airports = self.agent.environment.get_empty_airports()
                        self.agent.end_airport = random.choice(empty_airports)
                        #print(self.agent.end_airport)

                        await self.start_flying(self.agent.start_airport.position, self.agent.end_airport.position)
                        #self.agent.sent_msg = True
                        #self.agent.on_land = False


            def update_position(self):
                self.agent.environment.aircraft_positions[self.agent.idx] = self.agent.position




            async def start_flying(self, start_position, end_position):

                msg = Message(to="atc_agent@localhost")
                msg.set_metadata("performative", "query")
                msg.body = f"0001 {start_position} {end_position}"

                # Send the message
                print(f"AA - Sending this {msg.body}")
                await self.send(msg)

                response = await self.receive()
                if response:
                    print(response.body)
                    self.agent.sent_msg = True
                    self.agent.on_land = False

        self.add_behaviour(Fly())










class AirSpaceManager(Agent):

    def __init__(self, jid, password, environment, aircraft_jid=None, msg_received_from_aircraft=False, msg_to_cc=None, sent_msg_to_cc=False):
        super().__init__(jid, password)
        self.environment = environment
        self.aircraft_jid = aircraft_jid
        self.msg_received_from_aircraft = msg_received_from_aircraft
        self.msg_to_cc = msg_to_cc
        self.sent_msg_to_cc = sent_msg_to_cc




    async def setup(self):
        self.add_behaviour(self.MessageWithAircraft())


    class MessageWithAircraft(CyclicBehaviour):

        async def run(self):

            if not self.agent.msg_received_from_aircraft:
                print("ASM - ok")
                msg = await self.receive(timeout=10)
                if msg:
                    code = msg.body[0:4]
                    if code == "0001":
                        self.agent.aircraft_jid = str(msg.sender)
                        print(self.agent.aircraft_jid)
                        await self.tell_aircraft_msg_received()
                        self.agent.msg_to_cc = msg.body
                        #await self.send_msg_to_cc(msg.body)

            else:
                if not self.agent.sent_msg_to_cc:
                    await self.send_msg_to_cc()



        async def tell_aircraft_msg_received(self):
            msg = Message(to=self.agent.aircraft_jid)
            msg.body = "Message received"
            self.agent.msg_received_from_aircraft = True
            await self.send(msg)

        async def send_msg_to_cc(self):
            msg = Message(to="cc_agent@localhost")
            msg.body = self.agent.msg_to_cc
            await self.send(msg)

            response = await self.receive()
            if response and str(response.sender) == "cc_agent@localhost":
                print(f"response.body: {response.body}, {str(response.sender)}")
                self.agent.sent_msg_to_cc = True








class CentralCoordinationAgent(Agent):
    def __init__(self, jid, password, environment, path=None, msg_received=False, text=None):
        super().__init__(jid, password)
        self.environment = environment
        self.path = path
        self.msg_received = msg_received
        self.text = text

    async def setup(self):

        class GetPath(CyclicBehaviour):

            async def run(self):
                if not self.agent.msg_received:
                    print("CC - ok")
                    msg = await self.receive(timeout=10)
                    if msg:
                        print(f"CC - Got this {msg.body}")
                        self.agent.text = msg.body
                        self.agent.msg_received = True
                        await self.tell_asm_msg_received()
                else:
                    #print("ok")
                    words = re.findall(r'\(.*?\)|\w+', self.agent.text)
                    code = words[0]
                    if code == "0001":
                        #print("okok")
                        start_position = ast.literal_eval(words[1])
                        end_position = ast.literal_eval(words[2])
                        #print(f"start_position: {start_position}")
                        #print(f"end_position: {end_position}")

                        self.agent.path = self.astar(start_position, end_position)
                        #print("dwadwadw")
                        print(f"path: {self.agent.path}")
                        await self.send_path_to_asm()

            async def tell_asm_msg_received(self):
                msg = Message(to="atc_agent@localhost")
                msg.body = "Message received -d-a w-d aw--wda -wad -"
                self.agent.msg_received = True
                await self.send(msg)

            async def send_path_to_asm(self):
                msg = Message(to="atc_agent@localhost")
                msg.body = str(self.agent.path)
                """
                ESTAVA AQUI, ACABAR MANDAR PATH PARA ASM
                """



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

    aircraft_agent_1 = AircraftAgent("aircraft_agent_1@localhost", "password", environment, "A1", airport_1, airport_1.position)
    await aircraft_agent_1.start(auto_register=True)


    airspace_manager = AirSpaceManager("atc_agent@localhost", "password", environment)
    await airspace_manager.start(auto_register=True)

    central_coordination_agent = CentralCoordinationAgent("cc_agent@localhost", "password", environment)
    await central_coordination_agent.start(auto_register=True)


    #environment.print_environment()

    """
    aircraft_agent = AircraftAgent("aircraft_agent@localhost", "password", environment, [0, 1, 0])


    """

if __name__ == "__main__":
    spade.run(main())

