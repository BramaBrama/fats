# Copyright (c) 2006-2008 Alexander Burtsev
# See LICENSE for details

"""FastAGI test
@author: U{Alexander Burtsev<mailto:eburus@gmail.com>}

$Id: test_fastagi.py 24 2008-02-18 12:22:42Z burus $
"""

from twisted.fats.errors import AGICommandFailure, UndefinedTimeFormat, \
     AGICommandTimeout, FailureOnOpen
from twisted.fats.test.asterisk import ENV, AGITestCase, COMMANDS
from twisted.fats.agi import URL, Command
import time, datetime


from twisted.trial import unittest


class CommandTest(unittest.TestCase):

    def setUp(self):
        self.cmd = Command('cmd')
        
    def test_string(self):
        cmd_t = Command('cmd', '0')
        self.cmd.result = '0'
        self.cmd.value = None
        self.cmd.endpos = None
        self.assertEqual(cmd_t, self.cmd)

    def test_different_string(self):
        cmd_t = Command('cmd', '0')
        self.cmd.result = '1'
        self.cmd.value = None
        self.cmd.endpos = None
        self.assertNotEqual(cmd_t, self.cmd)
        
    def test_string_endpos(self):
        cmd_t = Command('cmd', '1', endpos=10)
        self.cmd.result = '1'
        self.cmd.value = None
        self.cmd.endpos = 10
        self.assertEqual(cmd_t, self.cmd)

    def test_convert_dtmf(self):
        cmd_t = Command('cmd', '55', endpos=10)
        cmd_t.convert_dtmf()
        self.cmd.result = '7'
        self.cmd.value = None
        self.cmd.endpos = 10
        self.assertEqual(cmd_t, self.cmd)
        

