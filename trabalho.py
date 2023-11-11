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






class AirSpaceManager(Agent):

    def __init__(self, jid, password, environment):
        super().__init__(jid, password)
        self.environment = environment


    async def setup(self):

        class monitor_airspace_behaviour(CyclicBehaviour):

            async def run(self):
                #print("receiving")
                #empty_spaces = self.get_empty_spaces()
                #airplanes = self.get_aircraft_positions()
                #airports = self.get_aiports()

                msg = await self.receive(timeout=10)
                if msg:
                    #words = msg.body.split()
                    words = re.findall(r'\(.*?\)|\w+', msg.body)
                    #print(words)
                    code = words[0]
                    if code == "0001":
                        start_position = ast.literal_eval(words[1])
                        end_position = ast.literal_eval(words[2])
                        print(start_position)
                        print(end_position)

                    sender_jid = str(msg.sender)
                    response = Message(to=sender_jid)
                    response.body = "ok"
                    response.metadata = {"performative": "inform"}
                    await self.send(response)

                #await self.agent.stop()

        self.add_behaviour(monitor_airspace_behaviour())



class AircraftAgent(Agent):
    def __init__(self, jid, password, environment, idx, start_airport, position, end_airport=None):
        super().__init__(jid, password)
        self.environment = environment
        self.idx = idx
        self.start_airport = start_airport
        self.position = position
        self.on_land = True
        self.end_airport = end_airport

        self.start_airport.to_full(self)


    async def setup(self):

        class Fly(CyclicBehaviour):
            async def run(self):
                if self.agent.on_land:

                    empty_airports = self.agent.environment.get_empty_airports()
                    self.agent.end_airport = random.choice(empty_airports)
                    #print(self.agent.end_airport)

                    await self.start_flying(self.agent.start_airport.position, self.agent.end_airport.position)
                    #self.agent.on_land = False


            def update_position(self):
                self.agent.environment.aircraft_positions[self.agent.idx] = self.agent.position




            async def start_flying(self, start_position, end_position):

                msg = Message(to="atc_agent@localhost")
                msg.set_metadata("performative", "query")
                msg.body = f"0001 {start_position} {end_position}"

                # Send the message
                print(f"Sending this {msg.body}")
                await self.send(msg)

                response = await self.receive(timeout=10)
                if response:
                    print(response.body)
                    self.agent.on_land = False

        self.add_behaviour(Fly())



class CentralCoordinationAgent(Agent):
    def __init__(self, jid, password, environment, path=None):
        super().__init__(jid, password)
        self.environment = environment
        self.path = path

















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

    #environment.print_environment()

    """
    aircraft_agent = AircraftAgent("aircraft_agent@localhost", "password", environment, [0, 1, 0])


    """

if __name__ == "__main__":
    spade.run(main())

