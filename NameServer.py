import socket
import time
import os
import json

# path to checkpoint and log files
CKPT = 'catalog.ckpt'
LOG = 'catalog.log'

# maximum message size to reach each time in bytes
MSG_SIZE = 1024


class Catalog:
    '''Catalog of registered users. Implemented as a dictionary of dictionaries.'''
    def __init__(self):
        self._catalog = dict()

    def add(self, name, address, status):
        # Add a new user to the catalog or update an existing user's information
        # address is a tuple of (host, port)
        self._catalog[name] = {
            'address': ':'.join(address),
            'status': status,
            'last_update': time.time(),
        }

    def lookup(self, name):
        # Lookup a user's information
        # return the user's dictionary, or None if not found
        return self._catalog.get(name, None)
    
    def items(self):
        # Return an iterator of (name, user) pairs
        return self._catalog.items()
    
    def update_stale(self):
        # Update status of stale users to 'offline' if they haven't been updated in 120 seconds
        ts = time.time()
        for name, user in self._catalog.items():
            if ts - user['last_update'] > 120.0:
                self._catalog[name]["status"] = 'offline'



class Checkpoint:
    '''FIXME not bug free yet'''
    '''Checkpoint class for periodically saving catalog to disk.'''
    def __init__(self, path):
        self.path = path
        try:
            self.ckpt = open(self.path, 'r')
        except FileNotFoundError:
            self.ckpt = open(self.path, 'w')
            self.ckpt.write(str('0.0')+'\n')
            self.ckpt.flush()
    
    def __del__(self):
        self.ckpt.close()

    def save(self, catalog: Catalog):
        # Save catalog to disk by shadowing
        self.ckpt.close()
        with open(self.path+'.tmp', 'w') as f:
            f.write(str(time.time())+'\n')
            for name, user in catalog.items():
                f.write(' '.join([name, user['address'], user['status']])+'\n')
            f.flush()
        os.sync()
        os.rename(self.path+'.tmp', self.path)
        self.ckpt = open(self.path, 'r')
    
    def load(self):
        # Load catalog from disk
        catalog = Catalog()
        ts = float(self.ckpt.readline().strip())
        for line in self.ckpt.read().splitlines():
            name, address, status = line.split()
            catalog.add(name, address, status)
        return catalog, ts



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
                # TODO: periodically save catalog to disk
                res = {'status': 'ok'}
            elif msg['op'] == 'lookup':
                # lookup a user's information
                user = self.catalog.lookup(msg['name'])
                res = user if user else {'status': 'error'}
            else:
                res = {'status': 'error'}
            # Send response
            res = json.dumps(res).encode()
            sz = len(res).to_bytes(8, "big")
            client.send(sz + res)
            # TODO: update stale users record
            client.close()


if __name__ == '__main__':
    ns = NameServer()
    ns.run()