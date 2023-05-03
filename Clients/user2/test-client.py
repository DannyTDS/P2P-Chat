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
    port = int(input("Enter your ID number (port): "))
    host = socket.gethostname()
    #print("Your host is " + host + "Your port is " + str(port) + ". Your username is " + username + ".")
    # Initialize the P2P client
    p2p_client = P2PClient(username, host, port, nameserver=(nshost, nsport))
    # Start the server
    #p2p_client.start_server()
    flag=False
    online=False
    online_counter = 0
    while True:
        online_counter += 1
        if not flag:
            print("> ", end="", flush=True)
            flag=True
        if online and online_counter % 30 == 0:
            p2p_client.go_online()
            online_counter = 1
        rlist, wlist, xlist = select.select([sys.stdin], [], [], TIMEOUT)
        if rlist:
            # user has entered input
            command = input("")
            command = command.strip()
            flag=False
        else:
            # no input received within the timeout period
            status = p2p_client.handle_udp()
            if status == True:
                flag = False
            continue
        if command == "quit" or command == "exit":
            print("Exiting commandline...")
            break
        elif command == "online":
            #p2p_client.connect_to_name_server()
            res = p2p_client.go_online()
            p2p_client.update_friend_info()
            if res:
                print("Successfully go online")
            else:
                print("Failed to go online")
            online = True
        elif command == "offline":
            p2p_client.go_offline()
        elif command and command.split()[0] == "history":
            try:
                username = command.split()[1]
            except IndexError:
                print("Usage: history <username>")
                continue
            p2p_client.get_chat_history(username)
        elif command == "listen": # open to chat
            p2p_client.start_server()
        elif command and len(command.split()) >= 3 and command.split()[0] == "message": # send udp message to a friend
            username = command.split()[1]
            msg = " ".join(command.split()[2:]).strip('"')
            p2p_client.send_udp_msg(username, msg)
        elif command == "update":
            p2p_client.update_friend_info()
        elif command and command.split()[0] == "lookup":
            try:
                username = command.split()[1]
            except IndexError:
                print("Usage: lookup <username>")
                continue
            res = p2p_client.lookup(username)
            print("User: ", username)
            print("Status: ", res["status"])
            last_time = strftime('%Y-%m-%d %H:%M:%S', localtime(res["last_update"]))
            print("Last updated: ", last_time)

        elif command and command.split()[0] == "connect": #connect to friend
            try:
                username = command.split()[1]
            except IndexError:
                print("Usage: connect <username>")
                continue
            conn = p2p_client.connect_to_friend(username)
            if not conn:
                print("Failed to connect to friend")
                continue
            while True:
                msg = input("> ")
                if msg == "quit" or msg == "exit":
                    print("Exiting chat...")
                    p2p_client.send_msg_to_friend(username, msg)
                    break
                p2p_client.send_msg_to_friend(username, msg)
                rec = p2p_client.handle_client(conn)
                if rec == "Fault":
                    break
        elif command == "list": # list friends
            p2p_client.list_friends()
        elif command and command.split()[0] == "add": # add friend
            try:
                friend_username = command.split()[1]
            except IndexError:
                print("Usage: add <username>")
                continue
            #addr = p2p_client.lookup(username)
            p2p_client.send_friend_request(friend_username)
        ### group chat ###
        elif command and len(command.split()) >= 2 and command.split()[0] == 'create_group':
            group_name = command.split()[1]
            if len(command.split()) > 2:
                is_public = bool(command.split()[2])
            else:
                is_public = True
            p2p_client.create_group(group_name, is_public)
        elif command and len(command.split()) >= 2 and command.split()[0] == 'join_group':
            p2p_client.join_group(command.split()[1])
        elif command and len(command.split()) >= 2 and command.split()[0] == 'leave_group':
            p2p_client.leave_group(command.split()[1])
        elif command and len(command.split()) >= 3 and command.split()[0] == 'invite':
            group_name = command.split()[1]
            friend_username = command.split()[2]
            p2p_client.invite_to_group(group_name, friend_username)
        elif command and len(command.split()) >= 3 and command.split()[0] == 'remove_member':
            group_name = command.split()[1]
            friend_username = command.split()[2]
            p2p_client.remove_member(group_name, friend_username)
        elif command and len(command.split()) >= 3 and command.split()[0] == 'broadcast':
            group_name = command.split()[1]
            message = " ".join(command.split()[2:]).strip('"')
            p2p_client.broadcast(group_name, message)
        

        #### post system ###
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