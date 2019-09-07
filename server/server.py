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
        self.state = 1
        self.server_pwd = config.BASEDIR
        self.client_pwd = '/'

    def run(self):
        while True:
            try:
                com,arg = receiveCommand(self.conn)
                payload = ''
                status = 'OK'
                if self.state == 1:
                    if com == 'open':
                        status = 'OK'
                        payload = 'Send credentials'
                        self.state = 2
                    else:
                        status = 'ER'
                        payload = 'unexpected command'
                elif self.state == 2:
                    if com == 'login':
                        r = checkCredentials(arg)
                        if r:
                            status = 'OK'
                            payload = self.client_pwd
                            self.state = 3
                        else:
                            status = 'ER'
                            payload = 'Invalid'
                    else:
                        status = 'ER'
                        payload = 'unexpected command'
                elif self.state == 3:
                    if com == 'ls':
                        payload = subprocess.check_output(["ls", self.server_pwd + self.client_pwd]).decode()
                    elif com == 'pwd':
                        payload = self.client_pwd
                    elif com == 'mkdir':
                        slash = ''
                        if self.client_pwd[-1] != '/':
                            slash = '/'
                        subprocess.call(['mkdir',self.server_pwd + self.client_pwd + slash + arg])
                        payload = arg
                    elif com == 'cd':
                        if arg == '..' and self.client_pwd == '/':
                            status = 'ER'
                        elif arg == '..':
                            tempDir = self.client_pwd[-1::-1]
                            slashIndex = tempDir.index('/')
                            tempDir = tempDir[slashIndex:]
                            self.client_pwd = tempDir[-1::-1]
                            if len(self.client_pwd) != 1:
                                self.client_pwd = self.client_pwd[:-1]
                        else:
                            files = subprocess.check_output(["ls", self.server_pwd + self.client_pwd]).decode().split('\n')
                            print(files)
                            if arg not in files:
                                status = 'ER'
                                payload = 'Folder not found'
                            elif self.client_pwd[-1] == '/':
                                self.client_pwd += arg 
                            else:
                                self.client_pwd += '/' + arg
                        if status == 'OK':
                            payload = self.client_pwd
                    elif com == 'put':
                        slash = ''
                        if self.client_pwd[-1] != '/':
                            slash = '/'
                        gRequests.add(self.addr[0], self.addr[1], "upload", self.server_pwd + self.client_pwd + slash + arg)
                    elif com == 'get':
                        slash = ''
                        if self.client_pwd[-1] != '/':
                            slash = '/'
                        gRequests.add(self.addr[0], self.addr[1], "download", self.server_pwd + self.client_pwd + slash + arg)
                    elif com == 'delete':
                        slash = ''
                        if self.client_pwd[-1] != '/':
                            slash = '/'
                        a = subprocess.call(['rm',self.server_pwd + self.client_pwd + slash + arg])
                    elif com == 'rmdir':
                        slash = ''
                        if self.client_pwd[-1] != '/':
                            slash = '/'
                        a = subprocess.call(['rm','-rf', self.server_pwd + self.client_pwd + slash + arg])
                    elif com == 'close':
                        self.state = 1
                        self.client_pwd = '/'
                        status = 'OK'
                        payload = 'Session closed'
                    elif com == 'quit':
                        status = 'OK'
                        payload = 'Connection closed'
                        self.state = 4
                    else:
                        status = 'ER'
                        payload = 'Unexpected command'
                
                res = {
                    'status': status,
                    'payload': payload
                }
                sendResponse(self.conn, res)
                if self.state == 4:
                    break
            except KeyboardInterrupt:
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
