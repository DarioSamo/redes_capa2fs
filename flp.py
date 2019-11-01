from rawsocketpy import RawSocket, RawRequestHandler, RawAsyncServer
import sys
import os

# Configuration file
MOUNTS_LIST = 'mounts.flp'

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

rawSocket = None
rawServer = None

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
    print "Received GETDIR message"

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
                    message.extend(filePath)
                    rawSocket.send(message, dest)

    # Send an empty DIR message which indicates no more entries are available.
    message = bytearray()
    message.append(DIR)
    rawSocket.send(message, dest)

def handleGetfile(data, dest):
    print "Received GETFILE message"
    message = bytearray()
    message.append(FILE)
    rawSocket.send(message, dest)

def handleGetblk(data, dest):
    print "Received GETBLK message"
    message = bytearray()
    message.append(BLK)
    rawSocket.send(message, dest)

def handleDir(data):
    print "Received DIR message"
    print data

def handleFile(data):
    print "Received FILE message"
    
def handleFnf(data):
    print "Received FNF message"
    
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

    def finish(self):
        print("End")

    def setup(self):
        print("Begin")

def startRawServer(interface):
    global rawServer
    rawServer = RawAsyncServer(interface, ETHER_TYPE, SharingHandler)
    rawServer.spin()

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
    global rawSocket
    rawSocket = RawSocket(interface, ETHER_TYPE)
    message = bytearray()
    message.append(GETFILE)
    message.append(remotepath)
    message.append(0)
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
