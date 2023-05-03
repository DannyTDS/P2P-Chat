# P2P-Chat

### Authors: Weike Fang, Ziang Tong
This repository contains the code for the Distributed Systems final project. Our final project is P2P social network.

# Video demos
[Private chat](https://drive.google.com/file/d/1jSZY459KEkFWlqZNrmry8UvDMHbh4pq8/view?usp=share_link) | [Group chat](https://drive.google.com/file/d/1Zc39VpYtDPgXQv-hEMbvFj7orxWcgNij/view?usp=share_link) | [Posts system](https://drive.google.com/file/d/1flqoAKEo0dPIbXUVlX1Lf0GINYWEBuPV/view?usp=share_link)

# Preparation
First clone the repository to local machine.
```
git clone https://github.com/DannyTDS/P2P-Chat.git
cd P2P-Chat
```

The directory for the system can look like the following, as a suggestion:
```
.
├── Clients
│   ├── user1
│   │   ├── Posts/
│   │   ├── Client.py
│   │   ├── protocols.py
│   │   └── test-client.py
│   └── user2
│       ├── Posts/
│       ├── Client.py
│       ├── protocols.py
│       └── test-client.py
├── NameServer.py
└── protocols.py
```
We suggest at least putting each user in its own directory for easier management. Also, each user's directory should contain a ```Posts/``` subdirectory for storing post files.

# How to run
First launch the name server in one terminal.
```
python NameServer.py
```
The script should print something like:
```
Name server listening on XXX.XXX.XXX.XX:12345
```
Copy the address printed into clipboard. Open another terminal for every client desired to be added into the network. Cd' into the user's directory and run the driver script with the copied server address.
```
cd Clients/danny/
python test-client.py XXX.XXX.XXX.XX:12345
```
This should bring you to a CLI waiting for user input. We supply the following comands:
| Command      | Description |
| ----------- | ----------- |
| online      | go online       |
| offline   | go offline        |
| exit      | exit the CLI |
| lookup *username* | lookup and display information of a user
| update | update the stored information of friends
| add *username* | request to add another user as friend |
| connect *username* | start private chat with another user |
| history *username* | display the chat history with another user |
| list | list information of all existing friends |
| message *username* *msg* | send a udp message to a friend |
| create_group *groupname* | create a public group of groupname |
| create_group *groupname* 0 | create a private group of groupname (0 for private, 1 for public - default) |
| join_group *groupname* | send a join request to group of name groupname |
| leave_group *groupname* | leave a group |
| invite *groupname* *username*| leader invite a friend to a group|
| remove_member *groupname* *username*| leader removes a member from a group|
| broadcast *groupname* *msg* | broadcast message to group| 
| post upload *filepath* | upload a post file |
| post remove *id* | remove a post file by id |
| post list | list all owned posts |
| post get *username* *id* | request to get a post from another user |
