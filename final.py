"""
COM - Communication Agent
ASM - Air Space Manager Agent
CC - Central Coordination Agent

Output:
As comunicações entre agentes ficam registadas num ficheiro chamado chatlog.txt
No terminal é imprimida uma matriz 15x15 onde representados os aeroportos pelos seus estados(E, R, F),
os aviões representados pelo seu número e as coordenadas (x, y) onde os aviões não podem passar,
o aeroporto militar, representado por A's e o pico da montanha representado por um P
O aeroporto militar impede os aviões de passar no seu espaço aéreo, obrigando-os a contorná-lo
A montanha impede os aviões de passar à sua volta numa altura mais baixa, obrigando-os a subir a altitude
"""

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
from spade.message import Message

#Tamanho da matriz (15x15x4)
SIZE = 15
HEIGHT = 4

#Matrix do ambiente
environment_matrix = np.zeros((SIZE, SIZE, HEIGHT)).astype(int).astype(str)

"""
Para simplificar, todas as posições proibidas são representadas com um X
"""

for y in range(SIZE): #Proibir o chão
    for x in range(SIZE):
        if environment_matrix[y][x][0] == '0':
            environment_matrix[y][x][0] = 'X'


for y in range(2, 4):  # Criar o aeroporto militar
    for x in range(10, 14):
        for z in range(HEIGHT):
            environment_matrix[y][x][z] = 'X'



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
    """
    Classe dos nódulos para o algoritmo astar

    Argumentos:
    parent - nó pai
    position - coordenadas na matriz
    g, h, f - valores do astar
    """
    def __init__(self, parent=None, position=None):
        self.parent = parent
        self.position = position

        self.g = 0
        self.h = 0
        self.f = 0

    def __eq__(self, other):
        return self.position == other.position

class Airport:
    """
    Classe para os aeroportos, cada aeroporto, caso esteja cheio ou reservado,
    tem um avião associado que é o avião que está lá ou se está a dirigir para lá

    Argumentos:
    position - coordenadas do aeroporto
    idx - nome do aeroporto
    status - estado do aeroport (empty->'E', reserved->'R', full->'F')
    airplane - avião associado ao aeroporto num determinado momento
    """
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
    """
    Classe que representa o ambiente

    Argumentos:
    matrix - matriz do ambiente
    aiports - aeroportos
    aircraft_positions - posições dos aviões num determinado momento
    """

    def __init__(self, matrix, airports):
        self.matrix = matrix
        self.airports = airports
        self.aircraft_positions = {}


    def build_airports(self):
        """
        Função para criar os aeroportos na matriz
        """
        for airport in self.airports:
            environment_matrix[airport.position[0]][airport.position[1]][airport.position[2]] = airport.status


    def get_empty_airports(self):
        """
        Função para obter os aeroportos vazios
        """
        empty_airports = []
        for airport in self.airports:
            if airport.is_empty():
                empty_airports.append(airport)
        return empty_airports

    def get_airports(self):
        """
        Função para obter todos os aeroportos
        """
        return self.airports

    def get_closest_not_full_airport(self, aircraft_position):
        """
        Função para obter o aeroporto não cheio mais próximo do avião num determinado momento
        """
        closest = None
        min_distance = math.inf

        for airport in self.airports:
            if airport.status != 'F':
                distance = math.sqrt(sum((p2 - p1)**2 for p1, p2 in zip(aircraft_position, airport.position)))
                if distance < min_distance:
                    min_distance = distance
                    closest = airport

        return(closest)





