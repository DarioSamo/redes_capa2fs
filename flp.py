from rawsocketpy import RawSocket, RawRequestHandler, RawAsyncServer
import os
import struct
import sys

# Configuration
MOUNTS_LIST = 'mounts.flp'
SEQUENCE_SIZE = 1024

# RawSocket constants
ETHER_TYPE = 0xEEFA

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
saveToPath = ''

def decodeStr(data):
    return data.decode("utf-8").partition(b'\0')[0]

def showHelp():
    print('\nflp - File Exchange Linked In Public Environment:\nCommands:\n')
    print('share <interface>')
    print(' Starts the sharing server and listens to requests on the specified network interface.')
    print('mount <path>')
    print(' Adds a path to the list of shared directories.')
    print('unmount <path>')
    print(' Removes a path from the list of shared directories.')
    print('getdir <interface> <mac>')
    print(" Get the list of files available from the server at <interface> <mac>.\n")
    print('getfile <interface> <mac> <remotepath> <localpath>')
    print(" Download the file at <remotepath> from the server at <interface> <mac> and save it to <localpath>.")

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
        filehash = 123456789
        message.append(FILE)
        message.extend(struct.pack("QHI", filesize, SEQUENCE_SIZE, filehash))
        message.extend(remotepath.encode("utf-8"))
    else:
        message.append(FNF)
        message.extend(remotepath.encode("utf-8"))
        
    rawSocket.send(message, dest)

def handleGetblk(data, dest):
    print "Received GETBLK message"
    message = bytearray()
    message.append(BLK)
    rawSocket.send(message, dest)

def handleDir(data):
    remotepath = decodeStr(data)
    if ord(remotepath[0]) == 0:
        print "> END"
        sys.exit()
    else:
        print ">", remotepath

def handleFile(data):
    unpacked = struct.unpack("QHI", data[0:14])
    filesize = unpacked[0]
    seqsize = unpacked[1]
    filehash = unpacked[2]
    remotepath = decodeStr(data[14:])
    print "Received FILE message with size",filesize,"sequence size",seqsize,"hash",filehas,"from the remote path",remotepath

def handleFnf(data):
    remotepath = decodeStr(data)
    print "File not found in destination:", remotepath
    sys.exit(1)

def handleBlk(data):
    print "Received BLK message"

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
        elif header == FNF:
            handleFnf(data)
        elif header == BLK:
            handleBlk(data)
        else:
            print "Received unknown header", header

def startRawServer(interface):
    global rawServer
    rawServer = RawAsyncServer(interface, ETHER_TYPE, SharingHandler)
    rawServer.spin()

def stopRawServer():
    global rawServer
    rawServer.running = False

def share(interface):
    print "Sharing files on network interface", interface
    global rawSocket
    rawSocket = RawSocket(interface, ETHER_TYPE)
    startRawServer(interface)

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
    global rawSocket
    rawSocket = RawSocket(interface, ETHER_TYPE)
    message = bytearray()
    message.append(GETDIR)
    macDecoded = mac.replace(':', '').decode('hex')
    rawSocket.send(message, macDecoded)
    startRawServer(interface)

def getfile(interface, mac, remotepath, localpath):
    global saveToPath
    global rawSocket
    rawSocket = RawSocket(interface, ETHER_TYPE)
    message = bytearray()
    message.append(GETFILE)
    message.extend(remotepath.encode("utf-8"))
    saveToPath = localpath
    macDecoded = mac.replace(':', '').decode('hex')
    rawSocket.send(message, macDecoded)
    startRawServer(interface)

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
