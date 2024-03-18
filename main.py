import urllib.parse
import mimetypes
import json
import logging
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from datetime import datetime

from jinja2 import Environment, FileSystemLoader
from threading import Thread

BASE_DIR = Path()
BUFFER_SIZE = 1024
HTTP_PORT = 3000
HTTP_HOST = 'localhost'
SOCKET_HOST = '127.0.0.1'
SOCKET_PORT = 5000
jinja = Environment(loader=FileSystemLoader(BASE_DIR.joinpath('templates')))


class MyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        route = urllib.parse.urlparse(self.path)
        match route.path:
            case '/':
                self.send_html('index.html')
            case '/message':
                self.send_html('message.html')
            case _:
                file = BASE_DIR.joinpath(route.path[1:])
                if file.exists():
                    self.send_static(file)
                else:
                    print(f'File {file} not found')
                    self.send_html('error.html', 404)

    def do_POST(self):
        size = int(self.headers.get('Content-Length'))
        data = self.rfile.read(size)

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.sendto(data, (SOCKET_HOST, SOCKET_PORT))
        client_socket.close()

        self.send_response(302)
        self.send_header('Location', '/message')
        self.end_headers()

    def send_html(self, filename, status_code=200):
        self.send_response(status_code)
        mime_type = mimetypes.guess_type(filename)[0]
        if mime_type:
            self.send_header('Content-type', mime_type)
        else:
            self.send_header('Content-type', 'text/plain')
        self.end_headers()
        with open(filename, 'rb') as f:
            self.wfile.write(f.read())

    def send_static(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as f:
            self.wfile.write(f.read())


def sava_data_from_form(data):
    parce_data = urllib.parse.unquote_plus(data.decode())
    final_dict = {}
    try:
        parce_dict = {key: value for key, value in
                      [el.split('=') for el in parce_data.split('&')]}
        with open('storage/data.json', 'w') as f:
            date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            final_dict[str(date)] = parce_dict
            logging.info(f'Data saved: {parce_dict}')
            json.dump(final_dict, f, ensure_ascii=False, indent=4)
    except ValueError as err:
        logging.error(err)
    except OSError as err:
        logging.error(err)

def run_socket_server(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((host, port))
    logging.info(f'Socket server started on {host}:{port}')
    try:
        while True:
            msg, address = server_socket.recvfrom(BUFFER_SIZE)
            logging.info(f'Received message from {address}: {msg.decode()}')
            sava_data_from_form(msg)
    except KeyboardInterrupt:
        server_socket.close()
        print('Server stopped')

def run_http_server(host, port):
    address = (host, port)
    http_server = HTTPServer(address, MyServer)
    try:
        http_server.serve_forever()
        logging.info(f'HTTP server started on {host}:{port}')
    except KeyboardInterrupt:
        pass
    finally:
        http_server.server_close()
        print('Server stopped')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(threadName)s %(message)s')
    
    server = Thread(target=run_http_server, args=(HTTP_HOST, HTTP_PORT))
    server.start()

    server_socket = Thread(target=run_socket_server, args=(SOCKET_HOST, SOCKET_PORT))
    server_socket.start()
