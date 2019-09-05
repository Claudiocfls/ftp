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
    clientSocket.connect((serverName,serverPort))
    return clientSocket

def sendToServer(conn, message):
    conn.send(json.dumps(message).encode())

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
        sendToServer(clientSocket, {"command": "ls"})
        print(clientSocket.recv(1024).decode())

    while True:
        pass
