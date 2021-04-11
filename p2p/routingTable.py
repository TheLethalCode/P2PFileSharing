import json
import os, sys
import time
import threading
import network
from constants import *

class routingTable(object):
    def __init__(self, updateFreq=10, inactiveLimit=10):
        self.myGUID = 0
        self.filename = 'RT.json'
        self.updateFreq = updateFreq
        self.inactiveLimit = inactiveLimit

        self.mutex = threading.Lock() #for locking rt
        self.mutexPP = threading.Lock() #for locking sentPing and recvPong

        self.sentPing = []
        self.recvPong = []

        direcs = os.listdir('./')
        if 'RT.json' in direcs:
            self.RT = json.load(open(self.filename, 'r'))
        else:
            self.RT = dict()
            with open(self.filename, 'w') as f:
                json.dump(self.RT, f)

        self.StayActive = True #Destructor sets it to false, thread then exits loop and joins
        self.thread = threading.Thread(target=self.periodicActivityCheck, args=())
        self.thread.start()
        
    def __del__(self):
        self.StayActive = False
        self.thread.join()

    def initialise(self, rt, myGUID, Central_GUID, Central_IP):
        if len(self.RT)!=0:
            print('Warning: Overriding routing Table')
        self.RT = rt
        self.myGUID = myGUID
        self.addPeer(GUID = Central_GUID, IPAddr = Central_IP, IsCentre = True)
        self.local_save()

    def getTable(self):
        return self.RT

    def local_save(self):
        #No mutex lock here, assumed to always be called within mutex locking of other functions
        with open(self.filename, 'w') as f:
            json.dump(self.RT, f)

    def addPeer(self, GUID, IPAddr='0', Port=APP_PORT, IsCentre=False):
        self.mutex.acquire()
        if GUID in self.RT.keys():
            #safety in case that GUID is already present
            self.mutex.release()
            self.updatePeer(GUID, IPAddr, Port)
        else:
            #Since we are inserting new node, we assume its active
            self.RT[GUID] = dict()
            self.RT[GUID]['IPAddr'] = IPAddr
            self.RT[GUID]['Port'] = Port
            self.RT[GUID]['ActiveBool'] = True
            self.RT[GUID]['InactiveTime'] = 0
            self.RT[GUID]['IsCentre'] = IsCentre
            self.local_save()
            self.mutex.release()
            
    def deletePeer(self, GUID):
        self.mutex.acquire()
        if GUID in self.RT.keys():
            self.RT.pop(GUID)
        self.local_save()
        self.mutex.release()
    
    def updatePeer(self, GUID, IPAddr, Port = APP_PORT, ActiveBool=True, InactiveTime=0, IsCentre=False):
        #Used to update change in port/ipaddress and to reset bool and inactivetime.
        self.mutex.acquire()
        if GUID in self.RT.keys():
            self.RT[GUID]['IPAddr'] = IPAddr
            self.RT[GUID]['Port'] = Port
            self.RT[GUID]['ActiveBool'] = ActiveBool
            self.RT[GUID]['InactiveTime'] = InactiveTime
            self.RT[GUID]['IsCentre'] = IsCentre

            self.local_save()
            self.mutex.release()
        else:
            self.mutex.release()
            #safety in case that GUID is already present
            self.addPeer(GUID = GUID, IPAddr = IPAddr, Port = Port, IsCentre = IsCentre)

    def handlePing(pingMsg):
        #Handle incoming Ping
        if pingMsg[TYPE] != PING:
            print('Warning HandlePing has not received PING message')
            return
        self.updatePeer(GUID = pingMsg[SEND_GUID], IPAddr = pingMsg[SEND_IP])
    
    def handlePong(pongMsg):
        #Handle incoming Pong
        if pongMsg[TYPE] != PING:
            print('Warning HandlePing has not received PING message')
            return
        self.updatePeer(GUID = pingMsg[SEND_GUID], IPAddr = pingMsg[SEND_IP])
        self.mutexPP.acquire()  
        self.recvPong.append(pingMsg[SEND_GUID])
        self.mutexPP.release()

    def sendPing(destGUID, destIP):
        pingMsg = {
            TYPE: PONG,
            SEND_IP: MY_IP,
            SEND_GUID: self.myGUID,
            DEST_IP: destIP,
            DEST_GUID: destGUID
        }
        network.send(pingMsg[SEND_IP], **pingMsg)
        self.mutexPP.acquire()
        self.sentPing.append(destGUID)
        self.mutexPP.release()
    
    def neighbours(self):
        self.mutex.acquire()
        nbr = []
        for guid in self.RT:
            nbr.append((self.RT[guid]['IPAddr'], guid))
        self.mutex.release()
        return nbr

    def periodicActivityCheck(self):
        while(self.StayActive):
            time.sleep(self.updateFreq)
            print('UPDATING')
            self.mutexPP.acquire()
            for guid in self.sentPing:
                self.mutex.acquire()
                if guid in self.RT.keys():
                    obj = self.RT[guid]
                else:
                    continue
                self.mutex.release()

                if guid in self.recvPong:
                    self.updatePeer(GUID=guid, IPAddr=obj['IPAddr'], Port=obj['Port'], IsCentre=obj['IsCentre'])
                else:
                    if obj['InactiveTime']+1>self.inactiveLimit:
                        self.deletePeer(guid)
                    else:
                        self.updatePeer(GUID=guid, IPAddr=obj['IPAddr'], Port=obj['Port'], ActiveBool=False, InactiveTime=obj['InactiveTime']+1, IsCentre=obj['IsCentre'])

            self.sentPing = []
            self.recvPong = []
            self.mutexPP.release()

            nbr = self.neighbours()
            for (guid, IPAddr) in nbr:
                self.sendPing(guid, self.RT[guid]['IPAddr'])

    def findNearestGUID(self, GUID):
        pass
