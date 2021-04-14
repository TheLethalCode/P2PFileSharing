import logging
import daiquiri

## Logger Constants ##

daiquiri.setup(level=logging.INFO)
LOGGER = daiquiri.getLogger(__name__)
LOGGER.info("Logger Initialized!")

#################### Network Constants ##########################################

APP_PORT = 4001             # Default Port for creating socket connection.
# ENCODING = 'utf-16'          # Default encoding.
ENCODING = 'utf-8'
MY_IP = '192.168.191.4'         # My IP address in the network
SOCKET_TIMEOUT = 10.0       # Time out for receiving message
MSG_SIZE = 4096             # Amount to receive in one go
SOCK_SLEEP = 0.001

#################### FileSystem Constants #######################################

FILESYS_PATH = "fs.pkl"         #
CHUNK_SIZE = 65536              # Chunk Size (in Bytes) 65536 bytes = 64KB

DOWNLOAD_FOLDER = "downloads/"
INCOMPLETE_FOLDER = "incomplete/"

# Statuses
FS_UPLOADED = "UPL"                     # Uploaded by current node
FS_REPLICATION_COMPLETE = "RPC"         # Replication - Download Complete
FS_REPLICATION_PROGRESS = "RIP"         # Replication - Download In Progress
FS_DOWNLOAD_COMPLETE = "FDC"            # Download Complete
FS_DOWNLOAD_PROGRESS = "FDP"            # Download In-Progress

# Database Details
DB_HOST = "localhost"                   # The location of the database
DB_USERNAME = "root"                    # Usernmae for accessing the database
DB_NAME = "fsys"                        # Name of the database

# Table
DB_TABLE_FILE = "FILETABLE"             #
FT_NAME = "name"                        #
FT_PATH = "path"                        #
FT_SIZE = "size"                        #
FT_CHECKSUM = "checksum"                #
FT_PARENTID = "parent_id"               #
FT_REQUESTID = "random_id"               #
FT_STATUS = "status"                    #
FT_REPLICATED_TO = "replication_node"   #
FT_ID = "ID"                            #

# Description of CONTENT, the attribute that holds the actual data transferred
# CONTENT = {
#     CHUNK,
#     FILENAME,
#     CHECKSUM
# }
CNT_CHUNK = "chunk"  # ChunkNo. (Int)
CNT_FILENAME = "filename"  # FileNmae (String)
CNT_CHECKSUM = "checksum"  # Checksum (String)
CNT_FILEPATH = "filepath"  # Filepath (String)
CNT_SIZE = "size"  # FileSize (Int)
######################## Message Constants ######################################

# Message Types
JOIN = 'Join'  # A message to join the network
JOIN_ACK = 'Join Ack'  # A message acknowledging the join with the GUID
PING = 'Ping'  # A ping message, heartbeat
PONG = 'Pong'  # Response to the ping, typically
QUERY = 'Query'  # Contains the query of the user
QUERY_RESP = 'Query Response'  # Response to the query
TRANSFER_REQ = 'Transfer Request'  # Request for a transfer of a chunk
TRANSFER_FILE = 'Transfer File'  # The actual content of the transfer

# Common Attributes
TYPE = 'Type'  # Type of the message (String)
SEND_IP = 'Sender IP'  # Sender's IP     (String)
SEND_GUID = 'Sender GUID'  # Sender's GUID   (String)
DEST_IP = 'Destination IP'  # Destination IP  (String)
DEST_GUID = 'Destination GUID'  # Destination     (String)

# Message Attributes

# JOIN MESSAGE = {
#     TYPE,
#     SEND_IP,
#     DEST_IP,
# }

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
ROUTING = 'Routing Table'               # The Routing Table ({IP, GUID})

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
SOURCE_IP = 'Source IP'                 # Ip of the query source (String)
SOURCE_GUID = 'Source GUID'             # GUID of the query source (String)
SEARCH = 'Search'                       # The query to search (String)
# The unique query id of the query (String)
QUERY_ID = 'Query ID'

# QUERY_RESP MESSAGE = {
#     TYPE,
#     SEND_IP,
#     SEND_GUID,
#     DEST_IP,
#     DEST_GUID,
#     QUERY_ID,
#     RESULTS,
# }
RESULTS = 'Results'                     # The Results received from the file system
# ([{FILE_ID, FT_NAME, NUM_CHUNKS, FT_CHECKSUM}, ])
# The total number of chunks in the file (Int)
NUM_CHUNKS = 'Total Chunks'

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
REQUEST_ID = 'Request ID'
FILE_ID = 'File ID'
CHUNK_NO = 'Chunk number'

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
CONTENT = 'Data'

############################# Routing Table Constants ###############
UPDATE_FREQ = 10
INACTIVE_LIMIT = 5

IP_ADDR = 'IPAddr'
RT_PORT = 'Port'
RT_ISACTIVE = 'ActiveBool'
RT_INACTIVE = 'InactiveTime'
RT_ISCENTRE = 'IsCentre'


############################# Node Constants ########################
LISTEN_QUEUE = 25               # The size of the connections queue
NUM_THREADS = 10                # The number of threads to use for the transfer
# The amount of time an individual thread waits before retrying when transferring data
TRANS_WAIT = 7

# Commands
HELP = 'help'                   # The Help Command
SEARCH_QUERY = 'search'         # Command to initiate search
DISPLAY = 'show'                # Command to display the results
CHOOSE = 'down'                 # Command to download the results
PROGRESS = 'progress'           # Command to display the progress
ABORT = 'abort'                 # Abort the download
SHARE = 'share'                 # Share Content
UNSHARE = 'remove'              # Unshare Content
