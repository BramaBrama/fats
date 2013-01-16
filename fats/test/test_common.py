# Copyright (c) 2006-2008 Alexander Burtsev
# See LICENSE for details

"""FastAGI common library tests
@author: U{Alexander Burtsev<mailto:eburus@gmail.com>}

$Id: test_common.py 24 2008-02-18 12:22:42Z burus $
"""

from twisted.fats.test.asterisk import AGITestCase, ENV, COMMANDS, SUCCESS, FAILURE
from twisted.fats.common import checkGroupCount, MaxGroupCount


class AsteriskCommonTest(AGITestCase):
    def test_checkGroupCount(self):
        self.agi.env = ENV
        max_group_count = 2
        real_group_count = 2
        
        def getResult(result):
            self.assertEqual(max_group_count, result)

        df = checkGroupCount(self.agi, max_group_count)
        df.addCallback(getResult)
        
        tell = self.agi.pendingMessages.pop(0)
        tell.callback(COMMANDS['SET VARIABLE'][SUCCESS])
        
        tell = self.agi.pendingMessages.pop(0)
        tell.callback(COMMANDS['GET FULL VARIABLE'][SUCCESS] % real_group_count)
        return df

    def test_checkGroupCountFailure(self):
        self.agi.env = ENV
        max_group_count = 2
        real_group_count = 2

        def getError(reason):
            if reason.trap(MaxGroupCount):
                pass
            else:
                return defer.fail('MaxGroupCount exception is required')
            
        df = checkGroupCount(self.agi, max_group_count)
        df.addErrback(getError)
        
        tell = self.agi.pendingMessages.pop(0)
        tell.callback(COMMANDS['SET VARIABLE'][SUCCESS])
        
        tell = self.agi.pendingMessages.pop(0)
        tell.callback(COMMANDS['GET FULL VARIABLE'][SUCCESS] % real_group_count)
        return df
        