class CommunicationAgent(Agent):
    """
    Agente encarregue de imprimir a matriz, os aeroportos (incluindo o seu estado e o avião associado ao aeroporto)
     e alguns avisos que recebe do ASM,
    estes avisos podem ser uma emergência de um avião ou o redirecionamento de um avião

    A matriz imprimida é uma matriz de dua dimensões que representa o espaço aéreo (é ignorada a altura)
    Nesta matriz está representada também os aeroportos, o aeroporto militar e o pico da montanha

    Argumentos:
    jid - jid do agente
    password - password do agente
    environment - ambiente
    warnings - avisos que recebe do ASM, cada aviso fica no ecrã 8 segundos
    same_coordinates_counter - número de vezes que dois aviões
                               passaram no mesmo sitio ao mesmo tempo
    """
    def __init__(self, jid, password, environment):
        super().__init__(jid, password)
        self.environment = environment
        self.warnings = []
        self.same_coordinates_counter = 0

    async def setup(self):

        class PrintEnvironment(PeriodicBehaviour):
            """
            Comportamento para imprimir o ambiente, imprime a matriz, os avisos e o contador
            """
            async def run(self):

                os.system('cls' if os.name == 'nt' else 'clear')

                matrix_to_print = np.zeros((SIZE, SIZE)).astype(int).astype(str)

                for y in range(2, 4):  # Criar o aeroporto militar na matriz para imprimir
                    for x in range(10, 14):
                            matrix_to_print[y][x] = 'A'

                matrix_to_print[11][3] = 'P' #Criar o pico da montanha

                for aircraft in self.agent.environment.aircraft_positions: #Criar os aviões
                    x = self.agent.environment.aircraft_positions[aircraft][0]
                    y = self.agent.environment.aircraft_positions[aircraft][1]
                    matrix_to_print[x][y] = aircraft[1]

                for airport in self.agent.environment.airports: #Criar os aeroportos
                    x = airport.position[0]
                    y = airport.position[1]
                    matrix_to_print[x][y] = airport.status

                for i in range(len(matrix_to_print)): #Imprimir a matriz
                    line = ""
                    for j in range(len(matrix_to_print)):
                        line += str(matrix_to_print[i][j]) + " "
                    print(line)

                print()

                for airport in self.agent.environment.airports: #Imprimir os aeroportos
                    print(f"{airport.idx} - {airport.status} - {airport.airplane}")

                print()

                #Contar e imprimir o número de vezes que aviões já passaram na mesma posição
                seen_values = set()
                for value in self.agent.environment.aircraft_positions.values():
                    if value in seen_values:
                        self.agent.same_coordinates_counter += 1
                    seen_values.add(value)
                print(f"Times aircrafts passed in the same point: {self.agent.same_coordinates_counter}\n")

                #Imprimir os avisos
                for i, warning in enumerate(self.agent.warnings):
                    print(warning[0])
                    if warning[1] > 7:
                        self.agent.warnings.pop(i)
                    warning[1] += 1


        class WaitingForWarnings(CyclicBehaviour):
            """
            Comportamento para receber as mensagens com os avisos
            """
            async def run(self):

                msg = await self.receive()
                if msg:
                    self.agent.warnings.append([msg.body, 0])


        self.add_behaviour(PrintEnvironment(1))
        self.add_behaviour(WaitingForWarnings())



