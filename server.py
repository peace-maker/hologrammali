#!/usr/bin/env python3
import tempfile
import threading
import socketserver
import time

import convert
import upload

class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):

    def handle(self):
        self.request.settimeout(5)
        self.request.sendall(b'Hi. Send an image to display.\nByte count: ')
        data = str(self.request.recv(1024), 'ascii')
        size = int(data)
        if size <= 0 or size > 3 * 1024 * 1024:
            self.request.sendall(b'Invalid size\n')
            return
        self.request.sendall(f'Awaiting {size} bytes: '.encode())
        data = b''
        while len(data) < size:
            data += self.request.recv(size)
        
        try:
            with tempfile.NamedTemporaryFile() as f:
                f.write(data)
                f.flush()
                out = convert.convert_image(f.name)
                if all(out, lambda x: x == 0):
                    self.request.sendall(b'Error converting image (no transparency pls)\n')
                    return
                self.request.sendall(f'Converted image size: {len(out)}\n'.encode())
                upload.FemtoCircleUpload().send_file("output.bin", [out])
        except Exception as e:
            self.request.sendall(b'Error converting image\n')
            print(e)
            return
        with open(f'uploaded/{time.time()}.image', 'wb') as f:
            f.write(data)
        self.request.sendall(b'OK\n')

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


if __name__ == "__main__":
    # Port 0 means to select an arbitrary unused port
    HOST, PORT = "0.0.0.0", 1337

    server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
    with server:
        ip, port = server.server_address

        # Start a thread with the server -- that thread will then start one
        # more thread for each request
        server_thread = threading.Thread(target=server.serve_forever)
        # Exit the server thread when the main thread terminates
        server_thread.daemon = True
        server_thread.start()
        print("Server loop running in thread:", server_thread.name)

        server.serve_forever()