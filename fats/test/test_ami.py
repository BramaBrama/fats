# Copyright (c) 2006-2008 Alexander Burtsev
# See LICENSE for details

"""AMI tests
@author: U{Alexander Burtsev<mailto:eburus@gmail.com>}

$Id: test_ami.py 24 2008-02-18 12:22:42Z burus $
"""

from twisted.trial import unittest
from twisted.internet.protocol import FileWrapper
from twisted.test.test_protocols import StringIOWithoutClosing as SIOWC 

from twisted.fats.ami import AMIClient, AMI
from twisted.fats.errors import AMIFailure, LoginFailed, NoSuchChannel

FAILURE = 0
SUCCESS = 1

RESPONSE_MAP = {
    'Login': {FAILURE:
              'Asterisk Call Manager/1.0'
              'Response: Error'
              'Message: Authentication failed',
              SUCCESS:
              'Asterisk Call Manager/1.0'
              'Response: Success'
              'Message: Authentication accepted'},

    'Ping': {FAILURE: 'Response: Pong',
             SUCCESS: 'Response: Pong'},

    'AbsoluteTimeout': {FAILURE:
                        'Response: Error'
                        'Message: No such channel',
                        SUCCESS:
                        'Response: Success'
                        'Message: Timeout Set'},

    'ChangeMonitor': {FAILURE:
                      'Response: Error'
                      'Message: No such channel',
                      SUCCESS:
                      'Response: Success'
                      'Message: Stopped monitoring channel'},
    
    }

"""
    '': {FAILURE:,
         SUCCESS:},
    '': {FAILURE:,
         SUCCESS:},
    '': {FAILURE:,
         SUCCESS:},
    '': {FAILURE:,
         SUCCESS:},
    '': {FAILURE:,
         SUCCESS:},
    '': {FAILURE:,
         SUCCESS:},
    '': {FAILURE:,
         SUCCESS:},
    '': {FAILURE:,
         SUCCESS:},
    '': {FAILURE:,
         SUCCESS:},
    '': {FAILURE:,
         SUCCESS:},
    '': {FAILURE:,
         SUCCESS:},
    '': {FAILURE:,
         SUCCESS:},
    """
class MockAMIFactory:
    pass


class AMITestCase(unittest.TestCase):
    def setUp(self):
        self.tunnel = SIOWC()
        self.ami = AMI()
        self.ami.makeConnection(FileWrapper(self.tunnel))

    def getCommandDF(self, command, args, kw):
        #prepare command

        if hasattr(self.ami, method):
            df = getattr(self.ami, method)(*args, **kwargs)

            # call lineReceived
            
            return df
        else:
            self.fail('Unknown protocol method: %r' % method)
            
    def assertResponse(self, cmd, *args, **kw):
        result = NotImplemented
        return self.getCommandDF(cmd, args, kw
            ).addCallback(self.assertEqual, result) 

    def assertException(self, cmd, result_line,
                        forErrors=(AMIFailure,), *args, **kw):
        def onError(failure, forErrors):
            if failure.trap(*forErrors):
                pass
            else:
                self.fail('expected: %s' % forErrors)
                    
        return self.getCommandDF(cmd, args, kw
            ).addErrback(onError, forErrors)



class AMIProtocolTest(AMITestCase):
    def test_loginFailed(self):
        def checkFailure(reason):
            if reason.trap(LoginFailed):
                pass
            else:
                self.fail('LoginFailed exception required.')

        df = self.ami.login('name', 'passwd', 'on')
        
        self.ami.lineReceived('Asterisk Call Manager/1.0')
        self.ami.lineReceived('Response: Error')
        self.ami.lineReceived('Message: Authentication failed')
        self.ami.lineReceived('\r\n')
        
        return df.addErrback(checkFailure)

    def test_login(self):
        df = self.ami.login('name', 'passwd', 'off')

        self.ami.lineReceived('Asterisk Call Manager/1.0')
        self.ami.lineReceived('Response: Success')
        self.ami.lineReceived('Message: Authentication accepted')
        self.ami.lineReceived('\r\n')

        return df.addCallback(self.assertEqual,
                              {'response': 'Success',
                               'message': 'Authentication accepted'})
    def test_event(self):
        self.assertEqual(self.ami.getEvent(), None)

        self.ami.lineReceived('Event: Newchannel')
        self.ami.lineReceived('Privilege: call,all')
        self.ami.lineReceived('Channel: SIP/fats-08173788')
        self.ami.lineReceived('State: Ring')
        self.ami.lineReceived('Callerid: fats')
        self.ami.lineReceived('Uniqueid: 1192989348.9')
        self.ami.lineReceived('Calleridname: <unknown>')
        self.ami.lineReceived('\r\n')
        
        return self.ami.getEvent(
            ).addCallback(self.assertEqual,
                          {'callerid': 'fats',
                           'state': 'Ring',
                           'uniqueid': '1192989348.9',
                           'calleridname': '<unknown>',
                           'privilege': 'call,all',
                           'event': 'Newchannel',
                           'channel': 'SIP/fats-08173788'})
        
