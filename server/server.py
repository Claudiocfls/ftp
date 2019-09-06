from socket import *
from threading import Thread
import sys
import json
import time

credentials = {
    "claudio":"claudio",
    "felipe":"felipe"
}

import subprocess
a = subprocess.check_output(["pwd"])
# print(a.decode(),type(a))


class globalRequests:
    def __init__(self):
        self.list = []

    def add(self, ip, port, mode, filename):
        self.list.append((ip,port,mode,filename))
    
    def get(self, ip, port):
        print("na lista", self.list, ip, port)
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

    def run(self):
        sent = ""
        while True:
            data = self.conn.recv(1024)
            if not data:
                break 
            sentence = data.decode()
            print("Received {} from {}".format(sentence, self.addr))
            received = json.loads(sentence)
            if self.state == 1:
                if received["passwd"] == credentials[received["username"]]:
                    self.conn.send("OKK".encode())
                    # time.sleep(1)
                    # self.conn.send(a)
                else:
                    self.conn.send("ERR".encode())
                self.state = 2
            else:
                if received["command"] == "get":
                    # self.conn.send(a)
                    gRequests.add(self.addr[0], self.addr[1], "download", "image.jpeg")
                    self.conn.send("OKK".encode())
                elif received["command"] == "upl":
                    gRequests.add(self.addr[0], self.addr[1], "upload", "image.jpeg")
                    self.conn.send("OKK".encode())

        self.conn.close()


class TransferWorker(Thread):
    def __init__(self, addr, connection):
        Thread.__init__(self)
        self.conn = connection
        self.addr = addr

    def run(self):
        print("rodando worker")
        mode, filename, ok = gRequests.get(self.addr[0], self.addr[1])
        print(mode,filename)
        if ok:
            if mode == "upload":
                print("modo upload")
                self.receiveFile(self.conn, filename)
                self.conn.close()
            elif mode == "download":
                print("modo download")
                self.sendFile(self.conn, filename)
                self.conn.close()
        else:
            print("ERror")

    def sendFile(self, conn, filename):
        print("starting download")
        f = open(filename,'rb')
        chunk = f.read(1024)
        cont = 0
        while (chunk):
            conn.send(chunk)
            cont += 1
            print('Sent ',repr(chunk))
            chunk = f.read(1024)
        f.close()
        print("Saiu", cont)
    
    def receiveFile(self, conn, filename):
        with open(filename, 'wb') as f:
            print('file opened')
            cont = 0
            print('receiving data...')
            data = conn.recv(1024)
            while data:
                cont += 1
                f.write(data)
                # if cont == 163648:
                    # break
                print(cont)
                data = conn.recv(1024)
            f.close()
            print("acabou", cont)
    
# def handleRequest(request):
#     a = json.loads(request)


def handleNewConnection(addr, connection):
    newThread = Th(addr, connection)
    newThread.start()

def handleNewTransfer(addr, connection):
    print("criando worker de transferencia")
    newWorker = TransferWorker(addr, connection)
    newWorker.start()

# thread = Th(1)
# thread.start()

# print(a)

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
            # if commandQueue.get(addr):
            #     print("Error: connection already exist!")
            # else:
            #     commandQueue[addr] = connectionSocket
            #     print("Thread created {}".format(addr))
            # sentence = connectionSocket.recv(1024).decode()
            # print("Received {} from {} - {}".format(sentence,addr,connectionSocket))
            print("New connection established from {}".format(addr))
            # capitalizedSentence = sentence.upper()
            # connectionSocket.send(capitalizedSentence.encode())

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
            # if commandQueue.get(addr):
            #     print("Error: connection already exist!")
            # else:
            #     commandQueue[addr] = connectionSocket
            #     print("Thread created {}".format(addr))
            # sentence = connectionSocket.recv(1024).decode()
            # print("Received {} from {} - {}".format(sentence,addr,connectionSocket))
            print("New connection established from {} to transfer".format(addr))
            # capitalizedSentence = sentence.upper()
            # connectionSocket.send(capitalizedSentence.encode())

        connectionSocket.close()



# if __name__ == "__main__":
commandServer = CommandServer()
commandServer.start()
transferServer = TransferServer()
transferServer.start()

while True:
    pass


