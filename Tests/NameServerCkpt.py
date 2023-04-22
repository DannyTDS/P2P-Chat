import sys
from TestClient import TestClient as Client


def main():
    try:
        server_addr= sys.argv[1]
        if ':' not in server_addr:
            raise IndexError
    except IndexError:
        print("Usage: python3 TestNameServer.py '<server_host>:<server_port>'")
        sys.exit(1)
    c = Client(server_addr)
    for i in range(15):
        print(i)
        status = 'online' if i%2==0 else 'offline'
        c.register('user1', status)


if __name__ == '__main__':
    main()