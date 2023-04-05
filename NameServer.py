import socket
import time
import os
from select import select


CKPT = 'catalog.ckpt'
LOG = 'catalog.log'


class Catalog:
    '''Catalog of registered users.'''
    def __init__(self):
        self.catalog = {}

    def add(self, name, address, status):
        # Add a new user to the catalog or update an existing user's information
        self.catalog[name] = {
            'address': address,
            'status': status,
            'last_update': time.time(),
        }

    def lookup(self, name):
        return self.catalog[name]
    
    def update_stale(self):
        # Update status of stale users to 'offline' if they haven't been updated in 60 seconds
        for name, user in self.catalog.items():
            if time.time() - user['last_update'] > 60:
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
        self.host = host if host else socket.gethostname()
        self.port = port
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.bind(('', self.port))
        self.s.listen(5)

    def __del__(self):
        self.log.close()
        self.s.close()

    def run(self):
        while True:
            client, address = self.s.accept()
            print("Connection from {}:{}".format(address[0], address[1]))
            # TODO: perform operation (register or lookup)
            # TODO: handle multiple clients concurrently
            # TODO: update stale users record
            client.close()


if __name__ == '__main__':
    ns = NameServer()
    ns.run()