import socket
import threading
import time
import copy
import sys
import os
import queue
import network
from constants import *
from routingTable import routingTable
from fileSystem import fileSystem

# TODO:- Save state periodically and load
# TODO:- Error Handling and logging

class Node(object):

    def __init__(self, isBootstrap=False):

        self.routTab = routingTable()
        self.fileSys = fileSystem()

        # Handle the case of bootstrapping node
        self.isJoined = isBootstrap
        if isBootstrap:
            self.GUID = network.generate_guid()
        else:
            self.GUID = None

        # Permanent socket for the APP
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(('', APP_PORT))
        self.sock.listen(LISTEN_QUEUE)

        # Listen at the APP_PORT
        self.listener = threading.Thread(target=self.listen)
        self.listener.daemon = True

        # Responses for query | queryRes[qId] = [query_rsp_msgs]
        self.queryCnt = 0
        self.queryRes = {}
        self.queryResQueue = queue.Queue()
        self.queryResLock = threading.RLock()

        # Chunks to be requested | chunkLeft[qId] = (total_chunks, set(chunks left))
        self.chunkLeft = {}
        self.chunkLeftLock = threading.RLock()
        self.chunkLeftTransferReq = {}
        self.reqCnt = 0

        # Paused downloads chunks
        self.pausedChunkLeft = {}

        # Repeated queries
        self.repQuer = set()
        self.repQuerQueue = queue.Queue()
        self.repQuerLock = threading.RLock()

    # Load Saved State
    def load_state(self):
        pass

    # Join the network using the bootstrapIP as the common point
    def joinNetwork(self, bootstrapIP):
        # Create a Join Message and send it to the bootstrap peer
        joinMsg = {
            TYPE: JOIN,
            SEND_IP: MY_IP,
            DEST_IP: bootstrapIP,
        }
        network.send(bootstrapIP, **joinMsg)

        # Wait for the JOIN_ACK message
        while not self.isJoined:
            clientsock, address = self.sock.accept()
            if address[0] != bootstrapIP:
                continue

            data = network.receive(clientsock)
            if data[TYPE] != JOIN_ACK:
                continue

            self.GUID = data[DEST_GUID]
            self.routTab.initialise(rt=data[ROUTING], myGUID=self.GUID,
                                    Central_GUID=data[SEND_GUID], Central_IP=bootstrapIP)
            self.isJoined = True
            print("Successfully Joined Network")

    # Join the network and start the listener thread
    def run(self, bootstrapIP=None):
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
            handleMsg = threading.Thread(
                target=self.msgHandler, args=(clientsock,))
            handleMsg.daemon = True
            handleMsg.start()

    # Handles the different type of incoming message
    def msgHandler(self, clientsock):
        msg = network.receive(clientsock)

        if msg is None or (DEST_GUID in msg and msg[DEST_GUID] != self.GUID):
            return

        if msg[TYPE] != TRANSFER_FILE:
            print(msg)  
            
        if msg[TYPE] == JOIN:
            joinAck = {
                TYPE: JOIN_ACK,
                SEND_IP: MY_IP,
                SEND_GUID: self.GUID,
                DEST_IP: msg[SEND_IP],
                DEST_GUID: network.generate_guid(),
                ROUTING: self.routTab.getTable()
            }
            network.send(joinAck[DEST_IP], **joinAck)
            self.routTab.addPeer(
                GUID=joinAck[DEST_GUID], IPAddr=joinAck[DEST_IP])

        if msg[TYPE] == PING:
            pongMsg = {
                TYPE: PONG,
                SEND_IP: MY_IP,
                SEND_GUID: self.GUID,
                DEST_IP: msg[SEND_IP],
                DEST_GUID: msg[SEND_GUID]
            }
            network.send(msg[SEND_IP], **pongMsg)
            self.routTab.handlePing(msg)

        elif msg[TYPE] == PONG:
            self.routTab.handlePong(msg)

        elif msg[TYPE] == QUERY:
            # Check whether the query is repeated
            with self.repQuerLock:
                ok = msg[QUERY_ID] in self.repQuer

            # If not repeated search database and forward query
            if not ok:
                results = self.fileSys.search(msg[SEARCH])

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
                    while len(self.repQuerQueue) >= REP_QUERY_CACHE:
                        self.repQuer.discard(self.repQuerQueue.get())
                    self.repQuer.add(msg[QUERY_ID])

                for neighbours in self.routTab.neighbours():
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
                DEST_GUID: msg[SEND_GUID],
                REQUEST_ID: msg[REQUEST_ID],
                CHUNK_NO: msg[CHUNK_NO],
                CONTENT: self.fileSys.getContent(msg[FILE_ID], msg[CHUNK_NO])
            }
            network.send(msg[SEND_IP], **fileTranMsg)

        elif msg[TYPE] == TRANSFER_FILE:
            # Acquire Lock
            with self.chunkLeftLock:

                # If the request is not yet done and the write to the file system is successful
                if msg[CHUNK_NO] in self.chunkLeft.get(msg[REQUEST_ID], (0, set()))[1] \
                        and self.fileSys.writeChunk(msg):
                    self.chunkLeft[msg[REQUEST_ID]][1].remove(msg[CHUNK_NO])

                    # If all the chunks are done, inform filesys of the completion
                    if not bool(self.chunkLeft[msg[REQUEST_ID]][1]):
                        self.fileSys.done(msg[REQUEST_ID])
                        del self.chunkLeft[msg[REQUEST_ID]]
                        del self.chunkLeftTransferReq[msg[REQUEST_ID]]

    # Function for a thread to use for requesting transfer of content
    def requestTransfer(self, tid, numChunks, msg):
        start = tid
        try:
            while start < numChunks:

                with self.chunkLeftLock:
                    ok = (start in self.chunkLeft[msg[REQUEST_ID]][1])
                msg[CHUNK_NO] = start

                while ok:
                    network.send(msg[DEST_IP], **msg)
                    time.sleep(TRANS_WAIT)
                    with self.chunkLeftLock:
                        ok = (start in self.chunkLeft[msg[REQUEST_ID]][1])

                start += NUM_THREADS

        except KeyError:
            pass

        print("Thread {} done".format(tid))

    # Sends a Query for the required content to all its neighbours
    def findContent(self, searchQ):

        if len(searchQ) < QUERY_MIN_SIZE:
            print("Query too small!")
            return

        if len(self.queryResQueue) >= QUERY_QUEUE:
            print("Throwing away older queries!")
            while len(self.queryResQueue) >= QUERY_QUEUE:
                del self.queryRes[self.queryResQueue.get()]

        qId = network.generate_uuid_from_guid(self.GUID, self.queryCnt)

        with self.queryResLock:
            self.queryRes[qId] = []
            self.queryResQueue.put(qId)

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

        for neighbours in self.routTab.neighbours():
            queryMsg[DEST_IP] = neighbours[0]
            queryMsg[DEST_GUID] = neighbours[1]
            network.send(queryMsg[DEST_IP], **queryMsg)

        print("Query Id: {}".format(qId))

    # Displays the results received till now
    def displayResults(self, qId):
        with self.queryResLock:
            for ind, results in enumerate(self.queryRes.get(qId, [])):
                print("Peer {}".format(ind + 1))

                for ind1, result in enumerate(results[RESULTS]):
                    print("\tResult {}".format(ind1 + 1))
                    print("\t\tName - {}".format(result[FT_NAME]))
                    print("\t\tSize - {:.2f} kB".format(result[FT_SIZE] / 1024))
                    print("\t\tChunks - {}".format(result[NUM_CHUNKS]))
                    print("---------------------\n")

                print("===================\n")

    # Choose the desired response for file transfer
    def chooseResults(self, qId, peerNum, resNum):

        with self.chunkLeftLock:
            cnt = len(self.chunkLeft) + len(self.pausedChunkLeft)
        
        if cnt >= DOWN_QUEUE:
            print("Too many pending downloads! Abort some before trying again.")
            return

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
            REQUEST_ID: self.reqCnt,
            FILE_ID: result[RESULTS][resNum][FILE_ID]
        }
        self.reqCnt += 1

        numChunks = result[RESULTS][resNum][NUM_CHUNKS]
        with self.chunkLeftLock:
            self.chunkLeft[transferReq[REQUEST_ID]] = (numChunks, set())
            for i in range(numChunks):
                self.chunkLeft[transferReq[REQUEST_ID]][1].add(i)
            self.chunkLeftTransferReq[transferReq[REQUEST_ID]] = transferReq

        for ind in range(NUM_THREADS):
            reqCopy = copy.deepcopy(transferReq)
            thr = threading.Thread(target=self.requestTransfer,
                                   args=(ind, numChunks, reqCopy))
            thr.daemon = True
            thr.start()
        print("Request ID: {}".format(transferReq[REQUEST_ID]))

    # Check the progress of the transfer
    def checkProgress(self, reqId):
        with self.chunkLeftLock:
            prog = self.chunkLeft.get(reqId, None)

        if prog is not None:
            print("Done {} / {}".format(prog[0] - len(prog[1]), prog[0]))

        elif self.fileSys.isFinished(reqId):
            print("Download finished")

        else:
            print("Incorrect ID")

    # Pause download
    def pause(self, reqId):
        with self.chunkLeftLock:
            if reqId in self.chunkLeft:
                self.pausedChunkLeft[reqId] = self.chunkLeft[reqId]
                del self.chunkLeft[reqId]
            else:
                print("No ongoing downloads with given Request Id")

    # Resume paused download
    def resume(self, reqId):
        if reqId in self.pausedChunkLeft:
            with self.chunkLeftLock:
                self.chunkLeft[reqId] = self.pausedChunkLeft[reqId]
                del self.pausedChunkLeft[reqId]

            for ind in range(NUM_THREADS):
                reqCopy = copy.deepcopy(self.chunkLeftTransferReq[reqId])
                thr = threading.Thread(target=self.requestTransfer,
                                    args=(ind, numChunks, reqCopy))
                thr.daemon = True
                thr.start()
                
        else:
            print("No paused downloads with given Request Id!")

    # Abort download
    def abort(self, reqId):
        with self.chunkLeftLock:
            if reqId in self.chunkLeft:
                del self.chunkLeft[reqId]
                del self.chunkLeftTransferReq[reqId]
                self.fileSys.abort_download(reqId)

            elif reqId in self.pausedChunkLeft:
                del self.pausedChunkLeft[reqId]
                del self.chunkLeftTransferReq[reqId]
                self.fileSys.abort_download(reqId)

            else:
                print("No ongoing downloads with given Request ID")

    # List all incomplete downloads
    def pending(self):
        with self.chunkLeftLock:
            goingOn = copy.deepcopy(self.chunkLeft)
            paused = copy.deepcopy(self.pausedChunkLeft)

        print("In progress\n============")
        for ind, reqId in enumerate(goingOn):
            print("{}. ReqId - {}, File - {}, Progress - {} / {}".format(
                    ind, reqId, self.fileSys.reqId_to_name(reqId), 
                    goingOn[reqId][0] - len(goingOn[reqId][1])), 
                    len(goingOn[reqId][1])
                )

        print("\nPaused\n============")
        for ind, reqId in enumerate(paused):
            print("{}. ReqId - {}, File - {}, Progress - {} / {}".format(
                    ind, reqId, self.fileSys.reqId_to_name(reqId), 
                    paused[reqId][0] - len(paused[reqId][1])), 
                    len(paused[reqId][1])
                )

    # Share Files
    def shareContent(self, path):
        if not self.fileSys.add(path):
            print("Please specify a path to a binary file")

    # Remove Shared Content
    def removeShare(self, path):
        self.fileSys.removeShare(path)

    # List all shared files
    def listFiles(self):
        for entry in self.fileSys.view_table():
            print("Id - {}, Name - {}, Path - {}, Size - {:.2f} kB, Type - {}".format(
                entry[FT_ID], entry[FT_NAME], entry[FT_PATH], 
                entry[FT_SIZE] / 1024, entry[FT_STATUS]
                )
            )


