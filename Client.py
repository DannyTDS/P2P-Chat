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

DEFAULT = {
    # 'weike':{
    #     'address': ('student11.cse.nd.edu', 1234),
    #     'status': 'online',
    #     'last_update': time.time()
    # },
    # "danny":{
    #     'address': ('student11.cse.nd.edu', 1235),
    #     'status': 'online',
    #     'last_update': time.time()
    # }

}

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
    except FileNotFoundError:
        friends = DEFAULT
    return friends

def save_friends(username, friends):
    # Implement saving friends to a file username.json
    with open(username + '.json', 'w') as f:
        json.dump(friends, f)
    return friends

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
    udp_sock.settimeout(10.0)
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
    try:
        response, _ = udp_sock.recvfrom(MSG_SIZE)
        response = json.loads(response.decode())
        if response['status'] == 'success':
            res = {'status': 'success'}
    except:
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
        self.udpsock.settimeout(2.0)
        self.chat_history = {}
        self.posts = {}     # {post_id : post_path} mapping
        self.post_cnt = 0   # monotonically increasing identifier for new post

    def __del__(self):
        save_chat_history(self.username, self.chat_history)
        save_friends(self.username, self.friends)
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
            return
        if self.friends[username]['status'] == 'offline':
            print("Error: this user is offline")
            return
        addr = self.friends[username]['address']
        self.friendconn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        retry_counter = 0
        success = False
        # send connection request udp packet
        to_host, to_port = addr
        res = send_udp('connect', self.host, self.port, to_host, to_port, "connection request from {}".format(self.username), self.username)
        if res["status"] == 'success':
            print("Connection request to {} is accepted. Connecting...".format(username))
        else:
            print("Error: cannot send or refused connection request to {}".format(username))
            return

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
                self.start_server()
                return True
            else:
                self.udpsock.sendto(json.dumps({'status': 'reject'}).encode(), addr)
                return False
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
                return True
            else:
                self.udpsock.sendto(json.dumps({'status': 'reject'}).encode(), addr)
                return False
        elif message["topic"] == 'new post':
            print("There is a new post from {}!".format(message["senderName"]))
        elif message["topic"] == 'get post':
            self.send_post(message["senderName"], message["senderHost"], message["senderPort"], message["content"])
        elif message["topic"] == 'post':
            print("\n" + message["senderName"] + " posted:")
            print(message["content"] + "\n> ", end="")
            

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
            response = json.loads(response)
            #print("response: ", response, "type: ", type(response))
            if not response:
                return
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
            print(f"{friend_username}: {msg}")
            dt_string = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            self.chat_history[friend_username].append((friend_username, msg, dt_string))
            message = {"status": "success"}
            message, length = self._process_response(message)
            conn.sendall(length + message)
            return friend_username
            #print(f"Message sent to {friend_username}.")

    def handle_client(self, conn, addr=None):
        # Implement handling client connections and incoming messages
        #print("Connected by", addr)
        data = receive_response(conn)
        if not data:
            return
        response = json.loads(data)
        if not isinstance(response, dict) or 'type' not in response:
            return 
        # if response['type'] == 'friend_request':
        #     self.handle_friend_request(conn, data)
        elif response['type'] == 'message':
            # if response["username"] not in self.friends:
            #     return
            # else:
            #     
            friend_username = self.handle_incoming_msg(conn, data)
            return friend_username
        else:
            print("Unknown request type.")

    def start_server(self):
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
                    while True:
                        friend_username = self.handle_client(conn, addr)
                        self.friendconn = conn
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
        # send content via TCP provided
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect((to_host, to_port))
                message = {"type": "post", "username": self.username, "post_id": post_id, "content": text}
                message, length = self._process_response(message)
                s.sendall(length + message)
            except:
                # if error occurs, ignore it
                pass

    def get_post(self, friend_username: str, post_id: str):
        if friend_username not in self.friends:
            print("Error: cannot get post from non-friend '{}'.".format(friend_username))
            return
        friend_info = self.friends[friend_username]
        friend_host, friend_port = friend_info["address"]
        # request to get the post from the friend with UDP, receive content with TCP
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, 0))
            s.settimeout(5.0)
            s.listen()
            port = s.getsockname()[1]
            send_udp('get post', self.host, port, friend_host, friend_port, str(post_id), self.username)
            try:
                conn, _ = s.accept()
            except socket.timeout:
                print("Error: failed to get post [{}] from '{}'.".format(post_id, friend_username))
                return
            data = receive_response(conn)
            conn.close()
            if not data:
                print("Error: failed to get post [{}] from '{}'.".format(post_id, friend_username))
            else:
                print("{} posted:".format(friend_username))
                print(data["content"])

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