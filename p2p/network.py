import json
import socket
import time
from json.decoder import JSONDecodeError
import uuid

from constants import MSG_SIZE, ENCODING, SOCK_SLEEP, APP_PORT, SOCKET_TIMEOUT


def send(ip: str, **data):
    """Send data to IP (default PORT).

    Args:
        ip (str): IP address of the receipent.
        data (key-value): data encode-able into JSON for sending.

    Returns:
        bool: True if success, False otherwise.
    """
    try:
        data = dict(data)
        data = json.dumps(data)
        data = len(data).to_bytes(4, 'big') + data.encode(ENCODING)
        socket = _get_socket(ip)
        socket.sendall(data)
        return True
    except (ValueError, TypeError, Exception) as err:
        print(f'ERROR: {err}')
        return False


def receive(socket: socket):
    """Receive data from socket until EOM_CHAR.

    Args:
        socket (socket): socket to receive data from.

    Returns:
        dict: received data decoded into dictionary
    """
    # timeout after TIMEOUT seconds if no data received
    socket.settimeout(SOCKET_TIMEOUT)
    buff = b''
    length = None

    while True:
        temp = b''
        temp = socket.recv(MSG_SIZE)

        if temp != b'':
            if length is None and len(temp) >= 4:
                length = int.from_bytes(temp[:4], 'big')
                temp = temp[4:]
            
            if length is not None:
                if length > len(temp):
                    buff += temp
                    length -= len(temp)

                else:
                    buff += temp[:length]
                    try:
                        buff = buff.decode(ENCODING)
                        return json.loads(buff)

                    except JSONDecodeError as err:
                        print(f"DEBUG: {err}")
                        print("ERROR: invalid dict received!")
                        return {}
        time.sleep(SOCK_SLEEP)


def _get_socket(ip: str):
    """Get socket to the provided IP.

    Args:
        ip (str): IP to connect socket to.

    Returns:
        socket: Socket to the IP.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(ip, APP_PORT)
    return sock


def generate_guid():
    """Generate a random UUID.

    Returns:
        str: UUID
    """
    return str(uuid.uuid4())

def generate_uuid_from_guid(guid:  str, number: int):
    """Generate UUID from MD5 Hash of GUID and sequence number.

    Args:
        guid (str): Hex digest of UUID.
        number (int): Sequence number.

    Returns:
        str: Hex digest of generate UUID.
    """
    return uuid.uuid3(uuid.UUID(guid), str(number))
