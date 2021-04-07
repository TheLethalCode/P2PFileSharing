# End character for send/receive messages.
EOM_CHAR = 0x04.to_bytes(1, 'big')
# Default Port for creating socket connection.
PORT = 4000
# Default encoding.
ENCODING = 'utf-8'
# Storage path for Hashed FileSystem
FILESYS_PATH = "fs.pkl"

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
