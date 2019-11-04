from rawsocketpy import RawSocket, RawRequestHandler, RawAsyncServer
import os
import struct
import sys
import threading #for the timer
import zlib #crc32

# Configuration
MOUNTS_LIST = 'mounts.flp'
SEQUENCE_SIZE = 512
MAX_ACTIVE_BLOCKS = 5
 
# Constants
ETHER_TYPE = 0xB0CA
FILE_FORMAT = 'QHI'
GETBLK_FORMAT = 'I'
BLK_FORMAT = 'I'

UPDATE_DOWNLOADSPEED_DELAY = 0.25 #time between download speed updates
 
# Message headers
GETDIR  = '\x10'
DIR     = '\x11'
GETFILE = '\x20'
FILE    = '\x21'
FNF     = '\x22'
GETBLK  = '\x30'
BLK     = '\x31'
 
# Global variables
rawSocket = None
rawServer = None
ftPath = ''
ftRemotePath = ''
ftSeqSize = 0
ftSeqCount = 0
ftFinSeqCount = 0
ftSize = 0
ftHash = None
ftProgress = []
ftActiveBlocks = MAX_ACTIVE_BLOCKS
 
def decodeStr(data):
    return data.decode("utf-8").partition(b'\0')[0]
 
def showHelp():
    print('\n')
    print('####################################################')
    print('#--------------------------------------------------#')
    print('#--------------------------------------------------#')
    print('#----File Exchange Linked In Public Environment----#')
    print('#--------------------------------------------------#')
    print('#--------------------------------------------------#')
    print('####################################################')
    print('\nCommands:\n')
    print('share ')
    print(' Starts the sharing server and listens to requests on the specified network interface.\n')
    print('mount ')
    print(' Adds a path to the list of shared directories.\n')
    print('unmount ')
    print(' Removes a path from the list of shared directories.\n')
    print('getdir ')
    print(" Gets the list of files available from the server at .\n")
    print('getfile ')
    print(" Downloads the file at from the server at and saves it to .")
 
def handleGetdir(dest):
    # Read mounts file to get current directories.
    if os.path.isfile(MOUNTS_LIST):
        file = open(MOUNTS_LIST, "r")
        for line in file:
            mountPath = line.rstrip()
 
            # Search for all files in each directory and send a DIR message back for each one.
            for file in os.listdir(mountPath):
                filePath = os.path.join(mountPath, file)
                if os.path.isfile(filePath):
                    message = bytearray()
                    message.append(DIR)
                    message.extend(filePath.encode("utf-8"))
                    rawSocket.send(message, dest)
 
    # Send an empty DIR message which indicates no more entries are available.
    message = bytearray()
    message.append(DIR)
    rawSocket.send(message, dest)
 
def handleGetfile(data, dest):
    # TODO: Validate if remotepath is a file inside one of the mounted directories.
    message = bytearray()
    remotepath = decodeStr(data)
    if os.path.isfile(remotepath):
        filesize = os.path.getsize(remotepath)
        filehash = crc(remotepath)
        message.append(FILE)
        message.extend(struct.pack(FILE_FORMAT, filesize, SEQUENCE_SIZE, filehash))
        message.extend(remotepath.encode("utf-8"))
    else:
        message.append(FNF)
        message.extend(remotepath.encode("utf-8"))
       
    rawSocket.send(message, dest)

def crc(fileName):
    prev = 0
    for eachLine in open(fileName,"rb"):
        prev = zlib.crc32(eachLine, prev)
    return (prev & 0xFFFFFFFF)

def handleGetblk(data, dest):
    replyMessage = bytearray()
    packSize = struct.calcsize(GETBLK_FORMAT)
    unpacked = struct.unpack(GETBLK_FORMAT, data[0:packSize])
    seqn = unpacked[0]
    remotePath = decodeStr(data[packSize:])
    if os.path.isfile(remotePath):
        file = open(remotePath, 'rb')
        file.seek(seqn * SEQUENCE_SIZE)
        block = file.read(SEQUENCE_SIZE)
        file.close()
 
        replyMessage.append(BLK)
        replyMessage.extend(struct.pack(BLK_FORMAT, seqn))
        replyMessage.extend(block)
        blockPadding = SEQUENCE_SIZE - len(block)
        if blockPadding > 0:
            replyMessage.extend([b'\0'] * blockPadding)
 
        replyMessage.extend(remotePath.encode("utf-8"))
    else:
        replyMessage.append(FNF)
        replyMessage.extend(remotePath.encode("utf-8"))
       
    rawSocket.send(replyMessage, dest)
 
