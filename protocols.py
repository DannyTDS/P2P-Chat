import json

class Base:
    '''Base class for all packages'''
    def __init__(self):
        self.kwargs = dict()

    def __str__(self):
        return json.dumps({
            **self.kwargs,
        })

    def to_dict(self):
        return self.kwargs

class UDPPackage(Base):
    '''UDP message formatter'''
    def __init__(self, senderName, senderHost, senderPort, topic):
        super().__init__()
        self.kwargs = {
            'senderName': senderName,
            'senderHost': senderHost,
            'senderPort': senderPort,
            'topic': topic,
        }

class NSPackage(Base):
    '''Package for NameServer'''
    def __init__(self, op, username, address=None, status=None, friend=None, isgroup=None):
        super().__init__()
        self.kwargs = {
            'op': op,
            'username': username,
            'isgroup': 'False',
        }
        if address:
            self.kwargs['address'] = address
        if status:
            self.kwargs['status'] = status
        if friend:
            self.kwargs['friend'] = friend
        if isgroup:
            self.kwargs['isgroup'] = isgroup