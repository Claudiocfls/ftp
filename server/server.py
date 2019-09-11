from socket import *
from threading import Thread
import sys
import json
import time
import config
import credentials
import subprocess
import base64

DEFAULT_SERVER_PORT = 2121
SIMULTANEOUS_CONNECTIONS = 3
ENDMARK = '  '
END_OF_FILE = chr(0).encode()

class Th(Thread):
    subtotal = 0
    def __init__ (self, addr, conn):
        Thread.__init__(self)
        self.conn = conn
        self.addr = addr
        self.server_pwd = config.BASEDIR
        self.resetConnection()
        self.status = ''
        self.payload = ''

    def nameIsPresent(self, filename):
        files = subprocess.check_output(["ls", self.server_pwd + self.client_pwd]).decode().split('\n')
        return filename in files
    
    def mountPath(self, filename):
        slash = ''
        if self.client_pwd[-1] != '/':
            slash = '/'
        path = self.server_pwd + self.client_pwd + slash + filename
        return path

    def resetConnection(self):
        self.state = 'not_logged'
        self.client_pwd = '/'
        self.requestedFile = None
    
    def returnError(self, message):
        self.status = 'ER'
        self.payload = message
    
    def returnSuccess(self, message):
        self.status = 'OK'
        self.payload = message
    
    def createResponse(self):
        return {
            'status': self.status,
            'payload': self.payload
        }

    def run(self):
        while runThreads:
            com,arg = receiveCommand(self.conn)
            if self.state == 'not_logged':
                if com == 'LG':
                    r = checkCredentials(arg)
                    if r:
                        self.returnSuccess(self.client_pwd)
                        self.state = 'logged'
                    else:
                        self.returnError('Invalid credentials')
                else:
                    self.returnError('Unexpected command')
            elif self.state == 'logged':
                if com == 'LS':
                    if len(arg) and not self.nameIsPresent(arg):
                        self.returnError('Directory not found')
                    else:
                        lsResult = subprocess.check_output(["ls", self.mountPath(arg)]).decode()
                        self.returnSuccess(lsResult)
                elif com == 'PW':
                    self.returnSuccess(self.client_pwd)
                elif com == 'MK':
                    if self.nameIsPresent(arg):
                        self.returnError("Folder already exist")
                    else:
                        subprocess.call(['mkdir', self.mountPath(arg)])
                        self.returnSuccess(arg)
                elif com == 'CD':
                    if arg == '..' and self.client_pwd == '/':
                        self.returnError('Directory not found')
                    elif arg == '..':
                        tempDir = self.client_pwd[-1::-1]
                        slashIndex = tempDir.index('/')
                        tempDir = tempDir[slashIndex:]
                        self.client_pwd = tempDir[-1::-1]
                        if len(self.client_pwd) != 1:
                            self.client_pwd = self.client_pwd[:-1]
                        self.returnSuccess(self.client_pwd)
                    else:
                        if not self.nameIsPresent(arg):
                            self.returnError('Directory not found')
                        elif self.client_pwd[-1] == '/':
                            self.client_pwd += arg 
                            self.returnSuccess(self.client_pwd)
                        else:
                            self.client_pwd += '/' + arg
                            self.returnSuccess(self.client_pwd)
                elif com == 'PT':
                    if self.nameIsPresent(arg):
                        self.returnError("File already exist")
                    else:
                        self.requestedFile = self.mountPath(arg)
                elif com == 'FP':
                    self.requestedFile = self.mountPath(arg)
                    if self.nameIsPresent(arg):
                        self.returnSuccess("Transfer with overwrite")
                    else:
                        self.returnSuccess("Common transfer")
                elif com == 'SF':
                    receiveFile(self.conn, self.requestedFile)
                    self.requestedFile = None
                    self.returnSuccess('Transfer completed')
                elif com == 'GT':
                    if not self.nameIsPresent(arg):
                        self.returnError("File not found in remote server")
                    else:
                        self.requestedFile = self.mountPath(arg)
                        self.returnSuccess("Request completed")
                elif com == 'GF':
                    sendFile(self.requestedFile, self.conn)
                    self.returnSuccess('Transfer completed')
                    self.requestedFile = None
                elif com == 'DL':
                    if not self.nameIsPresent(arg):
                        self.returnError('File not found')
                    else:
                        a = subprocess.call(['rm', self.mountPath(arg)])
                        self.returnSuccess('File {} deleted!'.format(arg))
                elif com == 'RM':
                    if not self.nameIsPresent(arg):
                        self.returnError('Folder not found')
                    else:
                        a = subprocess.call(['rm','-rf', self.mountPath(arg)])
                        self.returnSuccess('Directory deleted')
                elif com == 'CL':
                    self.resetConnection()
                    self.returnSuccess('Session closed')
                    self.state = 'finish'
                elif com == 'QT':
                    self.returnSuccess('Connection closed')
                    self.state = 'finish'
                else:
                    self.returnError('Unexpected command')
            
            res = self.createResponse()
            sendResponse(self.conn, res)
            if self.state == 'finish':
                break
            
        if self.conn:
            print("Closing connection {}".format(self.addr))
            self.conn.close()

