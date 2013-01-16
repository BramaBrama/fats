# Copyright (c) 2006-2008 Alexander Burtsev
# See LICENSE for details

"""Unit test tools

API Stability: unstable

@author: U{Alexander Burtsev<mailto:eburus@gmail.com>}

$Id: tool.py 24 2008-02-18 12:22:42Z burus $
"""


from twisted.internet import defer, task


class UnknownData(Exception):
    pass


class MockADBAPI:
    # todo: make tests
    def __init__(self, data):
        """
        Database mock object for testing.

        @itype data: C{list}. 
        @ivar data: results for the database query in sequence.
        Each result may be list or tuple from results.
        """
        self.data = data

    def _returnData(self):
        """
        @return: Deferred result like ADBAPI.
        @raise: UnknownData
        """
        
        try:
            test_data = self.data.pop(0)
            if isinstance(test_data, tuple) or isinstance(test_data, list):
                result = []
                for data in test_data:
                    result.append(tuple(data))    
                return defer.succeed(tuple(result))
            
            elif test_data is not None:
                result = ((test_data,),)
                return defer.succeed(result)
            else:
                return defer.succeed(test_data)
        except IndexError:
            return defer.fail(UnknownData)

    def runQuery(self, query):
        """
        @return: Deferred result
        """
        return self._returnData() 

    def runOperation(self, query):
        """
        @return: Deferred result
        """
        return self._returnData() 
        

class MockAsterisk:
    def __init__(self, agi, responses=None):
        """
        @ivar type: C{list}
        @ivar responses: Mock response list for asterisk server.
        """
        self.agi = agi
        self.responses = responses
        self.listener = task.LoopingCall(self.script)

    def setResponseList(self, responses):
        """
        @ivar type: C{list}
        @ivar responses: Mock response list for asterisk server.
        """
        self.responses = responses

    def start(self):
        """
        Start Asterisk listener.
        """
        self.listener.start(0.001)

    def script(self):
        if self.agi.pendingMessages:
            request = self.agi.pendingMessages.pop(0)
            request.callback(self.responses.pop(0))
                
            if not self.responses:
                self.stop()

    def stop(self):
        """
        Stop Asterisk listener.
        """
        self.listener.stop()
