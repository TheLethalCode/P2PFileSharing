import json
from json.decoder import JSONDecodeError
from p2p.constants import ENCODING, EOM_CHAR, PORT
import socket
import time

def send(ip, **data) -> bool:
    """Send data to IP (default PORT) with EOM_CHAR at the end.

    Args:
        ip (str): IP address of the receipent.
        data (key-value): data encode-able into JSON for sending.

    Returns:
        bool: True if success, False otherwise.
    """
    try:
        data = dict(data)
        data = json.dumps(data)
        data = data.encode(ENCODING) + EOM_CHAR
        socket = _get_socket(ip)
        socket.sendall(data)
    except (ValueError, TypeError, Exception) as err:
        print(f'ERROR: {err}')
        return False
    

def receive(socket) -> dict:
    """Receive data from socket until EOM_CHAR.

    Args:
        socket (socket): socket to receive data from.

    Returns:
        dict: received data decoded into dictionary
    """
    # timeout after 10 seconds if no data received
    socket.settimeout(10.0)
    buff = b''
    
    while True:
        temp = b''
        temp = socket.recv(4096)
        
        if temp != b'':
            buff += temp
            end = buff.find(EOM_CHAR)
            
            if end>0:
                try:
                    buff = buff[:end]
                    buff = buff.decode(ENCODING)
                    return json.loads(buff)
                except JSONDecodeError as err:
                    print(f"DEBUG: {err}")
                    print("ERROR: invalid dict received!")
                    return {}
        time.sleep(0.01)

    

def _get_socket(ip) -> socket:
    """Get socket to the provided IP.

    Args:
        ip (str): IP to connect socket to.

    Returns:
        socket: Socket to the IP.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(ip, PORT)
    return sock