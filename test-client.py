from Client import P2PClient
import select
import socket
import sys
from time import strftime, localtime
TIMEOUT = 5

if __name__ == "__main__":
    # Get user's information
    username = input("Enter your username: ")
    port = int(input("Enter your ID number: "))
    host = socket.gethostname()
    #print("Your host is " + host + "Your port is " + str(port) + ". Your username is " + username + ".")
    # Initialize the P2P client
    p2p_client = P2PClient(username, host, port)
    # Start the server
    #p2p_client.start_server()
    flag=False
    while True:
        if not flag:
            print(">", end="", flush=True)
            flag=True
        rlist, wlist, xlist = select.select([sys.stdin], [], [], TIMEOUT)
        if rlist:
            # user has entered input
            command = input("")
            flag=False
        else:
            # no input received within the timeout period
            p2p_client.handle_udp()
            continue
        if command == "quit" or command == "exit":
            print("Exiting commandline...")
            break
        elif command == "online":
            #p2p_client.connect_to_name_server()
            p2p_client.go_online()
        elif command == "offline":
            p2p_client.go_offline()
        elif command and command.split()[0] == "history":
            username = command.split()[1]
            p2p_client.get_chat_history(username)
        elif command == "listen": # open to chat
            p2p_client.start_server()
        elif command == "update":
            p2p_client.update_friend_info()
        elif command and command.split()[0] == "lookup":
            username = command.split()[1]
            res = p2p_client.lookup(username)
            print("User: ", username)
            print("Status: ", res["status"])
            last_time = strftime('%Y-%m-%d %H:%M:%S', localtime(res["last_update"]))
            print("Last updated: ", last_time)

        elif command and command.split()[0] == "connect": #connect to friend
            username = command.split()[1]
            conn = p2p_client.connect_to_friend(username)
            while True:
                msg = input("> ")
                if msg == "quit" or msg == "exit":
                    print("Exiting chat...")
                    break
                p2p_client.send_msg_to_friend(username, msg)
                p2p_client.handle_client(conn)
        elif command == "list": # list friends
            p2p_client.list_friends()
        elif command and command.split()[0] == "add": # add friend
            friend_username = command.split()[1]
            #addr = p2p_client.lookup(username)
            p2p_client.send_friend_request(friend_username)
        else:
            print("Invalid command. Please try again.")
        
    # conn = p2p_client.connect_to_friend("weike")
    # while True:
    #     msg = input("> ")
    #     p2p_client.send_msg_to_friend("weike", msg)
    #     p2p_client.handle_client(conn)