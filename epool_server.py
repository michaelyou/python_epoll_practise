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
serversocket.listen(1)
# 非阻塞
serversocket.setblocking(0)

# 状态触发

epoll = select.epoll()
# 监听读取事件
epoll.register(serversocket.fileno(), select.EPOLLIN)

try:
    # 映射文件描述符（file descriptors，整型）到对应的网络连接对象上
    connections = {}
    requests = {}
    responses = {}
    while True:
        # 最多等待1秒
        events = epoll.poll(1)
        # 返回文件描述符和event code
        for fileno, event in events:
            if fileno == serversocket.fileno():
                # 因为是监听socket的事件，需要重新生成一个描述符
                connection, address = serversocket.accept()
                connection.setblocking(0)
                # 注册read事件
                epoll.register(connection.fileno(), select.EPOLLIN)
                connections[connection.fileno()] = connection
                requests[connection.fileno()] = b''
                responses[connection.fileno()] = response
            # 发生读取事件
            elif event & select.EPOLLIN:
                requests[fileno] += connections[fileno].recv(1024)
                if EOL1 in requests[fileno] or EOL2 in requests[fileno]:
                    # 一旦完整的http请求接收到, 取消注册读取事件, 注册写入事件(EPOLLOUT), 写入事件在能够发送数据回客户端的时候产生
                    epoll.modify(fileno, select.EPOLLOUT)
                    # TCP_CORK 参数可以设置缓存消息直到一起被发送
                    # 适合给一个实现 http/1.1pipelining 的服务器来使用
                    connections[fileno].setsockopt(socket.IPPROTO_TCP, socket.TCP_CORK, 1)
                    # 即使通讯是交错的, 数据本身是作为一个完整的信息组合和处理的
                    print('-' * 40 + '\n' + requests[fileno].decode()[:-2])
            # 发生写入事件
            elif event & select.EPOLLOUT:
                byteswritten = connections[fileno].send(responses[fileno])
                # 一次发送一部分返回数据, 直到所有数据都交给操作系统的发送队列
                responses[fileno] = responses[fileno][byteswritten:]
                if len(responses[fileno]) == 0:
                    # 所有的返回数据都发送完, 取消监听读取和写入事件.
                    epoll.modify(fileno, 0)
                    connections[fileno].shutdown(socket.SHUT_RDWR)
            # HUP(hang-up)事件表示客户端断开了连接(比如 closed), 所以服务器这端也会断开. 不需要注册HUP事件, 因为它们都会标示到注册在epoll的socket
            elif event & select.EPOLLHUP:
                # 取消注册
                epoll.unregister(fileno)
                # 断开连接
                connections[fileno].close()
                del connections[fileno]
finally:
    # 在这里的异常捕捉的作用是, 我们的例子总是采用键盘中断来停止程序执行
    # 虽然开启的socket不需要手动关闭, 程序退出的时候会自动关闭, 明确写出来这样的代码, 是更好的编码风格
    epoll.unregister(serversocket.fileno())
    epoll.close()
    serversocket.close()
