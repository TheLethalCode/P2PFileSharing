import socket
import network
import threading
import sys, os
from queue import Queue
from constants import *
from routingTable import routingTable
from fileSystem import fileSystem

class Node(object):
    
    def __init__(self, bootstrapIP):
        self.GUID = None
        self.routTab = routingTable()
        self.fileSys = fileSystem()
        self.isJoined = False
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind('', APP_PORT)
        self.sock.listen(5)

        self.joinNetwork(bootstrapIP)
        self.eventQue = Queue()
        self.listener = threading.Thread(target=self.listen)
        self.retrieveMsg = threading.Thread(target=self.msgRetriever)

        self.queryDict = {}


    def joinNetwork(self, bootstrapIP):
        network.send_message(JOIN, sender=MY_IP, dest=bootstrapIP)

        while not self.isJoined:
            clientsock, address = self.sock.accept()
            if address[0] != bootstrapIP:
                continue

            data = network.recv_message(clientsock)
            if data[TYPE] != JOIN_ACK:
                continue

            self.routTab.initialise(data[ROUTING], data[SEND_GUID])
            self.GUID = data[DEST_GUID]
            self.isJoined = True

    def listen(self):
        while True:
            clientsock, _ = self.sock.accept()
            handleReq = threading.Thread(target=self.reqHandler, args=(clientsock,))
            handleReq.start()

    def reqHandler(self, clientsock):
        msg = network.recv_message(clientsock)
        if msg:
            self.eventQue.put(msg)

    def msgRetriever(self):
        msg = self.eventQue.get()
        handleMsg = threading.Thread(target=self.msgHandler, args=(msg,))
        handleMsg.start()

    def msgHandler(self, msg):
        if msg[TYPE] == PING:
            pass
        elif msg[TYPE] == PONG:
            pass
        elif msg[TYPE] == QUERY:
            pass
        elif msg[TYPE] == QUERY_RESP:
            pass
        elif msg[TYPE] == TRANSFER_REQ:
            pass
        elif msg[TYPE] == TRANSFER_FILE:
            pass

    def run(self):
        self.listener.start()
        self.retrieveMsg.start()


if __name__ == '__main__':

    if len(sys.argv) != 2:
        print("Incorrect Usage. Pass only the bootstrap IP as a cmdline arg!")
        exit(1)

    peer = Node(sys.argv[1])
    peer.run()
    
    while True:
        cmd = input()
        # TODO
        


