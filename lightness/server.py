from http.server import HTTPServer, BaseHTTPRequestHandler
from io import BytesIO
import json
import subprocess
import ssl
import threading
from lightness.process import Process
from lightness.db import DB

class LightnessServerRequestHandler(BaseHTTPRequestHandler):

    __db = DB()
    __root_dir = "/home/pi/lightness/htdocs"

    def do_GET(self):
        print("GET")
        if self.path == '/':
            self.path = '/index.html'

        self.path = self.__root_dir + self.path

        ext = self.path[self.path.rfind(".")+1:].lower()

        is_bytes = False
        if ext == 'ico':
            is_bytes = True
        elif ext == 'woff':
            is_bytes = True
        elif ext == 'woff2':
            is_bytes = True
        elif ext == 'ttf':
            is_bytes = True

        try:
            if is_bytes:
                file_to_open = open(self.path, 'rb').read()
            else:
                file_to_open = open(self.path).read()
            self.send_response(200)
        except Exception as e:
            print(e)
            file_to_open = "File not found"
            self.send_response(404)

        self.end_headers()

        if is_bytes:
            self.wfile.write(file_to_open)
        else:
            self.wfile.write(bytes(file_to_open, 'utf-8'))

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)

        post_data = json.loads(body.decode("utf-8"))
        action = post_data['action']
        if (action == 'enqueue'):
            response = self.enqueue(post_data)
        elif (action == 'skip'):
            response = self.skip(post_data)
        elif (action == 'clear'):
            response = self.clear(post_data)
        else:
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.end_headers()
        resp = BytesIO()
        resp.write(bytes(json.dumps(response), 'utf-8'))
        self.wfile.write(resp.getvalue())

    def enqueue(self, post_data):
        url = post_data['url']
        is_color = post_data['color']

        response_details = {}
        response_details['url'] = url
        response_details['is_color'] = is_color

        self.__db.enqueue(url, is_color)

        response_details['success'] = True
        return response_details

    def skip(self, post_data):
        self.__db.skip()

        response_details = {}
        response_details['success'] = True
        return response_details

    def clear(self, post_data):
        self.__db.clear()

        response_details = {}
        response_details['success'] = True
        return response_details

class LightnessServer(threading.Thread):

    __secure = False

    def __init__(self, secure=False):
        threading.Thread.__init__(self)
        self.__secure = secure;
        self._stop_event = threading.Event()

    def run(self):
        if (not self.__secure):
            httpd = HTTPServer(('0.0.0.0', 80), LightnessServerRequestHandler)
        else:
            httpd = HTTPServer(('0.0.0.0', 443), LightnessServerRequestHandler)

            httpd.socket = ssl.wrap_socket (httpd.socket,
                                            keyfile="/home/pi/.sslcerts/private.key",
                                            certfile='/home/pi/.sslcerts/certificate.crt',
                                            server_side=True)
        while(not self.stopped()):
            httpd.handle_request()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()