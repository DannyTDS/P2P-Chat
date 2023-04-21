import socket
import sys
import json


class Client:
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
        msg = {'op': 'register', 'name': name, 'address': ':'.join([str(x) for x in self.socket.getsockname()]), 'status': status}
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


def main():
    try:
        server_addr= sys.argv[1]
        if ':' not in server_addr:
            raise IndexError
    except IndexError:
        print("Usage: python3 TestNameServer.py '<server_host>:<server_port>'")
        sys.exit(1)
    
    c1, c2 = Client(server_addr), Client(server_addr)

    print("S1 registering...")
    assert(c1.register('user1'))
    print("S2 registering...")
    assert(c2.register('user2'))

    print("S1 looking up user2...")
    user2 = c1.lookup('user2')
    assert(user2)
    addr = user2['address'].split(':')
    print("User2 is at {}:{}".format(addr[0], addr[1]))

    print("S1 looking up user3 (doesn't exist)...")
    user3 = c1.lookup('user3')
    assert(not user3)
    print("Failed to find user3")

    print("All tests passed!")


if __name__ == '__main__':
    main()


# friends = {
#     'user1': {
#         'address': '129.168.0.0:1234',
#         'status': 'online',
#     },
# }