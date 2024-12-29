#!/usr/bin/env python3
from pwn import *

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <path to image> <target>")
    sys.exit(1)

data = read(sys.argv[1])
io = remote(sys.argv[2], 4242)
io.sendafter(b'Byte count: ', str(len(data)).encode())
io.sendafter(b'bytes: ', data)
result = io.recvallS()
print(result)
io.close()
