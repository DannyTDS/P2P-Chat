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