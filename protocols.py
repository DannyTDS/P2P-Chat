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
    def __init__(self, op, **kwargs):
        super().__init__()
        self.kwargs = {
            'op': op,
            **kwargs,
        }