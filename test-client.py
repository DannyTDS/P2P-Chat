from Client import P2PClient
import socket
if __name__ == "__main__":
    # Get user's information
    username = input("Enter your username: ")
    port = int(input("Enter your port number: "))
    host = socket.gethostname()
    print("Your host is " + host + "Your port is " + str(port) + ". Your username is " + username + ".")
    # Initialize the P2P client
    p2p_client = P2PClient(username, host, port)
    # Start the server
    #p2p_client.start_server()
    conn = p2p_client.connect_to_friend("weike")
    while True:
        msg = input("> ")
        p2p_client.send_msg_to_friend("weike", msg)
        p2p_client.handle_client(conn)