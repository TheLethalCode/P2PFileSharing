import logging
import daiquiri

# Initialize logger
daiquiri.setup(level=logging.INFO)
LOGGER = daiquiri.getLogger(__name__)
LOGGER.info("logger initialized!")

# End character for send/receive messages.
EOM_CHAR = 0x04.to_bytes(1, 'big')
# Default Port for creating socket connection.
APP_PORT = 4000
# Default encoding.
ENCODING = 'utf-8'
# Storage path for Hashed FileSystem
FILESYS_PATH = "fs.pkl"
# Chunk Size (in Bytes) 4096 bytes = 4KB
CHUNK_SIZE = 4096

# STATUSES FOR FILESYSTEM
# Uploaded by current node
FS_UPLOADED = "UPL"
# Replication - Download Complete
FS_REPLICATION_COMPLETE = "RPC"
# Replication - Download In Progress
FS_REPLICATION_PROGRESS = "RIP"
# Download Complete
FS_DOWNLOAD_COMPLETE = "FDC"
# Download In-Progress
FS_DOWNLOAD_PROGRESS = "FDP"

# DATABASE DETAILS
DB_HOST = "localhost"
DB_USERNAME = "user"
DB_PASSWORD = "pass"
DB_NAME = "fsys"

# MYMYSQL PASS 1234

# TABLE DETAILS
DB_TABLE_FILE = "FILETABLE"
FT_NAME = "name"
FT_PATH = "path"
FT_SIZE = "size"
FT_CHECKSUM = "checksum"
FT_PARENTID = "parent_id"
FT_RANDOMID = "random_id"
FT_STATUS = "status"
FT_REPLICATED_TO = "replication_node"
FT_ID = "ID"

# CONTENT = {
#     CHUNK,
#     FILENAME,
#     CHECKSUM
# }
# Description of CONTENT
CNT_CHUNK = "chunk"
CNT_FILENAME = "filename"
CNT_CHECKSUM = "checksum"
CNT_FILEPATH = "filepath"
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
