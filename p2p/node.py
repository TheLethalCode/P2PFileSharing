import socket
import network
from routingTable import routingTable
from fileSystem import fileSystem

class node(object):
    
    def __init__(self):
        self.GUID = None
        self.routTab = routingTable()
        self.fileSys = fileSystem()
        self.isJoined = False
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind('', network.APP_PORT)
        self.sock.listen(20)


    def joinNetwork(self, bootstrapIP):
        network.send_message('JOIN', sender=network.MY_IP, dest=bootstrapIP)

        while not self.isJoined:
            clientsock, address = self.sock.accept()
            if address[0] != bootstrapIP:
                continue

            data = network.read_message(clientsock)
            if data['type'] != 'JOIN_ACK':
                continue

            routTable.initialise(data['routTable'], data['myGUID'])
            self.GUID = data['GUID']
            self.isJoined = True


    def run(self, bootstrapIP):
        self.joinNetwork(bootstrapIP)
        while True:


