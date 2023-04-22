import json

class UDPPackage:
    '''UDP message formatter'''
    def __init__(self, senderName, senderHost, senderPort, topic):
        self.senderName = senderName
        self.senderHost = senderHost
        self.senderPort = senderPort
        self.topic = topic
    
    def __str__(self):
        return json.dumps({
            'senderName': self.senderName,
            'senderHost': self.senderHost,
            'senderPort': self.senderPort,
            'topic': self.topic,
        })