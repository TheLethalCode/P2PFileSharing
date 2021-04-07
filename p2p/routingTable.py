import json
import os
import time

class routingTable(object):
    def __init__(self, updateFreq):
        self.filename = 'RT.json'
        self.updateFreq = updateFreq
        self.lastUpdateTime = time.time()
        direcs = os.listdir('./')
        if 'RT.json' in direcs:
            self.RT = json.load(open(self.filename, 'r'))
        else:
            self.RT = dict()
            with open(self.filename, 'w') as f:
                json.dump(self.RT, f)

    def __del__(self):
        os.remove(self.filename)
    
    def local_save(self):
        #No mutex lock here, assumed to always be called within mutex locking of other functions
        with open(self.filename, 'w') as f:
            json.dump(self.RT, f)

    def insertPeer(self, GUID, IPAddr, Port):
        if GUID in self.RT.keys():
            #safety in case that GUID is already present
            self.updatePeer(GUID, IPAddr, Port)
        else:
            #Since we are inserting new node, we assume its active
            self.RT[GUID] = dict()
            self.RT[GUID]['IPAddr'] = IPAddr
            self.RT[GUID]['Port'] = Port
            self.RT[GUID]['ActiveBool'] = True
            self.RT[GUID]['InactiveTime'] = 0
            self.local_save()
            
    def deletePeer(self, GUID):
        if GUID in self.RT.keys():
            self.RT.pop(GUID)
        self.local_save()
    
    def updatePeer(self, GUID, IPAddr, Port, ActiveBool=True, InactiveTime=0):
        #Used to update change in port/ipaddress and to reset bool and inactivetime.
        if GUID in self.RT.keys():
            self.RT[GUID]['IPAddr'] = IPAddr
            self.RT[GUID]['Port'] = Port
            self.RT[GUID]['ActiveBool'] = ActiveBool
            self.RT[GUID]['InactiveTime'] = InactiveTime
            self.local_save()
        else:
            #safety in case that GUID is already present
            self.insertPeer(GUID, IPAddr, Port)


    def peerActivityCheck(self, GUID):
        #Ping message for the peer
        pass
    
    def periodicActivityCheck(self):
        #Ping to all peers
        pass

    def findNearestGUID(self, GUID):
        pass
