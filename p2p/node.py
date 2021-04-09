import socket
import network
import threading
import sys, os
from queue import Queue
from constants import *
from routingTable import routingTable
from fileSystem import fileSystem

# TODO:- Limit the number of threads to a specific amount

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

        # Responses for query
        self.queryRes = {}
        self.queryResLock = threading.RLock()

        # Chunks to be requested
        self.chunkLeft = {}
        self.chunkLeftLock = threading.RLock()


    def joinNetwork(self, bootstrapIP):
        joinMsg = {
            TYPE: JOIN,
            SEND_IP: MY_IP,
            DEST_IP: bootstrapIP,
        }
        network.send_message(bootstrapIP, **joinMsg)

        while not self.isJoined:
            clientsock, address = self.sock.accept()
            if address[0] != bootstrapIP:
                continue

            data = network.recv_message(clientsock)
            if data[TYPE] != JOIN_ACK:
                continue

            self.routTab.initialise(data[ROUTING], data[SEND_GUID])   # ROUT_ROB
            self.GUID = data[DEST_GUID]
            self.isJoined = True

    def run(self):
        self.listener.start()
        self.retrieveMsg.start()

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
            pongMsg = {
                TYPE: PONG,
                SEND_IP: MY_IP,
                SEND_GUID: self.GUID,
                DEST_IP: msg[SEND_IP],
                DEST_GUID: msg[SEND_GUID]
            }
            network.send_message(msg[SEND_IP], **pongMsg)
            self.routTab.handlePing(msg)   # ROUT_ROB

        elif msg[TYPE] == PONG:
            self.routTab.handlePong(msg)   # ROUT_ROB

        elif msg[TYPE] == QUERY:
            # TODO:- Handle Repeated Query
            results = self.fileSys.search(msg[SEARCH])  #FILESYS_SAT
            if results:
                reponseMsg = {
                    TYPE: QUERY_RESP,
                    SEND_IP: MY_IP,
                    SEND_GUID: self.GUID,
                    DEST_IP: msg[SOURCE_IP],
                    DEST_GUID: msg[SOURCE_GUID],
                    QUERY_ID: msg[QUERY_ID],
                    RESULTS: results
                }
                network.send_message(msg[SOURCE_IP], **reponseMsg)
            
            for neighbours in self.routTab.neighbours():   # ROUT_ROB
                msg[DEST_IP] = neighbours[0]
                msg[DEST_GUID] = neighbours[1]
                if msg[DEST_GUID] != msg[SEND_GUID]:
                    network.send_message(msg[DEST_IP], **msg)

        elif msg[TYPE] == QUERY_RESP:
            with self.queryResLock:
                if msg[QUERY_ID] in self.queryRes:
                    self.queryRes[msg[QUERY_ID]].append(msg)
            
        elif msg[TYPE] == TRANSFER_REQ:
            fileTranMsg = {
                TYPE: TRANSFER_FILE,
                SEND_IP: MY_IP,
                SEND_GUID: self.GUID,
                DEST_IP: msg[SEND_IP],
                DEST_GUID: msg[DEST_GUID],
                REQUEST_ID: msg[REQUEST_ID],
                CONTENT: self.fileSys.getContent(msg[FILE_ID], msg[CHUNK_NO])   #FILESYS_SAT
            }
            network.send_message(msg[SEND_IP], **fileTranMsg)

        elif msg[TYPE] == TRANSFER_FILE:
            with self.chunkLeftLock:
                if msg[CHUNK_NO] in self.chunkLeft.get(msg[REQUEST_ID], set()) \
                    and self.fileSys.writeChunk(msg):                       #FILESYS_SAT
                    self.chunkLeft[msg[REQUEST_ID]].remove(msg[CHUNK_NO])



if __name__ == '__main__':

    if len(sys.argv) != 2:
        print("Incorrect Usage. Pass only the bootstrap IP as a cmdline arg!")
        exit(1)

    peer = Node(sys.argv[1])
    peer.run()
    
    while True:
        cmd = input()
        # TODO
        