class FastAGIProtocolTest(AGITestCase):

    def test_environmentTransmitting(self):
        self.agi.readingEnv = True
        for var in ENV:
            self.agi.lineReceived('%s: %s\n' %(var, ENV[var]))
            self.assertEqual(ENV[var], self.agi.env[var])
        self.agi.lineReceived('\n\n')
        self.assertEqual(self.agi.readingEnv, False)

    def test_sendCommand(self):
        for cmd in COMMANDS:
            df = self.agi.sendCommand(cmd)
            _buffer = self.tunnel.getvalue()
            current_cmd = _buffer.splitlines()[-1]
            self.assertEqual(current_cmd, cmd)
    
    def test_answer(self):
        return self.assertCommandResponse(('answer', '0'), '0')

    def test_channelStatusSuccess(self):
        command = 'channel status'
        return self.assertCommandResponse(('channel status', '3'), '3')

    def test_channelStatusFailure(self):
        return self.assertCommandException(('channel status', '-1'), '-1')
	
    def test_controlStreamFileSuccess(self):
        return self.assertCommandResponse(('control stream file', '0', None, 123),
                                          '0 endpos=123', filename='test_audio')

    def test_controlStreamFileDigitPressed(self):
        """
        Test control stream file command returning key ``6'' (ASCII number - 54)
        pressed.
        """
        return self.assertCommandResponse(('control stream file', '6', None, 123),
                                          '54 endpos=123', filename='test_audio')

    def test_controlStreamFileFailure(self):
        return self.assertCommandException(('control stream file', '-1', None,
                                            123),
                                           '-1 endpos=123', filename='test_audio')

    def test_controlStreamFileFailureOnOpen(self):
        return self.assertCommandException(('control stream file', '0', None, 0),
                                           '0 endpos=0', forErrors=(FailureOnOpen,),
                                           filename='test_audio')

    def test_databaseDelSuccess(self):
        return self.assertCommandResponse(('database del', '1'), '1',
                                          family='test', key='t_key')

    def test_databaseDelFailure(self):
        return self.assertCommandException(('database del', '0'), '0',
                                           family='test', key='t_key')

    def test_databaseDeltreeSuccess(self):
        return self.assertCommandResponse(('database deltree', '1'), '1',
                                          family='test', keyTree='tree_key')

    def test_databaseDeltreeFailure(self):
        return self.assertCommandException(('database deltree', '0'), '0',
                                           family='test')

    def test_databaseGetSuccess(self):
        return self.assertCommandResponse(('database get', '1', 'TEST_PARAM'),
                                          '1 (TEST_PARAM)',
                                          family='test', key='t_key')

    def test_databaseGetFailure(self):
        return self.assertCommandException(('database get', '0'), '0',
                                           family='test', key='t_key')

    def test_databasePutSuccess(self):
        return self.assertCommandResponse(('database put', '1', 'tEsT_vAl'),
                                          '1 (tEsT_vAl)', family='test',
                                          key='t_key', value='tEsT_vAl')

    def test_databasePutFailure(self):
        return self.assertCommandException(('database put', '0'), '0',
                                           family='test', key='t_key',
                                           value='tEsT_vAl')

    def test_execSuccess(self):
        return self.assertCommandResponse(('exec_', 'some_result'), 'some_result',
                                          application='test')

    def test_execFailure(self):
        return self.assertCommandException(('exec_', '-2'), '-2',
                                           application='test')

    def test_getDataSuccess(self):
        return self.assertCommandResponse(('get data', 'Xyz'), 'Xyz',
                                          filename='test_audio')

    def test_getDataTimeout(self):
        return self.assertCommandResponse(('get data', 'Xyz', 'timeout'),
                                          'Xyz (timeout)', filename='test_audio')
    
    def test_getDataFailure(self):
        return self.assertCommandException(('get data', '-1'), '-1',
                                           filename='test_audio')

    def test_getFullVariableSuccess(self):
        return self.assertCommandResponse(('get full variable', '1', 'something'),
                                          '1 something', name='test_var')

    def test_getFullVariableFailure(self):
        return self.assertCommandException(('get full variable', '0'), '0',
                                           name='var')

    def test_getOptionDigitPressedDigit(self):
        return self.assertCommandResponse(('get option', 'X', None, 123456),
                                          '88 endpos=123456',
                                          filename='test_audio')

    def test_getOptionFailure(self):
        return self.assertCommandException(('get option', '-1', None, 0),
                                           '-1 endpos=0', filename='test_audio')

    def test_getOptionFailureOnOpen(self):
        return self.assertCommandException(('get option', '0', None, 0),
                                           '0 endpos=0', forErrors=(FailureOnOpen,),
                                           filename='test_audio')

    def test_getVariableSuccess(self):
        return self.assertCommandResponse(('get variable', '1', 'TeSt'),
                                          '1 TeSt', name='var')

    def test_getVariableFailure(self):
        return self.assertCommandException(('get variable', '0'), '0', name='var')

    def test_hangupSuccess(self):
        return self.assertCommandResponse(('hangup', '1'), '1')

    def test_hangupFailure(self):
        return self.assertCommandException(('hangup', '-1'), '-1')

    def test_noop(self):
        return self.assertCommandResponse(('noop', '0'), '0')

    def test_receiveCharSuccess(self):
        return self.assertCommandResponse(('receive char', 'X'),
                                          'X')

    def test_receiveCharTimeout(self):
        return self.assertCommandResponse(('receive char', 'X', 'timeout'),
                                          'X (timeout)')

    def test_receiveCharFailure(self):
        return self.assertCommandException(('receive char', '-1', 'hangup'),
                                           '-1 (hangup)')

    def test_receiveTextSuccess(self):
        return self.assertCommandResponse(('receive text', 'TeSt'), 'TeSt')

    def test_receiveTextFailure(self):
        return self.assertCommandException(('receive text', '-1'), '-1')

    def test_recordFilePressedDigit(self):
        return self.assertCommandResponse(('record file', '66', 'dtmf', 123456),
                                          '66 (dtmf) endpos=123456',
                                          filename='test_audio', format='wav')

    def test_recordFileTimeout(self):
        return self.assertCommandResponse(('record file', '0', 'timeout', 123456),
                                          '0 (timeout) endpos=123456',
                                          filename='test_audio', format='wav')

    def test_recordFileHangup(self):
        return self.assertCommandResponse(('record file','0', 'hangup', 123456),
                                          '0 (hangup) endpos=123456',
                                          filename='test_audio', format='wav')

    def test_recordFileRandomError(self):
        return self.assertCommandResponse(('record file', '666', 'randomerror',
                                           123),
                                          '666 (randomerror) endpos=123',
                                          filename='test_audio', format='wav')

    def test_recordFileFailureToWrite(self):
        return self.assertCommandException(('record file', '-1', 'writefile'),
                                           '-1 (writefile)', filename='test_audio',
                                           format='wav')

    def test_recordFileFailureOnWaitFor(self):
        return self.assertCommandException(('record file', '-1', 'waitfor', 123),
                                           '-1 (waitfor) endpos=123',
                                           filename='test_audio', format='wav',
                                           escapeDigits='*')

    def test_sayAlpha(self):
        return self.assertCommandResponse(('say alpha', '0'), '0',
                                          string='asdasfsadf')

    def test_sayAlphaDigitPressed(self):
        return self.assertCommandResponse(('say alpha', '7'), '55',
                                          string='asdasfsadf')

    def test_sayAlphaFailure(self):
        return self.assertCommandException(('say alpha', '-1'), '-1',
                                           string='asdasfsadf')

    def test_dateAsSeconds(self):
        test0 = time.time()
        test1 = time.localtime()
        test2 = datetime.datetime.now()
        
        def checkResult(result, correct_value):
            self.failUnlessEqual(result, correct_value)
        
        self.agi._dateAsSeconds(test0
            ).addCallback(checkResult, test0)
        self.agi._dateAsSeconds(test1
            ).addCallback(checkResult, time.mktime(test1))
        self.agi._dateAsSeconds(test2
            ).addCallback(checkResult, time.mktime(test2.timetuple()))

    def test_dateAsSecondsFailure(self):
        def checkExcept(exception):
            if exception.trap(UndefinedTimeFormat):
                pass
            else:
                self.fail('UndefinedTimeFormat exception required.')
                
        self.agi._dateAsSeconds('2007 01 30 16:12').addErrback(checkExcept)

    def test_sayDate(self):
        return self.assertCommandResponse(('say date', '0'), '0', time.time())

    def test_sayDateDigitPressed(self):
        return self.assertCommandResponse(('say date', '7'), '55', time.time())

    def test_sayDateFailure(self):
        self.assertCommandException(('say date', '-1'), '-1',
                                    date=datetime.datetime.now())

    def test_sayDateUndefinedTimeFormat(self):
        self.assertCommandException(('say date', '-1'), '-1',
                                    forErrors=(UndefinedTimeFormat,),
                                    date='2007 01 30 16:12 june', escapeDigits='')

    def test_sayDatetime(self):
        return self.assertCommandResponse(('say datetime', '0'), '0', time.time())

    def test_sayDatetimeDigitPressed(self):
        return self.assertCommandResponse(('say datetime', '7'), '55', time.time())

    def test_sayDatetimeFailure(self):
        self.assertCommandException(('say datetime', '-1'), '-1',
                                    time=datetime.datetime.now())

    def test_sayDatetimeUndefinedTimeFormat(self):
        self.assertCommandException(('say datetime', '-1'), '-1',
                                    forErrors=(UndefinedTimeFormat,),
                                    time='2007 01 30 16:12', escapeDigits='',
                                    format='MdY')
        
    def test_sayDigits(self):
        return self.assertCommandResponse(('say digits', '0'), '0', '1231341')

    def test_sayDigitsDigitPressed(self):
        return self.assertCommandResponse(('say digits', '7'), '55', '1231341')

    def test_sayDigitsFailure(self):
        self.assertCommandException(('say digits', '-1'), '-1', number='666')

    def test_sayNumber(self):
        return self.assertCommandResponse(('say number', '0'), '0', '1231341')

    def test_sayNumberDigitPressed(self):
        return self.assertCommandResponse(('say number', '7'), '55', '1231341')

    def test_sayNumberFailure(self):
        self.assertCommandException(('say number', '-1'), '-1', number='666')

    def test_sayPhonetic(self):
        return self.assertCommandResponse(('say phonetic', '0'), '0',
                                          '123adfd13af41')

    def test_sayPhoneticDigitPressed(self):
        return self.assertCommandResponse(('say phonetic', '7'), '55',
                                          '123adfd13af41')

    def test_sayPhoneticFailure(self):
        self.assertCommandException(('say phonetic', '-1'), '-1', string='preved')

    def test_sayTime(self):
        return self.assertCommandResponse(('say time', '0'), '0',
                                          time=time.time())

    def test_sayTimeDigitPressed(self):
        return self.assertCommandResponse(('say time', '7'), '55',
                                          time=time.time())

    def test_sayTimeFailure(self):
        self.assertCommandException(('say time', '-1'), '-1',
                                    time=time.time(), escapeDigits='')

    def test_sayTimeUndefinedTimeFormat(self):
        self.assertCommandException(('say time', '-1'), '-1',
                                    forErrors=(UndefinedTimeFormat,),
                                    time='2057 06 07 15:13', escapeDigits='')

    def test_sendImage(self):
        return self.assertCommandResponse(('send image', '0'), '0',
                                          filename='test_image')

    def test_sendImageFailure(self):
        self.assertCommandException(('send image', '-1'), '-1',
                                    filename='test_image')

    def test_sendText(self):
        return self.assertCommandResponse(('send text', '0'), '0',
                                          text='text to send')

    def test_sendTextFailure(self):
        self.assertCommandException(('send text', '-1'), '-1', text='text to send')

    def test_setAutohangup(self):
        return self.assertCommandResponse(('set autohangup', '0'), '0', time=0)

    def test_setCallerid(self):
        return self.assertCommandResponse(('set callerid', '1'), '1',
                                          number='123123')

    def test_setContext(self):
        return self.assertCommandResponse(('set context', '0'), '0',
                                          context='test')

    def test_setExtension(self):
        return self.assertCommandResponse(('set extension', '0'), '0',
                                          extension='test')

    def test_setMusic(self):
        return self.assertCommandResponse(('set music', '0'), '0',
                                          on=True, musicClass='test')

    def test_setPriority(self):
        return self.assertCommandResponse(('set priority', '0'), '0', num=2)

    def test_setVariable(self):
        return self.assertCommandResponse(('set variable', '1'), '1',
                                          variablename='testvar', value='test')

    def test_streamFileDigitSuccess(self):
        return self.assertCommandResponse(('stream file', '0', None, 123),
                                          '0 endpos=123', filename='test_audio')

    def test_streamFileDigitPressed(self):
        # XXX has_response ??
        return self.assertCommandResponse(('stream file', '7', None, 123),
                                          '55 endpos=123', filename='test_audio')
    
    def test_streamFileFailure(self):
        return self.assertCommandException(('stream file', '-1', None, 123),
                                           '-1 endpos=123', filename='foo')

    def test_streamFileFailureOnOpen(self):
        return self.assertCommandException(('stream file', '0', None, 0),
                                           '0 endpos=0', forErrors=(FailureOnOpen,),
                                           filename='test_audio')

    def test_tddMode(self):
        return self.assertCommandResponse(('tdd mode', '1'), '1', on=None)

    def test_tddModeFailure(self):
        return self.assertCommandException(('tdd mode', '-1'), '-1', on=False)

    def test_verbose(self):
        return self.assertCommandResponse(('verbose', '1'), '1',
                                          message='test message 1 or 2', level=4)

    def test_waitForDigitSuccess(self):
        return self.assertCommandResponse(('wait for digit', '7'), '55', timeout=-1)

    def test_waitForDigitFailure(self):
        return self.assertCommandException(('wait for digit', '-1'), '-1',
                                           timeout=0.123)

    def test_waitForDigitTimeout(self):
        return self.assertCommandException(('wait for digit', '0'), '0',
                                           forErrors=(AGICommandTimeout,),
                                           timeout=0.123)


class TestURLParser(unittest.TestCase):

    def _test_URL(self, url_string, path, params):
        url = URL(url_string)
        self.assertEqual(url.path, path)
        self.assertEqual(url.params, params)

    def test_parseURL_full(self):
        self._test_URL('agi://test:666/wrim/wram/wrom/?k1=v1&k2=v2',
                       ('wrim', 'wram', 'wrom'),
                       {'k1': 'v1', 'k2': 'v2'})

    def test_parseURL_no_path(self):
        self._test_URL('agi://test:666/?kill=yourself',(), {'kill': 'yourself'})

    def test_parseURL_no_params(self):
        self._test_URL('agi://test:666/foo/', ('foo',), {})
