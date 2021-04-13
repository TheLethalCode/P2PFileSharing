import json
import socket
import time
from json.decoder import JSONDecodeError
import uuid
from constants import *


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
        isTransfer = False

        if data[TYPE] == TRANSFER_FILE:
            isTransfer = True
            content = data[CONTENT][CNT_CHUNK]
            data[CONTENT][CNT_CHUNK] = ''

        data = json.dumps(data)
        data = data.encode(ENCODING)
        data = len(data).to_bytes(4, 'big') + data
        socket = _get_socket(ip)

        if isTransfer:
            data = int(1).to_bytes(1, 'big') + data
            data += len(content).to_bytes(4, 'big') + content
        else:
            data = int(0).to_bytes(1, 'big') + data

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
    toSend = {}
    isContent = None
    length, contLength = None, None
    done = False

    while True:
        temp = b''
        temp = socket.recv(MSG_SIZE)
        
        if temp != b'':
            if isContent is None:
                isContent = bool(int.from_bytes(temp[:1], 'big'))
                temp = temp[1:]

            if length is None and len(temp) >= 4:
                length = int.from_bytes(temp[:4], 'big')
                temp = temp[4:]

            if length is not None and not done:
                if length > len(temp):
                    buff += temp
                    length -= len(temp)

                else:
                    buff += temp[:length]
                    try:
                        buff = buff.decode(ENCODING)
                        toSend = json.loads(buff)
                        if isContent:
                            done = True
                            buff = b''
                        else:
                            return toSend

                    except JSONDecodeError as err:
                        print(f"DEBUG: {err}")
                        print("ERROR: invalid dict received!")
                        None
            
            if done and isContent:
                if contLength is None and len(temp) >= 4:
                    contLength = int.from_bytes(temp[:4], 'big')
                    temp = temp[4:]

                if contLength is not None:
                    if contLength > len(temp):
                        buff += temp
                        contLength -= len(temp)

                    else:
                        buff += temp[:contLength]
                        toSend[CONTENT][CNT_CHUNK] = buff
                        return toSend

        time.sleep(SOCK_SLEEP)


def _get_socket(ip: str):
    """Get socket to the provided IP.

    Args:
        ip (str): IP to connect socket to.

    Returns:
        socket: Socket to the IP.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, APP_PORT))
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
    return str(uuid.uuid3(uuid.UUID(guid), str(number)))
