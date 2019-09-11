import sys
from getpass import getpass
from socket import *
import json
import time
import subprocess
import  base64

serverName = '0.0.0.0'
serverPort = 12000

DEFAULT_SERVER_NAME = '0.0.0.0'
DEFAULT_SERVER_PORT = 2121
DEFAULT_CLIENT_PORT = 12000

serverName = ''
serverPort = 0
clientControlPort = 0

ENDMARK = '  '
END_OF_FILE = chr(0).encode()

def wrapPacket(command, payload):
    packet = {
        'comm': command,
        'arg': payload 
    }
    packet = json.dumps(packet)
    return packet.encode()

def unwrapPacket(packet):
    a = packet.decode()
    a = json.loads(a)
    return a

def pad(string):
    return string + ' ' if len(string)%2 else string

def unpad(string):
    if len(string):
        return string[:-1] if string[-1] == ' ' else string
    return ''

def promptCredentials():
    username = input("username: ")
    passwd = getpass("password: ")
    return username+':'+passwd

def isValidCommand(command):
    return command in ['cd', 'ls', 'rmdir', 'mkdir', 'delete', 'pwd', 'put', 'get', 'close', 'quit']

def mapToSend(command):
    rel = {
        'cd': 'CD',
        'ls': 'LS',
        'rmdir': 'RM',
        'mkdir': 'MK',
        'delete': 'DL',
        'pwd': 'PW',
        'put': 'PT',
        'get': 'GT',
        'close': 'CL',
        'quit': 'QT',
        'login': 'LG',
        'forced_put': 'FP',
        'send_file_now': 'SF',
        'get_file_now': 'GF'
    }
    return rel[command]

def sendCommand(command, argument, conn):
    payload = pad(mapToSend(command)+argument)
    while len(payload):
        conn.send(payload[:2].encode())
        conn.recv(51)
        payload = payload[2:]
    conn.send(ENDMARK.encode())
    buffer = ''
    while True:
        a = conn.recv(51).decode()
        if a == ENDMARK:
            break
        buffer += a
        conn.send('OK'.encode())
    status = buffer[:2]
    response = unpad(buffer[2:])

    if status == 'OK':
        return True, response
    return False, response

def sendSignal(command, conn):
    payload = mapToSend(command)
    while len(payload):
        conn.send(payload[:2].encode())
        conn.recv(51)
        payload = payload[2:]
    conn.send(ENDMARK.encode())

def openConnection(serverAddress):
    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    clientPort = clientControlPort
    clientSocket.bind(('0.0.0.0', clientPort))
    print("Connected to ",serverAddress)
    clientSocket.connect(serverAddress)
    return clientSocket

def receiveFile(filename, conn):
    transferSocket = conn
    sendSignal('get_file_now', transferSocket)
    with open(filename, 'wb') as f:
        print('Receiving data...')
        chunk = transferSocket.recv(51)
        while chunk != END_OF_FILE:
            f.write(chunk)
            transferSocket.send('OK'.encode())
            chunk = transferSocket.recv(51)
        f.close()
        print("Done")
    transferSocket.send('OK'.encode())
    while True:
        a = conn.recv(51).decode()
        if a == ENDMARK:
            break
        conn.send('OK'.encode())


def sendFile(filename, conn):
    print("Starting upload...")
    transferSocket = conn
    sendSignal('send_file_now', transferSocket)
    transferSocket.recv(51)
    f = open(filename,'rb')
    chunk = f.read(51)
    cont = 0
    while (chunk):
        cont += 1
        transferSocket.send(chunk)
        transferSocket.recv(51)
        chunk = f.read(51)
    f.close()
    
    conn.send(END_OF_FILE)
    while True:
        a = conn.recv(51).decode()
        if a == ENDMARK:
            break
        conn.send('OK'.encode())
    print("Upload completed!")

def nameIsPresent(filename):
    files = subprocess.check_output(["ls"]).decode().split('\n')
    return filename in files

def askForConfirmationForOverride():
    answer = ''
    answered = False 
    while not answered:
        option = input("Do you want override {} in your folder?(Y/N) ".format(argument))
        if option in 'YN':
            answer = option
            answered = True
    return True if answer == 'Y' else False

if __name__ == "__main__":
    clientSocket = None
    p = None
    try:
        p = int(sys.argv[1])
    except:
        pass
    clientControlPort = int(p or DEFAULT_CLIENT_PORT)
    print(" *** File Transfer System *** ")
    print("Control port: ", clientControlPort)
    current_dir = '/'
    state = 'open'
    user = ''
    while True:
        if state == 'open':
            a = input("> ")
            try:
                command,argument = a.split()
            except:
                command,argument = a,None
            if command != 'open':
                print("Type 'open SERVER_IP' to initiate a connection.")
            else:
                serverName = argument or DEFAULT_SERVER_NAME
                clientSocket = openConnection((serverName, DEFAULT_SERVER_PORT))
                state = 'login'
        elif state == 'login':
            credentials = promptCredentials()
            response = sendCommand('login', credentials, clientSocket)
            if response[0]:
                print("Access granted to {}".format(credentials.split(':')[0]))
                user = credentials.split(':')[0] + '@'
                current_dir = response[1]
                state = 'command'
            else:
                print("Server says: {}".format(response[1]))
        elif state == 'command':

            a = input("{}ftp:{}$ ".format(user,current_dir))
            try:
                command,argument = a.split()
            except:
                command,argument = a,""
            argument = argument.strip()
            if not isValidCommand(command):
                print("Unknown command")
                continue
            if command == 'get' and nameIsPresent(argument):
                allow = askForConfirmationForOverride()
                if not allow:
                    command = None
            if command == 'put':
                res = sendCommand(command, argument, clientSocket)
                if not res[0]:
                    allow = askForConfirmationForOverride()
                    if not allow:
                        command = None
                    else:
                        command = 'forced_put'

            if command:
                res = sendCommand(command, argument, clientSocket)
                if command == 'cd' and res[0]:
                    current_dir = res[1]
                elif command == 'cd' and not res[0]:
                    print(res[1])
                elif command == 'ls' and res[0]:
                    print(res[1],end="")
                elif command == 'ls':
                    print(res[1])
                elif command == 'mkdir' and not res[0]:
                    print(res[1])
                elif command == 'rmdir' and not res[0]:
                    print(res[1])
                elif command == 'pwd' and res[0]:
                    print(res[1])
                elif command == 'put' or command == 'forced_put':
                    sendFile(argument, clientSocket)
                elif command == 'get' and res[0]:
                    receiveFile(argument, clientSocket)
                elif command == 'get':
                    print(res[1])
                elif command == 'close' and res[0]:
                    print(res[1])
                    state = 'open'
                    clientSocket.close()
                elif command == 'quit' and res[0]:
                    print(res[1])
                    break