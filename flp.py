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

rawSocket = 0
rawServer = 0

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

def handleGetdir(packet, dest):
    print "Received GETDIR message"
    messageByteArray = bytearray()
    messageByteArray.append(DIR)
    messageByteArray.append('mydirectory')
    messageByteArray.append(0)
    rawSocket.send(messageByteArray, dest)

def handleGetfile(packet, dest):
    print "Received GETFILE message"

def handleGetblk(packet, dest):
    print "Received GETBLK message"

def handleDir(packet):
    print "Received DIR message"

def handleFile(packet):
    print "Received FILE message"
    
def handleFnf(packet):
    print "Received FNF message"
    
def handleBlk(packet):
    print "Received BLK message"

class SharingHandler(RawRequestHandler):
    def handle(self):
        header = self.packet.data[0]
        if header == GETDIR:
            handleGetdir(self.packet.data, self.packet.src)
        elif header == GETFILE:
            handleGetfile(self.packet.data, self.packet.src)
        elif header == GETBLK:
            handleGetblk(self.packet.data, self.packet.src)
        elif header == DIR:
            handleDir(self.packet.data)
        elif header == FILE:
            handleFile(self.packet.data)
        elif header == FNF:
            handleFnf(self.packet.data)
        elif header == BLK:
            handleBlk(self.packet.data)
        else:
            print "Received unknown header", header

    def finish(self):
        print("End")

    def setup(self):
        print("Begin")

def share(interface):
    print "Sharing files on network interface", interface
    rawSocket = RawSocket(interface, ETHER_TYPE)
    rawServer = RawAsyncServer(interface, ETHER_TYPE, SharingHandler)
    rawServer.spin()

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
    rawSocket = RawSocket(interface, ETHER_TYPE)
    messageByteArray = bytearray()
    messageByteArray.append(GETDIR)
    macDecoded = mac.replace(':', '').decode('hex')
    rawSocket.send(messageByteArray, macDecoded)
    rawServer = RawAsyncServer(interface, ETHER_TYPE, SharingHandler)
    rawServer.spin()

def getfile(interface, mac, remotepath, localpath):
    rawSocket = RawSocket(interface, ETHER_TYPE)
    messageByteArray = bytearray()
    messageByteArray.append(GETFILE)
    messageByteArray.append(remotepath)
    messageByteArray.append(0)
    macDecoded = mac.replace(':', '').decode('hex')
    rawSocket.send(messageByteArray, macDecoded)
    rawServer = RawAsyncServer(interface, ETHER_TYPE, SharingHandler)
    rawServer.spin()

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
