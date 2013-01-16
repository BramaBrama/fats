# -*- test-case-name: twisted.fats.test_service -*-
# Copyright (c) 2006-2008 Alexander Burtsev
# See LICENSE for details

"""FATS services system

API Stability: unstable

@author: U{Alexander Burtsev<mailto:eburus@gmail.com>}

$Id: service.py 24 2008-02-18 12:22:42Z burus $
"""

from twisted.python import log
from twisted.internet import protocol
from zope.interface import implements, Interface, Attribute
from twisted.fats.agi import FastAGIProtocol


class IFastAGIFactory(Interface):
    """FastAGI factory.
    """
    handler = Attribute(
        """Call handler class.
        """)
    
    def handleCall(agi):
        """Handle incoming call.

        @param agi: L{FasAGIProtocol} instance for the call session.
        """

    def buildProtocol(addr):
        """
        @return: FastAGI protocol instance.
        """


class ICallHandler(Interface):
    agi = Attribute(
        """Protocol instance for the current call session.
        """)

    def startCall():
        """Start call script

        @return: deferred
        """


class CallHandler(object):
    implements(ICallHandler)
    
    agi = None


class FastAGIFactory(protocol.ServerFactory):
    """FastAGI server factory.

    Produces protocol instances for asterisk's  call sessions
    and handle incoming call.
    """
    implements(IFastAGIFactory)
    protocol = FastAGIProtocol
    handler = CallHandler

    def handleCall(self, agi):
        """Start call handler
        """
        def onResult(result):
            log.msg('Call handler result:', result)
            agi.finish()

        def onError(result):
            log.msg('Call handler err result:', result.getTraceback())
            agi.finish()

        try:
            handler = ICallHandler(self.handler())
            handler.agi = agi
            #print handler.agi == agi
            return handler.startCall(
                ).addCallbacks(onResult, onError)
        except TypeError:
            log.err(
                'CallHandler[%s] must implement ICallHandler interface.'
                % self.handler)
