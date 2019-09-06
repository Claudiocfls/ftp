import sys
from getpass import getpass
from socket import *
import json
import time

serverName = '0.0.0.0'
serverPort = 12000

status = 1

def promptCredentials():
    username = input("username: ")
    passwd = getpass("password: ")
    return {
        "type": "login",
        "username": username,
        "passwd": passwd
    }

def openConnection(serverAddress):
    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.connect(serverAddress)
    return clientSocket

def sendToServer(conn, message):
    conn.send(json.dumps(message).encode())

def receiveFile():
    transferSocket = openConnection((serverName, 12001))
    with open('received_file.jpeg', 'wb') as f:
        print('file opened')
        cont = 0
        print('receiving data...')
        data = transferSocket.recv(1024)
        while data:
            cont += 1
            f.write(data)
            # if cont == 163648:
                # break
            print(cont)
            data = transferSocket.recv(1024)
        f.close()
        print("acabou", cont)

def sendFile():
    print("starting upload")
    transferSocket = openConnection((serverName, 12001))
    f = open('received_file.jpeg','rb')
    chunk = f.read(1024)
    cont = 0
    while (chunk):
        transferSocket.send(chunk)
        cont += 1
        print('Sent ',repr(chunk))
        chunk = f.read(1024)
    f.close()
    print("Saiu", cont)


        # print('data=%s', (data))
        # if not data:
        #     break
        # write data to a file

if __name__ == "__main__":
    # print("hell0")
    # print(sys.argv)
    clientSocket = openConnection((serverName, serverPort))
    while status == 1:
        credentialsPayload = promptCredentials()
        clientSocket.send(json.dumps(credentialsPayload).encode())
        res = clientSocket.recv(1024).decode()
        if res != "OKK":
            print("access denied!")
        else: 
            status = 2
            print("access granted!")
    while True:
        a = input("ftp:/$ ")
        sendToServer(clientSocket, {"command": a})
        if a == "get":
            receiveFile()
        elif a == "upl":
            sendFile()
        # print(clientSocket.recv(1024).decode())

    while True:
        pass
