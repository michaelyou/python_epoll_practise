import socket
import select


host = 'localhost'
port = 50000
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((host, port))

s.send("comming from select client\n\n")
s.close()