class AircraftAgent(Agent):
    """
    Agente que representa os aviões
    Este agente tem um probabilidade de 1/20 em cada movimento de ter uma emergência
    durante o voo caso isto aconteça o ASM redireciona-o para o aeroporto não cheio
    mais próximo se haja um avião em viagem para esse aeroporto, esse avião é também
    redirecionado para outro aleatóriamente

    Argumentos:
    jid - jid do agente
    password - password do agente
    environment - ambiente
    idx - id do agente, para ser mais facilmente reconhecido
    start_airport - aeroporto onde começou o voo
    end_airport - aeroporto onde vai acabar o voo
    position - posição num determinado momento
    path - caminho a percorrer no voo

    Para além dos argumentos tem também algumas flags que facilitam o funcinamento do agente
    """
    def __init__(self, jid, password, environment, idx, start_airport):
        super().__init__(jid, password)
        self.environment = environment
        self.idx = idx
        self.start_airport = start_airport
        self.end_airport = None
        self.position = start_airport.position
        self.path = None

        #Flags
        self.begin_flight = True
        self.on_land = True
        self.asked_for_path = False
        self.wait_in_airport = True
        self.got_emergency = False
        self.already_got_emergency = False
        self.asked_for_emergency_path = False

        #Preencher o aeroporto inicial
        self.start_airport.to_full(str(self.jid))

    async def setup(self):

        class GetPath(CyclicBehaviour):
            """
            Comportamento para pedir e receber o caminho do voo
            Todas comunicações são feitas com o ASM
            """
            async def run(self):

                if not self.agent.got_emergency:
                    #Processo de requesição do caminho numa situação normal
                    if not self.agent.wait_in_airport:
                        if self.agent.begin_flight:
                            if not self.agent.asked_for_path:

                                empty_airports = self.agent.environment.get_empty_airports()
                                if len(empty_airports) > 0:
                                    end_airport = random.choice(empty_airports)
                                    end_airport.to_reserved(str(self.agent.jid))
                                    self.agent.end_airport = end_airport
                                    await self.ask_asm_for_path()

                            else:
                                await self.receive_path()
                    else:
                        random_number = np.random.randint(2, 5)
                        await asyncio.sleep(random_number)
                        self.agent.wait_in_airport = False
                else:
                    #Processo de requesição do caminho numa situação de emergência
                    if not self.agent.asked_for_emergency_path:
                        await self.ask_asm_for_path()
                    else:
                        await self.receive_path()


            def get_end_airport(self, airport_name):
                """
                Função para obter o novo aeroporto destino através do nome que é enviado pelo ASM
                """
                for airport in self.agent.environment.airports:
                    if airport.idx == airport_name:
                        self.agent.end_airport = airport


            async def ask_asm_for_path(self):
                """
                Função para requisitar o caminho ao ASM
                """
                if not self.agent.got_emergency:
                    """
                    Processo para requesitar o caminho numa situação normal
                    Neste caso o agente informa o ASM da sua posição e para onde quer ir
                    O código da mensagem(primeiro quatro digitos) indicam que é uma situação normal
                    a seguir ao código seguem-se as coordenadas iniciais e finais da viagem
                    """

                    msg = Message(to="asm_agent@localhost")
                    msg.set_metadata("performative", "request")

                    if self.agent.on_land:
                        msg.body = f"0001 {self.agent.start_airport.position} {self.agent.end_airport.position}"
                    else:
                        msg.body = f"0001 {self.agent.position} {self.agent.end_airport.position}"

                    with open('chatlog.txt', 'a') as file:
                        file.write(f"{self.agent.idx} - I want to take off, asking ASM the path\n\n")

                    await self.send(msg)

                    self.agent.asked_for_path = True

                else:
                    """
                    Processo para requesitar o caminho numa situação de emergência
                    Neste caso o agente apenas informa o ASM da sua posição
                    O código da mensagem indica que é uma situação de emergência
                    a seguir ao código seguem-se as coordenadas do avião
                    """

                    msg = Message(to="asm_agent@localhost")
                    msg.set_metadata("performative", "inform")
                    msg.body = f"0002 {self.agent.position}"

                    with open('chatlog.txt', 'a') as file:
                        file.write(f"{self.agent.idx} - Got a problem, asking ASM for help\n\n")

                    await self.send(msg)

                    #Mensagem com o nome do novo aeroporto de destino
                    new_end_airport_msg = await self.receive(timeout=10)
                    if new_end_airport_msg:
                        self.get_end_airport(new_end_airport_msg.body)

                    self.agent.asked_for_emergency_path = True


            async def receive_path(self):
                """
                Função para receber o caminho
                """
                if not self.agent.got_emergency:
                    #Processo para receber o caminho numa situação normal

                    msg_with_path = await self.receive(timeout=10)
                    if msg_with_path and msg_with_path.body != "0003":
                        """
                        É preciso verificar se a mensage é diferente da mensegem que este 
                        agente recebe caso vá ser redirecionado(0003) porque por vezes
                        o agente recebe as mensagens quase ao mesmo tempo e acabavam por ficar 
                        trocadas
                        """

                        #Passar o caminho de string para lista
                        self.agent.path = ast.literal_eval(msg_with_path.body)

                        with open('chatlog.txt', 'a') as file:
                            file.write(f"{self.agent.idx} - Got this path: {self.agent.path}\n\n")

                        self.agent.begin_flight = False
                        self.agent.on_land = False
                        self.agent.start_airport.to_empty()

                else:

                    #Processo para receber o caminho numa situação de emergência
                    msg_with_path_emergency = await self.receive(timeout=10)
                    if msg_with_path_emergency:

                        with open('chatlog.txt', 'a') as file:
                            file.write(f"{self.agent.idx} - Got this emergency path {msg_with_path_emergency.body}\n\n")

                        #Passar o caminho de string para uma lista
                        self.agent.path = ast.literal_eval(msg_with_path_emergency.body[5:])

                        self.agent.got_emergency = False
                        self.agent.already_got_emergency = True


        class WaitForEmergency(CyclicBehaviour):
            """
            Comportamento para receber a mensagem a dizer que este avião precisa de ser redirecionado
            Isto acontece quando este agente está a dirigir-se para um aeroporto e outro avião
            tem uma emergência e precisa de ir para esse aeroporto
            """

            async def run(self):

                msg = await self.receive()
                if msg and msg.body == "0003":
                    #Caso receba a mensagem as flags voltam ao estado inicial
                    self.agent.end_airport = None
                    self.agent.begin_flight = True
                    self.agent.asked_for_path = False
                    self.agent.wait_in_airport = True
                    self.agent.already_got_emergency = False
                    self.agent.got_emergency = False
                    self.agent.asked_for_emergency_path = False

        class Fly(PeriodicBehaviour):
            """
            Comportamento para voar, tem uma velocidade de uma posição por segundo
            """
            async def run(self):

                if not self.agent.begin_flight:
                    if not self.agent.got_emergency:

                        """
                        Criar uma emergência
                        Só pode haver uma emergência caso o avião não tenha tido já uma emergência
                        e o aeroporto mais próximo não seja o de partido ou o de chegada
                        """
                        random_number = np.random.randint(1, 20)
                        if (random_number == 3
                            and not self.agent.already_got_emergency
                            and self.agent.environment.get_closest_not_full_airport(self.agent.position) != self.agent.start_airport
                            and self.agent.environment.get_closest_not_full_airport(self.agent.position) != self.agent.end_airport):

                            self.agent.got_emergency = True
                            self.agent.asked_for_path = False
                            self.agent.end_airport.to_empty()

                        else:
                            #Se não houver uma emergência neste movimento
                            #O avião passa para a pŕoxima posição do caminho
                            self.agent.position = self.agent.path.pop(0)

                            #Atualizar as coordenadas no ambiente
                            self.agent.environment.aircraft_positions[self.agent.idx] = self.agent.position

                            #with open('teste.txt', 'a') as file:
                            #    file.write(f"{self.agent.idx} - {self.agent.end_airport}\n\n")

                            #Se a posição for a posição final (chegou ao destino)
                            if self.agent.position == self.agent.end_airport.position:

                                with open('chatlog.txt', 'a') as file:
                                    file.write(f"{self.agent.idx} - I have arrived\n\n")

                                #Volta ao estado inicial
                                self.agent.start_airport = self.agent.end_airport
                                self.agent.end_airport = None
                                self.agent.begin_flight = True
                                self.agent.on_land = True
                                self.agent.asked_for_path = False
                                self.agent.start_airport.to_full(str(self.agent.jid))
                                self.agent.wait_in_airport = True
                                self.agent.already_got_emergency = False
                                self.agent.got_emergency = False
                                self.agent.asked_for_emergency_path = False


        self.add_behaviour(WaitForEmergency())
        self.add_behaviour(Fly(2))
        self.add_behaviour(GetPath())



