#!/usr/bin/env python3
import tempfile
import threading
import socketserver
import time
import atexit

import convert
import upload
import control

mutex = threading.Lock()

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
                if all(v == 0 for v in out):
                    self.request.sendall(b'Error converting image (no transparency pls)\n')
                    return
                self.request.sendall(f'Converted image size: {len(out)}\n'.encode())
                with mutex:
                    upload.FemtoCircleUpload().send_file("output.bin", [out])
                    upload.FemtoCircleUpload().send_file("output2.bin", [out])
                    upload.FemtoCircleUpload().send_file("output3.bin", [out])
                    upload.FemtoCircleUpload().send_file("output4.bin", [out])
                    client = control.FemtoCircleControl()
                    client.playFileFromList(1) # TODO get OUTPUT.BIN index from client.state.filelist
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
    HOST, PORT = "0.0.0.0", 4242

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

        def shutdown():
            server.shutdown()
        atexit.register(shutdown)

        server.serve_forever()
