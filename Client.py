#!/usr/bin/env python3

import socket
import json
import time

NAMESERVER = ("catalog.cse.nd.edu", 9097)
UPDATE_INTERVAL = 60
ACK_TIMEOUT = 5
MSG_SIZE = 1024

DEFAULT = {
    'weike':{
        'address': ('student11.cse.nd.edu', 1234),
        'status': 'online',
        'last_update': time.time()
    },
    "danny":{
        'address': ('student11.cse.nd.edu', 1235),
        'status': 'online',
        'last_update': time.time()
    }

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
    def __del__(self):
        if not isinstance(self.nameserverconn, bool):
           self.nameserverconn.close()
        if not isinstance(self.friendconn, bool):
           self.friendconn.close()


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
                self.client_socket.connect((host, port))
                success = True
            except:
                print("Connection error: cannot connect to nameserver. Retry in {} seconds".format(2**retry_counter))
                time.sleep(2**retry_counter)
                retry_counter += 1
                continue
            if success:
                print("Connected to host: {} and port: {}".format(self.host, self.port))
                break
    def update_friend_info(self):
        # Implement updating friend info from the name server
        retry_counter = 0
        for friend in self.friends:
            raw = {'type': 'lookup', 'username': friend}
            message, length = self._process_response(raw)
            self._send_response(message, length)
            data = self._receive_response()
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
        message = {'type': 'online', 'username': self.username, 'address': (self.host, self.port)}
        message, length = self._process_response(message)
        self._send_response_to_server(message, length)
        data = receive_response(self.nameserverconn)
        retry_counter = 0
        while not data:
            print("Receive error: cannot receive message from nameserver on go_online. Retry in {} seconds".format(2**retry_counter))
            time.sleep(2**retry_counter)
            self._send_response_to_server(message, length)
            data = receive_response(self.nameserverconn)
        response = json.loads(data)
        if response['status'] == 'success':
            self.online = True
            print("Successfully go online")
        else:
            print("Error: cannot go online")
    def go_offline(self):
        # Implement going offline and updating the name server
        message = {'type': 'offline', 'username': self.username, 'address': (self.host, self.port)}
        message, length = self._process_response(message)
        self._send_response_to_server(message, length)
        data = receive_response(self.nameserverconn)
        retry_counter = 0
        while not data:
            print("Receive error: cannot receive message from nameserver on go_offline. Retry in {} seconds".format(2**retry_counter))
            time.sleep(2**retry_counter)
            self._send_response_to_server(message, length)
            data = receive_response(self.nameserverconn)
        response = json.loads(data)
        if response['status'] == 'success':
            self.online = False
            print("Successfully go offline")
        else:
            print("Error: cannot go offline")
    def lookup(self, username):
        # Implement looking up a peer from name server
        message = {'type': 'lookup', 'username': username}
        message, length = self._process_response(message)
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
            print("Successfully lookup")
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
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect((friend_host, friend_port))
                request = {
                    'type': 'friend_request',
                    'username': self.username,
                    'address': (self.host, self.port),
                    'timestamp': time.time(),
                }
                message, length = self._process_response(request)
                s.send(length + message)
                response = receive_response(s)
                response = json.loads(response)
                if not response:
                    return
                if response["status"] == "success":
                    print(f"{friend_username} accepted your friend request.")
                    self.friends[friend_username] = {'address': (friend_host, friend_port), 'status': 'online', 'last_update': time.time()}
                    save_friends(self.username, self.friends)
                else:
                    print(f"{friend_username} rejected your friend request.")
            except Exception as e:
                print(f"Error sending friend request: {str(e)}")

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
            msg = response['message']
            print(f"{friend_username}: {msg}")
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
        if response['type'] == 'friend_request':
            self.handle_friend_request(conn, data)
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
            print("Listening on port " + str(port))
            self.port = port
            while True:
                conn, addr = s.accept()
                with conn:
                    while True:
                        friend_username = self.handle_client(conn, addr)
                        self.friendconn = conn
                        msg = input("> ")
                        #message = {"type":"message", "username":self.username, "message":msg}
                        #msg, length = self._process_response(message)
                        self.send_msg_to_friend(friend_username, msg)
                        #conn.send(length + msg)