# Display help for the commands
def displayHelp():
    print("{}: display all options".format(HELP))
    print("{} <query>: intiate a search across the peers".format(SEARCH_QUERY))
    print("{} <qid>: display results till now".format(DISPLAY))
    print("{} <qid> <peerNum> <resNum>: choose a result to download".format(CHOOSE))
    print("{} <reqId>: shows the progress of the download".format(PROGRESS))
    print("{} <reqId>: pause the download".format(PAUSE))
    print("{} <reqId>: restart the download".format(UNPAUSE))
    print("{} <reqId>: aborts the download".format(ABORT))
    print("{}: show pending downloads".format(PENDING))
    print("{} <path>: share the specified path with the network".format(SHARE))
    print("{} <path>: remove the shared content from the network".format(UNSHARE))
    print("{}: show shared files".format(LIST))


# Parse the input commmandss
def parseCmds(cmd, peer):
    if len(cmd) < 1:
        return

    # Help
    elif cmd[0].lower() == HELP:
        displayHelp()

    # Search Query
    elif cmd[0].lower() == SEARCH_QUERY and len(cmd) > 1:
        query = ' '.join(cmd[1:])
        peer.findContent(query)

    # Display Results
    elif cmd[0].lower() == DISPLAY and len(cmd) == 2:
        peer.displayResults(cmd[1])

    # Choose Results
    elif cmd[0].lower() == CHOOSE and len(cmd) == 4:
        peer.chooseResults(cmd[1], int(cmd[2]) - 1, int(cmd[3]) - 1)

    # Progress of download
    elif cmd[0].lower() == PROGRESS and len(cmd) == 2:
        peer.checkProgress(int(cmd[1]))

    # Pause download
    elif cmd[0].lower() == PAUSE and len(cmd) == 2:
        peer.pause(int(cmd[1]))

    # Resume download
    elif cmd[0].lower() == UNPAUSE and len(cmd) == 2:
        peer.resume(int(cmd[1]))

    # Print pending downloads
    elif cmd[0].lower() == PENDING and len(cmd) == 1:
        peer.pending()

    # Abort Download
    elif cmd[0].lower() == ABORT and len(cmd) == 2:
        peer.abort(int(cmd[1]))

    # Share files
    elif cmd[0].lower() == SHARE and len(cmd) == 2:
        peer.shareContent(cmd[1])

    # Remove share files
    elif cmd[0].lower() == UNSHARE and len(cmd) == 2:
        peer.removeShare(cmd[1])

    # List shared files
    elif cmd[0].lower() == LIST and len(cmd) == 1:
        peer.listFiles()

    # Incorrect command
    else:
        print("Wrong Command or format!")
        displayHelp()


if __name__ == '__main__':

    peer = Node(True)
    peer.load_state()

    bootstrapIP = None
    if not peer.isJoined:
        bootstrapIP = input("Bootstrap IP: ")

    peer.run(bootstrapIP)

    while True:
        cmd = input("> ").split()
        parseCmds(cmd, peer)
