# encoding=utf-8
import socket
import time

EOL1 = b'\n\n'
EOL2 = b'\n\r\n'
response = b'HTTP/1.0 200 OK\r\nDate: Mon, 1 Jan 1996 01:01:01 GMT\r\n'
response += b'Content-Type: text/plain\r\nContent-Length: 13\r\n\r\n'
response += b'Hello, world!'

serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
serversocket.bind(('localhost', 50000))
serversocket.listen(1)

try:
    while True:
        connectiontoclient, address = serversocket.accept()
        # 虽然生成了新的socket，但是不是多线程，仍然是顺序执行的，同一时刻只有一个请求
        request = b''
        while EOL1 not in request and EOL2 not in request:
            request += connectiontoclient.recv(1024)
        print(request.decode())
        connectiontoclient.send(response)
        time.sleep(5)
        connectiontoclient.close()
finally:
    serversocket.close()
