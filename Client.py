#!/usr/bin/env python3

import os, shutil
import socket
import json
import time
from protocols import *
from datetime import datetime

NAMESERVER = ("129.74.152.141", 47697)
UPDATE_INTERVAL = 60
ACK_TIMEOUT = 5
MSG_SIZE = 1024

DEFAULT = {}

# Helper functions
def save_chat_history(username, chat_history):
    # Implement saving chat history to username-chat.json
    # chat_history is a dictionary of {username: [chat]}
    # chat is a list of (timestamp, username, message)
    with open(username + '-chat.json', 'w') as f:
        json.dump(chat_history, f)
    return chat_history

def load_chat_history(username):
    # Implement loading chat history
    # chat_history is a dictionary of {username: [chat]}
    # chat is a list of (timestamp, username, message)
    try:
        with open(username + '-chat.json', 'r') as f:
            chat_history = json.load(f)
    except FileNotFoundError:
        chat_history = {}
    return chat_history

def load_friends(username):
    # Implement loading friends from a file username.json
    # load it into a dictionary
    try:
        with open(username + '.json', 'r') as f:
            friends = json.load(f)
        for friend in friends:
            if isinstance(friends[friend]["address"], str):
                host, port = friends[friend]["address"].split()
                friends[friend]["address"] = (host, int(port))
    except FileNotFoundError:
        friends = DEFAULT
    return friends

def save_friends(username, friends):
    # Implement saving friends to a file username.json
    with open(username + '.json', 'w') as f:
        json.dump(friends, f)
    return friends


def save_groups(username, groups):
    # Implement saving groups to a file username-groups.json
    with open(username + '-groups.json', 'w') as f:
        json.dump(groups, f)
    return groups

def load_groups(username):
    # Implement loading groups from a file username-groups.json
    try:
        with open(username + '-groups.json', 'r') as f:
            groups = json.load(f)
    except FileNotFoundError:
        groups = {}
    return groups
# Edge case: If receive fails, return none and 
# the corresponding operation should retry sending request
def receive_response(conn):
    while True:
        try:
            sz = conn.recv(8)
            length = int.from_bytes(sz, "big")
            data = b''
            while len(data) < length:
                to_read = length - len(data)
                data += conn.recv(MSG_SIZE if to_read > MSG_SIZE else to_read)
            break
        except:
            print("Receive error: cannot receive message.")
            return None
    # If data is not None, decode it
    data = data.decode()
    return data



# Send UDP
def send_udp(topic, from_host, from_port, to_host, to_port, content=None, name = None):
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.settimeout(10)
    message = {
            'senderHost': from_host,
            'senderPort': from_port,
            'topic': topic,
        }
    if content:
        message['content'] = content
    if name:
        message['senderName'] = name
    message = json.dumps(message).encode()
    udp_sock.sendto(message, (to_host, to_port))
    # wait for response
    #retry_count = 1
    try:
        response, _ = udp_sock.recvfrom(MSG_SIZE)
    except socket.timeout:
        return None

    response = json.loads(response.decode())
    if response['status'] == 'success':
        return response
    else:
        res = {'status': 'error'}
    udp_sock.close()
    return res


