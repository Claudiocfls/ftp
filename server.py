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
                    time.sleep(1)
                    self.conn.send(a)
                else:
                    self.conn.send("ERR".encode())
                self.state = 2
            else:
                if received["command"] == "get":
                    # self.conn.send(a)
                    sendFile(self.conn, "image.jpeg")

        self.conn.close()




# def handleRequest(request):
#     a = json.loads(request)

def sendFile(conn, filename):
    f = open(filename,'rb')
    chunk = f.read(1024)
    while chunk:
       conn.send(chunk)
    #    print('Sent ',repr(l))
       chunk = f.read(1024)
       print(chunk)
    f.close()


def handleNewConnection(addr, connection):
    newThread = Th(addr, connection)
    newThread.start()

# thread = Th(1)
# thread.start()

# print(a)

if __name__ == "__main__":
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
        print("New connection established")
        # capitalizedSentence = sentence.upper()
        # connectionSocket.send(capitalizedSentence.encode())

    connectionSocket.close()