def handleDir(data):
    if ord(data[0]) == 0:
        print "> END"
        sys.exit()
    else:
        remotePath = decodeStr(data)
        print ">", remotePath
 
def handleFile(data):
    global ftSeqSize
    global ftSeqCount #Block amount
    global ftFinSeqCount #Finished blocks
    global ftSize
    global ftHash
    global ftProgress
    packSize = struct.calcsize(FILE_FORMAT)
    unpacked = struct.unpack(FILE_FORMAT, data[0:packSize])
    ftSize = unpacked[0]
    ftSeqSize = unpacked[1]
    ftHash = unpacked[2]
    ftSeqCount = (ftSize // ftSeqSize) + ((ftSize % ftSeqSize) > 0)
    ftFinSeqCount = 0
    ftProgress = [0] * ftSeqCount
    remotePath = decodeStr(data[packSize:])
    start_timer_downloadspeed(ftFinSeqCount) #starts download speed's timer

 
    # Create empty file for writing.
    file = open(ftPath, "wb")
    file.seek(ftSize - 1)
    file.write('\0')
    file.close()
 
def handleFnf(data):
    remotePath = decodeStr(data)
    print "File not found in destination:", remotePath
    sys.exit(1)
 
def handleBlk(data):
    global ftActiveBlocks
    global ftProgress
    global ftFinSeqCount
    packSize = struct.calcsize(BLK_FORMAT)
    unpacked = struct.unpack(BLK_FORMAT, data[0:packSize])
    seqn = unpacked[0]
    blockEnd = packSize + ftSeqSize
    rest = (ftSize % ftSeqSize)
    if seqn == (len(ftProgress) - 1) and rest > 0:
        blockEnd = packSize + rest
 
    block = data[packSize:blockEnd]
    pathStart = packSize + ftSeqSize
    remotePath = decodeStr(data[pathStart:])
    if ftRemotePath == remotePath:
        file = open(ftPath, "rb+")
        file.seek(seqn * ftSeqSize)
        file.write(block)
        file.close()
        ftProgress[seqn] = 2
        ftActiveBlocks += 1
	ftFinSeqCount += 1

def start_timer_downloadspeed(lastFinSeqCount):
    global ftFinSeqCount
    global ftSeqCount
    speed = (ftFinSeqCount - lastFinSeqCount) * SEQUENCE_SIZE / UPDATE_DOWNLOADSPEED_DELAY
    if(ftFinSeqCount < ftSeqCount): #si es menor, no termino todavia
	timer = threading.Timer(UPDATE_DOWNLOADSPEED_DELAY, start_timer_downloadspeed,[ftFinSeqCount])
	timer.start() 
    print_progressbar(ftFinSeqCount, ftSeqCount, speed, decimals=1)
   
# Print iterations progress
def print_progressbar(iteration, total, speed, prefix='Downloading', decimals=1, bar_length=50):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string [Byte/s] (Str)
        speed       - Required  : download speed  (Double)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        bar_length  - Optional  : character length of bar (Int)
    """
    str_format = "{0:." + str(decimals) + "f}"
    percents = str_format.format(100 * (iteration / float(total)))
    filled_length = int(round(bar_length * iteration / float(total)))
    bar = '#' * filled_length + '-' * (bar_length - filled_length)

    unit = 'B'
    if(speed > 1024): # if greater than 1k
        speed /= 1024.0#format KBps
	unit = 'KB'
    if(speed > 1024): # if greather than 1mega
	speed /= 1024.0 #format MBps
	unit = 'MB'

    sys.stdout.write('\r%s |%s| %s%s [%.2f %s/s]  ' % (prefix, bar, percents, '%', speed, unit)),
    #                                           ^^ these are totally necessary, pls do not delete
    if iteration == total:
        sys.stdout.write('\n')
    sys.stdout.flush()
 
 
 
def checkActiveFt(dest):
    global ftActiveBlocks
    global ftHash
    global ftPath #localpath
    if len(ftProgress) > 0:
        finished = True
        for i in range(0, len(ftProgress)):
            # Block hasn't been requested for transfer yet.
            if ftProgress[i] == 0:
                finished = False
                if ftActiveBlocks > 0:
                    ftProgress[i] = 1
                    message = bytearray()
                    message.append(GETBLK)
                    message.extend(struct.pack(GETBLK_FORMAT, i))
                    message.extend(ftRemotePath.encode("utf-8"))
                    rawSocket.send(message, dest)
                    ftActiveBlocks -= 1
            # Block has been requested for transfer.
            elif ftProgress[i] == 1:
                finished = False
               
       
        if finished:
            ftNewHash = crc(ftPath)
            if(ftNewHash == ftHash):
                print_progressbar(1, 1, 0, decimals=1) #prints a hard-coded full progressbar :P
                sys.exit()
            else:
                print("Hash error, quitting...")
                sys.exit()
#TODO QUE REINICIE LA WEA
 
class SharingHandler(RawRequestHandler):
    def handle(self):
        header = self.packet.data[0]
        data = self.packet.data[1:]
        if header == GETDIR:
            handleGetdir(self.packet.src)
        elif header == GETFILE:
            handleGetfile(data, self.packet.src)
        elif header == GETBLK:
            handleGetblk(data, self.packet.src)
        elif header == DIR:
            handleDir(data)
        elif header == FILE:
            handleFile(data)
            checkActiveFt(self.packet.src)
        elif header == FNF:
            handleFnf(data)
        elif header == BLK:
            handleBlk(data)
            checkActiveFt(self.packet.src)
        else:
            print "Received unknown header", header
 
def createRawSocket(interface):
    global rawSocket
    rawSocket = RawSocket(interface, ETHER_TYPE)
 
def createRawServer(interface):
    global rawServer
    rawServer = RawAsyncServer(interface, ETHER_TYPE, SharingHandler)
 
def initRawServer():
    rawServer.spin()
 
def stopRawServer():
    global rawServer
    rawServer.running = False
 
def share(interface):
    print "Sharing files on network interface", interface
    createRawSocket(interface)
    createRawServer(interface)
    initRawServer()
 
def mount(path):
    # Make sure the path is not in the active mounts list.
    if os.path.isfile(MOUNTS_LIST):
        file = open(MOUNTS_LIST, "r")
        for line in file:
            if line.rstrip() == path:
                print "Path", path, "is already mounted."
                file.close()
                return False
 
    # Append the new directory to the end of the file.
    if os.path.isdir(path):
        file = open(MOUNTS_LIST, "a")
        file.write(path + "\n")
        file.close()
        print "Mounted", path, "successfully."
        return True
    else:
        print "Path", path, "is not a valid directory."
        return False
 
def unmount(path):
    if os.path.isfile(MOUNTS_LIST):
        file = open(MOUNTS_LIST, "r")
        lines = list()
        unmounted = False
        for line in file:
            if not (line.rstrip() == path):
                lines.append(line)
            else:
                unmounted = True
 
        file.close()
 
        if unmounted:
            file = open(MOUNTS_LIST, "w")
            file.writelines(lines)
            file.close()
            print "Unmounted", path, "successfully."
        else:
            print "Path", path, "not found in mount list."
 
def getdir(interface, mac):
    createRawSocket(interface)
    createRawServer(interface)
    message = bytearray()
    message.append(GETDIR)
    macDecoded = mac.replace(':', '').decode('hex')
    rawSocket.send(message, macDecoded)
    initRawServer()
 
def getfile(interface, mac, remotepath, localpath):
    global ftPath
    global ftRemotePath
    createRawSocket(interface)
    createRawServer(interface)
    message = bytearray()
    message.append(GETFILE)
    message.extend(remotepath.encode("utf-8"))
    ftPath = localpath
    ftRemotePath = remotepath
    macDecoded = mac.replace(':', '').decode('hex')
    rawSocket.send(message, macDecoded)
    initRawServer()
 
argCount = len(sys.argv)
if argCount >= 2:
    command = sys.argv[1]
    if (command == 'share') and (argCount >= 3):
        share(sys.argv[2])
    elif (command == 'mount') and (argCount >= 3):
        mount(sys.argv[2])
    elif (command == 'unmount') and (argCount >= 3):
        unmount(sys.argv[2])
    elif (command == 'getdir') and (argCount >= 4):
        getdir(sys.argv[2], sys.argv[3])
    elif (command == 'getfile') and (argCount >= 6):
        getfile(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    else:
        showHelp()
else:
    showHelp()
