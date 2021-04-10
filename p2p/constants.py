# End character for send/receive messages.
EOM_CHAR = 0x04.to_bytes(1, 'big')
# Default Port for creating socket connection.
APP_PORT = 4000
# Default encoding.
ENCODING = 'utf-8'
# Socket timeout.
SOCKET_TIMEOUT = 10.0
# chunk size
CHUNK_SIZE = 4096
# My IP address in the network
MY_IP = '127.0.0.1'
# Num threads for requesting content
NUM_THREADS = 10

# Message related constant
JOIN = 'Join'
JOIN_ACK = 'Join Ack'
PING = 'Ping'
PONG = 'Pong'
QUERY = 'Query'
QUERY_RESP = 'Query Response'
TRANSFER_REQ = 'Transfer Request'
TRANSFER_FILE = 'Transfer File'

TYPE = 'Type'
SEND_IP = 'Sender IP'
SEND_GUID = 'Sender GUID'
DEST_IP = 'Destination IP'
DEST_GUID = 'Destination GUID'

ROUTING = 'Routing Table'

SOURCE_IP = 'Source IP'
SOURCE_GUID = 'Source GUID'
SEARCH = 'Search'
QUERY_ID = 'Query ID'

RESULTS = 'Results'

FILE_ID = 'File ID'
CHUNK_NO = 'Chunk number'
NUM_CHUNKS = 'Number Chunks'
REQUEST_ID = 'Request ID'

CONTENT = 'Data'

# JOIN MESSAGE = {
#     TYPE,
#     SEND_IP,
#     DEST_IP,
# }

# JOIN_ACK MESSAGE = {
#     TYPE,
#     SEND_IP,
#     SEND_GUID,
#     DEST_IP,
#     DEST_GUID,
#     ROUTING,
# }

# PING MESSAGE = {
#     TYPE,
#     SEND_IP,
#     SEND_GUID,
#     DEST_IP,
#     DEST_GUID,
# }

# PONG MESSAGE = {
#     TYPE,
#     SEND_IP,
#     SEND_GUID,
#     DEST_IP,
#     DEST_GUID,
# }

# QUERY_MESSAGE = {
#     TYPE
#     SEND_IP
#     SEND_GUID
#     DEST_IP
#     DEST_GUID
#     SOURCE_IP
#     SOURCE_GUID
#     SEARCH
#     QUERY_ID
# }

# QUERY_RESP MESSAGE = {
#     TYPE,
#     SEND_IP,
#     SEND_GUID,
#     DEST_IP,
#     DEST_GUID,
#     QUERY_ID,
#     RESULTS,
# }

# TRANSFER_REQ = {
#     TYPE,
#     SEND_IP,
#     SEND_GUID,
#     DEST_IP,
#     DEST_GUID,
#     REQUEST_ID,
#     FILE_ID,
#     CHUNK_NO,
# }

# TRANSFER_FILE = {
#     TYPE,
#     SEND_IP,
#     SEND_GUID,
#     DEST_IP,
#     DEST_GUID,
#     REQUEST_ID,
#     CHUNK_NO,
#     CONTENT,
# }

