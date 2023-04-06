import socket
import sys
import json


def main():
    try:
        server_host = sys.argv[1]
        server_port = int(sys.argv[2])
    except IndexError:
        print("Usage: python3 TestNameServer.py <server_host> <server_port>")
        sys.exit(1)
    s1, s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM), socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s1.bind(('localhost', 0))
    s2.bind(('localhost', 0))
    s1.connect((server_host, server_port))
    s2.connect((server_host, server_port))

    print("S1 registering...")
    msg = {'op': 'register', 'name': 'user1', 'address': ':'.join([str(x) for x in s1.getsockname()]), 'status': 'online'}
    s1.sendall(len(json.dumps(msg)).to_bytes(8, 'big') + json.dumps(msg).encode())
    print("S2 registering...")
    msg = {'op': 'register', 'name': 'user2', 'address': ':'.join([str(x) for x in s2.getsockname()]), 'status': 'online'}
    s2.sendall(len(json.dumps(msg)).to_bytes(8, 'big') + json.dumps(msg).encode())

    print("S1 looking up user2...")
    msg = {'op': 'lookup', 'name': 'user2'}
    s1.sendall(len(json.dumps(msg)).to_bytes(8, 'big') + json.dumps(msg).encode())
    res = json.loads(s1.recv(1024).decode())
    addr = res['address'].split(':')
    print("User2 is at {}:{}".format(addr[0], addr[1]))

    print("S1 looking up user3 (doesn't exist)...")
    msg = {'op': 'lookup', 'name': 'user3'}
    s1.sendall(len(json.dumps(msg)).to_bytes(8, 'big') + json.dumps(msg).encode())
    print("S1 received: {}".format(json.loads(s1.recv(1024).decode())))

    s1.close()
    s2.close()


if __name__ == '__main__':
    main()


friends = {
    'user1': {
        'address': '129.168.0.0:1234',
        'status': 'online',
    },
}