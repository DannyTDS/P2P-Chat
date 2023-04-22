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
    while True:
        command = input(">")
        if command == "quit" or command == "exit":
            print("Exiting commandline...")
            break
        elif command == "listen":
            p2p_client.start_server()
        elif command.split()[0] == "connect":
            username = command.split()[1]
            conn = p2p_client.connect_to_friend(username)
            while True:
                msg = input(">> ")
                if msg == "quit" or msg == "exit":
                    print("Exiting chat...")
                    break
                p2p_client.send_msg_to_friend(username, msg)
                p2p_client.handle_client(conn)
        else:
            print("Invalid command. Please try again.")
    # Start the server
    #p2p_client.start_server()
    #p2p_client.connect_to_friend("wfang")
    #p2p_client.send_msg_to_friend("wfang", "Hello!")