class AirSpaceManager(Agent):
    """
    Agente que gere o espaço aéreo
    Este agente recebe o aviso do avião que quer partir, pede ao CC o caminho
    e envia-o ao avião
    É também, em caso de emergência responsável por identificar qual é o aeroporto mais
    próximo do avião com problemas e avisar, caso seja necessário, outro avião que precisa de
    ser redirecionado

    Argumentos:
    jid - jid do agente
    password - password do agente
    environment - ambiente
    AA_wait_queue - fila de aviões que estão à espera que este agente lhes dê o caminho
    para poderem partir
    aircraft_data - jid, posição inicial e posição final do  agente que requisitou o caminho

    Para além dos argumentos tem também alguma flags que facilitam o funcinamento do agente
    """
    def __init__(self, jid, password, environment):
        super().__init__(jid, password)
        self.environment = environment
        self.AA_wait_queue = []
        self.aircraft_data = None

        #Flags
        self.waiting_for_path = False
        self.asked_for_path = False


    async def setup(self):

        class WaitForAAMessages(CyclicBehaviour):
            """
            Comportamento para receber mensagens de aviões que querem partir,
            após receber a mensagem coloca-o avião que a mandou no fim da fila
            Caso o avião que envie a mensagem esteja numa situação de emergência
            o ASM trata logo do caso
            """
            async def run(self):

                msg = await self.receive(timeout=10)
                if msg and str(msg.sender)[0:8] == "aircraft":
                    """
                    separeted_text é uma lista com o conteúdo da mensagem
                    Os primeiro 4 digitos da mensagem é um código de 4 algarismos e 
                    depois seguem-se as coordenadas. Este função(re.findall) com este
                    padrão(o primeiro argumento da função) apena separa a string em palavras, 
                    e considera tudo o que está dentro de parenteses como uma palavra
                    por exemplo, se a mensagem for "0001 (0, 0, 0) (1, 1, 1)" a lista fica
                    ["0001", "(0, 0, 0)", "(1, 1, 1)"]
                    """
                    separated_text = re.findall(r'\(.*?\)|\w+', msg.body)
                    code = separated_text[0]


                    if code == "0001":
                        """
                        Quando o código é 0001, é uma situação normal
                        a seguir ao código vêm as coordenadas iniciais e as finais
                        """
                        start_position = separated_text[1]
                        end_position = separated_text[2]

                        self.agent.AA_wait_queue.append((str(msg.sender), start_position, end_position))

                        with open('chatlog.txt', 'a') as file:
                            file.write(f"ASM - Added {str(msg.sender)} to the AA wait queue with the start position: {start_position} and end position: {end_position}\n\n")


                    if code == "0002":
                        """
                        Quando o código é 0002, é uma situação de emergência
                        a seguir ao código vêm só as coordenadas iniciais
                        """

                        #Mensagem para o COM com o que ele deve imprimir
                        warning_msg = Message(to="com_agent@localhost")
                        warning_msg.body = f"{str(msg.sender)} Got an emergency!"
                        warning_msg.set_metadata("performative", "inform")
                        await self.send(warning_msg)

                        """
                        Esta função(ast.literal_eval) transforma a string na sua estrutura literal
                        por exemplo, a string "(0, 0, 0)" passa a ser o tuple (0, 0, 0)
                        """
                        start_position = ast.literal_eval(separated_text[1])

                        #Aeroporto não cheio mais próximo
                        closest_airport = self.agent.environment.get_closest_not_full_airport(start_position)

                        if closest_airport.is_reserved():
                            """
                            Caso este aeroport esteja reservado, avisa o avião que se dirijia para
                            ele que precisa de ser redirecionado e manda mensagem ao COM com o aviso
                            que ele deve imprimir
                            O código que envia para o avião é 0003
                            """
                            aircraft_to_redirect = closest_airport.airplane
                            with open('chatlog.txt', 'a') as file:
                                file.write(f"ASM - Telling {aircraft_to_redirect} he has to be redirected\n\n")

                            redirect_msg = Message(to=aircraft_to_redirect)
                            redirect_msg.body = "0003"
                            redirect_msg.set_metadata("performative", "inform")
                            await self.send(redirect_msg)

                            redirect_warning_msg = Message(to="com_agent@localhost")
                            redirect_warning_msg.body = f"Redirecting {aircraft_to_redirect}"
                            redirect_warning_msg.set_metadata("performative", "inform")
                            await self.send(redirect_warning_msg)

                        #Dizer ao avião o seu novo aeroporto
                        await self.tell_aa_new_end_airport(str(msg.sender), closest_airport.idx)

                        """
                        Preencher o aeroporto, neste caso o aeroporto fica cheio e nao reservado
                        para este avião não ter que ser redirecionado no caso de haver outra emergência
                        """
                        self.fill_airport(str(closest_airport.position), str(msg.sender))

                        #Pedir ao CC o novo caminho
                        await self.emergency_ask_cc_for_path(start_position, closest_airport.position)

                        #Resposta do CC com o caminho
                        response = await self.receive(timeout=10)
                        if response and str(response.sender) == "cc_agent@localhost" and response.body[0:4] == "0002":

                            #Mensagem com o novo caminho para enviar ao avião
                            msg_with_path = Message(to=str(msg.sender))
                            msg_with_path.set_metadata("performative", "inform")
                            msg_with_path.body = f"0002 {response.body[5:]}"

                            with open('chatlog.txt', 'a') as file:
                                file.write(f"ASM - Sending {str(msg.sender)} this emergency path {msg_with_path.body}\n\n")

                            await self.send(msg_with_path)

            async def tell_aa_new_end_airport(self, aircraft, airport):
                """
                Função para enviar o nome do aeroporto ao avião
                """
                msg = Message(to=aircraft)
                msg.set_metadata("performative", "inform")
                msg.body = airport

                with open('chatlog.txt', 'a') as file:
                    file.write(f"ASM - Telling {aircraft} his new airport\n\n")

                await self.send(msg)

            async def emergency_ask_cc_for_path(self, start_position, end_position):
                """
                Função para pedir o caminho ao CC
                """
                msg = Message(to="cc_agent@localhost")
                msg.set_metadata("performative", "request")
                msg.body = f"0002 {start_position} {end_position}"

                with open('chatlog.txt', 'a') as file:
                    file.write(f"ASM - Asked CC for the path from {start_position} to {end_position}\n\n")

                await self.send(msg)


            def fill_airport(self, position, aircraft):
                """
                Função para tornar cheio o aeroporto
                """
                for airport in self.agent.environment.airports:
                    if airport.position == ast.literal_eval(position):
                        airport.to_full(str(aircraft))



        class GetPath(CyclicBehaviour):
            """
            Comportamento para receber o caminho enviado pelo CC
            e enviá-lo para o avião
            """
            async def run(self):

                if not self.agent.waiting_for_path:
                    #Retirar o primeiro da lista
                    if len(self.agent.AA_wait_queue) > 0:
                        self.agent.aircraft_data = self.agent.AA_wait_queue.pop(0)
                        self.agent.waiting_for_path = True

                else:
                    if not self.agent.asked_for_path:
                        #Pedir o caminho so CC
                        await self.ask_cc_for_path()

                    else:
                        #Mensagem enviada pelo CC com o caminho
                        msg = await self.receive()
                        if msg and str(msg.sender) == "cc_agent@localhost" and msg.body[0:4] == "0001":
                            msg_with_path = Message(to=self.agent.aircraft_data[0])
                            msg_with_path.set_metadata("performative", "inform")
                            msg_with_path.body = msg.body[5:]

                            await self.send(msg_with_path)

                            with open('chatlog.txt', 'a') as file:
                                file.write(f"ASM - Sending {self.agent.aircraft_data[0]} his path\n\n")

                            self.agent.waiting_for_path = False
                            self.agent.asked_for_path = False





            async def ask_cc_for_path(self):
                """
                Função para pedir o caminho ao CC
                """

                start_position = self.agent.aircraft_data[1]
                end_position = self.agent.aircraft_data[2]

                msg = Message(to="cc_agent@localhost")
                msg.set_metadata("performative", "request")
                msg.body = f"0001 {start_position} {end_position}"

                with open('chatlog.txt', 'a') as file:
                    file.write(f"ASM - Asking CC for the path from {start_position} to {end_position}\n\n")

                await self.send(msg)
                self.agent.asked_for_path = True


        self.add_behaviour(GetPath())
        self.add_behaviour(WaitForAAMessages())




