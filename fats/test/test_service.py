# Copyright (c) 2006-2008 Alexander Burtsev
# See LICENSE for details

"""FATS service tests.

@author: U{Alexander Burtsev<mailto:eburus@gmail.com>}

$Id: test_service.py 24 2008-02-18 12:22:42Z burus $
"""

#from twisted.fats.errors import AGICommandFailure, UndefinedTimeFormat, \
#     AGICommandTimeout, FailureOnOpen
#from twisted.fats.test.asterisk import ENV, AGITestCase, COMMANDS
from zope.interface import implements
from twisted.internet import defer
from twisted.fats.service import FastAGIFactory, ICallHandler
from twisted.fats.test.asterisk import ENV
from twisted.trial import unittest
#import time, datetime


class GoodCallHandler:
    implements(ICallHandler)

    agi = None
    
    def startCall(self):
        return defer.succeed(True)


class RottenCallHandler:
    agi = None

    def startcall(self):
        return defer.succeed(True)


class MockTransport:
    def loseConnection(self):
        pass


class FastAGIFactoryTest(unittest.TestCase):
    def setUp(self):
        self.factory = FastAGIFactory()
        self.agi = self.factory.buildProtocol(None)
        self.agi.env = ENV
        self.agi.transport = MockTransport() 
        self.agi.readingEnv = True
        
    def test_factoryWithGoodCallHandler(self):
        self.factory.handler = GoodCallHandler
        self.agi.lineReceived('\n\n')   
        self.assertEqual(self.agi, self.factory.handler.agi)
    test_factoryWithGoodCallHandler.skip = True
        
    def test_factoryWithRottenCallHandler(self):
        self.factory.handler = RottenCallHandler
        self.agi.lineReceived('\n\n')   
        self.assertEqual(self.agi, self.factory.handler.agi)
    test_factoryWithRottenCallHandler.skip = True
