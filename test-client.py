from Client import P2PClient
import select
import socket
import sys
from time import strftime, localtime
TIMEOUT = 1

if __name__ == "__main__":
    # Get user's information
    try:
        nameserver = sys.argv[1]
        nshost, nsport = nameserver.split(":")
        nsport = int(nsport)
    except (IndexError, ValueError):
        print("Usage: python test-client.py <nameserver_host>:<nameserver_port>")
        exit(1)
    username = input("Enter your username: ")
    port = int(input("Enter your ID number: "))
    host = socket.gethostname()
    #print("Your host is " + host + "Your port is " + str(port) + ". Your username is " + username + ".")
    # Initialize the P2P client
    p2p_client = P2PClient(username, host, port, nameserver=(nshost, nsport))
    # Start the server
    #p2p_client.start_server()
    flag=False
    while True:
        if not flag:
            print("> ", end="", flush=True)
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
        # post system
        elif command and command.split()[0] == 'post':
            try:
                args = command.split()[1:]
                action = args[0]
                if action == 'upload':
                    fpath = args[1]
                    p2p_client.upload_post(fpath)
                elif action == 'remove':
                    post_id = args[1]
                    p2p_client.remove_post(post_id)
                elif action == 'list':
                    p2p_client.list_posts()
                elif action == 'get':
                    friend_username, post_id = args[1], args[2]
                    p2p_client.get_post(friend_username, post_id)
                else:
                    raise ValueError("Unrecognized combination.")
            except (IndexError, ValueError):
                print("\tUsage: post upload|remove|list|get")
                print("\t| post upload path_to_file")
                print("\t| post remove post_id")
                print("\t| post list")
                print("\t| post get friend_username post_id")
        else:
            print("Invalid command. Please try again.")
        
    # conn = p2p_client.connect_to_friend("weike")
    # while True:
    #     msg = input("> ")
    #     p2p_client.send_msg_to_friend("weike", msg)
    #     p2p_client.handle_client(conn)