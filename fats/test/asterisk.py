# Copyright (c) 2006-2008 Alexander Burtsev
# See LICENSE for details

"""
Base components for testing fastagi compatible applications

@author: U{Alexander Burtsev<mailto:eburus@gmail.com>}

$Id: asterisk.py 24 2008-02-18 12:22:42Z burus $
"""

from twisted.trial import unittest
from twisted.internet.protocol import FileWrapper
from twisted.test.test_protocols import StringIOWithoutClosing as SIOWC 

from twisted.fats.agi import FastAGIProtocol, Command, COMMANDS, SUCCESS, FAILURE
from twisted.fats.errors import AGICommandFailure
from twisted.fats.test.tool import MockAsterisk
import time


ENV = {'agi_network': 'yes',
       'agi_request': 'agi://localhost:9000/?foo=bar',
       'agi_channel': 'SIP/tester',
       'agi_language': 'en',
       'agi_type': 'SIP',
       'agi_uniqueid': str(round(time.time(), 2)),
       'agi_callerid': 'Tester',
       'agi_calleridname': 'FastAGI Tester',
       'agi_callingpres': '0',
       'agi_callingani2': '0',
       'agi_callington': '0',
       'agi_callingtns': '0',
       'agi_dnid': 'destination_id',
       'agi_rdnis': 'unknown',
       'agi_context': 'testing',
       'agi_extension': 'extension',
       'agi_priority': '1',
       'agi_enhanced': '0.0',
       'agi_accountcode': '1337'}


class MockFastAGIFactory:
    def handleCall(self, agi):
        pass


class AGITestCase(unittest.TestCase):
    """
    Test case for the FastAGI applications. Has FastAGI protocol and
    mock asterisk instances.
    """
    def setUp(self):
        self.tunnel = SIOWC()
        self.agi = FastAGIProtocol()
        self.agi.factory = MockFastAGIFactory()
        self.agi.makeConnection(FileWrapper(self.tunnel))
        self.agi._setEnv(ENV)
        self.asterisk = MockAsterisk(self.agi)
        
    def getCommandDF(self, command, result_line, args, kwargs):
        cmd = command.title().split()
        method = cmd[0].lower() + (''.join(cmd[1:]) if len(cmd) > 1 else '')
        if hasattr(self.agi, method):
            df = getattr(self.agi, method)(*args, **kwargs)
            self.agi.lineReceived('200 result=%s' % result_line)
            return df
        else:
            self.fail('Unknown protocol method: %r' % method)
            
    def assertCommandResponse(self, params, result_line, *args, **kwargs):
        return self.getCommandDF(params[0], result_line, args, kwargs
                                 ).addCallback(self.assertEqual,
                                               Command(*params)) 

    def assertCommandException(self, params, result_line,
                               forErrors=(AGICommandFailure,), *args, **kwargs):
        def onError(failure, forErrors):
            if failure.trap(*forErrors):
                pass
            else:
                self.fail('expected: %s' % forErrors)
                    
        return self.getCommandDF(params[0], result_line, args, kwargs
                                 ).addErrback(onError, forErrors)


__all__ = ['ENV', 'AGITestCase', 'COMMANDS', 'SUCCESS', 'FAILURE']
        
