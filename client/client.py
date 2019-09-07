import sys
from getpass import getpass
from socket import *
import json
import time

serverName = '0.0.0.0'
serverPort = 12000

def promptCredentials():
    username = input("username: ")
    passwd = getpass("password: ")
    return username+':'+passwd

# def pad(a):
#     if len(a)%2 == 0:
#         return a
#     else:
#         return a + ' '

# def unpad(a):
#     if a[-1] == ' ':
#         return a[:-1]
#     else:
#         return a 

def sendCommand(command, argument, conn):
    packet = {
        'comm': command,
        'arg': argument 
    }
    packet = json.dumps(packet)
    conn.sendall(packet.encode())
    response = conn.recv(1024).decode()
    response = json.loads(response)
    # print("respondido ",response)
    if response['status'] == 'OK':
        return True,response['payload']
    return False,response['payload']


def openConnection(serverAddress, isTransfer = False):
    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    clientPort = 13000 if not isTransfer else 13001
    clientSocket.bind(('0.0.0.0', clientPort))
    clientSocket.connect(serverAddress)
    return clientSocket

# def sendToServer(conn, message):
#     conn.send(json.dumps(message).encode())

def receiveFile(filename):
    transferSocket = openConnection((serverName, 12001), True)
    with open(filename, 'wb') as f:
        print('file opened')
        cont = 0
        print('receiving data...')
        data = transferSocket.recv(1024)
        while data:
            cont += 1
            f.write(data)
            # if cont == 163648:
                # break
            # print(cont)
            data = transferSocket.recv(1024)
        f.close()
        print("acabou", cont)
    transferSocket.close()

def sendFile(filename):
    print("Starting upload...")
    transferSocket = openConnection((serverName, 12001), True)
    f = open(filename,'rb')
    chunk = f.read(1024)
    cont = 0
    while (chunk):
        transferSocket.send(chunk)
        cont += 1
        # print('Sent ',repr(chunk))
        chunk = f.read(1024)
    f.close()
    transferSocket.close()
    print("Upload completed!", cont)

if __name__ == "__main__":
    # print(sys.argv)
    clientSocket = openConnection((serverName, serverPort))
    print(" *** File Transfer System *** ")
    print("Control port: ", 13000)
    print("Transfer port: ", 13001)
    current_dir = '/'
    state = 'open'
    user = ''
    while True:
        if state == 'open':
            a = input("> ")
            if a != 'open':
                print("Session not stablished. Type 'open' to initiate a connection.")
            else:
                response = sendCommand('open', '', clientSocket)
                if response[0]:
                    state = 'login'
                else:
                    print("Server says: {}".format(response[1]))
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
            
            res = sendCommand(command, argument, clientSocket)
            if command == 'cd' and res[0]:
                current_dir = res[1]
            elif command == 'cd' and not res[0]:
                print(res[1])
            elif command == 'ls' and res[0]:
                print(res[1],end="")
            elif command == 'pwd' and res[0]:
                print(res[1])
            elif command == 'put':
                sendFile(argument)
            elif command == 'get':
                receiveFile(argument)
            elif command == 'close' and res[0]:
                print(res[1])
                state = 'open'
            elif command == 'quit' and res[0]:
                print(res[1])
                break