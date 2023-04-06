import socket
import time
import os
import json


CKPT = 'catalog.ckpt'
LOG = 'catalog.log'

MSG_SIZE = 1024


class Catalog:
    '''Catalog of registered users.'''
    def __init__(self):
        self.catalog = {}

    def add(self, name, address, status):
        # Add a new user to the catalog or update an existing user's information
        self.catalog[name] = {
            'address': ':'.join(address),
            'status': status,
            'last_update': time.time(),
        }

    def lookup(self, name):
        return self.catalog[name]
    
    def update_stale(self):
        # Update status of stale users to 'offline' if they haven't been updated in 120 seconds
        for name, user in self.catalog.items():
            if time.time() - user['last_update'] > 120:
                user['status'] = 'offline'


class NameServer:
    '''Name server for user discovery.'''
    def __init__(self, host=None, port=0):
        # Initialize catalog from checkpoint file and playback log
        self.catalog = Catalog()
        # Read checkpoint file
        try:
            with open(CKPT, 'r') as f:
                self.ckpt_ts = float(f.readline().strip())
                for line in f.read().splitlines():
                    name, address, status = line.split()
                    self.catalog.add(name, address, status)
        except FileNotFoundError:
            self.ckpt_ts = 0.0
        # Read log file
        write_new_log = False
        valid_records = []
        log_ts = self.ckpt_ts
        self.log_length = 0
        try:
            with open(LOG, 'r') as f:
                log_ts = float(f.readline().strip())
                if log_ts > self.ckpt_ts:
                    for line in f.read().splitlines():
                        try:
                            name, address, status = line.split()
                            valid_records.append((name, address, status))
                            self.log_length += 1
                        except ValueError:
                            # invalid record, skip it
                            continue
                        self.catalog.add(name, address, status)
                else:
                    # log is stale, overwrite it
                    log_ts = self.ckpt_ts
                    write_new_log = True
        except FileNotFoundError:
            # log file doesn't exist, create it
            write_new_log = True
        if write_new_log:
            with open(LOG+'.tmp', 'w') as f:
                f.write(str(log_ts)+'\n')
                for name, address, status in valid_records:
                    f.write(' '.join([name, address, status])+'\n')
                f.flush()
            os.sync()
            os.rename(LOG+'.tmp', LOG)
        # Keep the log open for appending
        self.log = open(LOG, 'a')

        # initialize socket
        host = host if host else socket.gethostname()
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.bind((host, port))
        self.s.listen(5)
        self.host, self.port = self.s.getsockname()
        print("Name server listening on {}:{}".format(self.host, self.port))

    def __del__(self):
        self.log.close()
        self.s.close()

    def run(self):
        while True:
            client, address = self.s.accept()
            client.settimeout(10.0)
            print("Connection from {}:{}".format(address[0], address[1]))
            # TODO: perform operation (register or lookup)
            try:
                sz = client.recv(8)
                if not sz:
                    # connection closed by client
                    raise ConnectionAbortedError("Connection closed by client")
                length = int.from_bytes(sz, "big")
                msg = b''
                while len(msg) < length:
                    to_read = length - len(msg)
                    msg += client.recv(MSG_SIZE if to_read > MSG_SIZE else to_read)
            except:
                client.close()
                continue
            # Operate on the message
            msg = json.loads(msg.decode())
            if msg['op'] == 'register':
                # register a new user or update an existing user's information
                host, port = msg['address'].split(':')
                print("Registered user {} at {}:{} as {}".format(msg['name'], host, port, msg['status']))
                self.catalog.add(msg['name'], (host, port), msg['status'])
                self.log.write(' '.join([msg['name'], msg['address'], msg['status']])+'\n')
                self.log.flush()
                os.sync()
                self.log_length += 1
            elif msg['op'] == 'lookup':
                # lookup a user's information
                try:
                    user = self.catalog.lookup(msg['name'])
                    client.send(json.dumps(user).encode())
                except KeyError:
                    client.send(json.dumps({'status': 'offline'}).encode())
            else:
                client.send(json.dumps({'status': 'error'}).encode())
            # TODO: handle multiple clients concurrently
            # TODO: update stale users record
            client.close()


if __name__ == '__main__':
    ns = NameServer()
    ns.run()