class CentralCoordinationAgent(Agent):
    """
    Agente responsável por calcular os caminhos
    este agente recebe uma mensagem do ASM com as coordenadas e responde com
    o caminho da viagem

    Argumentos:
    jid - jid do agente
    password - password do agente
    environment - ambiente
    path - caminho calculado que vai ser enviado

    Para além dos argumentos tem também alguma flags que facilitam o funcinamento do agente
    """
    def __init__(self, jid, password, environment):
        super().__init__(jid, password)
        self.environment = environment
        self.path = None

        #Flags
        self.got_path = False
        self.got_coordinates = False

    async def setup(self):

        class GetPath(CyclicBehaviour):
            """
            Comportamento para calular e enviar o caminho ao ASM
            """
            async def run(self):

                #Mensagem com as coordenadas enviada pelo ASM
                msg = await self.receive(timeout=10)
                if msg:
                    separated_text = re.findall(r'\(.*?\)|\w+', msg.body)
                    code = separated_text[0]
                    start_position = ast.literal_eval(separated_text[1])
                    end_position = ast.literal_eval(separated_text[2])

                    path = self.astar(start_position, end_position)
                    msg_with_path = Message(to="asm_agent@localhost")
                    msg_with_path.set_metadata("performative", "inform")

                    #Para o trabalho do CC, o código é irrelevante, mas vai ser importante para o ASM
                    msg_with_path.body = f"{code} {path}"

                    with open('chatlog.txt', 'a') as file:
                        file.write(f"CC - Sending ASM this path {path}\n\n")

                    await self.send(msg_with_path)


            def astar(self, start, end):
                """
                Função para calcular o caminho entre dois pontos usando o algoritmo A*

                Este algoritmo foi adaptado do que pode ser encontrado  neste site:
                https://medium.com/@nicholas.w.swift/easy-a-star-pathfinding-7e6689c7f7b2
                Apenas adaptamos o que estava feito ao nosso código e alteramos para
                aceitar matrizes com 3 dimensões
                """
                start_node = Node(None, start)
                start_node.g = start_node.h = start_node.f = 0
                end_node = Node(None, end)
                end_node.g = end_node.h = end_node.f = 0

                open_list = []
                open_list.append(start_node)
                closed_list = []

                while (len(open_list) > 0):
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

    #Aeroportos
    airport_1 = Airport((0, 0, 0), "airport_1")
    airport_2 = Airport((0, 14, 0), "airport_2")
    airport_3 = Airport((3, 6, 0), "airport_3")
    airport_4 = Airport((5, 12, 0), "airport_4")
    airport_5 = Airport((8, 6, 0), "airport_5")
    airport_6 = Airport((14, 0, 0), "airport_6")
    airport_7 = Airport((14, 14, 0), "airport_7")

    airport_list = [airport_1, airport_2, airport_3, airport_4, airport_5, airport_6, airport_7]

    #Ambiente
    environment = Environment(environment_matrix, airport_list)
    environment.build_airports()

    #Limpar o ficheiro com as mensagens
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

    aircraft_agent_4 = AircraftAgent("aircraft_agent_4@localhost", "password", environment, "A4", airport_4)
    await aircraft_agent_4.start(auto_register=True)

    aircraft_agent_5 = AircraftAgent("aircraft_agent_5@localhost", "password", environment, "A5", airport_5)
    await aircraft_agent_5.start(auto_register=True)


if __name__ == "__main__":
    spade.run(main())
