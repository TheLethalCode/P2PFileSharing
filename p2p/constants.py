# End character for send/receive messages.
EOM_CHAR = 0x04.to_bytes(1, 'big')
# Default Port for creating socket connection.
PORT = 4000
# Default encoding.
ENCODING = 'utf-8'
# Socket timeout.
SOCKET_TIMEOUT = 10.0
# chunk size
CHUNK_SIZE = 4096