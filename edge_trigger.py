# encoding=utf-8
import socket
import select


EOL1 = b'\n\n'
EOL2 = b'\n\r\n'
response = b'HTTP/1.0 200 OK\r\nDate: Mon, 1 Jan 1996 01:01:01 GMT\r\n'
response += b'Content-Type: text/plain\r\nContent-Length: 13\r\n\r\n'
response += b'Hello, world!'

serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
serversocket.bind(('0.0.0.0', 8080))
# 监听等待队列的大小
# 它告诉了操作系统, 在python代码accept前, 缓存多少TCP/IP连接在队列中.
# 每次python代码调用accept()的时候, 一个连接从队列中移除,
# 为新的连接进来空出一个位置. 如果队列满了, 新的连接自动放弃
serversocket.listen(1)
serversocket.setblocking(0)

epoll = select.epoll()
# 注册为边缘触发
epoll.register(serversocket.fileno(), select.EPOLLIN | select.EPOLLET)

try:
    connections = {}
    requests = {}
    responses = {}
    while True:
        events = epoll.poll(1)
        for fileno, event in events:
            if fileno == serversocket.fileno():
                try:
                    # 边沿触发程序需要调用accept建立新的socket连接直到一个socket.error错误产生,
                    # 然后状态触发下只需要处理一个单独的accept(),
                    # 然后继续epoll查询新的事件来判断是否有新的accept需要操作
                    while True:
                        connection, address = serversocket.accept()
                        connection.setblocking(0)
                        epoll.register(connection.fileno(), select.EPOLLIN | select.EPOLLET)
                        connections[connection.fileno()] = connection
                        requests[connection.fileno()] = b''
                        responses[connection.fileno()] = response
                except socket.error:
                    pass
            elif event & select.EPOLLIN:
                try:
                    while True:
                        requests[fileno] += connections[fileno].recv(1024)
                except socket.error:
                    pass
                if EOL1 in requests[fileno] or EOL2 in requests[fileno]:
                    epoll.modify(fileno, select.EPOLLOUT | select.EPOLLET)
                    print('-'*40 + '\n' + requests[fileno].decode()[:-2])
            elif event & select.EPOLLOUT:
                try:
                    while len(responses[fileno]) > 0:
                        byteswritten = connections[fileno].send(responses[fileno])
                        responses[fileno] = responses[fileno][byteswritten:]
                except socket.error:
                    pass
                if len(responses[fileno]) == 0:
                    epoll.modify(fileno, select.EPOLLET)
                    connections[fileno].shutdown(socket.SHUT_RDWR)
            elif event & select.EPOLLHUP:
                epoll.unregister(fileno)
                connections[fileno].close()
                del connections[fileno]
finally:
    epoll.unregister(serversocket.fileno())
    epoll.close()
    serversocket.close()
