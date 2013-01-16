# -*- test-case-name: twisted.fats.examples.test.test_hello_agi -*-
# Copyright (c) 2006-2008 Alexander Burtsev
# See LICENSE for details

"""Hello FastAGI application.

API Stability: unstable

@author: U{Alexander Burtsev<mailto:eburus@gmail.com>}

$Id: hello_agi.py 25 2008-02-18 15:34:56Z burus $
"""
from zope.interface import implements, Interface
from twisted.python import log, components
from twisted.application import internet, service
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.fats.service import FastAGIFactory, IFastAGIFactory, CallHandler


class HelloCallHandler(CallHandler):
    """My first call handler.
    """
    def startCall(self):
        log.msg('Hello FastAGI logging system.')
        # Answer the call.
        df = self.agi.answer()
        
        # Say number and stop call session
        df.addCallback(lambda _: self.agi.sayNumber(666))

        return df
            

class IHelloFastAGIService(Interface):
    """Example service interface
    """
    def my_method(param):
        """Example method

        @param param: parameter 
        """


class ExampleService:
    implements(IHelloFastAGIService)


class HelloFastAGIFactoryFromService(FastAGIFactory):
    """My factory from service.
    Implement service method and use them in the factory if it's
    required.
    """
    implements(IFastAGIFactory)
    handler = HelloCallHandler

    def __init__(self, service):
        self.service = service

    def my_method(self, param):
        """Adapt method from the service.
        """
        return self.service.my_method(param)
    
components.registerAdapter(HelloFastAGIFactoryFromService,
                           IHelloFastAGIService,
                           IFastAGIFactory)

# create application and TCP server with factory.
PORT = 9000
factory = HelloFastAGIFactoryFromService(ExampleService)
    
application = service.Application("HelloFastAGI")
fastagi_service = internet.TCPServer(PORT, factory)
fastagi_service.setServiceParent(application)
