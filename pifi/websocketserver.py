import string
import random
import asyncio
import websockets
import time
import subprocess
import traceback
from pifi.logger import Logger
from pifi.queue import Queue
from pifi.games.unixsockethelper import UnixSocketHelper, SocketClosedException

class WebSocketServer:

    __PORT = 8765

    def __init__(self):
        self.__logger = Logger().set_namespace(self.__class__.__name__)

    def run(self):
        local_ip = self.__get_local_ip()
        self.__logger.info("Starting websocket server at {}:{}".format(local_ip, self.__PORT))
        start_server = websockets.serve(self.server_connect, local_ip, self.__PORT)
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()

    async def server_connect(self, websocket, path):
        uniq_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(5))
        # create a logger local to this thread so that the namespace isn't clobbered by another thread
        logger = Logger().set_namespace(self.__class__.__name__ + '__' + uniq_id)
        logger.info("websocket server_connect. ws: " + str(websocket) + " path: " + str(path))

        is_connect_success = True
        unix_socket_helper = UnixSocketHelper()
        try:
            logger.info("Calling unix_socket_helper.connect")
            unix_socket_helper.connect(Queue.UNIX_SOCKET_PATH)
            logger.info("Done calling unix_socket_helper.connect")
        except Exception:
            is_connect_success = False
            logger.error('Caught exception: {}'.format(traceback.format_exc()))

        while is_connect_success:
            move = None

            # figure this shit out...
            # setting the timeout to 0.0000000001 maxes out CPU and ocasionally lags. Wheras setting to 0.01 doesnt max out
            # CPU and we don't lag (check log lines). But for some reason snake runs slower?? doesn't make sense since it's
            # a different process running snake...
            start = time.time()
            try:
                move = await asyncio.wait_for(websocket.recv(), 0.01)
            except asyncio.TimeoutError:
                pass
            except Exception as e2:
                logger.info("Exception reading from websocket. Ending game. Exception: " + str(e2))
                break

            elapsed = time.time() - start
            if elapsed >= 0.1:
                logger.info("reading from websocket took: {}".format(elapsed))

            if move is not None:
                try:
                    unix_socket_helper.send_msg(move)
                except Exception:
                    logger.error('Unable to send move: {}'.format(traceback.format_exc()))
                    break

            if unix_socket_helper.is_ready_to_read():
                msg = None
                try:
                    msg = unix_socket_helper.recv_msg()
                except (SocketClosedException, ConnectionResetError):
                    logger.info("Unix socket was closed")
                    break # server detected game over and closed the socket

                await websocket.send(msg)

        unix_socket_helper.close()
        logger.info("ending ws server_connect")

    def __get_local_ip(self):
        return (subprocess
            .check_output(
                r'sudo ifconfig | grep -Eo \'inet (addr:)?([0-9]*\.){3}[0-9]*\' | grep -Eo \'([0-9]*\.){3}[0-9]*\' | grep -v \'127.0.0.1\'',
                stderr = subprocess.STDOUT, shell = True, executable = '/bin/bash'
            )
            .decode("utf-8")
            .strip())