# Client class
# Currently, only allow one connection at a time
class P2PClient:
    def __init__(self, username, host, port, nameserver=NAMESERVER):
        # Name server host and port
        self.username = username
        self.host = host
        self.port = port
        self.friends = load_friends(username) # Format: {username: {'address': addr, 'status': status, 'last_update': last_update}}}
        self.chat_history = load_chat_history(username)
        self.online = False
        self.nameserver = nameserver # (host, port)
        self.nameserverconn = False
        self.friendconn = False
        self.udpsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udpsock.bind((self.host, self.port))
        self.udpsock.settimeout(5.0)
        self.chat_history = {}
        self.posts = {}     # {post_id : post_path} mapping
        self.post_cnt = 0   # monotonically increasing identifier for new post
        self.groups = load_groups(username)    # {group_name : [group_members]} mapping

    def __del__(self):
        save_chat_history(self.username, self.chat_history)
        save_friends(self.username, self.friends)
        save_groups(self.username, self.groups)
        self.udpsock.close()
        if not isinstance(self.nameserverconn, bool):
           self.nameserverconn.close()
        if not isinstance(self.friendconn, bool):
           self.friendconn.close()
        
    
    def list_friends(self):
        # Implement listing friends
        # Return a list of friends
        for name, friend_info in self.friends.items():
            print(name + " " + friend_info['status'])

    def get_chat_history(self, friend):
        # Implement getting chat history
        # Return a list of (timestamp, username, message)
        if friend in self.chat_history:
            for chat in self.chat_history[friend]:
                print(chat[2] + "  " + chat[0] + ":  " + chat[1])
            return self.chat_history[friend]
        else:
            print("No chat history with {}".format(friend))
            return []

    # process a dictionary response and
    # return encoded message and length
    def _process_response(self, response):
        message = json.dumps(response).encode()
        length = len(message).to_bytes(8, 'big')
        return message, length


    ### Interactions with Name Server ###
    # Send a message to the name server
    # Edge case: If send fails, sleep for a while
    # and then close the socket, reconnect, and send again
    def _send_response_to_server(self, message, length):
        retry_counter = 0
        while True:
            try:
                self.connect_to_name_server()
                self.nameserverconn.send(length + message)
                break
            except:
                print("Send error: cannot send message. Retry in {} seconds".format(2**retry_counter))
                time.sleep(2**retry_counter)
                self.nameserverconn.close()
                self.connect_to_name_server()
                retry_counter += 1
                continue

    def connect_to_name_server(self):
        # Implement connection to the name server
        self.nameserverconn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        retry_counter = 0
        success = False
        while True:
            try:
                host, port = self.nameserver
                self.nameserverconn.connect((host, port))
                success = True
            except:
                print("Connection error: cannot connect to nameserver. Retry in {} seconds".format(2**retry_counter))
                time.sleep(2**retry_counter)
                retry_counter += 1
                continue
            if success:
                # print("Connected to host: {} and port: {}".format(self.host, self.port))
                break
    
    def update_friend_info(self):
        # Implement updating friend info from the name server
        retry_counter = 0
        for friend in self.friends:
            package = NSPackage('lookup', friend)
            message, length = self._process_response(package.to_dict())
            self._send_response_to_server(message, length)
            data = receive_response(self.nameserverconn)
            while not data:
                time.sleep(2**retry_counter)
                print("Receive error: cannot receive message from nameserver on update_friend. Retry in {} seconds".format(2**retry_counter))
                retry_counter += 1
                self._send_response_to_server(message, length)
                data = receive_response(self.nameserverconn)
            friend_info = json.loads(data)
            self.friends[friend] = friend_info # {'address': addr, 'status': status, 'last_update': last_update}
    
    def go_online(self):
        # Implement going online and updating the name server
        package = NSPackage('register', self.username, (self.host, self.port), 'online')
        message, length = self._process_response(package.to_dict())
        self._send_response_to_server(message, length)
        data = receive_response(self.nameserverconn)
        retry_counter = 0
        while not data:
            print("Receive error: cannot receive message from nameserver on go_online. Retry in {} seconds".format(2**retry_counter))
            time.sleep(2**retry_counter)
            self._send_response_to_server(message, length)
            data = receive_response(self.nameserverconn)
        response = json.loads(data)
        if response['status'] == 'ok':
            self.online = True
            return True
        else:
            return False
    
    def go_offline(self):
        # Implement going offline and updating the name server
        package = NSPackage('register', self.username, (self.host, self.port), 'offline')
        message, length = self._process_response(package.to_dict())
        self._send_response_to_server(message, length)
        data = receive_response(self.nameserverconn)
        retry_counter = 0
        while not data:
            print("Receive error: cannot receive message from nameserver on go_offline. Retry in {} seconds".format(2**retry_counter))
            time.sleep(2**retry_counter)
            self._send_response_to_server(message, length)
            data = receive_response(self.nameserverconn)
        response = json.loads(data)
        if response['status'] == 'ok':
            self.online = False
            print("Successfully go offline")
        else:
            print("Error: cannot go offline")

    def lookup(self, username):
        # Implement looking up a peer from name server
        package = NSPackage('lookup', username)
        message, length = self._process_response(package.to_dict())
        self._send_response_to_server(message, length)
        data = receive_response(self.nameserverconn)
        retry_counter = 0
        while not data:
            print("Receive error: cannot receive message from nameserver on lookup. Retry in {} seconds".format(2**retry_counter))
            time.sleep(2**retry_counter)
            self._send_response_to_server(message, length)
            data = receive_response(self.nameserverconn)
        response = json.loads(data)
        if response:
            # print("Successfully lookup {}".format(username))
            if isinstance(response["address"], str):
                    host, port = response["address"].split()
                    port = int(port)
                    response["address"] = (host, port)
            if username in self.friends:
                self.friends[username] = response
            return response # {'address': addr, 'status': status, 'last_update': last_update}
        else:
            print("Error: cannot lookup")
            return None

    ### Interactions with Friends ###

    # receive a message (data) from a friend (conn)
    def connect_to_friend(self, username):
        if username not in self.friends:
            print("Error: you are not friends with this user")
            return False
        if self.friends[username]['status'] == 'offline':
            print("Error: this user is offline")
            return False
        addr = self.friends[username]['address']
        self.friendconn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.friendconn.settimeout(5.0)
        retry_counter = 0
        success = False
        # send connection request udp packet
        if isinstance(addr, str):
            to_host, to_port = addr.split()[0], int(addr.split()[1])
        else:
            to_host, to_port = addr
        res = send_udp('connect', self.host, self.port, to_host, to_port, "connection request from {}".format(self.username), self.username)
        while not res:
            print(f"Error: cannot send connection request to {username} {to_host}:{to_port} retry in {2**retry_counter} sec")
            time.sleep(1)
            res = send_udp('connect', self.host, self.port, to_host, to_port, "connection request from {}".format(self.username), self.username)
            retry_counter += 1
            if retry_counter > 10:
                return False
        if res["status"] == 'success':
            print("Connection request to {} is accepted. Connecting...".format(username))
        else:
            print("Error: cannot send or refused connection request to {}".format(username))
            return False

        while True:
            try:
                host, port = addr
                self.friendconn.connect((host, port))
                success = True
            except:
                print("Connection error: cannot connect to friend. Retry in {} seconds".format(2**retry_counter))
                time.sleep(2**retry_counter)
                retry_counter += 1
                continue
            if success:
                print("Connected to host: {} and port: {}".format(host, port))
                break
        return self.friendconn

    # handle udp packet request
    def handle_udp(self):
        # receive udp packet
        try:
            message, addr = self.udpsock.recvfrom(MSG_SIZE)
        except: #timeout
            return False
        message = json.loads(message.decode())
        if message["topic"] == "connect":
            print("Received connection request from {}".format(message["senderName"]) + " with content {}".format(message["content"]))
            decision = input("Do you accept the request? (yes/no): ")
            if decision.lower() == 'yes':
                self.udpsock.sendto(json.dumps({'status': 'success'}).encode(), addr)
                self.start_server(message["senderName"])
                #return True
            else:
                self.udpsock.sendto(json.dumps({'status': 'reject'}).encode(), addr)
                #return False
        elif message["topic"] == 'add friend':
            friendname = message["content"]["username"]
            print(f"Received friend request from {friendname}")
            decision = input("Do you accept the request? (yes/no): ")
            if decision.lower() == 'yes':
                self.udpsock.sendto(json.dumps({'status': 'success'}).encode(), addr)
                # add friend
                content = message["content"]
                fhost, fport = content["host"], content["port"]
                self.friends[content["username"]] = {'address': (fhost, fport), 'status': 'online', 'last_update': time.time()}
                #return True
            else:
                self.udpsock.sendto(json.dumps({'status': 'reject'}).encode(), addr)
                #return False
        elif message["topic"] == "join group":
            user_name, group_name = message["content"].split()
            print(f"Received join group request from {user_name} to join group {group_name}")
            decision = input("Do you accept the request? (yes/no): ")
            if decision.lower() == 'yes':
                self.groups[group_name]["members"].append((user_name, addr))
                save_groups(self.username, self.groups)
                self.udpsock.sendto(json.dumps({'status': 'success', "leader": self.username, "members":self.groups[group_name]["members"]}).encode(), addr)
            else:
                self.udpsock.sendto(json.dumps({'status': 'reject'}).encode(), addr)
                return False
        elif message["topic"] == "invite to group":
            sender_name, group_name = message["content"].split()
            print(f"Received invite to group {group_name} from {sender_name}")
            decision = input("Do you accept the request? (yes/no): ")
            if decision.lower() == 'yes':
                self.udpsock.sendto(json.dumps({'status': 'success'}).encode(), addr)
                # add group
                group_host, group_port = message["senderHost"], message["senderPort"]
                self.groups[group_name] = {"leader": sender_name, "members": [(self.username, addr)], "address": (group_host, group_port)}
                save_groups(self.username, self.groups)
                #return True
            else:
                self.udpsock.sendto(json.dumps({'status': 'reject'}).encode(), addr)
                #return False
        elif message["topic"] == "remove from group":
            sender_name, group_name = message["content"].split()
            print(f"You are removed from group {group_name} by {sender_name}")
            self.groups.pop(group_name)
            save_groups(self.username, self.groups)
            self.udpsock.sendto(json.dumps({'status': 'success'}).encode(), addr)
        elif message["topic"] == "leave group":
            def find_member_index(group_name, friend_username):
                for i, member in enumerate(self.groups[group_name]["members"]):
                    if member[0] == friend_username:
                        return i
                return -1
            sender_name, group_name = message["content"].split()
            print(f"{sender_name} left group {group_name}")
            if sender_name == self.username:
                print("Leaders cannot leave group")
                self.udpsock.sendto(json.dumps({'status': 'reject'}).encode(), addr)
            else:
                self.groups[group_name]["members"].pop(find_member_index(group_name, sender_name))
                save_groups(self.username, self.groups)
                self.udpsock.sendto(json.dumps({'status': 'success'}).encode(), addr)
        elif message["topic"] == "broadcast":
            group_name = message["senderName"]
            sender_name = message["content"].split()[0]
            message_content = " ".join(message["content"].split()[1:])
            print("Group {}".format(group_name))
            print(f"{sender_name} broadcasted:")
            print(message_content)
            self.udpsock.sendto(json.dumps({'status': 'success'}).encode(), addr)
        elif message["topic"] == "broadcast_request":
            print("Received broadcast request from {}".format(message["senderName"]))
            group_name = message["senderName"]
            sender_name = message["content"].split()[0]
            message_content = " ".join(message["content"].split()[1:])
            self.udpsock.sendto(json.dumps({'status': 'success'}).encode(), addr)
            self.broadcast(group_name, message_content, sender_name)
            print("Group {}".format(group_name))
            print(f"{sender_name} broadcasted:")
            print(message_content)
        elif message["topic"] == 'new post':
            print("There is a new post from {}!".format(message["senderName"]))
        elif message["topic"] == 'get post':
            self.send_post(message["senderName"], message["senderHost"], message["senderPort"], message["content"])
        elif message["topic"] == 'post':
            print("\n" + message["senderName"] + " posted:")
            print(message["content"] + "\n> ", end="")
        elif message["topic"] == "message":
            print("\n" + message["senderName"] + " sent you a message:")
            print(message["content"] + "\n", end="")
            self.udpsock.sendto(json.dumps({'status': 'success'}).encode(), addr)
        else:
            print("Received udp packet with unknown topic")
            print(message)
        return True
    
    def send_udp_msg(self, friendname, msg):
        if friendname not in self.friends:
            print("Error: you are not friends with this user")
            return False
        if self.friends[friendname]['status'] == 'offline':
            print("Error: this user is offline")
            return False
        addr = self.friends[friendname]['address']
        if isinstance(addr, str):
            to_host, to_port = addr.split()[0], int(addr.split()[1])
        else:
            to_host, to_port = addr
        res = send_udp('message', self.host, self.port, to_host, to_port, msg, self.username)
        if res:
            print("Message sent to {}".format(friendname))
        else:
            print("Error: cannot send message to {}".format(friendname))
        return res

    def handle_friend_request(self, conn, data):
        # Implement handling friend request from a peer
        response = json.loads(data)
        if response['type'] == 'friend_request':
            friend_username = response['username']
            addr = response['address']
            timestamp = response['timestamp']
            print(f"{friend_username} wants to be your friend.")
            decision = input("Do you accept the request? (yes/no): ")
            if decision.lower() == 'yes':
                self.friends[friend_username] = {'address': addr, 'status': 'online', 'last_update': timestamp}
                save_friends(self.username, self.friends)
                message = {"status": "success"}
                message, length = self._process_response(message)
                conn.sendall(length + message)
                print(f"{friend_username} is now your friend.")
            else:
                message = {"status": "failure"}
                message, length = self._process_response(message)
                conn.sendall(length + message)
                print(f"You rejected {friend_username}'s friend request.")
    
    def send_friend_request(self, friend_username):
        # Implement sending friend request to a peer
        if friend_username in self.friends:
            print(f"{friend_username} is already your friend.")
            return
        friend_info = self.lookup(friend_username)
        if friend_info is None:
            print("User not found.")
            return
        friend_host, friend_port = friend_info["address"]
        friend_online = (friend_info["status"] == "online") # True or False
        if not friend_online:
            print(f"{friend_username} is not online.")
            return
        package = NSPackage('add_friend', username=self.username, friend=friend_username)
        message, length = self._process_response(package.to_dict())
        self._send_response_to_server(message, length)
        data = receive_response(self.nameserverconn)
        retry_counter = 0
        while not data:
            print("Receive error: cannot receive message from nameserver on lookup. Retry in {} seconds".format(2**retry_counter))
            time.sleep(2**retry_counter)
            self._send_response_to_server(message, length)
            data = receive_response(self.nameserverconn)
        response = json.loads(data)
        if not response:
            return
        if response["status"] == "success":
            print(f"{friend_username} accepted your friend request.")
            self.friends[friend_username] = {'address': (friend_host, friend_port), 'status': 'online', 'last_update': time.time()}
            save_friends(self.username, self.friends)
        else:
            print(f"{friend_username} rejected your friend request.")
        # with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        #     try:
        #         s.connect((friend_host, friend_port))
        #         request = {
        #             'type': 'friend_request',
        #             'username': self.username,
        #             'address': (self.host, self.port),
        #             'timestamp': time.time(),
        #         }
        #         message, length = self._process_response(request)
        #         s.send(length + message)
        #         response = receive_response(s)
        #         response = json.loads(response)
        #         if not response:
        #             return
        #         if response["status"] == "success":
        #             print(f"{friend_username} accepted your friend request.")
        #             self.friends[friend_username] = {'address': (friend_host, friend_port), 'status': 'online', 'last_update': time.time()}
        #             save_friends(self.username, self.friends)
        #         else:
        #             print(f"{friend_username} rejected your friend request.")
        #     except Exception as e:
        #         print(f"Error sending friend request: {str(e)}")

    def disconnect(self):
        # Implement disconnecting and updating the name server and friends
        self.go_offline()
        for friend_username in self.friends:
            self.send_msg_to_friend(friend_username, "Goodbye!")
        self.friendconn.close()

    def send_msg_to_friend(self, friend_username, msg):
        # Implement sending a message to a friend and handling acknowledgement
        if friend_username not in self.friends:
            print(f"{friend_username} is not your friend.")
            return
        friend_info = self.friends[friend_username]
        friend_host, friend_port = friend_info["address"]
        friend_online = (friend_info["status"] == "online") # True or False
        if not friend_online:
            print(f"{friend_username} is not online.")
            return
        
        if not self.friendconn:
            self.connect_to_friend(friend_username)
        try:
            request = {
                'type': 'message',
                'username': self.username,
                'message': msg,
            }
            message, length = self._process_response(request)
            self.friendconn.send(length + message)
            response = receive_response(self.friendconn)
            if not response:
                return
            response = json.loads(response)
            if response["status"] == "success":
                #print(f"Message sent to {friend_username}.")
                if friend_username not in self.chat_history:
                    self.chat_history[friend_username] = []
                dt_string = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                self.chat_history[friend_username].append((self.username, msg, dt_string))
                pass
            else:
                print(f"Message failed to send to {friend_username}.")
        except Exception as e:
            print(f"Error sending message to {friend_username}: {str(e)}")

    def handle_incoming_msg(self, conn, data):
        # Implement handling incoming messages and sending acknowledgements
        response = json.loads(data)
        if response['type'] == 'message':
            friend_username = response['username']
            if friend_username not in self.chat_history:
                self.chat_history[friend_username] = []
            msg = response['message']
            if msg == "exit" or msg == "quit":
                print(f"{friend_username} has exited.")
                self.chat_history[friend_username].append((friend_username, msg, datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
                message = {"status": "success"}
                message, length = self._process_response(message)
                conn.sendall(length + message)
                return "Fault"
            print(f"{friend_username}: {msg}")
            dt_string = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            self.chat_history[friend_username].append((friend_username, msg, dt_string))
            message = {"status": "success"}
            message, length = self._process_response(message)
            conn.sendall(length + message)
            return friend_username
            #print(f"Message sent to {friend_username}.")
        return "Fault"

    def handle_client(self, conn, addr=None):
        # Implement handling client connections and incoming messages
        #print("Connected by", addr)
        data = receive_response(conn)
        if not data:
            return
        response = json.loads(data)
        if not isinstance(response, dict) or 'type' not in response:
            return 
        elif response['type'] == 'message':
            friend_username = self.handle_incoming_msg(conn, data)
            return friend_username
        else:
            print("Unknown request type.")

    def start_server(self,friend_username=None):
        # Implement starting the server to listen for incoming connections
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen()
            port = s.getsockname()[1]
            #print("Listening on port " + str(port))
            self.port = port
            s.settimeout(10)
            while True:
                try:
                    conn, addr = s.accept()
                    print('Connection established:', addr)
                except socket.timeout:
                    print('Timeout occurred. No connection made.')
                    break
                with conn:
                    flag = False
                    self.friendconn = conn
                    while True:
                        friend_username = self.handle_client(conn, addr)
                        if friend_username == "Fault":
                            flag = True
                            break
                        msg = input("> ")
                        #message = {"type":"message", "username":self.username, "message":msg}
                        #msg, length = self._process_response(message)
                        if msg.split()[0] == "exit" or msg.split()[0] == "break":
                            flag = True
                            break
                        self.send_msg_to_friend(friend_username, msg)
                        #conn.send(length + msg)
                    if flag:
                        break


### Group Chatting ###
# 1. The person creating the group is the leader of the group and is responsible for 
#    registering the chat server with the name server (for public groups)
# 2. The leader picks whether the group is publicly visible or by invitation only
#    For public groups: discoverable on the name server and anyone can join by request
#    For private groups: not discoverable on the name server and only invited members can join
# 3. The leader can invite friends to join the group, remove members from the group, and manage join requests
# 4. The leader should keep track of members and their addresses
# 5. If a group member wants to leave a group, it should send a message to the leader
# 6. If the leader leaves the group, a new leader should be elected (TODO)
# 7. To send a message in the group chat, the client should send the message to the leader, and the leader
#   should broadcast the message to all members
    
    def create_group(self, group_name: str, is_public: bool):
        ''' Create a group with the given name and visibility '''
        # Register group with name server
        # Create group chat server
        # Add group to own group list
        if is_public:
            # "members": [(username, address), (username, address), ...]
            self.groups[group_name] = {"is_public": True, "members": [], "leader": self.username, "address": (self.host, self.port)}
            # register with name server
            package = NSPackage('register', group_name, address=(self.host, self.port), status='online',isgroup=True)
            message, length = self._process_response(package.to_dict())
            self._send_response_to_server(message, length)
            data = receive_response(self.nameserverconn)
            retry_counter = 0
            while not data:
                print("Receive error: cannot receive message from nameserver on go_online. Retry in {} seconds".format(2**retry_counter))
                time.sleep(2**retry_counter)
                self._send_response_to_server(message, length)
                data = receive_response(self.nameserverconn)
            response = json.loads(data)
            if response['status'] == 'ok':
                print("Created public group [{}].".format(group_name))
                save_groups(self.username, self.groups)
            else:
                print("Error: cannot register with nameserver.")
                return
        else:
            self.groups[group_name] = {"is_public": False, "members": [], "leader": self.username, "address": (self.host, self.port)}
            print("Created private group [{}].".format(group_name))
            save_groups(self.username, self.groups)
    
    def join_group(self, group_name: str): # join a public group
        ''' Join a public group with the given name '''
        # Find the group on name server
        package = NSPackage('lookup', group_name)
        message, length = self._process_response(package.to_dict())
        self._send_response_to_server(message, length)
        data = receive_response(self.nameserverconn)
        retry_counter = 0
        while not data:
            print("Receive error: cannot receive message from nameserver on lookup. Retry in {} seconds".format(2**retry_counter))
            time.sleep(2**retry_counter)
            self._send_response_to_server(message, length)
            data = receive_response(self.nameserverconn)
        response = json.loads(data) # response is a dict{'address': address,'status': status,'last_update': time.time(),'isgroup': True}
        if response:
            if isinstance(response["address"], str):
                    host, port = response["address"].split()
                    port = int(port)
                    response["address"] = (host, port)
        else:
            print("Error: cannot lookup")
            return None

        # Send join request to group leader
        group_host, group_port = response["address"]
        jres = send_udp("join group", self.host, self.port, group_host, group_port, content="{} {}".format(self.username, group_name),name=self.username)
        while not jres:
            print(f"Error: cannot send join group request for {group_name}. Retry in {2**retry_counter} sec")
            time.sleep(1)
            jres = send_udp("join group", self.host, self.port, group_host, group_port, content="{} {}".format(self.username, group_name),name=self.username)
            retry_counter += 1
            if retry_counter > 10:
                return False
        if jres["status"] == 'success':
            print("Request to join group {} is approved by the group leader.".format(group_name))
            if "leader" not in jres:
                print(jres)
            leader_name = jres["leader"]
            self.groups[group_name] = {"is_public": True, "members": jres["members"], "leader": leader_name, "address": (group_host, group_port)}
            save_groups(self.username, self.groups)
        else:
            print("Error: cannot send join group request to {}".format(group_name))
            return False
        return True
    
    def invite_to_group(self, group_name: str, friend_username: str):
        ''' Invite a friend to the group '''
        self.update_group_info()
        # Send invite to friend
        if group_name not in self.groups:
            print("Error: group [{}] does not exist.".format(group_name))
            return
        if self.username != self.groups[group_name]["leader"]:
            print("Error: only group leader can invite friends to the group.")
            return
        if friend_username not in self.friends:
            print("Error: friend [{}] does not exist.".format(friend_username))
            return
        # Send invite to friend
        friend_host, friend_port = self.friends[friend_username]["address"]
        res = send_udp("invite to group", self.host, self.port, friend_host, friend_port, content="{} {}".format(self.username, group_name),name=self.username)
        retry_counter = 1
        while not res:
            print(f"Error: cannot send invite to group request for {group_name}. Retry in {2**retry_counter} sec")
            time.sleep(5)
            res = send_udp("invite to group", self.host, self.port, friend_host, friend_port, content="{} {}".format(self.username, group_name),name=self.username)
            retry_counter += 1
            if retry_counter > 5:
                return False
        if res["status"] == 'success':
            print("Invite to group {} is approved by {}.".format(group_name, friend_username))
            self.groups[group_name]["members"].append((friend_username, (friend_host, friend_port)))
            save_groups(self.username, self.groups)
        else:
            print("Invite to group request to {} is denied".format(group_name))
            return False
        return True
    def remove_member(self, group_name: str, friend_username: str):
        def find_member_index(group_name, friend_username):
            for i, member in enumerate(self.groups[group_name]["members"]):
                if member[0] == friend_username:
                    return i
            return -1
        self.update_group_info()
        if self.username != self.groups[group_name]["leader"]:
            print("Error: only group leader can remove members.")
            return
        if friend_username not in self.friends:
            print("Error: friend [{}] does not exist.".format(friend_username))
            return
        if (friend_username, self.friends[friend_username]["address"]) not in self.groups[group_name]["members"]:
            print("Error: friend [{}] is not in group [{}].".format(friend_username, group_name))
            return
        # Send remove notice to friend
        friend_host, friend_port = self.friends[friend_username]["address"]
        res = send_udp("remove from group", self.host, self.port, friend_host, friend_port, content="{} {}".format(self.username, group_name),name=self.username)
        idx = find_member_index(group_name, friend_username)
        if idx != -1:
            self.groups[group_name]["members"].pop(idx)
            save_groups(self.username, self.groups)
        else:
            print("Error: friend [{}] is not in group [{}].".format(friend_username, group_name))
            return
    
    def leave_group(self, group_name: str):
        ''' Leave a group '''
        if group_name not in self.groups:
            print("Error: group [{}] does not exist.".format(group_name))
            return
        if self.username == self.groups[group_name]["leader"]:
            print("Error: group leader cannot leave the group.")
            return
        # Send leave notice to group leader
        group_host, group_port = self.groups[group_name]["address"]
        res = send_udp("leave group", self.host, self.port, group_host, group_port, content="{} {}".format(self.username, group_name),name=self.username)
        retry_counter = 1
        while not res:
            print(f"Error: cannot send leave group request for {group_name}. Retry in 5 sec")
            time.sleep(5)
            res = send_udp("leave group", self.host, self.port, group_host, group_port, content="{} {}".format(self.username, group_name),name=self.username)
            retry_counter += 1
            if retry_counter > 5:
                return False
        if res["status"] == 'success':
            print("Leave group {} successfully.".format(group_name))
            self.groups.pop(group_name)
            save_groups(self.username, self.groups)
        else:
            print("Error: leave group {} unsuccessful because leader didn't receive it.".format(group_name))
            return False
        return True
    # broadcast message to all members in the group
    def broadcast(self, group_name: str, message: str, sender_name = None):
        self.update_group_info()
        if group_name not in self.groups:
            print("Error: group [{}] does not exist.".format(group_name))
            return
        if self.username == self.groups[group_name]["leader"]:
            ## send udp messages to all members in the group
            if sender_name is None:
                sender_name = self.username
            for member in self.groups[group_name]["members"]:
                mname, maddr = member
                try:
                    mhost, mport = maddr
                except:
                    mhost, mport = maddr.split(":")
                res = send_udp("broadcast", self.host, self.port, mhost, mport, content="{} {}".format(sender_name, message),name=group_name)
                retry_counter = 1
                while not res:
                    print(f"Error: cannot send broadcast message to {mname}. Retry in 5 sec")
                    time.sleep(5)
                    res = send_udp("broadcast", self.host, self.port, mhost, mport, content="{} {}".format(sender_name, message),name=group_name)
                    retry_counter += 1
                    if retry_counter > 3:
                        print(f"Cannot deliver message to {mname}. Continue...")
                        return False
                if res["status"] == 'success':
                    continue
                else:
                    print("Error: Deliver message to {} unsuccessful... Continue".format(mname))
                    return False
        else:
            ## send udp message to group leader to broadcast
            group_host, group_port = self.groups[group_name]["address"]
            res = send_udp("broadcast_request", self.host, self.port, group_host, group_port, content="{} {}".format(self.username, message),name=group_name)
            print(f"Sent broadcast request to {group_host}:{group_port}")
            retry_counter = 1
            while not res:
                print(f"Error: cannot send broadcast request for {group_name}. Retry in 5 sec")
                time.sleep(5)
                res = send_udp("broadcast_request", self.host, self.port, group_host, group_port, content="{} {}".format(self.username, message),name=group_name)
                retry_counter += 1
                if retry_counter > 5:
                    print(f"Cannot deliver message to {group_name}. Please retry...")
                    return False
            if res["status"] == 'success':
                #print("Broadcast message to group {} successfully.".format(group_name))
                return True
            else:
                print("Error: broadcast message to group {} unsuccessful because leader didn't receive it.".format(group_name))
                return False
        return True
    
    def update_group_info(self):
        for group, group_info in self.groups.items():
            if self.username == group_info["leader"]:
                for i, member in enumerate(group_info["members"]):
                    if member[0] not in self.friends:
                        group_info["members"].remove(member)
                    else:
                        # look up the most updated address
                        group_info["members"][i] = (member[0], self.friends[member[0]]["address"])
                    


### Posting ###
    def upload_post(self, fpath: str):
        ''' Upload a post from local space, create identifier for it and broadcast to friends '''
        # Move post file to Posts folder, generate unique identifier for it
        if not os.path.exists(fpath):
            print("File does not exist.")
            return
        if not os.path.exists("Posts"):
            os.mkdir("Posts")
        filename = os.path.basename(fpath)
        new_fpath = os.path.join("Posts", filename)
        shutil.move(fpath, new_fpath)
        self.posts[str(self.post_cnt)] = new_fpath
        print("Uploaded post with id [{}].".format(self.post_cnt))
        print("> ", end="")
        # Broadcast post to friends
        self.update_friend_info()
        for info in self.friends.values():
            to_host, to_port = info["address"]
            if info["status"] == "online":
                send_udp('new post', self.host, self.port, to_host, to_port, "New post available: {}:{}".format(self.username, self.post_cnt), self.username)
        self.post_cnt += 1

    def send_post(self, friend_username: str, to_host, to_port, post_id: str):
        ''' Send a post to a friend '''
        if friend_username not in self.friends:
            # ignore the request if sender is not friend
            return
        to_port = int(to_port)
        # send the content of the post file to the friend with UDP
        if post_id not in self.posts:
            text = "Post [{}] does not exist. Available posts are {}.".format(post_id, list(self.posts.keys()))
        else:
            fpath = self.posts[post_id]
            with open(fpath, 'r') as f:
                text = f.read()
        # send content via UDP
        send_udp('post', self.host, self.port, to_host, to_port, text, self.username)

    def get_post(self, friend_username: str, post_id: str):
        if friend_username not in self.friends:
            print("Error: cannot get post from non-friend '{}'.".format(friend_username))
            return
        friend_info = self.friends[friend_username]
        friend_host, friend_port = friend_info["address"]
        # request to get the post from the friend with UDP
        send_udp('get post', self.host, self.port, friend_host, friend_port, str(post_id), self.username)

    def remove_post(self, post_id):
        if post_id not in self.posts:
            return
        fpath = self.posts[post_id]
        os.remove(fpath)
        del self.posts[post_id]
        print("Removed post [{}].".format(post_id))

    def list_posts(self):
        for post_id, fpath in self.posts.items():
            print("[{}]\t{}".format(post_id, fpath))