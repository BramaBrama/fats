# Copyright (c) 2006-2008 Alexander Burtsev
# See LICENSE for details

"""Call API tests
@author: U{Alexander Burtsev<mailto:eburus@gmail.com>}

$Id: test_hello_agi.py 25 2008-02-18 15:34:56Z burus $
"""

from twisted.fats.test.asterisk import AGITestCase, ENV, COMMANDS, SUCCESS, FAILURE
from twisted.fats.examples.hello_agi import HelloCallHandler
#from twisted.fats.test.tool import MockADBAPI


class HelloFastAGIExampleTest(AGITestCase):
    def _baseCall(self, expectedResponse):
        def callResult(result):
            self.assertEqual(expectedResponse, result)
            
        call = HelloCallHandler()
        call.agi = self.agi
        df = call.startCall()
        df.addCallback(callResult)
        return df

    def test_callScriptAndAsteriskCollaboration(self):
        # Call script execute commands in the sequence:
        # --> answer : * response SUCCESS
        # --> say_number : * response SUCCESS
        asterisk_responses = [
            COMMANDS['ANSWER'][SUCCESS],
            COMMANDS['SAY NUMBER'][SUCCESS]]

        req_result = 'magic_result'
        call = self._baseCall(req_result)
        
        self.asterisk.setResponseList(asterisk_responses)
        self.asterisk.start()
        return call
