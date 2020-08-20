import socket
import string
import random
import asyncio
import websockets
import select
import time
import subprocess
import os
import shlex
from pifi.logger import Logger
from pifi.queue import Queue

class WebSocketServer:

    __PORT = 8765

    __logger = None

    def __init__(self):
        self.__logger = Logger().set_namespace(self.__class__.__name__)

        # cleanup
        cleanup_cmd = 'sudo rm -rf {}*'.format(shlex.quote(self.__get_unix_socket_path_prefix()))
        subprocess.check_output(cleanup_cmd, shell = True, executable = '/bin/bash')

    def run (self):
        local_ip = self.__get_local_ip()
        self.__logger.info("Starting websocket server at {}:{}".format(local_ip, self.__PORT))
        start_server = websockets.serve(self.server_connect, local_ip, self.__PORT)
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()

    # todo: automatically close old websockets when a new one is opened -- no reason to have multiple open.
    async def server_connect(self, websocket, path):
        uniq_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(5))
        # create a logger local to this thread so that the namespace isn't clobbered by another thread
        logger = Logger().set_namespace(self.__class__.__name__ + '__' + uniq_id)
        unix_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        unix_socket_path = self.__get_unix_socket_path_prefix() + uniq_id
        unix_socket.bind(unix_socket_path)
        logger.info("websocket server_connect. ws: " + str(websocket) + " path: " + str(path))

        while True:
            move = None

            # figure this shit out...
            # setting the timeout to 0.0000000001 maxes out CPU and ocasionally lags. Wheras setting to 0.01 doesnt max out
            # CPU and we don't lag (check log lines). But for some reason snake runs slower?? doesn't make sense since it's
            # a different process running snake...
            start = time.time()
            try:
                move = await asyncio.wait_for(websocket.recv(), 0.01)
            except asyncio.TimeoutError as e:
                pass
            except Exception as e2:
                logger.info("Exception reading from websocket. Ending game. Exception: " + str(e2))
                sent = unix_socket.sendto("game_over".encode(), Queue.UNIX_SOCKET_PATH)
                break

            elapsed = time.time() - start
            if elapsed >= 0.1:
                logger.info("reading from websocket took: {}".format(elapsed))

            if move is not None:
                sent = unix_socket.sendto(move.encode(), Queue.UNIX_SOCKET_PATH)

            is_ready_to_read, ignore1, ignore2 = select.select([unix_socket], [], [], 0)
            if is_ready_to_read:
                result, address = unix_socket.recvfrom(4096)
                result = result.decode()
                if result == 'close_websocket':
                    logger.info("got message: {} from: {}".format(result, address))
                    break
                else:
                    await websocket.send(result)

        unix_socket.shutdown(socket.SHUT_RDWR)
        unix_socket.close()
        os.remove(unix_socket_path)
        logger.info("ending ws server_connect")

    def __get_local_ip(self):
        return (subprocess
            .check_output(
                'ifconfig | grep -Eo \'inet (addr:)?([0-9]*\.){3}[0-9]*\' | grep -Eo \'([0-9]*\.){3}[0-9]*\' | grep -v \'127.0.0.1\'',
                stderr = subprocess.STDOUT, shell = True, executable = '/bin/bash'
            )
            .decode("utf-8")
            .strip())

    def __get_unix_socket_path_prefix(self):
        return Queue.UNIX_SOCKET_PATH + '_'
