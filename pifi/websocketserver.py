import asyncio
import subprocess
import time
import traceback
import websockets

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
        # create a logger local to this thread so that the namespace isn't clobbered by another thread
        logger = Logger().set_namespace(self.__class__.__name__ + '__' + Logger.make_uuid())
        logger.info("websocket server_connect. ws: " + str(websocket) + " path: " + str(path))

        try:
            # The client should send the playlist_video_id of the game they are joining as their first
            # message. The client is obtaining the playlist_video_id (via HTTP POST request) and
            # connecting to the websocket server concurrently, so give up to 5 seconds for the client
            # to get the playlist_video_id and send it to us.
            playlist_video_id_msg = await asyncio.wait_for(websocket.recv(), 5)
        except Exception as e:
            logger.info(f"Did not receive playlist_video_id message from client. Exception: {e}")
            self.__end_connection(logger)
            return

        unix_socket_helper = UnixSocketHelper()
        try:
            unix_socket_helper.connect(Queue.UNIX_SOCKET_PATH)
            unix_socket_helper.send_msg(playlist_video_id_msg)
        except Exception:
            logger.error('Caught exception: {}'.format(traceback.format_exc()))
            self.__end_connection(logger, unix_socket_helper)
            return

        while True:
            try:
                move = await websocket.recv()
            except Exception as e:
                logger.info(f"Exception reading from websocket. Ending game. Exception: {e}")
                break

            try:
                unix_socket_helper.send_msg(move)
            except Exception:
                logger.error(f'Unable to send move [{move}]: {traceback.format_exc()}')
                break

            if unix_socket_helper.is_ready_to_read():
                msg = None
                try:
                    msg = unix_socket_helper.recv_msg()
                except (SocketClosedException, ConnectionResetError):
                    logger.info("Unix socket was closed")
                    break # server detected game over and closed the socket

                await websocket.send(msg)

        self.__end_connection(logger, unix_socket_helper)

    def __end_connection(self, logger, unix_socket_helper = None):
        if unix_socket_helper:
            unix_socket_helper.close()
        logger.info("ending ws server_connect")

    def __get_local_ip(self):
        return (subprocess
            .check_output(
                'sudo ifconfig | grep -Eo \'inet (addr:)?([0-9]*\.){3}[0-9]*\' | grep -Eo \'([0-9]*\.){3}[0-9]*\' | grep -v \'127.0.0.1\'',
                stderr = subprocess.STDOUT, shell = True, executable = '/usr/bin/bash'
            )
            .decode("utf-8")
            .strip())