def checkCredentials(arg):
    user,passw = arg.split(':')
    if credentials.credentials.get(user) and credentials.credentials[user] == passw:
        return True
    return False

def sendResponse(conn, res):
    payload = pad(res["status"] + res["payload"])
    while len(payload):
        conn.send(payload[:2].encode())
        conn.recv(51)
        payload = payload[2:]
    conn.send(ENDMARK.encode())

def pad(string):
    return string + ' ' if len(string)%2 else string

def unpad(string):
    if len(string):
        return string[:-1] if string[-1] == ' ' else string
    return ''

def receiveCommand(conn):
    buffer = ''
    while True:
        a = conn.recv(51).decode()
        if a == ENDMARK:
            break
        conn.send('OK'.encode())
        buffer += a

    command = buffer[:2]
    argument = unpad(buffer[2:])

    return command, argument

def sendFile(filename, conn):
    print("Sending file...")
    f = open(filename, 'rb')
    chunk = f.read(51)
    while (chunk):
        conn.send(chunk)
        conn.recv(51)
        chunk = f.read(51)
    f.close()
    conn.send(END_OF_FILE)
    conn.recv(51)
    print("Transfer completed!")

def receiveFile(conn, filename):
    conn.send('SF'.encode())
    with open(filename, 'wb') as f:
        cont = 0
        print('Receiving data...')
        chunk = conn.recv(51)
        while chunk != END_OF_FILE:
            f.write(chunk)
            conn.send('OK'.encode())
            chunk = conn.recv(51)
        f.close()
        print("Finished")

def handleNewConnection(addr, connection):
    newThread = Th(addr, connection)
    newThread.start()

class CommandServer(Thread):
    def __init__(self):
        Thread.__init__(self)

    def run(self):
        serverPort = DEFAULT_SERVER_PORT
        serverSocket = socket(AF_INET,SOCK_STREAM)
        serverSocket.bind(('',serverPort))
        serverSocket.listen(SIMULTANEOUS_CONNECTIONS)
        print('Server is running at port {}'.format(serverPort))
        while True:
            connectionSocket, addr = serverSocket.accept()
            handleNewConnection(addr, connectionSocket)
            connectionSocket = None
            print("New connection established from {}".format(addr))
        serverSocket.close()

if __name__ == '__main__':
    runThreads = True

    serverPort = DEFAULT_SERVER_PORT
    serverSocket = socket(AF_INET,SOCK_STREAM)
    serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    serverSocket.bind(('',serverPort))
    serverSocket.listen(2)
    print('Server is running at port {}'.format(serverPort))
    while True:
        try:
            connectionSocket, addr = serverSocket.accept()
            handleNewConnection(addr, connectionSocket)
            connectionSocket = None
            print("New connection established from {}".format(addr))
        except KeyboardInterrupt:
            serverSocket.close()
            runThreads = False
            break
