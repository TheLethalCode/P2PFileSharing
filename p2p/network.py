import json
from p2p.constants import ENCODING, EOM_CHAR, PORT
import socket

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
        print(f'DEBUG: {err}')
        return False
    

def receive(socket) -> dict:
    """Receive data from socket until EOM_CHAR.

    Args:
        socket (socket): socket to receive data from.

    Returns:
        dict: received data decoded into dictionary
    """
    pass


def _get_socket(ip) -> socket:
    """[summary]

    Args:
        ip ([type]): [description]

    Returns:
        socket: [description]
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    socket.bind(ip, PORT)
    socket.timeout(10.0)
    socket.listen(1)
    return socket