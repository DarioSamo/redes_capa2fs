from rawsocketpy import RawSocket

sock = RawSocket("ens33", 0xEEFA)
sock.send("some data")