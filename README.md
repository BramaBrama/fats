fats
====

VOIP application code:


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
            df.addCalback(lambda _: self.agi.sayNumber(666))
            return df


Запуск приложения Hello World
-----------------------------


Сервер Asterisk extensions.conf:

[fats-test]
exten => 222,n,AGI(agi://localhost:9000)


Linux terminal:


    $ twistd -ny fats-trunk/fats/examples/hello_agi.py
    
    [-] Log opened.
    [-] twistd 2.5.0+rUnknown (/usr/bin/python 2.5.1) starting up
    [-] reactor class: 
    [-] __builtin__.HelloFastAGIFactoryFromService starting on 9000
    [-] Starting factory <__builtin__.HelloFastAGIFactoryFromService instance at 0xb780580c>
    [FastAGIProtocol,0,127.0.0.1] Hello FastAGI logging system.
    [FastAGIProtocol,0,127.0.0.1] Send Command: 'ANSWER'
    [FastAGIProtocol,0,127.0.0.1] Send Command: "SAY NUMBER 666 ''"
    [FastAGIProtocol,0,127.0.0.1] SAY NUMBER:[0(), None(), None()]
    [FastAGIProtocol,0,127.0.0.1] Call handler result: SAY NUMBER:[0(), None(), None()]
    [FastAGIProtocol,0,127.0.0.1] Connection terminated to the FastAGI server 3077895596


*Теперь осталось позвонить на номер 222!*