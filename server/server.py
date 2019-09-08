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

class Th(Thread):
    subtotal = 0
    def __init__ (self, addr, conn):
        # sys.stdout.write("Making thread number " + str(num) + "n")
        # sys.stdout.flush()
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
        self.state = 1
        self.client_pwd = '/'
        self.confirmation_state = 1
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
            if self.state == 1:
                if com == 'login':
                    r = checkCredentials(arg)
                    if r:
                        self.returnSuccess(self.client_pwd)
                        self.state = 3
                    else:
                        self.returnError('Invalid credentials')
                else:
                    self.returnError('Unexpected command')
            elif self.state == 3:
                if com == 'ls':
                    if len(arg) and not self.nameIsPresent(arg):
                        self.returnError('Directory not found')
                    else:
                        lsResult = subprocess.check_output(["ls", self.mountPath(arg)]).decode()
                        self.returnSuccess(lsResult)
                elif com == 'pwd':
                    self.returnSuccess(self.client_pwd)
                elif com == 'mkdir':
                    if self.nameIsPresent(arg):
                        self.returnError("Folder already exist")
                    else:
                        subprocess.call(['mkdir', self.mountPath(arg)])
                        self.returnSuccess(arg)
                elif com == 'cd':
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
                elif com == 'put':
                    if self.nameIsPresent(arg) and self.confirmation_state == 1:
                        self.returnError("File already exist")
                        self.confirmation_state = 2
                    else:
                        self.returnSuccess("File transfer with override")
                        self.confirmation_state = 1
                        self.requestedFile = self.mountPath(arg)
                elif com == 'PUTC':
                    receiveFile(self.conn, self.requestedFile)
                    self.requestedFile = None
                    self.returnSuccess('Transfer completed')
                elif com == 'cancel_put':
                    self.confirmation_state = 1
                    self.returnSuccess('Upload aborted')
                elif com == 'get':
                    if not self.nameIsPresent(arg):
                        self.returnError("File not found in remote server")
                    else:
                        self.requestedFile = self.mountPath(arg)
                        self.returnSuccess("Request completed")
                elif com == 'SEND':
                    sendFile(self.requestedFile, self.conn)
                    self.returnSuccess('Transfer completed')
                    self.requestedFile = None
                elif com == 'delete':
                    if not self.nameIsPresent(arg):
                        self.returnError('File not found')
                    else:
                        a = subprocess.call(['rm', self.mountPath(arg)])
                        self.returnSuccess('File {} deleted!'.format(arg))
                elif com == 'rmdir':
                    if not self.nameIsPresent(arg):
                        self.returnError('Folder not found')
                    else:
                        a = subprocess.call(['rm','-rf', self.mountPath(arg)])
                        self.returnSuccess('Directory deleted')
                elif com == 'close':
                    self.resetConnection()
                    self.returnSuccess('Session closed')
                    self.state = 4
                elif com == 'quit':
                    self.returnSuccess('Connection closed')
                    self.state = 4
                else:
                    self.returnError('Unexpected command')
            
            res = self.createResponse()
            sendResponse(self.conn, res)
            if self.state == 4:
                break
            
        if self.conn:
            self.conn.close()

def checkCredentials(arg):
    user,passw = arg.split(':')
    if credentials.credentials.get(user) and credentials.credentials[user] == passw:
        return True
    return False

def sendResponse(conn, res):
    a = json.dumps(res)
    conn.send(a.encode())

def receiveCommand(conn):
    print("recebendo comando")
    com = conn.recv(1024).decode()
    print("recebido: ",com)
    a = json.loads(com)
    command,argument = a["comm"],a["arg"]
    return command,argument

def wrapPacket(command, payload):
    packet = {
        'status': command,
        'payload': payload 
    }
    packet = json.dumps(packet)
    return packet.encode()

def unwrapPacket(packet):
    a = packet.decode()
    a = json.loads(a)
    return a

def sendFile(filename, conn):
    print("Starting download...")
    f = open(filename, 'rb')
    chunk = f.read(512)
    cont = 0
    while (chunk):
        packet = wrapPacket('DATA', base64.encodebytes(chunk).decode())
        conn.send(packet)
        res = conn.recv(1024)
        cont += 1
        chunk = f.read(512)
    f.close()
    print("Download finished...")

def receiveFile(conn, filename):
    conn.send(wrapPacket('SEND', ''))
    with open(filename, 'wb') as f:
        cont = 0
        print('Receiving data...')
        packet = conn.recv(1024)
        packet = unwrapPacket(packet)
        while packet['comm'] == 'DATA':
            cont += 1
            f.write(base64.decodebytes(packet['arg'].encode()))
            conn.send(wrapPacket('OK',''))
            packet = conn.recv(1024)
            packet = unwrapPacket(packet)
        f.close()
        print("Finished {} kbytes".format(cont/2))

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
        serverSocket.listen(2)
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
