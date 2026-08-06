#!/usr/bin/env python
import socket


TCP_IP = '192.168.0.100'
TCP_PORT = 10001
BUFFER_SIZE = 1024

#MESSAGE = "eec" + "\r"
#MESSAGE = "EMON" + "\r"
#MESSAGE = "SDC 0.0" + "\r"
#MESSAGE = "EMOFF" + "\r"
MESSAGE = "ABN" + "\r"

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((TCP_IP, TCP_PORT))
s.send(MESSAGE.encode())
print("1")
data = s.recv(1024).decode()
print("2")
s.close()

print("received data: " + data)