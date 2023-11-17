import numpy as np
import os
import re
import ast
import random
import math
import asyncio
import spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour
from spade.behaviour import FSMBehaviour
from spade.behaviour import State
from spade.behaviour import OneShotBehaviour
from spade.template import Template
from spade.message import Message

SIZE = 15
HEIGHT = 4


environment_matrix = np.zeros((SIZE, SIZE, HEIGHT)).astype(int).astype(str)


for y in range(SIZE): #Proibir o chão
    for x in range(SIZE):
        #print(environment_matrix[y][x][0])
        if environment_matrix[y][x][0] == '0':
            environment_matrix[y][x][0] = 'X'


for y in range(2, 4):  # Criar o aeroporto militar
    for x in range(10, 14):
        for z in range(HEIGHT):
            environment_matrix[y][x][z] = 'X'


#environment_matrix[0][3][HEIGHT-1] = 'X' #Criar a nuvem
#environment_matrix[0][4][HEIGHT-1] = 'X'


for y in range(10, 13):  # Criar montanha
    for x in range(2, 5):
        environment_matrix[y][x][1] = 'X'
environment_matrix[10][3][2] = 'X'
environment_matrix[11][2][2] = 'X'
environment_matrix[11][3][2] = 'X'
environment_matrix[11][4][2] = 'X'
environment_matrix[12][3][2] = 'X'
environment_matrix[11][3][3] = 'X'




class Node:
    def __init__(self, parent=None, position=None):
        self.parent = parent
        self.position = position

        self.g = 0
        self.h = 0
        self.f = 0

    def __eq__(self, other):
        return self.position == other.position

class Airport:
    def __init__(self, position, idx):
        self.position = position
        self.idx = idx
        self.status = 'E'
        self.airplane = None

    def is_empty(self):
        return self.status == 'E'

    def is_full(self):
        return self.status == 'F'

    def is_reserved(self):
        return self.status == 'R'

    def to_empty(self):
        self.status = 'E'
        self.airplane = None

    def to_full(self, airplane):
        self.status = 'F'
        self.airplane = airplane

    def to_reserved(self, airplane):
        self.status = 'R'
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

    def get_airports(self):
        return self.airports

    def get_closest_not_full_airport(self, aircraft_position):
        closest = None
        min_distance = math.inf

        for airport in self.airports:
            distance = math.sqrt(sum((p2 - p1)**2 for p1, p2 in zip(aircraft_position, airport.position)))
            if distance < min_distance:
                min_distance = distance
                closest = airport
        return(closest)





class CommunicationAgent(Agent):
    def __init__(self, jid, password, environment):
        super().__init__(jid, password)
        self.environment = environment
        self.warnings = []
        self.counter = 0

    async def setup(self):

        class PrintEnvironment(PeriodicBehaviour):

            async def run(self):

                os.system('cls' if os.name == 'nt' else 'clear')

                matrix_to_print = np.zeros((SIZE, SIZE)).astype(int).astype(str)

                for y in range(2, 4):  # Criar o aeroporto militar
                    for x in range(10, 14):
                            matrix_to_print[y][x] = 'A'

                matrix_to_print[11][3] = 'P'

                for aircraft in self.agent.environment.aircraft_positions:
                    #print(f"{aircraft} - {self.agent.environment.aircraft_positions[aircraft]}")
                    x = self.agent.environment.aircraft_positions[aircraft][0]
                    y = self.agent.environment.aircraft_positions[aircraft][1]
                    matrix_to_print[x][y] = aircraft[1]

                for airport in self.agent.environment.airports:
                    x = airport.position[0]
                    y = airport.position[1]
                    matrix_to_print[x][y] = airport.status

                for i in range(len(matrix_to_print)):
                    line = ""
                    for j in range(len(matrix_to_print)):
                        line += str(matrix_to_print[i][j]) + " "
                    print(line)

                print()

                for airport in self.agent.environment.airports:
                    print(f"{airport.idx} - {airport.status} - {airport.airplane}")

                print()

                for i, warning in enumerate(self.agent.warnings):
                    print(warning[0])
                    if warning[1] > 7:
                        self.agent.warnings.pop(i)
                    warning[1] += 1

                #print(self.agent.counter)
                #self.agent.counter += 1

        class WaitingForWarnings(CyclicBehaviour):

            async def run(self):

                msg = await self.receive()
                if msg:
                    self.agent.warnings.append([msg.body, 0])


        self.add_behaviour(PrintEnvironment(1))
        self.add_behaviour(WaitingForWarnings())















