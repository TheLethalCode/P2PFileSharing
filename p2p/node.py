import socket
import threading
import time
import copy
import sys
import os
import queue
import logging
import network
from constants import *
from routingTable import routingTable
from fileSystem import fileSystem
# import p2p.network as network
# from p2p.constants import *
# from p2p.routingTable import routingTable
# from p2p.fileSystem import fileSystem

# TODO:- Save state periodically and load
# TODO:- Error Handling and logging

# Setting up the log
logger = logging.getLogger('node')
logger.setLevel(logging.INFO)

fh = logging.FileHandler(os.path.join(LOG_PATH, LOG_FILE))
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(threadName)s - %(levelname)s - %(message)s'
)
fh.setFormatter(formatter)
logger.addHandler(fh)

class Node(object):

    def __init__(self, isBootstrap=False):

        self.routTab = routingTable()
        self.fileSys = fileSystem()
        self.isBootstrap = isBootstrap

        # Handle the case of bootstrapping node
        if self.isBootstrap:
            self.isJoined = True
            self.GUID = network.generate_guid()
            logging.info('Starting BootStrap node with GUID: {}'.format(self.GUID))
        else:
            self.isJoined = False
            self.GUID = None

        # Permanent socket for the APP
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(('', APP_PORT))
        self.sock.listen(LISTEN_QUEUE)
        logging.info("Binded listening socket to port {}".format(APP_PORT))

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
        
        # Wait for the JOIN_ACK message
        while not self.isJoined:
            
            # If error sending JOIN message
            while not network.send(bootstrapIP, **joinMsg):
                time.sleep(ERROR_RETRY)
                logging.warning('Failed to send JOIN message to {}'.format(bootstrapIP))
            logging.info('Sent JOIN message to {}'.format(bootstrapIP))

            clientsock, address = self.sock.accept()

            if address[0] == bootstrapIP:
                data = network.receive(clientsock)
                if data and data[TYPE] == JOIN_ACK:
                    self.GUID = data[DEST_GUID]
                    self.routTab.initialise(
                            rt=data[ROUTING], myGUID=self.GUID,
                            Central_GUID=data[SEND_GUID], 
                            Central_IP=bootstrapIP
                        )
                    self.isJoined = True
                    print("Joined Network! Your GUID: {}".format(self.GUID))
                    logging.info('Joined Network! GUID: {}'.format(self.GUID))
            
    # Join the network and start the listener thread
    def run(self, bootstrapIP=None):
        logging.info('Starting up peer!')
        if not self.isJoined:
            if bootstrapIP is None:
                print("Error! Need Bootstrap IP")
                return
            self.joinNetwork(bootstrapIP)

        self.listener.start()
        logging.info('Started listener thread')

    # Keeps listening and creates separate threads to handle messages
    def listen(self):
        while True:
            clientsock, address = self.sock.accept()
            handleMsg = threading.Thread(
                    target=self.msgHandler, 
                    args=(clientsock, address)
                )
            handleMsg.daemon = True
            handleMsg.start()

    # Handles the different type of incoming message
    def msgHandler(self, clientsock, address):

        msg = network.receive(clientsock)

        if not msg:
            logging.warning('Did not receive message properly from {}'.format(address[0]))
            return

        if (DEST_GUID in msg and msg[DEST_GUID] != self.GUID):
            logging.warning('Not the intended recipient for message. Destination GUID: {}'.format(msg[DEST_GUID]))
            print(msg)
            return

        # If received Join message (for bootstrap node)
        if msg[TYPE] == JOIN:
            if self.isBootstrap:
                logging.info('Received JOIN message from {}'.format(msg[SEND_IP]))
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
                    GUID=joinAck[DEST_GUID], 
                    IPAddr=joinAck[DEST_IP]
                )
                logging.info('Assigned GUID {} to {}'.format(joinAck[DEST_GUID], joinAck[DEST_IP]))
            else:
                logging.warning('Join message received! But not bootstrap node')

        # Reciving PING message
        if msg[TYPE] == PING:
            logging.info('Received PING message from {} ({})'.format(msg[SEND_IP], msg[SEND_GUID]))
            pongMsg = {
                TYPE: PONG,
                SEND_IP: MY_IP,
                SEND_GUID: self.GUID,
                DEST_IP: msg[SEND_IP],
                DEST_GUID: msg[SEND_GUID]
            }
            network.send(msg[SEND_IP], **pongMsg)
            self.routTab.handlePing(msg)

        # Receiving PONG message
        elif msg[TYPE] == PONG:
            logging.info('Received PONG message from {} ({})'.format(msg[SEND_IP], msg[SEND_GUID]))
            self.routTab.handlePong(msg)

        # Receiving QUERY message
        elif msg[TYPE] == QUERY:
            logging.info(
                'Received QUERY message with ID {} from {} ({}). Source:- {} ({})'.format(
                    msg[QUERY_ID], msg[SEND_IP], msg[SEND_GUID], msg[SOURCE_IP], msg[SOURCE_GUID]
                )
            )

            # Check whether the query is repeated
            with self.repQuerLock:
                ok = msg[QUERY_ID] in self.repQuer

            # If not repeated search database and forward query
            if not ok:
                # Search for results in database and send back if any
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
                    logging.info('Sending {} response(s) to Query {} to {} ({})'.format(
                            len(results), msg[QUERY_ID], msg[SOURCE_IP], msg[SOURCE_GUID]
                        )
                    )

                # Throw away older cached query
                with self.repQuerLock:
                    while self.repQuerQueue.qsize() >= REP_QUERY_CACHE:
                        self.repQuer.discard(self.repQuerQueue.get())
                    self.repQuer.add(msg[QUERY_ID])
                logging.info('Adding Query {} to cache'.format(msg[QUERY_ID]))

                msg[SEND_IP] = MY_IP
                msg[SEND_GUID] = self.GUID

                # Send queries to neighbours in Table
                for neighbours in self.routTab.neighbours():
                    msg[DEST_IP] = neighbours[0]
                    msg[DEST_GUID] = neighbours[1]
                    if msg[DEST_GUID] != msg[SEND_GUID]:
                        network.send(msg[DEST_IP], **msg)
                        logging.info('Forwarding query to neighbour {} ({})'.format(
                                msg[DEST_IP], msg[DEST_GUID]
                            )
                        )
            else:
                logging.info('Repeated query {}'.format(msg[QUERY_ID]))

        # If received QUERY_RESP message
        elif msg[TYPE] == QUERY_RESP:
            logging.info(
                'Received QUERY_RESP with {} result(s) for query {} from {} ({})'.format(
                    len(msg[RESULTS]), msg[QUERY_ID], msg[SEND_IP], msg[SEND_GUID], 
                )
            )
            with self.queryResLock:
                if msg[QUERY_ID] in self.queryRes:
                    self.queryRes[msg[QUERY_ID]].append(msg)
                    return
            logging.warning('Query {} previously discarded'.format(msg[QUERY_ID]))

        # If received TRANSFER_REQ
        elif msg[TYPE] == TRANSFER_REQ:
            logging.info('Received TRANSFER_REQ from {} ({}) for File ID {} and Chunk {}'.format(
                    msg[SEND_IP], msg[SEND_GUID], msg[FILE_ID], msg[CHUNK_NO]
                )
            )
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
            if fileTranMsg[CONTENT] is None:
                logging.warning('Content Unavailable for File ID {}'.format(msg[FILE_ID]))
            else:
                network.send(msg[SEND_IP], **fileTranMsg)

        # If received TRANSFER_FILE message
        elif msg[TYPE] == TRANSFER_FILE:
            logging.info('Received TRANSFER_FILE from {} ({}) for Request ID {} and Chunk {}'.format(
                    msg[SEND_IP], msg[SEND_GUID], msg[REQUEST_ID], msg[CHUNK_NO]
                )
            )
            with self.chunkLeftLock:
                # If the request is not yet done and the write to the file system is successful
                if msg[CHUNK_NO] in self.chunkLeft.get(msg[REQUEST_ID], (0, set()))[1] \
                        and self.fileSys.writeChunk(msg):

                    # Remove the chunk no from the required chunk list    
                    self.chunkLeft[msg[REQUEST_ID]][1].remove(msg[CHUNK_NO])

                    # If all the chunks are done, inform filesys of the completion
                    if not bool(self.chunkLeft[msg[REQUEST_ID]][1]):
                        self.fileSys.done(msg[REQUEST_ID])
                        del self.chunkLeft[msg[REQUEST_ID]]
                        del self.chunkLeftTransferReq[msg[REQUEST_ID]]

    # Function for a thread to use for requesting transfer of content
    def requestTransfer(self, tid, numChunks, msg):
        start = tid
        logging.info('Started thread {} for Request {}'.format(tid, msg[REQUEST_ID]))

        # while the reqId is to be downloaded
        try:
            while start < numChunks:
                with self.chunkLeftLock:
                    ok = (start in self.chunkLeft[msg[REQUEST_ID]][1])

                msg[CHUNK_NO] = start
                while ok:
                    logging.info('Asking Chunk {} for Request {} from {} ({})'.format(
                            start, msg[REQUEST_ID], msg[DEST_IP], msg[DEST_GUID]
                        )
                    )
                    network.send(msg[DEST_IP], **msg)
                    time.sleep(TRANS_WAIT)
                    with self.chunkLeftLock:
                        ok = (start in self.chunkLeft[msg[REQUEST_ID]][1])

                start += NUM_THREADS

        except KeyError:
            pass

        logging.info('Finishing thread {} for Request {}'.format(tid, msg[REQUEST_ID]))

    # Sends a Query for the required content to all its neighbours
    def findContent(self, searchQ):

        # Check for minimum query size
        if len(searchQ) < QUERY_MIN_SIZE:
            print("Query too small!")
            return

        with self.queryResLock:
            if self.queryResQueue.qsize() >= QUERY_QUEUE:
                print("Throwing away older queries!")                
                while self.queryResQueue.qsize() >= QUERY_QUEUE:
                    which = self.queryResQueue.get()
                    del self.queryRes[which]
                    logger.warning('Throwing away query {}'.format(which))

            qId = network.generate_uuid_from_guid(self.GUID, self.queryCnt)
            self.queryRes[qId] = []
            self.queryResQueue.put(qId)
            logger.info('Generated Query {}'.format(qId))

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

        # Caching for ignoring repeated
        with self.repQuerLock:
            while self.repQuerQueue.qsize() >= REP_QUERY_CACHE:
                self.repQuer.discard(self.repQuerQueue.get())
            self.repQuer.add(queryMsg[QUERY_ID])
            logger.info('Adding query {} to cache'.format(queryMsg[QUERY_ID]))

        # Sending Query to neighbours for flooding
        for neighbours in self.routTab.neighbours():
            queryMsg[DEST_IP] = neighbours[0]
            queryMsg[DEST_GUID] = neighbours[1]
            network.send(queryMsg[DEST_IP], **queryMsg)
            logging.info('Sending query to neighbour {} ({})'.format(
                                queryMsg[DEST_IP], queryMsg[DEST_GUID]
                            )
                        )

        print("Query Id: {}".format(qId))

    # Displays the results received till now
    def displayResults(self, qId):
        with self.queryResLock:
            if qId not in self.queryRes:
                print("No such Query ID!")
                return
            peers = copy.deepcopy(self.queryRes[qId])

        # Display results
        for ind, results in enumerate(peers):
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
        logging.info('Created request {}'.format(transferReq[REQUEST_ID]))

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
                return
        logging.info('Paused request {}'.format(reqId))
    
    # Resume paused download
    def resume(self, reqId):
        if reqId in self.pausedChunkLeft:
            with self.chunkLeftLock:
                self.chunkLeft[reqId] = self.pausedChunkLeft[reqId]
                del self.pausedChunkLeft[reqId]
                numChunks = self.chunkLeft[reqId][0]

            logging.info('Resumed request {}'.format(reqId))
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
            # If download is ongoing
            if reqId in self.chunkLeft:
                del self.chunkLeft[reqId]
                del self.chunkLeftTransferReq[reqId]
                self.fileSys.abort_download(reqId)

            # If download is paused   
            elif reqId in self.pausedChunkLeft:
                del self.pausedChunkLeft[reqId]
                del self.chunkLeftTransferReq[reqId]
                self.fileSys.abort_download(reqId)

            # If no such download
            else:
                print("No ongoing downloads with given Request ID")
                return
        
        logging.info('Aborted request {}'.format(reqId))

    # List all incomplete downloads
    def pending(self):
        # Make a copy
        with self.chunkLeftLock:
            goingOn = copy.deepcopy(self.chunkLeft)
            paused = copy.deepcopy(self.pausedChunkLeft)

        print("In progress\n============")
        for ind, reqId in enumerate(goingOn):
            print("{}. ReqId - {}, File - {}, Progress - {} / {}".format(
                ind, reqId, self.fileSys.reqId_to_name(reqId),
                goingOn[reqId][0] - len(goingOn[reqId][1]),
                goingOn[reqId][0])
            )

        print("\nPaused\n============")
        for ind, reqId in enumerate(paused):
            print("{}. ReqId - {}, File - {}, Progress - {} / {}".format(
                ind, reqId, self.fileSys.reqId_to_name(reqId),
                paused[reqId][0] - len(paused[reqId][1]),
                paused[reqId][0])
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
        for entry in self.fileSys.view_table(DB_TABLE_FILE):
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

    # Starting up the peer
    peer = Node(True)
    peer.load_state()

    bootstrapIP = None
    if not peer.isJoined:
        bootstrapIP = input("Bootstrap IP: ")

    peer.run(bootstrapIP)

    while True:
        cmd = input("> ").split()
        parseCmds(cmd, peer)
