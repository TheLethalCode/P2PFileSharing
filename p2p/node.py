import socket
import network
import threading
import time
import copy
import sys, os
from constants import *
from routingTable import routingTable
from fileSystem import fileSystem

# TODO:- Limit the number of threads to a specific amount
# TODO:- Garbage collection of expired results, queries, transfer requests (Or keep a limit)
# TODO:- Save state periodically and load
# TODO:- Make the transfer for each thread faster by using an intermediate signal of sorts
# without waiting for the timeout and recheck

class Node(object):
    
    def __init__(self):

        self.GUID = None
        self.routTab = routingTable()
        self.fileSys = fileSystem()
        self.isJoined = False
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind('', APP_PORT)
        self.sock.listen(5)

        # Listen at the APP_PORT
        self.listener = threading.Thread(target=self.listen)

        # Responses for query
        self.queryCnt = 0
        self.queryRes = {}
        self.queryResLock = threading.RLock()

        # Chunks to be requested | chunkLeft[qId] = (num_chunks, set(chunks left))
        self.chunkLeft = {}
        self.chunkLeftLock = threading.RLock()

        # Repeated queries
        self.repQuer = set()
        self.repQuerLock = threading.RLock()

    # Load Saved State
    def load_state(self):
        pass

    def joinNetwork(self, bootstrapIP):
        joinMsg = {
            TYPE: JOIN,
            SEND_IP: MY_IP,
            DEST_IP: bootstrapIP,
        }
        network.send(bootstrapIP, **joinMsg)

        while not self.isJoined:
            clientsock, address = self.sock.accept()
            if address[0] != bootstrapIP:
                continue

            data = network.receive(clientsock)
            if data[TYPE] != JOIN_ACK:
                continue

            self.routTab.initialise(data[ROUTING], data[SEND_GUID])   # ROUT_ROB
            self.GUID = data[DEST_GUID]
            self.isJoined = True

    # Join the network and start the listener thread
    def run(self, bootstrapIP = None):
        if not self.isJoined:
            if bootstrapIP is None:
                print("Error! Need Bootstrap IP")
                return
            self.joinNetwork(bootstrapIP)
        self.listener.start()

    # Keeps listening and creates separate threads to handle messages
    def listen(self):
        while True:
            clientsock, _ = self.sock.accept()
            handleMsg = threading.Thread(target=self.msgHandler, args=(clientsock,))
            handleMsg.start()

    # Handles the different type of incoming message
    def msgHandler(self, clientsock):
        msg = network.receive(clientsock)
        
        if msg is None:
            return

        if msg[TYPE] == PING:
            pongMsg = {
                TYPE: PONG,
                SEND_IP: MY_IP,
                SEND_GUID: self.GUID,
                DEST_IP: msg[SEND_IP],
                DEST_GUID: msg[SEND_GUID]
            }
            network.send(msg[SEND_IP], **pongMsg)
            self.routTab.handlePing(msg)   # ROUT_ROB

        elif msg[TYPE] == PONG:
            self.routTab.handlePong(msg)   # ROUT_ROB

        elif msg[TYPE] == QUERY:
            # Check whether the query is repeated
            with self.repQuerLock:
                ok = msg[QUERY_ID] in self.repQuer
            
            # If not repeated search database and forward query
            if not ok:                
                results = self.fileSys.search(msg[SEARCH])  #FILESYS_SAT

                if bool(results):
                    reponseMsg = {
                        TYPE: QUERY_RESP,
                        SEND_IP: MY_IP,
                        SEND_GUID: self.GUID,
                        DEST_IP: msg[SOURCE_IP],
                        DEST_GUID: msg[SOURCE_GUID],
                        QUERY_ID: msg[QUERY_ID],
                        RESULTS: results
                    }
                    network.send(msg[SOURCE_IP], **reponseMsg)
                
                with self.repQuerLock:
                    self.repQuer.add(msg[QUERY_ID])

                for neighbours in self.routTab.neighbours():   # ROUT_ROB
                    msg[DEST_IP] = neighbours[0]
                    msg[DEST_GUID] = neighbours[1]
                    if msg[DEST_GUID] != msg[SEND_GUID]:
                        network.send(msg[DEST_IP], **msg)

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
            network.send(msg[SEND_IP], **fileTranMsg)

        elif msg[TYPE] == TRANSFER_FILE:
            # Acquire Lock
            with self.chunkLeftLock:
                
                # If the request is not yet done and the write to the file system is successful
                if msg[CHUNK_NO] in self.chunkLeft.get(msg[REQUEST_ID], (0, set()))[1] \
                    and self.fileSys.writeChunk(msg):                       #FILESYS_SAT

                    self.chunkLeft[msg[REQUEST_ID]][1].remove(msg[CHUNK_NO])

                    # If all the chunks are done, inform filesys of the completion
                    if not bool(self.chunkLeft[msg[REQUEST_ID]][1]):
                        self.fileSys.done(msg[REQUEST_ID])                  #FILESYS_SAT
                        del self.chunkLeft[msg[REQUEST_ID]]

    # Function for a thread to use for requesting transfer of content
    def requestTransfer(self, tid, numChunks, msg):
        start = tid
        while start < numChunks:
            ok = True
            msg[CHUNK_NO] = start
            while ok:
                network.send(msg[DEST_IP], **msg)
                time.sleep(15)
                with self.chunkLeftLock:
                    ok = (start in self.chunkLeft[msg[REQUEST_ID]][1])
            start += NUM_THREADS

    # Sends a Query for the required content to all its neighbours
    def findContent(self, searchQ):

        qId = network.generateId(self.GUID, self.queryCnt)
        print("Query Id: {}".format(qId))

        with self.queryResLock:
            self.queryRes[qId] = []
        
        queryMsg = {
            TYPE: QUERY,
            SEND_IP: MY_IP,
            SEND_GUID: self.GUID,
            SOURCE_IP: MY_IP,
            SOURCE_GUID: self.GUID,
            SEARCH: searchQ,
            QUERY_ID: qId
        }
        self.queryCnt += 1

        for neighbours in self.routTab.neighbours():   # ROUT_ROB
                queryMsg[DEST_IP] = neighbours[0]
                queryMsg[DEST_GUID] = neighbours[1]
                network.send(queryMsg[DEST_IP], **queryMsg)

    # Displays the results received till now
    def displayResults(self, qId):
        with self.queryResLock:
            for ind, results in enumerate(self.queryRes[qId]):
                print("Peer {}".format(ind + 1))
                
                for ind1, result in enumerate(results[RESULTS]):
                    print("\tResult {}".format(ind1 + 1))
                    print("\t{}".format(result))
                    print("---------------------\n")

                print("\n===================\n")


    # Choose the desired response for file transfer
    def chooseResults(self, qId, peerNum, resNum):
        try:
            with self.queryResLock:
                result = self.queryRes[qId][peerNum]
        except (KeyError, IndexError):
            print("Invalid arguments.")
            return
        
        transferReq = {
            TYPE: TRANSFER_REQ,
            SEND_IP: MY_IP,
            SEND_GUID: self.GUID,
            DEST_IP: result[SEND_IP],
            DEST_GUID: result[SEND_GUID],
            REQUEST_ID: qId,
            FILE_ID: result[RESULTS][resNum][FILE_ID]        # FILESYS_SAT
        }

        numChunks = result[RESULTS][resNum][NUM_CHUNKS]         # FILESYS_SAT
        with self.chunkLeftLock:
            self.chunkLeft[qId] = (numChunks, set())
            for i in range(numChunks):
                self.chunkLeft[qId][1].add(i)

        for ind in range(NUM_THREADS):
            reqCopy = copy.deepcopy(transferReq)
            thr = threading.Thread(target=self.requestTransfer, 
                            args=(ind, numChunks, reqCopy))
            thr.start()

    # Check the progress of the transfer
    def checkProgress(self, qId):
        with self.chunkLeftLock:
            prog = self.chunkLeft.get(qId, None)
        
        if prog is not None:
            print("Done {} / {}".format(prog[0] - len(prog[1]), prog[0]))
        elif self.fileSys.isFinished(qId):          # FILESYS_SAT
            print("Download finished")
        else:
            print("Incorrect ID")


def parseCmds(cmd):
    pass


if __name__ == '__main__':

    peer = Node()
    peer.load_state()

    bootstrapIP = None
    if not peer.isJoined:
        bootstrapIP = input("Bootstrap IP: ")

    peer.run(bootstrapIP)

    while True:
        cmd = input(">").split()
        parseCmds(cmd)