class AircraftAgent(Agent):
    def __init__(self, jid, password, environment, idx, start_airport):
        super().__init__(jid, password)
        self.environment = environment
        self.idx = idx
        self.start_airport = start_airport
        self.end_airport = None
        #self.end_position = None
        self.position = start_airport.position
        self.path = None

        self.on_land = True
        self.asked_for_path = False
        self.wait_in_airport = True
        self.got_emergency = False
        self.already_got_emergency = False
        self.asked_for_emergency_path = False


        self.start_airport.to_full(self.jid)

    async def setup(self):

        class GetPath(CyclicBehaviour):
            async def run(self):
                if not self.agent.got_emergency:
                    if not self.agent.wait_in_airport:
                        if self.agent.on_land:
                            if not self.agent.asked_for_path:
                                empty_airports = self.agent.environment.get_empty_airports()

                                if len(empty_airports) > 0:
                                    end_airport = random.choice(empty_airports)
                                    self.agent.end_airport = end_airport
                                    self.agent.end_position = end_airport.position
                                    await self.ask_asm_for_path()

                            else:
                                await self.receive_path()
                    else:
                        #random_number = np.random.randint(2, 5)
                        await asyncio.sleep(3)
                        self.agent.wait_in_airport = False
                else:
                    if not self.agent.asked_for_emergency_path:
                        #print("dasdw")
                        await self.ask_asm_for_path()


                    else:
                        await self.receive_path()


            def get_end_airport(self, airport_name):
                for airport in self.agent.environment.airports:
                    if airport.idx == airport_name:
                        self.agent.end_airport = airport


            async def ask_asm_for_path(self):
                if not self.agent.got_emergency:
                    msg = Message(to="asm_agent@localhost")
                    msg.set_metadata("performative", "query")
                    msg.body = f"0001 {self.agent.start_airport.position} {self.agent.end_airport.position}"

                    with open('chatlog.txt', 'a') as file:
                        file.write(f"{self.agent.idx} - Sending ASM this {msg.body}\n\n")

                    #print(f"{self.agent.idx} - Sending ASM this {msg.body}\n")

                    await self.send(msg)

                    self.agent.asked_for_path = True




                else:
                    msg = Message(to="asm_agent@localhost")
                    msg.set_metadata("performative", "query")
                    msg.body = f"0002 {self.agent.position}"
                    #print(f"AA - Asking ASM for help, I am here {self.agent.position}")

                    with open('chatlog.txt', 'a') as file:
                        file.write(f"{self.agent.idx} - Got a problem, asking ASM for help\n\n")

                    await self.send(msg)

                    new_end_airport_msg = await self.receive(timeout=10)
                    if new_end_airport_msg:
                        self.get_end_airport(new_end_airport_msg.body)
                        #print(f"AA - My new end airport is {self.agent.end_airport.idx}")

                    self.agent.asked_for_emergency_path = True


            async def receive_path(self):
                if not self.agent.got_emergency:
                    msg_with_path = await self.receive(timeout=10)
                    if msg_with_path:
                        self.agent.path = ast.literal_eval(msg_with_path.body)

                        with open('chatlog.txt', 'a') as file:
                            file.write(f"{self.agent.idx} - Got this path: {self.agent.path} from {str(msg_with_path.sender)}\n\n")

                        #print(f"{self.agent.idx} - Got this path: {self.agent.path}\n")


                        self.agent.on_land = False
                        self.agent.start_airport.to_empty()

                else:
                    msg_with_path_emergency = await self.receive(timeout=10)
                    if msg_with_path_emergency:
                        #print(f"AA - Got this emergency path {msg_with_path_emergency.body} from {str(msg_with_path_emergency.sender)}")

                        with open('chatlog.txt', 'a') as file:
                            file.write(f"{self.agent.idx} - Got this emergency path {msg_with_path_emergency.body}\n\n")

                        #print(f"AWADAWDWADWA - {msg_with_path.body}")
                        self.agent.path = ast.literal_eval(msg_with_path_emergency.body[5:])
                        #print(f"AA - This is my path now {self.agent.path}")
                        self.agent.got_emergency = False
                        self.agent.already_got_emergency = True


        class WaitForEmergency(CyclicBehaviour):

            async def run(self):
                msg = await self.receive()
                if msg and msg.body == "0003":
                    #self.agent.end_airport.to_empty()

                    self.agent.end_airport = None
                    self.agent.on_land = True
                    self.agent.asked_for_path = False
                    self.agent.wait_in_airport = True
                    self.agent.already_got_emergency = False
                    self.agent.got_emergency = False
                    self.agent.asked_for_emergency_path = False

        class Fly(PeriodicBehaviour):
            async def run(self):



                if not self.agent.on_land:
                    #print(self.agent.got_emergency)
                    if not self.agent.got_emergency:
                        random_number = np.random.randint(1, 2)
                        if random_number == 1 and self.agent.already_got_emergency==False and self.agent.environment.get_closest_not_full_airport(self.agent.position) != self.agent.start_airport and self.agent.environment.get_closest_not_full_airport(self.agent.position) != self.agent.end_airport:
                            #print("Got Emergency")


                            self.agent.got_emergency = True
                            self.agent.asked_for_path = False
                            self.agent.end_airport.to_empty()
                        #    await self.ask_asm_for_help()
                        #    await self.get_emergency_path()
                        else:

                            #print(f"AA - My position {self.agent.position}")
                            #print(f"AA - End position {self.agent.end_airport.position}")
                            #print(f"AA - My path {self.agent.path}")


                            self.agent.position = self.agent.path.pop(0)


                            self.agent.environment.aircraft_positions[self.agent.idx] = self.agent.position

                            #print(self.agent.environment.aircraft_positions[self.agent.idx])

                            #with open('chatlog.txt', 'a') as file:
                            #    file.write(f"{self.agent.idx} - Moving to this position {self.agent.position}\n")

                            #print(f"{self.agent.idx} - Moving to this position {self.agent.position}\n")

                            #self.agent.environment.print_environment()


                            if self.agent.position == self.agent.end_airport.position:
                                with open('chatlog.txt', 'a') as file:
                                    file.write(f"I have arrived\n\n")

                                self.agent.start_airport = self.agent.end_airport
                                self.agent.end_airport = None
                                self.agent.on_land = True
                                self.agent.asked_for_path = False
                                self.agent.start_airport.to_full(self.agent.jid)
                                self.agent.wait_in_airport = True
                                self.agent.already_got_emergency = False
                                self.agent.got_emergency = False
                                self.agent.asked_for_emergency_path = False






            async def get_emergency_path(self):
                await asyncio.sleep(1)

                new_path = await self.receive()
                if new_path and new_path.body[0:4] == "0002":
                    #print(f"AA - Emergency - Got this path {new_path.body[4:]}")

                    self.agent.path = ast.literal_eval(new_path.body[4:])
                    self.agent.got_emergency = True


            async def ask_asm_for_help(self):

                msg = Message(to="asm_agent@localhost")
                msg.set_metadata("performative", "query")
                msg.body = f"0002 {self.agent.position}"

                #print("AA - Asking ASM for help")

                with open('chatlog.txt', 'a') as file:
                    file.write(f"{self.agent.idx} - Got a problem, asking ASM for help\n\n")

                await self.send(msg)




        self.add_behaviour(Fly(2))
        self.add_behaviour(GetPath())



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
                    #print(f"ASM - {msg.body}")
                    separated_text = re.findall(r'\(.*?\)|\w+', msg.body)
                    code = separated_text[0]


                    if code == "0001":
                        start_position = separated_text[1]
                        end_position = separated_text[2]
                        self.reserve_airport(end_position, str(msg.sender))

                        self.agent.AA_wait_queue.append((str(msg.sender), start_position, end_position))

                        with open('chatlog.txt', 'a') as file:
                            file.write(f"ASM - Added {str(msg.sender)} to the AA wait queue with the start position: {start_position} and end position: {end_position}\n\n")

                        #print(f"ASM - Added {str(msg.sender)} to the AA wait queue with the start position: {start_position} and end position: {end_position}\n")

                    if code == "0002":

                        warning_msg = Message(to="com_agent@localhost")
                        warning_msg.body = f"{str(msg.sender)} Got an emergency!"
                        await self.send(warning_msg)


                        start_position = ast.literal_eval(separated_text[1])
                        #end_position = ast.literal_eval(separated_text[2])
                        closest_airport = self.agent.environment.get_closest_not_full_airport(start_position)
                        print(f"{closest_airport.idx} - {closest_airport.status}")


                        if closest_airport.is_reserved():
                            aircraft_to_redirect = closest_airport.airplane
                            redirect_msg = Message(to=aircraft_to_redirect)
                            redirect_msg.body = "0003"
                            await self.send(redirect_msg)

                            redirect_warning_msg = Message(to="com_agent@localhost")
                            redirect_warning_msg.body = f"Redirecting {aircraft_to_redirect}"

                        else:
                            aircraft_to_change = None

                        await self.tell_aa_new_end_airport(str(msg.sender), closest_airport.idx)
                        self.fill_airport(str(closest_airport.position), str(msg.sender))


                        await self.emergency_ask_cc_for_path(start_position, closest_airport.position)

                        response = await self.receive(timeout=10)

                        if response and str(response.sender) == "cc_agent@localhost" and response.body[0:4]=="0002":
                            msg_with_path = Message(to=str(msg.sender))
                            msg_with_path.set_metadata("performative", "query")
                            msg_with_path.body = f"0002 {response.body[5:]}"

                            with open('chatlog.txt', 'a') as file:
                                file.write(f"ASM - Sending AA this emergency path {msg_with_path.body}\n\n")

                            #print(f"ASM - Sending AA this emergency path {msg_with_path.body}")



                            await self.send(msg_with_path)

            async def tell_aa_new_end_airport(self, aircraft, airport):

                msg = Message(to=aircraft)
                msg.set_metadata("performative", "query")
                msg.body = airport

                await self.send(msg)

            async def emergency_ask_cc_for_path(self, start_position, end_position):

                msg = Message(to="cc_agent@localhost")
                msg.set_metadata("performative", "query")
                msg.body = f"0002 {start_position} {end_position}"

                with open('chatlog.txt', 'a') as file:
                    file.write(f"ASM - Emergency - Asked CC for the path from {start_position} to {end_position}\n\n")

                #print(f"ASM - Emergency - Asked CC for the path from {start_position} to {end_position}\n")
                await self.send(msg)





            def fill_airport(self, position, aircraft):

                for airport in self.agent.environment.airports:
                    if airport.position == ast.literal_eval(position):
                        airport.to_full(aircraft)



            def reserve_airport(self, position, aircraft):

                for airport in self.agent.environment.airports:
                    if airport.position == ast.literal_eval(position):
                        airport.to_reserved(aircraft)


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
                        if msg and str(msg.sender) == "cc_agent@localhost" and msg.body[0:4]=="0001":
                            #print(f"ASM - Got this path {msg.body}")

                            msg_with_path = Message(to=self.agent.aircraft_data[0])
                            msg_with_path.set_metadata("performative", "query")
                            msg_with_path.body = msg.body[5:]

                            await self.send(msg_with_path)

                            with open('chatlog.txt', 'a') as file:
                                file.write(f"ASM - Sending this path {msg_with_path.body} to {self.agent.aircraft_data[0]}\n\n")

                            #print(f"ASM - Sending this path {msg_with_path.body} to {self.agent.aircraft_data[0]}\n")
                            self.agent.waiting_for_path = False
                            self.agent.asked_for_path = False





            async def ask_cc_for_path(self):

                start_position = self.agent.aircraft_data[1]
                end_position = self.agent.aircraft_data[2]

                msg = Message(to="cc_agent@localhost")
                msg.set_metadata("performative", "query")
                msg.body = f"0001 {start_position} {end_position}"

                with open('chatlog.txt', 'a') as file:
                    file.write(f"ASM - Asked CC for the path from {start_position} to {end_position}\n\n")

                #print(f"ASM - Asked CC for the path from {start_position} to {end_position}\n")
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
                #print()
                #if not self.agent.got_path:

                msg = await self.receive(timeout=10)
                if msg:
                    #print(f"CC - {msg.body}")
                    separated_text = re.findall(r'\(.*?\)|\w+', msg.body)
                    code = separated_text[0]
                    start_position = ast.literal_eval(separated_text[1])
                    end_position = ast.literal_eval(separated_text[2])

                    """
                    
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
                    """

                    if code == "0001":
                        path = self.astar(start_position, end_position)
                        #print(f"CC - {path}")

                        msg_with_path = Message(to="asm_agent@localhost")
                        msg_with_path.body = f"0001 {path}"
                        msg_with_path.set_metadata("performative", "query")
                        await self.send(msg_with_path)

                        with open('chatlog.txt', 'a') as file:
                            file.write(f"CC - Sending ASM this path {msg_with_path.body}\n\n")

                    elif code == "0002":
                        path = self.astar(start_position, end_position)
                        #print(f"CC - Emergency - {path}")

                        msg_with_path = Message(to="asm_agent@localhost")
                        msg_with_path.body = f"0002 {path}"
                        msg_with_path.set_metadata("performative", "query")
                        await self.send(msg_with_path)

                        with open('chatlog.txt', 'a') as file:
                            file.write(f"CC - Emergency - Sending ASM this path {msg_with_path.body}\n\n")


                    #print(f"CC - Sending ASM the path \n")




            def astar(self, start, end):

                start_node = Node(None, start)
                start_node.g = start_node.h = start_node.f = 0
                end_node = Node(None, end)
                end_node.g = end_node.h = end_node.f = 0

                open_list = []
                closed_list = []

                open_list.append(start_node)
                #print(f"{start} -> {end}")
                #print(self.agent.environment.matrix[end[0]][end[1]][end[2]])
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
                        #print("Got path!")
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

    airport_1 = Airport((0, 0, 0), "airport_1")
    airport_2 = Airport((0, 14, 0), "airport_2")
    airport_3 = Airport((3, 6, 0), "airport_3")
    airport_4 = Airport((5, 12, 0), "airport_4")
    airport_5 = Airport((8, 6, 0), "airport_5")
    airport_6 = Airport((14, 0, 0), "airport_6")
    airport_7 = Airport((14, 14, 0), "airport_7")


    airport_list = [airport_1, airport_2, airport_3, airport_4]



    environment = Environment(environment_matrix, airport_list)
    environment.build_airports()

    with open('chatlog.txt', 'w') as file:
        file.truncate(0)

    communication_agent = CommunicationAgent("com_agent@localhost", "password", environment)
    await communication_agent.start(auto_register=True)

    central_coordination_agent = CentralCoordinationAgent("cc_agent@localhost", "password", environment)
    await central_coordination_agent.start(auto_register=True)

    airspace_manager = AirSpaceManager("asm_agent@localhost", "password", environment)
    await airspace_manager.start(auto_register=True)





    aircraft_agent_1 = AircraftAgent("aircraft_agent_1@localhost", "password", environment, "A1", airport_1)
    await aircraft_agent_1.start(auto_register=True)

    aircraft_agent_2 = AircraftAgent("aircraft_agent_2@localhost", "password", environment, "A2", airport_2)
    await aircraft_agent_2.start(auto_register=True)


    aircraft_agent_3 = AircraftAgent("aircraft_agent_3@localhost", "password", environment, "A3", airport_3)
    await aircraft_agent_3.start(auto_register=True)

    #aircraft_agent_4 = AircraftAgent("aircraft_agent_4@localhost", "password", environment, "A4", airport_4)
    #await aircraft_agent_4.start(auto_register=True)

    #aircraft_agent_5 = AircraftAgent("aircraft_agent_5@localhost", "password", environment, "A5", airport_5)
    #await aircraft_agent_5.start(auto_register=True)

    #aircraft_agent_6 = AircraftAgent("aircraft_agent_6@localhost", "password", environment, "A6", airport_6)
    #await aircraft_agent_6.start(auto_register=True)

if __name__ == "__main__":
    spade.run(main())


