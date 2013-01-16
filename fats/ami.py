# -*- test-case-name: twisted.fats.test.test_ami -*-
# Copyright (c) 2006-2008 Alexander Burtsev
# See LICENSE for details

"""AMI Protocol

API Stability: unstable

@author: U{Alexander Burtsev<mailto:eburus@gmail.com>}

$Id: ami.py 26 2008-06-23 09:05:55Z burus $
"""

from twisted.internet import reactor, defer, error, protocol
from twisted.protocols import basic
from twisted.python import log
from string import Template
from twisted.fats.errors import LoginFailed

COMMANDS = {
    'login': Template('action: login\r\n'
                      'Username: $username\r\n'
                      'Secret: $secret\r\n'
                      'Events: $events\r\n'),
    
    'ping': 'action: ping\r\n',

    'absoluteTimeout': Template('action: AbsoluteTimeout\r\n'
                                'channel: $channel\r\n'
                                'timeout: $timeout\r\n'),
    
    'changeMonitor': Template('action: ChangeMonitor\r\n'
                              'channel: $channel\r\n'
                              'file: $file\r\n'),

    
    }

class AMI(basic.LineOnlyReceiver):
    """
    http://www.voip-info.org/wiki/view/Asterisk+manager+API

    devel*CLI> show manager commands
    Action           Privilege        Synopsis
    ------           ---------        --------
    AbsoluteTimeout  call,all         Set Absolute Timeout
    AgentCallbackLo  agent,all        Sets an agent as logged in by callback
    AgentLogoff      agent,all        Sets an agent as no longer logged in
    Agents           agent,all        Lists agents and their status
    ChangeMonitor    call,all         Change monitoring filename of a channel
    Command          command,all      Execute Asterisk CLI Command
    DBGet            system,all       Get DB Entry
    DBPut            system,all       Put DB Entry
    Events           <none>           Control Event Flow
    ExtensionState   call,all         Check Extension Status
    Getvar           call,all         Gets a Channel Variable
    Hangup           call,all         Hangup Channel
    IAXnetstats      <none>           Show IAX Netstats
    IAXpeers         <none>           List IAX Peers
    ListCommands     <none>           List available manager commands
    Logoff           <none>           Logoff Manager
    MailboxCount     call,all         Check Mailbox Message Count
    MailboxStatus    call,all         Check Mailbox
    Monitor          call,all         Monitor a channel
    Originate        call,all         Originate Call
    ParkedCalls      <none>           List parked calls
    Ping             <none>           Keepalive command
    QueueAdd         agent,all        Add interface to queue.
    QueuePause       agent,all        Makes a queue member temporarily unavailable
    QueueRemove      agent,all        Remove interface from queue.
    Queues           <none>           Queues
    QueueStatus      <none>           Queue Status
    Redirect         call,all         Redirect (transfer) a call
    SetCDRUserField  call,all         Set the CDR UserField
    Setvar           call,all         Set Channel Variable
    SIPpeers         system,all       List SIP peers (text format)
    SIPshowpeer      system,all       Show SIP peer (text format)
    Status           call,all         Lists channel status
    StopMonitor      call,all         Stop monitoring a channel
    """
    
    def __init__(self):
        self.__response_farm = []
        self._events = []
        self.__events_farm = []
        self.__have_event = False
            
    def lineReceived(self, line):
        def composeResponse(response, key, value, exception, condition):
            if exception is not None:
                if value == condition:
                    return defer.fail(exception(value))
            response.setdefault(key, value)
            return response

        def composeEvent(event, key, value):
            event.setdefault(key, value)
            return event
        
        if line.startswith('Asterisk Call Manager'):
            _, cmd, _ = self.__response_farm[0]
            self.sendLine(cmd[0])
                
        elif not line.strip():
            if not self.__have_event:
                response, _, deferredResponse = self.__response_farm.pop(0)
                deferredResponse.addCallback(
                    lambda value: response.callback(value))
                deferredResponse.addErrback(
                    lambda value: response.errback(value))
                deferredResponse.callback(_AsteriskResponse())
            
                if self.__response_farm:
                    _, cmd, _ = self.__response_farm[0]
                    self.sendLine(cmd[0])
            else:
                event, deferredEvent = self.__events_farm.pop(-1)
                deferredEvent.addCallback(lambda value: event.callback(value))
                deferredEvent.addErrback(lambda value: event.errback(value))
                deferredEvent.callback(_AsteriskEvent())
                self._events.append(event)
        else:
            type_, value = line.split(': ')
            if type_ == 'Response':
                self.__have_event = False
            elif type_ == 'Event':
                self.__have_event = True
                
            if not self.__have_event:
                _, cmd, deferredResponse  = self.__response_farm[0]
                _, exception, condition = cmd
                deferredResponse.addCallback(
                    composeResponse, type_.lower(), value, exception, condition)
            else:
                if type_ == 'Event':
                    self.__events_farm.append(
                        (defer.Deferred(), defer.Deferred()))
                    
                _, deferredEvent = self.__events_farm[-1]
                deferredEvent.addCallback(composeEvent, type_.lower(), value)
        
    def _sendCommand(self, command, exception=None, condition='Error'):
        response = defer.Deferred()
        
        # TODO: append a substance
        self.__response_farm.append((response, (command, exception, condition),
                           defer.Deferred()))
        
        # add callback for the values representation
        return response

    def getEvent(self):
        """
        """
        if self._events:
            return self._events.pop(0)
        return None

    def login(self, username, secret, events):
        """
        To login and authenticate to the manager, you must call this method,
        with your user name, secret (password) and events flag as parameters.
        
        If you do not need to subscribe to events being generated by Asterisk,
        you may also include the set events='off',

        @param username: C{str}
        @param secret: C{str}
        @param events: C{str} 'on' or 'off'

        @return: deferred result L{_AsteriskResponse}
        """
        command = str(COMMANDS['login'].substitute(
            username=username, secret=secret, events=events))
        return self._sendCommand(command, exception=LoginFailed)
        
    def ping(self):
        """
        Ping asterisk.

        @return: deferred Pong =)
        """
        command = str(COMMANDS['ping'])
        return self._sendCommand(command)

    def absoluteTimeout(self, channel, timeout):
        """
        This command will request Asterisk to hangup a given channel
        after the specified number of seconds, thereby effectively
        ending the active call.

        If the channel is linked with another channel
        (an active connected call is in progress),
        the other channel will continue it's path through the dialplan
        (if any further steps remains).

        @param channel: Which channel to hangup, e.g. SIP/123-1c20 C{str}
        @param timeout: The number of seconds until the channel
            should hangup C{int}

        @return: deferred result L{_AsteriskResponse}
        """
    def changeMonitor(self, channel, file):
        """
        Changes the file name of a recording occuring on a channel
        This will change the names of the two audio recording
        files for this channel: filename-in.gsm, filename-out.gsm
        
        @param channel: Which channel to hangup, e.g. SIP/123-1c20 C{str}
        @param timeout: filename C{str}

        @return: deferred result L{_AsteriskResponse}
        """

class _AsteriskResponse(dict):
    pass

class _AsteriskEvent(dict):
    pass


class AMIClient(protocol.ClientFactory):
    protocol = AMI

    def __init__(self):
        # XXX not allow have multi protocol.
        self.df = defer.Deferred()

    def buildProtocol(self, addr):
         p = self.protocol()
         p.factory = self
         self.df.callback(p)
         return p

    def getProto(self):
        return self.df

    def clientConnectionLost(self, connector, reason):
        pass

    def clientConnectionFailed(self, _, reason):
        self.df.errback(reason)


def connectAMI(username, password, host='127.0.0.1', port=5038, events='on'):
    def authorize(ami):
        ami.login(username, password, events)
        return ami
    
    factory = AMIClient()
    reactor.connectTCP(host, port, factory)

    proto = factory.getProto()
    return proto.addCallback(authorize)
