import os
import errno
import socket
import select

# unix dgram socket toy example: https://gist.github.com/dasl-/d2e97baeb640e320f8cf8d73a9a3ab2c
# unix stream socket toy example: https://gist.github.com/dasl-/e220fedee43ac16dc212fd053775e4e9
class UnixSocketHelper:

    __CONNECTION_HANDSHAKE_MSG = 'connection_handshake_msg'

    # fixed message length encoding scheme
    __MSG_LENGTH = 256

    __SOCKET_TIMEOUT_S = 3

    # a socket we can call `accept` on
    __server_socket = None

    # a socket we can send and receive data on
    __connection_socket = None

    def __init__(self):
        __server_socket = None
        __connection_socket = None

    def create_server_unix_socket(self, socket_path):
        unix_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            os.remove(socket_path)
        except OSError as e: # this would be "except OSError, e:" before Python 2.6
            if e.errno != errno.ENOENT: # errno.ENOENT = no such file or directory
                raise e # re-raise exception if a different error occurred
        unix_socket.bind(socket_path)

        # don't let socket.accept() block indefinitely if something goes wrong
        # https://docs.python.org/3/library/socket.html#notes-on-socket-timeouts
        unix_socket.settimeout(self.__SOCKET_TIMEOUT_S)
        unix_socket.listen(16)
        return unix_socket

    def set_server_socket(self, socket):
        self.__server_socket = socket
        return self

    def set_connection_socket(self, socket):
        self.__connection_socket = socket
        return self

    # raises socket.timeout, SocketConnectionHandshakeException, and others
    def accept(self):
        self.__connection_socket, unused_address = self.__server_socket.accept()
        self.__connection_socket.settimeout(self.__SOCKET_TIMEOUT_S)
        self.__exchange_connection_handshake_messages()


    # raises socket.timeout, SocketConnectionHandshakeException, and others
    def connect(self, socket_path):
        self.__connection_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.__connection_socket.settimeout(self.__SOCKET_TIMEOUT_S)
        self.__connection_socket.connect(socket_path)
        self.__exchange_connection_handshake_messages()
        return self

    def is_ready_to_read(self):
        is_ready_to_read, ignore1, ignore2 = select.select([self.__connection_socket], [], [], 0)
        return bool(is_ready_to_read)

    # param: msg - string
    # return: void
    # raises: exception, i.e. if trying to send on a socket whose other end has been closed (BrokenPipeError).
    #   Maybe other types of exceptions too?
    def send_msg(self, msg):
        if len(msg) > self.__MSG_LENGTH:
            raise Exception("Message is too long: {}".format(msg))
        self.__connection_socket.sendall(msg.ljust(self.__MSG_LENGTH).encode())

    # return: string
    # raises: ConnectionResetError, SocketClosedException if the other end of the socket was closed. Maybe other
    #   types of exceptions too?
    def recv_msg(self):
        msg = b''
        msg_len = len(msg)
        while msg_len < self.__MSG_LENGTH:
            # can raise ConnectionResetError if other end of socket was closed
            msg += self.__connection_socket.recv(self.__MSG_LENGTH - msg_len)
            msg_len = len(msg)

            # receiving 0 bytes indicates the connection has been closed: https://docs.python.org/3.7/howto/sockets.html#using-a-socket
            if msg_len == 0:
                raise SocketClosedException("unix socket was closed")
        return msg.decode().rstrip()

    def close(self):
        if self.__connection_socket == None:
            return
        self.__connection_socket.shutdown(socket.SHUT_RDWR)
        self.__connection_socket.close()

    # A client calling `connect` can return before the server has called `accept` on the corresponding connection.
    # The client won't know whether the server has actually accepted its connection until trying to send / receive
    # some data. Sending alone can also return immediately with no indication of error.
    #
    # For an example of this scenario, see: https://gist.github.com/dasl-/90ff02273aa11416e85117eba2ecb05e
    #
    # Thus, force both ends of the connection to send and receive a handshake message after calling `accept` and
    # `connect`. We will know if the connection failed immediately.
    def __exchange_connection_handshake_messages(self):
        try:
            self.send_msg(self.__CONNECTION_HANDSHAKE_MSG)
            if self.recv_msg() != self.__CONNECTION_HANDSHAKE_MSG:
                raise SocketConnectionHandshakeException("didn't receive expected connection handshake message.")
        except SocketConnectionHandshakeException as e:
            raise e
        except Exception as e2:
            raise SocketConnectionHandshakeException("Wrapping original exception: {}".format(e2))

class SocketClosedException(Exception):
    pass

class SocketConnectionHandshakeException(Exception):
    pass
