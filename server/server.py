from socket import *
from threading import Thread
import sys
import json
import time
import config
import credentials
import subprocess

a = subprocess.check_output(["pwd"])
# print(a.decode(),type(a))

class globalRequests:
    def __init__(self):
        self.list = []

    def add(self, ip, port, mode, filename):
        self.list.append((ip,port,mode,filename))
    
    def get(self, ip, port):
        for i in range(len(self.list)):
            if self.list[i][0] == ip:
                a = self.list[i][2]
                b = self.list[i][3]
                print(a,b)
                del self.list[i]
                return a,b,True 
        return None, None, False

gRequests = globalRequests()

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
        while True:
            try:
                com,arg = receiveCommand(self.conn)
                if self.state == 1:
                    if com == 'open':
                        self.returnSuccess('Send credentials')
                        self.state = 2
                    else:
                        self.returnError('Unexpected command')
                elif self.state == 2:
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
                        gRequests.add(self.addr[0], self.addr[1], "upload", self.mountPath(arg))
                    elif com == 'get':
                        gRequests.add(self.addr[0], self.addr[1], "download", self.mountPath(arg))
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
                    elif com == 'quit':
                        self.returnSuccess('Connection closed')
                        self.state = 4
                    else:
                        self.returnError('Unexpected command')
                
                res = self.createResponse()
                sendResponse(self.conn, res)
                if self.state == 4:
                    break
            except KeyboardInterrupt:
                print("CTRL C DETECTED")
                break

        self.conn.close()

def checkCredentials(arg):
    user,passw = arg.split(':')
    if credentials.credentials[user] == passw:
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

def receiveArgument(conn):
    # conn.settimeout(2)
    print("timeout padrao ",conn.gettimeout())
    print("recebendo argumento")
    serverResponse = ''.encode()
    while True:
        try:
            res = conn.recv(1024)
            serverResponse += res
        except:
            break
        print("recebido",res.decode(), sys.getsizeof(res))
    print("argumento decodificado: {}".format(serverResponse.decode()))

class TransferWorker(Thread):
    def __init__(self, addr, connection):
        Thread.__init__(self)
        self.conn = connection
        self.addr = addr

    def run(self):
        mode, filename, ok = gRequests.get(self.addr[0], self.addr[1])
        print(mode,filename)
        if ok:
            if mode == "upload":
                self.receiveFile(self.conn, filename)
                self.conn.close()
            elif mode == "download":
                self.sendFile(self.conn, filename)
                self.conn.close()
        else:
            print("ERror")

    def sendFile(self, conn, filename):
        print("starting download...")
        f = open(filename, 'rb')
        chunk = f.read(1024)
        cont = 0
        while (chunk):
            conn.send(chunk)
            cont += 1
            # print('Sent ',repr(chunk))
            chunk = f.read(1024)
        f.close()
        print("Download finished...")
    
    def receiveFile(self, conn, filename):
        with open(filename, 'wb') as f:
            print('file opened')
            cont = 0
            print('Receiving data...')
            data = conn.recv(1024)
            while data:
                cont += 1
                f.write(data)
                # if cont == 163648:
                    # break
                print(cont)
                data = conn.recv(1024)
            f.close()
            print("Finished", cont)

def handleNewConnection(addr, connection):
    newThread = Th(addr, connection)
    newThread.start()

def handleNewTransfer(addr, connection):
    newWorker = TransferWorker(addr, connection)
    newWorker.start()

class CommandServer(Thread):
    def __init__(self):
        Thread.__init__(self)

    def run(self):
        serverPort = 12000
        serverSocket = socket(AF_INET,SOCK_STREAM)
        serverSocket.bind(('',serverPort))
        serverSocket.listen(2)
        print('Server is running at port {}'.format(serverPort))
        while True:
            connectionSocket, addr = serverSocket.accept()
            handleNewConnection(addr, connectionSocket)
            connectionSocket = None
            print("New connection established from {}".format(addr))

        connectionSocket.close()


class TransferServer(Thread):
    def __init__(self):
        Thread.__init__(self)

    def run(self):
        serverPort = 12001
        serverSocket = socket(AF_INET,SOCK_STREAM)
        serverSocket.bind(('',serverPort))
        serverSocket.listen(2)
        print('TransferServer is running at port {}'.format(serverPort))
        while True:
            connectionSocket, addr = serverSocket.accept()
            handleNewTransfer(addr, connectionSocket)
            print("New connection established from {} to transfer".format(addr))

        connectionSocket.close()

# if __name__ == "__main__":
commandServer = CommandServer()
commandServer.start()
transferServer = TransferServer()
transferServer.start()
