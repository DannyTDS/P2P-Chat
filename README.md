# P2P-Chat

### Authors: Weike Fang, Ziang Tong
This repository contains the code for the Distributed Systems final project. Our final project is P2P social network.

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
| add *username* | request to add another user as friend |
| connect *username* | start private chat with another user |
| history *username* | display the chat history with another user |
| list | list information of all existing friends |
| post upload *filepath* | upload a post file |
| post remove *id* | remove a post file by id |
| post list | list all owned posts |
| post get *username* *id* | request to get a post from another user |