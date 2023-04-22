import socket
import time
import os
import json
from select import select
from protocols import UDPPackage

# path to checkpoint and log files
CKPT = 'catalog.ckpt'
LOG = 'catalog.log'
# maximum number of logs before checkpoint
MAX_LOGS = 10

# maximum message size to reach each time in bytes
MSG_SIZE = 1024


class Catalog:
    '''Catalog of registered users. Implemented as a dictionary of dictionaries.'''
    def __init__(self):
        self._catalog = dict()

    def add(self, name, address, status, verbose=True):
        # Add a new user to the catalog or update an existing user's information
        # address is a tuple of (host, port)
        self._catalog[name] = {
            'address': address,
            'status': status,
            'last_update': time.time(),
        }
        if verbose:
            print("Registered user {} at {} as {}".format(name, address, status))

    def lookup(self, name):
        # Lookup a user's information
        # return the user's dictionary, or None if not found
        return self._catalog.get(name, None)
    
    def items(self):
        # Return an iterator of (name, user) pairs
        return self._catalog.items()
    
    def update_stale(self, verbose=True):
        # Update status of stale users to 'offline' if they haven't been updated in 120 seconds
        ts = time.time()
        updated = []
        for name, user in self._catalog.items():
            if ts - user['last_update'] > 120.0 and user['status'] == 'online':
                self._catalog[name]["status"] = 'offline'
                if verbose:
                    print("Updated stale user {} as offline".format(name))
                updated.append((name, user['address'], user['status']))
        return updated

class Checkpoint:
    '''Checkpoint class for periodically saving catalog to disk.'''
    def __init__(self, path):
        self.path = path

    def save(self, catalog: Catalog, ts: float):
        # Save catalog to disk by shadowing
        with open(self.path+'.tmp', 'w') as f:
            f.write(str(ts)+'\n')
            for name, user in catalog.items():
                if isinstance(user['address'], list) or isinstance(user['address'], tuple):
                    user['address'] = ' '.join(map(str, user['address']))
                f.write(' '.join([name, user['address'], user['status']])+'\n')
            f.flush()
        os.sync()
        os.rename(self.path+'.tmp', self.path)
    
    def load(self):
        # Load catalog from disk, returns a catalog object and timestamp
        catalog = Catalog()
        try:
            with open(self.path, 'r') as f:
                ts = float(f.readline().strip())
                for line in f.read().splitlines():
                    name, address, status = line.split()
                    catalog.add(name, address, status, verbose=False)
        except FileNotFoundError:
            ts = 0.0
        return catalog, ts

class Log:
    '''Log class for recording updates'''
    def __init__(self, path):
        self.path = path
        try:
            self.log = open(self.path, 'r+')
        except FileNotFoundError:
            self.log = open(self.path, 'w+')
            self.log.write('0.0\n')
        self.length = 0
    
    def playback(self, catalog: Catalog, ckpt_ts: float):
        # playback log file, update catalog, and skip incomplete logs
        # if log is stale, truncate it and return the original catalog
        # else, return new catalog updated with log
        log_ts = float(self.log.readline().strip())
        if log_ts < ckpt_ts:
            # log is stale, truncate it
            self.truncate(ckpt_ts)
            return catalog
        else:
            for line in self.log.read().splitlines():
                try:
                    name, address, status = line.split()
                    catalog.add(name, address, status, verbose=False)
                    self.length += 1
                except ValueError:
                    # invalid record, skip it
                    continue
            return catalog

    def append(self, name, address, status) -> int:
        # append a new record to log file
        address = ' '.join(map(str, address))
        self.log.write(' '.join([name, address, status])+'\n')
        self.log.flush()
        os.sync()
        self.length += 1
        return self.length

    def truncate(self, ts):
        # truncate log file
        self.log.truncate(0)
        self.log.seek(0)
        # write current timestamp
        self.log.write(str(ts)+'\n')
        self.log.flush()
        os.sync()
        self.length = 0


class NameServer:
    '''Name server for user discovery.'''
    def __init__(self, host=None, port=0):
        # Initialize catalog from checkpoint file and playback log
        self.catalog = Catalog()
        # Read checkpoint file
        self.ckpt = Checkpoint(CKPT)
        self.catalog, self.ckpt_ts = self.ckpt.load()
        # Read log file
        self.log = Log(LOG)
        self.catalog = self.log.playback(self.catalog, self.ckpt_ts)

        # initialize socket
        host = host if host else socket.gethostname()
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.bind((host, port))
        self.s.listen(5)
        self.host, self.port = self.s.getsockname()
        print("Name server listening on {}:{}".format(self.host, self.port))

        # send UDP broadcast to known online users in the catalog
        broadcast = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        package = UDPPackage('NAMESERVER', self.host, self.port, 'address update')
        for name, user in self.catalog.items():
            if user['status'] == 'online':
                ip_addr, port = user['address']
                broadcast.sendto(str(package).encode(), (ip_addr, port))
        broadcast.close()

    def __del__(self):
        self.s.close()

    def run(self):
        self.last_update_stale = time.time()
        while True:
            # Update stale users every 120 seconds
            if time.time() - self.last_update_stale > 120.0:
                updated = self.catalog.update_stale()
                self.last_update_stale = time.time()
                # Update log
                for user_info in updated:
                    self.log.append(*user_info)
            # Check for new connections
            readable, _, _ = select([self.s], [], [], 0.0)
            if not readable:
                continue
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
            try:
                msg = json.loads(msg.decode())
                if msg['op'] == 'register':
                    # register a new user or update an existing user's information
                    self.catalog.add(msg['username'], msg['address'], msg['status'])
                    # Update log
                    log_length = self.log.append(msg['username'], msg['address'], msg['status'])
                    if log_length > MAX_LOGS:
                        # Update checkpoint
                        save_ts = time.time()
                        self.ckpt.save(self.catalog, save_ts)
                        self.log.truncate(save_ts)
                    res = {'status': 'ok'}
                elif msg['op'] == 'lookup':
                    # lookup a user's information
                    user = self.catalog.lookup(msg['username'])
                    res = user if user else {'status': 'error'}
                else:
                    raise ValueError("Unrecognized operation")
            except ValueError:
                res = {'status': 'error'}
            # Send response
            res = json.dumps(res).encode()
            sz = len(res).to_bytes(8, "big")
            client.send(sz + res)
            client.close()


if __name__ == '__main__':
    ns = NameServer()
    ns.run()