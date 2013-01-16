# -*- test-case-name: twisted.fats.test.test_common -*-
# Copyright (c) 2006-2008 Alexander Burtsev
# See LICENSE for details

"""
Asterisk common library

API Stability: unstable

@author: U{Alexander Burtsev<mailto:eburus@gmail.com>}

See also: U{Asterisk Gateway Interface
<http://www.voip-info.org/wiki-Asterisk+AGI>}

$Id: common.py 24 2008-02-18 12:22:42Z burus $
"""

from twisted.internet import defer
from twisted.python import log


class MaxGroupCount(Exception):
    """Maximum users count in the group"""


def checkGroupCount(agi, max_group_calls):
    """
    Check maximum allowed calls for the current accountcode.

    @type agi: L{broccoli.core.asterisk.fastagi.FastAGIProtocol}
    @ivar agi: FastAGIProtocol instance for the current call session.
    @type max_group_calls: C{int}
    @ivar max_group_calls: Maximum allowed calls for one accountcode

    @raise: MaxGroupCount
    @return: Group count
    """
    def checkGroup(skip_result):
        def onResult(cmd):
            group_count = int(cmd.extra)
                
            if group_count > max_group_calls:
                log.msg(
                    """Maximum allowed calls restriction for account '%s',
                    current group count '%s'"""%
                    (agi.env['agi_accountcode'], group_count))
                raise MaxGroupCount
            return group_count
            
        return agi.getFullVariable('${GROUP_COUNT(${GROUP})}'
            ).addCallback(onResult)
        
    return agi.setVariable('GROUP',
        agi.env['agi_accountcode']
        ).addCallback(checkGroup)
