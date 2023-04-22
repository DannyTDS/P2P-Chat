import socket
import json

class TestClient:
    def __init__(self, server_addr):
        server_host, server_port = server_addr.split(':')
        server_port = int(server_port)
        self.server_addr = (server_host, server_port)
    
    def new_socket(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(self.server_addr)
        return s
    
    def recv(self, s):
        sz = s.recv(8)
        length = int.from_bytes(sz, "big")
        msg = b''
        while len(msg) < length:
            to_read = length - len(msg)
            msg += s.recv(1024 if to_read > 1024 else to_read)
        return json.loads(msg.decode())

    def register(self, name, status='online') -> bool:
        s = self.new_socket()
        msg = {'op': 'register', 'name': name, 'address': (str(x) for x in s.getsockname()), 'status': status}
        s.send(len(json.dumps(msg)).to_bytes(8, 'big') + json.dumps(msg).encode())
        res = self.recv(s)
        s.close()
        return res['status'] == 'ok'
    
    def lookup(self, name):
        s = self.new_socket()
        msg = {'op': 'lookup', 'name': name}
        s.send(len(json.dumps(msg)).to_bytes(8, 'big') + json.dumps(msg).encode())
        res = self.recv(s)
        s.close()
        return res if res['status'] != 'error' else None