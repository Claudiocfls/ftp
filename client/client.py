import sys
from getpass import getpass
from socket import *
import json
import time
import subprocess

serverName = '0.0.0.0'
serverPort = 12000

DEFAULT_SERVER_NAME = '0.0.0.0'
DEFAULT_SERVER_PORT = 2121
DEFAULT_CLIENT_PORT = 12000

serverName = ''
serverPort = 0
clientControlPort = 0
clientTransferPort = 0


def promptCredentials():
    username = input("username: ")
    passwd = getpass("password: ")
    return username+':'+passwd

def sendCommand(command, argument, conn):
    packet = {
        'comm': command,
        'arg': argument 
    }
    packet = json.dumps(packet)
    conn.sendall(packet.encode())
    response = conn.recv(1024).decode()
    response = json.loads(response)
    if response['status'] == 'OK':
        return True,response['payload']
    return False,response['payload']

def openConnection(serverAddress, isTransfer = False):
    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    clientPort = clientControlPort if not isTransfer else clientTransferPort
    clientSocket.bind(('0.0.0.0', clientPort))
    print(serverAddress)
    clientSocket.connect(serverAddress)
    return clientSocket

def receiveFile(filename):
    transferSocket = openConnection((serverName, DEFAULT_SERVER_PORT+1), True)
    with open(filename, 'wb') as f:
        print('file opened')
        cont = 0
        print('receiving data...')
        data = transferSocket.recv(1024)
        while data:
            cont += 1
            f.write(data)
            data = transferSocket.recv(1024)
        f.close()
        print("Finishid")
    transferSocket.close()

def sendFile(filename):
    print("Starting upload...")
    transferSocket = openConnection((serverName, DEFAULT_SERVER_PORT+1), True)
    f = open(filename,'rb')
    chunk = f.read(1024)
    cont = 0
    while (chunk):
        transferSocket.send(chunk)
        cont += 1
        chunk = f.read(1024)
    f.close()
    transferSocket.close()
    print("Upload completed!", cont)

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
    clientTransferPort = clientControlPort + 1
    print(" *** File Transfer System *** ")
    print("Control port: ", clientControlPort)
    print("Transfer port: ",clientTransferPort)
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

            if command == 'get' and nameIsPresent(argument):
                allow = askForConfirmationForOverride()
                if not allow:
                    command = None
            if command == 'put':
                res = sendCommand(command, argument, clientSocket)
                if not res[0]:
                    allow = askForConfirmationForOverride()
                    if not allow:
                        command = 'cancel_put'

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
                elif command == 'put':
                    sendFile(argument)
                elif command == 'cancel_put' and res[0]:
                    print(res[1])
                elif command == 'get' and res[0]:
                    receiveFile(argument)
                elif command == 'get':
                    print(res[1])
                elif command == 'close' and res[0]:
                    print(res[1])
                    state = 'open'
                    clientSocket.close()
                elif command == 'quit' and res[0]:
                    print(res[1])
                    break