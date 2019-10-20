from rawsocketpy import RawSocket, to_str

print("hola1")
sock = RawSocket("ens33", 0xEEFA)
print("hola2")
packet = sock.recv()
print("hola3")
# The type of packet is RawPacket() which allows pretty printing and unmarshal the raw data.

# If you are using Python2, all data is encoded as unicode strings "\x01.." while Python3 uses bytearray.

print(packet) # Pretty print
packet.dest # string "\xFF\xFF\xFF\xFF\xFF\xFF" or bytearray(b"\xFF\xFF\xFF\xFF\xFF\xFF")
packet.src # string "\x12\x12\x12\x12\x12\x13" or bytearray(b"\x12\x12\x12\x12\x12\x13")
packet.type # string "\xEE\xFA" or bytearray([b"\xEE\xFA"]
packegt.data # string "some data" or bytearray(b"some data"]

print(to_str(packet.dest)) # Human readable MAC: FF:FF:FF:FF:FF:FF
print(to_str(packet.type, "")) # Human readable type: EEFA