import numpy as np
import os
import asyncio
import spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.behaviour import FSMBehaviour
from spade.behaviour import State
from spade.template import Template
from spade.message import Message

SIZE = 15
HEIGHT = SIZE

airports = [
            [0, 1, 0, 'E'], [1, 0, 0, 'E'], [1, 1, 0, 'E'],
            [14, 0, 0, 'E'], [14, 1, 0, 'E'], [14, 2, 0, 'E'],
            [0, 14, 0, 'E'], [1, 13, 0, 'E'], [2, 12, 0, 'E'],
            [14, 13, 0, 'E'], [13, 14, 0, 'E']
            ]

environment_matrix = np.zeros((SIZE, SIZE, HEIGHT)).astype(int).astype(str)

for y in range(6, 8):
    for x in range(0, 4):
        for z in range(HEIGHT):
            environment_matrix[y][x][z] = 'X'


for z in range(HEIGHT-3, HEIGHT):
    environment_matrix[0][7][z] = 'X'
    environment_matrix[0][8][z] = 'X'
    environment_matrix[0][9][z] = 'X'
    environment_matrix[1][6][z] = 'X'
    environment_matrix[1][7][z] = 'X'
    environment_matrix[1][8][z] = 'X'


for z in range(5):
    environment_matrix[9][9][z] = 'X'
    environment_matrix[9][11][z] = 'X'
    environment_matrix[11][9][z] = 'X'
    environment_matrix[11][11][z] = 'X'

for z in range(10):
    environment_matrix[9][10][z] = 'X'
    environment_matrix[10][9][z] = 'X'
    environment_matrix[10][11][z] = 'X'
    environment_matrix[11][10][z] = 'X'

for z in range(HEIGHT):
    environment_matrix[10][10][z] = 'X'




class Environment:
    def __init__(self, matrix):
        self.matrix = matrix
        self.airports = []
        self.aircraft_positions = {}

    def get_aircraft_position(self):
        #
        pass


    def update_aircraft_position(self, aircraft_id, position):
        self.aircraft_positions[aircraft_id] = position
        print(self.aircraft_positions)


    def update_matrix(self):
        for airport in airports:
            #print(airport)
            self.airports.append(airport)
            self.matrix[airport[0]][airport[1]][airport[2]] = airport[3]


    def get_airports_empty_spaces(self):
        empty_spaces = []
        for airport in self.airports:
            for space in airport:
                if space[3] == 'E':
                    empty_spaces.append(space)
        return empty_spaces


    def fill_airport_space(self, space_to_fill):
        for airport in self.airports:
            for space in airport:
                if space == space_to_fill:
                    #print(space[3])
                    space[3] = 'F'
        self.update_matrix()

    def empty_airport_space(self, space_to_empty):
        for airport in self.airports:
            for space in airport:
                if space == space_to_empty:
                    #print(space[3])
                    space[3] = 'E'
        self.update_matrix()

    #def add_airplane(self, space):
    #    self.fill_airport_space(space)
    #    self.airplanes.append([space[0], space[1], space[2]])



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
                print("receiving")
                #empty_spaces = self.get_empty_spaces()
                #airplanes = self.get_aircraft_positions()
                #airports = self.get_aiports()

                msg = await self.receive(timeout=10)
                print(msg)
                if msg:
                    print(f"Message received with content: {msg.body}")


            def get_aiports(self):
                return self.agent.environment.airports

            def get_empty_spaces(self):
                return self.agent.environment.get_airports_empty_spaces()

        self.add_behaviour(monitor_airspace_behaviour())



class AircraftAgent(Agent):
    def __init__(self, jid, password, environment, position):
        super().__init__(jid, password)
        self.environment = environment
        self.position = position
        self.on_land = True


    async def setup(self):
        # Define a behavior to interact with the environment and air traffic control
        class Fly(CyclicBehaviour):
            async def run(self):
                if self.agent.on_land:


                    await self.start_flying(self.agent.position)


            async def start_flying(self, position):
                # Create an ACL message to send data to the air traffic control agent
                msg = Message(to="atc_agent@localhost")  # Replace with the correct ATC agent JID
                msg.set_metadata("performative", "query")
                msg.body = f"0001 {position}"

                # Send the message
                print(f"Sending this {msg.body}")
                await self.send(msg)
        self.add_behaviour(Fly())








async def main():
    environment = Environment(environment_matrix)
    environment.update_matrix()
    # environment.fill_airport_space([27, 1, 0, 'E'])
    # environment.add_airplane([27, 1, 0, 'E'])
    # print(environment.airports)
    environment.print_environment()

    aircraft_agent = AircraftAgent("aircraft_agent@localhost", "password", environment, [0, 1, 0])
    await aircraft_agent.start(auto_register=True)

    airspace_manager = AirSpaceManager("atc_agent@localhost", "password", environment)
    await airspace_manager.start(auto_register=True)


if __name__ == "__main__":
    spade.run(main())

