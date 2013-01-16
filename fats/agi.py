# -*- test-case-name: twisted.fats.test.test_fastagi -*-
# Copyright (c) 2006-2008 Alexander Burtsev
# See LICENSE for details

"""FastAGI Protocol

API Stability: unstable

You use an asterisk FastAGI server like this from extensions.conf:

exten => 1000,3,AGI(agi://127.0.0.1:4573?arg1=val1&arg2=val2)

Where 127.0.0.1 is the server hostname/ip and 4573 is the port on which 
the server is listening.
Parse agi_request like standart URI to identify arguments and variables.

Maintainer: U{Alexander Burtsev<mailto:eburus@gmail.com>}

See also: U{Asterisk Gateway Interface
<http://www.voip-info.org/wiki-Asterisk+AGI>}

$Id: agi.py 24 2008-02-18 12:22:42Z burus $
"""

import re, time, urllib
from twisted.internet import reactor, defer, error
from twisted.protocols import basic
from twisted.python import log

from twisted.fats.errors import AGICommandFailure, UndefinedTimeFormat, \
     AGICommandTimeout, FailureOnOpen

SUCCESS = 0
FAILURE = 1

CHANNEL_AVAILABLE               = 0
CHANNEL_RESERVED                = 1
CHANNEL_OFF_HOOK                = 2
CHANNEL_DIGITS_DIALED           = 3
CHANNEL_LINE_IS_RINGING         = 4
CHANNEL_REMOTE_IS_RINGING       = 5
CHANNEL_LINE_UP                 = 6
CHANNEL_LINE_BUSY               = 7

COMMANDS = {'ANSWER':               ('0', '-1'),
            'CHANNEL STATUS':       ('%s', '-1'),
            'CONTROL STREAM FILE':  ('0 endpos=%s', '-1 endpos=%s'),
            'DATABASE DEL':         ('1', '0'),
            'DATABASE DELTREE':     ('1', '0'),
            'DATABASE GET':         ('1 (%s)', '0'),
            'DATABASE PUT':         ('1 (%s)', '0'),
            'EXEC':                 ('%s', '-2'),
            'GET DATA':             ('%s %s', '-1'),
            'GET FULL VARIABLE':    ('1 %s', '0'),
            'GET OPTION':           ('0 endpos=%s', '-1 endpos=%s'),
            'GET VARIABLE':         ('1 (%s)', '0'),
            'HANGUP':               ('1', '-1'),
            'NOOP':                 ('0', '0'),
            'RECEIVE CHAR':         ('%s %s', '-1 %s'),
            'RECEIVE TEXT':         ('%s', '-1'),
            'RECORD FILE':          ('%s %s endpos=%s', '-1 %s'),
            'SAY ALPHA':            ('0', '-1'),
            'SAY DATE':             ('0', '-1'),
            'SAY DATETIME':         ('0', '-1'),
            'SAY DIGITS':           ('0', '-1'),
            'SAY NUMBER':           ('0', '-1'),
            'SAY PHONETIC':         ('0', '-1'),
            'SAY TIME':             ('0', '-1'),
            'SEND IMAGE':           ('0', '-1'),
            'SEND TEXT':            ('0', '-1'),
            'SET AUTOHANGUP':       ('0', '0'),
            'SET CALLERID':         ('1', '1'),
            'SET CONTEXT':          ('0','0'),
            'SET EXTENSION':        ('0', '0'),
            'SET MUSIC':            ('0', '0'),
            'SET PRIORITY':         ('0', '0'),
            'SET VARIABLE':         ('1', '1'),
            'STREAM FILE':          ('0 endpos=%s', '-1 endpos=%s'),
            'TDD MODE':             ('1', '-1'),
            'VERBOSE':              ('1', '1'),
            'WAIT FOR DIGIT':       ('0', '-1')}


"""
_result2dig = lambda res: int(res) if not res is None and ((res[1:].isdigit()
            if res.startswith('-') else res) is True or res.isdigit()) else res

def cmd_code(cmd_name, type):
    return COMMANDS[cmd_name][type].split()[0]
"""

class Command(object):
    """
    AGI command object. See AGI commands reference for detail info.

    @ivar result: command result
    @type result: C{str}
    @ivar extra: is a second result for the command if available
    @type extra: C{str}
    @ivar endpos: third result for the cammand if available.
    @type result: C{int}
    @ivar has_dtmf: boolean flag is defined for the cammand which have
        DTMF ASCII code in the result value. DTMF ASCII result is
        automaticaly converted to the ''char''.

    @method __rcode: return default result code
    @method is_success: return ''true'' if result code is success
    @method is_failure: return ''true'' if result code is failure
    @method is_default: Return ''true'' if command is in default of results
    @method has_error: check result for an undefined error

    """
    __rcode = lambda self, type: COMMANDS[self.name][type].split()[0]
    is_success = lambda self: bool(self.result == self.__rcode(SUCCESS))
    is_failure = lambda self: bool(self.result == self.__rcode(FAILURE))
    is_default = lambda self: bool(self.result in (self.__rcode(SUCCESS),
                                                   self.__rcode(FAILURE)))
    has_error = lambda self: bool(self.is_failure() and not self.is_success())

    def __init__(self, name, result=None, extra=None, endpos=None):
        if name.endswith('_'):
            name = name[:-1]
        self.name = name.upper()

        self.result = result
        self.endpos = None if endpos is None else int(endpos)
        self.extra = None if not endpos is None and extra == '' else extra

        self.has_dtmf = False
                                            
    def __cmp__(self, obj):
        """
        Allow to compare two commands.
        """
        compare_attributes = ('name', 'result', 'endpos')
        return not reduce(
            lambda acc, a: acc * (getattr(self, a) == getattr(obj, a)),
                                  compare_attributes, 1)

    def convert_dtmf(self):
        """
        Use to convert ASCII responce to the alpha symbol.
        Be careful and check COMMAND.has_dtmf value.
        """
        self.has_dtmf = True
        self.result = chr(int(self.result))

    def __repr__(self):
        """
        Command representation for the debug process.
        """
        return '%s:[%s(%s), %s(%s), %s(%s)]' % (self.name, self.result,
                                                type(self.result),
                                                self.extra, type(self.extra),
                                                self.endpos, type(self.endpos))


class FastAGIProtocol(basic.LineOnlyReceiver):
    """
    Base protocol methods

    @ivar delimiter: uses bald newline instead of carriage-return-newline
    @ivar readingEnv: whether the instance is still in initialising by
        reading the environment variables from the dial session
    @ivar pendingMessages: set of outstanding messages for which we expect replies
    @ivar url: parsed url params from the agi_request variable.

    @ivar env: environment variables for the current asterisk dial session:
        
        - agi_network = 'yes'
        - agi_request = 'agi://localhost'
        - agi_channel = 'SIP/test-321555es'
        - agi_language = 'en'
        - agi_type = 'SIP'
        - agi_uniqueid = '1139871605.0'
        - agi_callerid = '70065798'
        - agi_calleridname = 'Test Name'
        - agi_callingpres = '0'
        - agi_callingani2 = '0'
        - agi_callington = '0'
        - agi_callingtns = '0'
        - agi_dnid = '1'
        - agi_rdnis = 'unknown'
        - agi_context = 'testing'
        - agi_extension = '1'
        - agi_priority = '1'
        - agi_enhanced = '0.0'
        - agi_accountcode = ''
    """
    delimiter = '\n'

    def connectionMade(self):
        """
        Handle incoming connection (new AGI request).

        Initiate reading of the initial attributes passed by the server.
        """
        log.msg('New Connection to the Fastagi server %s' % id(self))

        self.env = {}
        self.url = None
        self.pendingMessages = []
        self.readingEnv = True

    def connectionLost(self, reason):
        """
        Handle loss of the connection (remote hangup).
        """
        log.msg('Connection terminated to the FastAGI server %s' % id(self))

        for df in self.pendingMessages:
            df.errback(error.ConnectionDone('FastAGI connection terminated'))
        del self.pendingMessages[:]

    def __getitem__(self, key):
        return self.env[key]

    def __setitem__(self, key, value):
        self.env[key] = value

    def _setURL(self):
        if self.env.get('agi_request', None):
            self.url = URL(self.env['agi_request'])

    def _setEnv(self, env):
        self.readingEnv = False
        self.env = env

    def lineReceived(self, line):
        """
        Handle Twisted's report of an incoming line from the manager.
        """
        if self.readingEnv:
            if not line.strip():
                self.readingEnv = False
                self._setURL()
                self.factory.handleCall(self)
            else:
                try:
                    key, value = line.split(': ', 1)
                    value = value.rstrip()
                except ValueError, err:
                    log.err('Invalid variable line: %r' %line)
                else:
                    self.env[key.lower()] = value 
                    #log.msg('%s = %r' % (key, value), debug=True)
        else:
            try:
                df = self.pendingMessages.pop(0)
            except IndexError, err:
                log.err('Line received without pending deferred: %r' %line)
            else:
                if line.lower().startswith('200 result='):
                    line = line[11:]
                    df.callback(line)
                else:
                    try:
                        errCode, line = line.split(' ', 1)
                        errCode = int(errCode)
                    except ValueError, err:
                        errCode = 500
                    finally:
                        df.errback(AGICommandFailure(errCode, line))
                   
    def sendCommand(self, name, args=None):
        """
        Send the given command to the other side.
        """            
        command_string = args and name+' '+str(args) or name
        log.msg('Send Command: %r'% command_string)

        df = defer.Deferred()
        self.pendingMessages.append(df)
        self.sendLine(command_string)

        return df.addCallback(self._returnCommandValues, name)

    @staticmethod
    def _returnCommandValues(result, command_name):
        """
        Return command values.
        
        Check command result for failure and return base pattern for all kinds of
        FastAGI command's result.

        @return: L{Command} instance is container for the results.
        @raise AGICommandFailure: Raised on failure error code.
        """
        
        r_pattern = re.compile(
            r"""
            (?P<result>[\S]?[0-9]?[\w]{0,})
            (?:|[\b, (]{0,2}(?P<extra>.*?)[\b, )]{0,2})
            (?:|endpos=(?P<endpos>\d+))$
            """,
            re.IGNORECASE|re.VERBOSE)
        result = r_pattern.match(result).groups()

        command = Command(command_name, *result)
        if command.has_error():
            raise AGICommandFailure(command)
        else:
            log.msg(command)
            return command
        
    def finish(self):
        """
        Finish the AGI scenary (drop connection).
	
        This command simply drops the connection to the Asterisk server, which
        the FastAGI protocol interprets as a successful termination.
        """
        self.transport.loseConnection()
        
    def wait(self, duration):
        """
        Wait for X seconds.
        
        Just a wrapper around callLater, doesn't talk to server)
        
        @return: Deferred which fires some time after duration seconds have passed
        """
        df = defer.Deferred()
        reactor.callLater(duration, df.callback, 0)
        return df
    
    def answer(self):
        """
        Answer channel.
        
        Answers channel if not already in answer state.
        
	@return: deferred integer response code::
            Success: 0
            Failure: -1
	"""
        return self.sendCommand('ANSWER')
    
    def channelStatus(self, channel=None):
        """Returns the status of the specified channel.
        
        If no channel name is given the returns the status of the current channel.
        
        Status values:
            0. Channel is down and available
            1. Channel is down, but reserved
            2. Channel is off hook
            3. Digits (or equivalent) have been dialed
            4. Line is ringing
            5. Remote end is ringing
            6. Line is up
            7. Line is busy
            
        @note: See CHANNEL_* constants for details
        
        @return: deferred integer result code::
            Success: 200 result=<status> 
            Failure: 200 result=-1
	"""
        return self.sendCommand('CHANNEL STATUS', channel)

    @staticmethod
    def __checkResultDTMF(cmd):
        """
        Check result for the
            - controlStreamFile
            - getOption
            - streamFile
        AGI commands.

        @param cmd: L{Command}
        @return: L{Command}
        @raise: L{FailureOnOpen}
        """
        if cmd.is_success() and cmd.endpos == 0:
            raise FailureOnOpen(cmd)
        elif not cmd.is_default():
            cmd.convert_dtmf()
        return cmd
        
    def controlStreamFile(self, filename, escapeDigits='', skipMS=0, ffChar='*',
                          rewChar='#', pauseChar=None):
        """
        Send the given file, allowing playback to be controled by the given
        digits, if any.

        Use double quotes for the digits if you wish none to be permitted.

        @param skipms: If provided, audio will seek to sample offset before
        play starts.

        @param pauseChar: Aallows you to control playback if exist.
        
        @note: Remember, the file extension must not be included in the filename.

        @param offset: Offset is the stream position streaming stopped. If it
        equals `sample offset' there was probably an error.

        @param digit: ASCII code for the digit pressed.

        @return: deferred list of result code and endpos variables::
            Success: 200 result=0 endpos=<offset>
            Digit pressed: 200 result=<digit> endpos=<offset>
            Failure: 200 result=-1 endpos=<offset>
            Failure on open: 200 result=0 endpos=0

        @raise: L{AGICommandFailure}, L{FailureOnOpen}
            
	"""
        args =  '%s %r %s %r %r' % (filename, escapeDigits, skipMS, ffChar,
                                    rewChar)
        if pauseChar:
            args += ' %r' % pauseChar

        return self.sendCommand('CONTROL STREAM FILE', args
            ).addCallback(self.__checkResultDTMF)
    
    def databaseDel(self, family, key):
        """
        Deletes an entry in the Asterisk database for a given family and key.
        
        @return: deferred integer result code::
            Success: 200 result=1
            Failure: 200 result=0
        """
        args =  '%s %s' % (family, key)
        return self.sendCommand('DATABASE DEL', args)
    
    def databaseDeltree(self, family, keyTree=None):
        """
        Deletes a family or specific keytree withing a family in the Asterisk
        database.

        @return: deferred integer result code::
            Success: 200 result=1
            Failure: 200 result=0
        """
        args = keyTree and str(family)+' %s '% keyTree or str(family)
        return self.sendCommand('DATABASE DELTREE', args)
    
    def databaseGet(self, family, key):
        """
        Retrieves an entry in the Asterisk database for a given family and key.
        
        @return: deferred string value for the key::
            Success: 200 result=1 (<value>)
            Failure or <key> not set: 200 result=0
        """
        args =  '%s %s' % (family, key)        
        return self.sendCommand('DATABASE GET', args)
    
    def databasePut(self, family, key, value):
        """
        Adds or updates an entry in the Asterisk database for a given family, key,
        and value.
    
        @return: deferred integer result code::
            Success: 200 result=1 (<value>)
            Failure: 200 result=0
        """
        args = '%s %s %s' % (family, key, value)
        return self.sendCommand('DATABASE PUT', args)

    def exec_(self, application, *options):
        """
        Executes <application> with given <options>.

        Applications are the functions you use to create a dial plan in
        extensions.conf.

        EXAMPLE:

        EXEC Dial Zap/g1/123456

        Also, you have to use the pipe character (|) to separate arguments for
        the application:

        EXEC Dial "IAX2/alice|20"

        @return: deferred string result for the application, which may have
        failed, result values are application dependant::
            Success: 200 result=<ret>
            Failure: 200 result=-2
                <ret> is whatever the application returns
        """
        args = application
        if options:
            args += ' "%s"' % '|'.join([str(opt) for opt in options])
        return self.sendCommand('EXEC', args)
    
    def getData(self, filename, timeout=2.000, maxDigits=None):
        """
        Stream the given file, and recieve DTMF data.

        This is similar to stream file, but this command can accept and return
        many DTMF digits, while stream file returns immediately after the first
        DTMF digit is detected.

        Asterisk looks for the file to play in /var/lib/asterisk/sounds/ by
        default.

        If the user doesn't press any keys when the message plays,
        there is <timeout> milliseconds of silence then the command ends.
        If you don't specify a <timeout>, then a default timeout of 2000
        is used following a pressed digit.

        If no digits are pressed then 6 seconds of silence follow the message.
        If you don't specify <max digits>, then the user can enter as many digits
        as they want.

        Pressing the ``#'' key ends the command. When ended this way, the command
        ends successfullywith any previously keyed digits in the result.
        A side effect of this is that there is no easy way to read a ``#'' key
        using this command.

        @param filename: filename without extension to play
        @param timeout: timeout in seconds (Asterisk uses milliseconds)
        @param maxDigits: maximum number of digits to collect
		
        @return: deferred tuple with pressed digit scancode or time out flag::
            Success: 200 result=<digits>
            Timeout: 200 result=<digits> (timeout)
            Failure: 200 result=-1
                         <digits> is the digits pressed.
        """
        args = '%s %s %s'% (filename, int(timeout * 1000), maxDigits)
        return self.sendCommand('GET DATA', args)
    
    def getFullVariable(self, name, channel=None):
        """
        Understands complex variable names and builtin variables, unlike
        getVariable.

        @return: deferred tuple with status, variable value::
            Success: 200 result=1 <value>
            Failure or not set: 200 result=0
        """
        # XXX check with asterisk API ... ${VAR1(VARIABLE)} !!!
        args = '%s %s' % (name, channel) if channel else name
        return self.sendCommand('GET FULL VARIABLE', args)

    def getOption(self, filename, escapeDigits='', timeout=None):
        """
        Behaves similar to STREAM FILE but used with a timeout option.

        Note that if you do not pass <timeout> there seems to be a default.
        Passing 0 however, works as expected (exactly like STREAM FILE).
        
        @param filename: filename to play 
        @param escapeDigits: digits which cancel playback/recording
        @param timeout: timeout in seconds (Asterisk uses milliseconds)
		
        @return: deferred tuple with status code\digit, endpos::
            Success: 200 result=0 endpos=<offset>
            Failure: 200 result=-1 endpos=0
            Failure on open: 200 result=0 endpos=0
            Digit pressed: 200 result=<digit> endpos=<offset>
                <offset> is the stream position streaming stopped.
                <digit> is the ascii code for the digit pressed.

        @raise: L{AGICommandFailure}, L{FailureOnOpen}
        """
        args = '%s %r' % (filename, escapeDigits)
        if timeout:
            timeout *= 1000
            args += ' %s' % timeout

        return self.sendCommand('GET OPTION', args
            ).addCallback(self.__checkResultDTMF)
    
    def getVariable(self, name):
        # XXX test with Asterisk
        """
        Does not work with global variables.
        
        Does not work with some variables that are generated by modules. (works
        for global variables in 1.2.10 - see
        http://bugs.digium.com/view.php?id=7609 )

        'Variable' actually includes functions (but no expression parsing).

        @param variable: a string of the asterisk dialplan variable:

            - ACCOUNTCODE -- Account code, if specified
            - ANSWEREDTIME -- Time call was answered
            - BLINDTRANSFER -- Active SIP channel that dialed the number. 
                This will return the SIP Channel that dialed the number when 
                doing blind transfers
            - CALLERID -- Current Caller ID (name and number) # deprecated?
            - CALLINGPRES -- PRI Call ID Presentation variable for incoming calls 
            - CHANNEL -- Current channel name
            - CONTEXT -- Current context name
            - DATETIME -- Current datetime in format: DDMMYYYY-HH:MM:SS
            - DIALEDPEERNAME -- Name of called party (Broken)
            - DIALEDPEERNUMBER -- Number of the called party (Broken)
            - DIALEDTIME -- Time number was dialed
            - DIALSTATUS -- Status of the call
            - DNID -- Dialed Number Identifier (limited apparently)
            - EPOCH -- UNIX-style epoch-based time (seconds since 1 Jan 1970)
            - EXTEN -- Current extension
            - HANGUPCAUSE -- Last hangup return code on a Zap channel connected 
                to a PRI interface
            - INVALID_EXTEN -- Extension asked for when redirected to the i 
                (invalid) extension
            - LANGUAGE -- The current language setting. See Asterisk multi-language
            - MEETMESECS -- Number of seconds user participated in a MeetMe conference
            - PRIORITY -- Current priority
            - RDNIS -- The current redirecting DNIS, Caller ID that redirected 
                the call. Limitations apply.
            - SIPDOMAIN -- SIP destination domain of an inbound call 
                (if appropriate)
            - SIP_CODEC -- Used to set the SIP codec for a call (apparently 
                broken in Ver 1.0.1, ok in Ver. 1.0.3 & 1.0.4, not sure about 1.0.2)
            - SIPCALLID -- SIP dialog Call-ID: header
            - SIPUSERAGENT -- SIP user agent header (remote agent)
            - TIMESTAMP -- Current datetime in the format: YYYYMMDD-HHMMSS
            - TXTCIDNAME -- Result of application TXTCIDName
            - UNIQUEID -- Current call unique identifier 
            - TOUCH_MONITOR -- Used for 'one touch record' (see features.conf, 
                and wW dial flags). If is set on either side of the call then 
                that var contains the app_args for app_monitor otherwise the 
                default of WAV||m is used
		
        @return: deferred string value for the key::
            Success: 200 result=1 <value> 
            Failure or not set: 200 result=0
        """
        return self.sendCommand('GET VARIABLE', name)
    
    def hangup(self, channel=None):
        """
        Hangs up the specified channel.

        If no channel name is given, hangs up the current channel.

        @return: deferred integer response code::
            Success: 200 result=1
            Failure: 200 result=-1
        """
        return self.sendCommand('HANGUP', channel)

    def noop(self):
        """
        Does nothing.

        @return: deferred integer response code::
                 Success: 200 result=0 
        """
        return self.sendCommand('NOOP')
    
    def receiveChar(self, timeout=None):
        """
        Receive a character of text on a channel, and discard any further
        characters after the first one waiting.

        Most channels do not support the reception of text. See Asterisk Text for
        details.

        @param timeout: timeout in seconds (Asterisk uses milliseconds)
		
        @return: deferred tuple response (char, timeout flag)::
            Success: 200 result=<char>
            Failure or hangup: 200 result=-1 (hangup)
            Timeout: 200 result=<char> (timeout)
                <char> is the character received, or 0 if the channel does not
                support text reception.
        """
        return self.sendCommand('RECEIVE CHAR', timeout and int(timeout * 1000))

    
    def receiveText(self, timeout=None):
        """
        Receives a string text on a channel.

        Specify <timeout> to be the maximum time to wait for input in
        milliseconds, or 0 for infinite.

        Most channels do not support the reception of text. See Asterisk Text for
        details.
		
        @param timeout: timeout in seconds (Asterisk uses milliseconds)
		
        @return: deferred string response value (unaltered)::
                 Success: 200 result=<text>
                 Failure, hangup, or timeout: 200 result=-1
                 <text> is the text received on the channel.
        """
        return self.sendCommand('RECEIVE TEXT', timeout and int(timeout * 1000))

    def recordFile(self, filename, format, escapeDigits='', timeout=-1,
		offsetSamples=None, beep=True, silence=None):
        """
        Record to a file until <escape digits> are received as dtmf.

        @param filename: filename on the server to which to save 
        @param format: encoding format in which to save data
        @param escapeDigits: digits which end recording 
        @param timeout: maximum time to record in seconds, -1 gives infinite
            (Asterisk uses milliseconds)
        @param offsetSamples: move into file this number of samples before
        recording
        @param beep: if true, play a Beep on channel to indicate start of
        recording
        @param silence: if specified, silence duration to trigger end of
        recording 
		
        @return: deferred list of results (code/digits, typeOfExit, endpos)::
            Hangup: 200 result=0 (hangup) endpos=<offset>
            Interrrupted: 200 result=<digit> (dtmf) endpos=<offset>
            Timeout: 200 result=0 (timeout) endpos=<offset>
            Failure to write: 200 result=-1 (writefile)
            Failure on waitfor: 200 result=-1 (waitfor) endpos=<offset>
            Random error: 200 result=<error> (randomerror) endpos=<offset>
                 <offset> is the end offset in the file being recorded.
                 <digit> is the ascii code for the digit pressed.
                 <error> ?????
        """
        if timeout:
            timeout *= 1000
        args = '%s %s %s %s' % (filename, format, escapeDigits, timeout)

        if offsetSamples:
            args += ' %s' % offsetSamples
        if beep:
            args += ' BEEP'
        if silence:
            args += ' s=%s' % silence
            
        return self.sendCommand('RECORD FILE', args)


    def _sayWrapper(self, command, args, escapeDigits):
        """Wrapper for the Astesrik say methods
        """
        def checkResult(cmd):
            if not cmd.is_default():
                cmd.convert_dtmf()
            return cmd
        
        args = '%s %r' % (args, escapeDigits or '')
        return self.sendCommand(command, args).addCallback(checkResult)

    def sayAlpha(self, string, escapeDigits=''):
        # test with asterisk, can it say digits?
        """
        Say a given character string, returning early if any of the given DTMF
        digits are received on the channel.
	
        @return: deferred 0 or the digit pressed::
            Success: 200 result=0
            Digit pressed: 200 result=<digit>
            Failure: 200 result=-1
               <digit> is the ascii code for the digit pressed.
        """
        string = ''.join([x for x in string if x.isalnum()])
        return self._sayWrapper('SAY ALPHA', string, escapeDigits)

    @staticmethod
    def _dateAsSeconds(date):
        """
        Convert date to the asterisk compatible format.
        """

        if hasattr(date, 'timetuple'):
            date = time.mktime(date.timetuple())
        elif isinstance(date, time.struct_time):
            date = time.mktime(date)

        if isinstance(date, float):
            return defer.succeed(date)
        else:
            return defer.fail(UndefinedTimeFormat(type(date)))

    def sayDate(self, date, escapeDigits=''):
        """
        Say a given date, returning early if any of the given DTMF digits are
        received on the channel.

        @param date: is number of seconds elapsed since 00:00:00 on January 1,
        1970, Coordinated Universal Time (UTC).

        Note: This function does not recite the date in the same manner as
        C{SayUnixTime(date||ABdY)}. In particular, it says 'December thirty one,
        one thousand nine hundred sixty nine' instead of 'December thirty first,
        nineteen sixty nine.' Use C{SAY DATETIME <date> <escape digits> 'ABdY'}
        if you want this more natural reading.
        		
        @return: deferred 0 or digit-pressed as integer::
            Success: 200 result=0
            Digit pressed: 200 result=<digit>
            Failure: 200 result=-1
                <digit> is the ascii code for the digit pressed.
        """
        return self._dateAsSeconds(date
            ).addCallback(lambda dt:
                          self._sayWrapper('SAY DATE', dt, escapeDigits))

    def sayDatetime(self, time, escapeDigits='', format=None, timezone=None):
        """
        Say a given date and time, returning early if any of the given DTMF
        digits are received on the channel.

        @param time: is number of seconds elapsed since 00:00:00 on January
        1, 1970, Coordinated Universal Time (UTC).

        @param format: is the format the time should be said in. See
        voicemail.conf (defaults to 'ABdY 'digits/at' IMp').

            - A or a -- Day of week (Saturday, Sunday, ...)
            - B or b or h -- Month name (January, February, ...)
            - d or e -- numeric day of month (first, second, ..., thirty-first)
            - Y -- Year
            - I or l -- Hour, 12 hour clock
            - H -- Hour, 24 hour clock (single digit hours preceded by "oh")
            - k -- Hour, 24 hour clock (single digit hours NOT preceded by "oh")
            - M -- Minute
            - P or p -- AM or PM
            - Q -- 'today', 'yesterday' or ABdY (*note: not standard strftime value)
            - q -- '' (for today), 'yesterday', weekday, or ABdY
                   (*note: not standard strftime value)
            - R -- 24 hour time, including minute		

        @param timezone: acceptable values can be found in /usr/share/zoneinfo.
        Defaults to machine default.
		
        @return: deferred 0 or digit-pressed as integer::
                Success: 200 result=0
                Failure: 200 result=-1
                Digit pressed: 200 result=<digit>
                    <digit> is the ascii code for the digit pressed.
        """ 
        def formatQuery(args, format, timezone):
            if format:
                args += ' %s' % format
            if timezone:
                args += ' %s' % timezone
            return args
        
        return self._dateAsSeconds(time
            ).addCallback(formatQuery, format, timezone
            ).addCallback(lambda args:
                          self._sayWrapper('SAY DATETIME', args, escapeDigits))

    def sayDigits(self, number, escapeDigits=''):
        """
        Say a given digit string, returning early if any of the given DTMF digits
        are received on the channel. 

        The digits five, five, five, one, two, one, two will be spoken out. If
        durning the speech, the DTMF keys 1, 2, 5 or # are pressed it will stop
        the playback.
        
        @return: deferred 0 or digit-pressed as integer::
            Success: 200 result=0
            Failure: 200 result=-1
            Digit pressed: 200 result=<digit>
                <digit> is the ASCII code for the digit pressed.
        """
        number = ''.join([x for x in str(number) if x.isdigit()])
        return self._sayWrapper('SAY DIGITS', number, escapeDigits)

    def sayNumber(self, number, escapeDigits=''):
        """
        Say a given number, returning early if any of the given DTMF digits are
        received on the channel. 

        The number one thousand two hundred and thirty four will be spoken, and
        if the DTMFs 1, * or # is pressed during the speach it will be terminated.

        @return: deferred 0 or digit-pressed as integer::
            Success: 200 result=0
            Digit pressed: 200 result=<digit>
            Failure: 200 result=-1
                <digit> is the ascii code for the digit pressed.
        """
        number = ''.join([x for x in str(number) if x.isdigit()])
        return self._sayWrapper('SAY NUMBER', number, escapeDigits)
    
    def sayPhonetic(self, string, escapeDigits=''):
        # XXX test with asterisk, can it say some digits
        """
        Say a given character string with phonetics, returning early if any of
        the given DTMF digits are received on the channel.
		
        @return: deferred 0 or digit-pressed as integer::
            Success: 200 result=0
            Digit pressed: 200 result=<digit>
            Failure: 200 result=-1
                <digit> is the ascii code for the digit pressed. 
        """
        string = ''.join([x for x in string if x.isalnum()])
        return self._sayWrapper('SAY PHONETIC', string, escapeDigits)

    def sayTime(self, time, escapeDigits=''):
        """
        Say a given time, returning early if any of the given DTMF digits are
        received on the channel.

        @param time: is number of seconds elapsed since 00:00:00 on January
        1, 1970, Coordinated Universal Time (UTC)
            
        @return: deferred 0 or digit-pressed as integer::
            Success: 200 result=0
            Digit pressed: 200 result=<digit>
            Failure: 200 result=-1
                <digit> is the ascii code for the digit pressed. 
        """
        return self._dateAsSeconds(time
            ).addCallback(lambda tm:
                          self._sayWrapper('SAY TIME', tm, escapeDigits))

    def sendImage(self, filename):
        """
        Sends the given image on a channel.

        Most channels do not support the transmission of images. Image names
        should not include extensions.
		
        @return: deferred integer result code::
            Success: 200 result=0 
            Failure: 200 result=-1
        """
        return self.sendCommand('SEND IMAGE', filename)

    def sendText(self, text):
        """
        Sends the given text on a channel.

        Most channels do not support the transmission of text. See Asterisk Text
        for details.

        Text consisting of greater than one word should be placed in quotes since
        the command only accepts a single argument.
	
        @return: deferred integer result code::
            Success: 200 result=0 
            Failure: 200 result=-1
        """
        return self.sendCommand('SEND TEXT', '%r' % text)

    def setAutohangup(self, time):
        """
        Cause the channel to automatically hangup at <time> seconds in the future.

        Of course it can be hungup before then as well. Setting to 0 will cause
        the autohangup feature to be disabled on this channel.

        @return: deferred integer result code::
            200 result=0
        """
        return self.sendCommand('SET AUTOHANGUP', time)

    def setCallerid(self, number):
        """
        Changes the callerid of the current channel.
		
        @return: deferred integer result code::
            200 result=1
        """
        return self.sendCommand('SET CALLERID', number)

    def setContext(self, context):
        """
        Sets the context for continuation upon exiting the application.

        @note: no checking is done to verify that the context is valid. Specifying
        an invalid context will cause the call to drop
        
        @return: deferred integer result code::
            200 result=0
        """
        return self.sendCommand('SET CONTEXT', context)
    
    def setExtension(self, extension):
        """
        Changes the extension for continuation upon exiting the application.

        @note: no checking is done to verify that the extension extists. If the
        extension does not exist, the PBX will attempt to move to the "i"
        (invalid) extension. If the invalid 'i' extension does not exist, the
        call will drop. Move channel to given extension (or 'i' if invalid) or
        drop if neither there
		
        @return: deferred integer result code::
            200 result=0
        """
        return self.sendCommand('SET EXTENSION', extension)
    
    def setMusic(self, on=True, musicClass=None):
        """
        Enables/Disables the music on hold generator.

        If <musicClass> is not specified then the default music on hold class
        will be used.
		
        @return: deferred integer result code::
            200 result=0
        """
        args = ['OFF', 'ON'][on]
        if musicClass:
            args += ' %s' % musicClass
        return self.sendCommand('SET MUSIC', args)
    
    def setPriority(self, num):
        """
        Changes the priority for continuation upon exiting the application.
		
        @return: deferred integer result code::
            200 result=0 
        """
        return self.sendCommand('SET PRIORITY', num)
    
    def setVariable(self, variablename, value):
        """
        These variables live in the channel Asterisk creates when you pickup a
        phone and as such they are both local and temporary. Variables created in
        one channel can not be accessed by another channel. When you hang up the
        phone, the channel is deleted and any variables in that channel are
        deleted as well.

        Just like get variable, this works for writing to functions too.

        @note: currently (*version<= 1.2.11) the value cannot contain spaces.
        Putting quotes or double quotes aound the value wont work.
        Workaround is to change spaces to e.g. underscores.
        In unix sh this would be something like :
        C{echo 'part1 part2' | tr ' ' '_'}
        		
        @return: deferred integer result code::
            200 result=1
        """
        return self.sendCommand('SET VARIABLE', '%s %r' % (variablename, value))

    def streamFile(self, filename, escapeDigits='', offset=0):
        """
        Send the given file, allowing playback to be interrupted by the given
        digits, if any.

        Use double quotes for the digits if you wish none to be permitted.

        @param offset: if provided, audio will seek to sample offset before play
        starts.
        @param filename: filename, extension must not be included in the filename.
        @bfgug: STREAM FILE is known to behave inconsistently, especially when
        used in conjuction with other languages, i.e. C{Set(LANGUAGE()=xy)}.
        @note: Use EXEC PLAYBACK instead.
        @return: deferred result list (result_code, endpos)::
            Success: 200 result=0 endpos=<offset>
            Digit pressed: 200 result=<digit> endpos=<offset>
            Failure: 200 result=-1 endpos=<sample offset>
            Failure on open: 200 result=0 endpos=0
                <offset> is the stream position streaming stopped. If it equals
                <sample offset> there was probably an error.
                <digit> is the ascii code for the digit pressed.

        @raise: L{AGICommandFailure}, L{FailureOnOpen}
        """
        args =  '%s %r' % (filename, escapeDigits)
        if offset:
            args += ' %s' % offset
        return self.sendCommand('STREAM FILE', args
            ).addCallback(self.__checkResultDTMF)
    
    def tddMode(self, on=True):
        """
        Enable/Disable TDD transmission/reception on a channel.

        This function is currently (01July2005) only supported on Zap channels.
        As of 02July2005, this function never returns 0 (Not Capable). If it
        fails for any reason, -1 (Failure) will be returned, otherwise 1 (Success)
        will be returned. The capability for returning 0 if the channel is not
        capable of TDD MODE is a future plan.
		
        @param on: ON (True), OFF (False) or MATE (None)

        @return: deferred integer result code::
            Fuccess: 200 result=1
            Not capable: 200 result=0
            Failure: 200 result=-1
        """
        on = 2 if on is None else on
        return self.sendCommand('TDD MODE', ['OFF', 'ON', 'MATE'][on])

    def verbose(self, message, level=None):
        """
        Sends message to the console via verbose message system.

        If you specify a verbose level less than 1 or greater than 4, the
        verbosity is 1. The default verbosity seems to be 0 (in 1.0.8), and
        supplying a 0 (zero) verbosity does work: the message will be displayed
        regardless of the console verbosity setting.
        		
        @param message: text to pass 
        @param level: 1-4 denoting verbosity level
		
        @return: deferred integer result code::
            200 result=1 
        """
        args = '%r' % message
        if level:
            args += ' %s' % level

        return self.sendCommand('VERBOSE', args)

    def waitForDigit(self, timeout):
        """
        Waits for channel to receive a DTMF digit.
	
        @param timeout: timeout in seconds or -1 for infinite timeout (Asterisk
        uses miliseconds)
		
        Wait up to timeout seconds for single digit to be pressed 
        @return: deferred 0 on timeout or digit::
            Digit pressed: 200 result=<digit>
            Failure: 200 result=-1
            Timeout: 200 result=0
                <digit> is the ascii code for the digit received. 
        """
        def checkResult(cmd):
            if not cmd.is_default():
                cmd.convert_dtmf()
            elif cmd.is_success():
                raise AGICommandTimeout(cmd)
            elif cmd.is_failure():
                raise AGICommandFailure(cmd)
            return cmd
        
        return self.sendCommand('WAIT FOR DIGIT', int(timeout * 1000)
            ).addCallback(checkResult)


class URL:
    """
    Special class for the agi request URL parsing.

    @ivar path: Path to the AGI service parsed from the AGI request url.
    @ivar params: A dictionary form the URL parameters.
    """
    def __init__(self, url):
        """
        @param url: AGI request url. See L{FastAGIProtocol.env} for detail.
        """
        scheme, rest = urllib.splittype(url)
        host_and_port, path_and_query = urllib.splithost(rest)
        path, query = urllib.splitquery(path_and_query)
        path = tuple(part for part in path.split('/') if part)
        pairs = query and query.split('&') or ()
        params = dict(urllib.splitvalue(p) for p in pairs)

        self.path = path
        self.params = params

__all__ = ['Command', 'FastAGIProtocol', 'COMMANDS', 'SUCCESS', 'FAILURE',
           'CHANNEL_AVAILABLE', 'CHANNEL_RESERVED', 'CHANNEL_OFF_HOOK',
           'CHANNEL_DIGITS_DIALED', 'CHANNEL_LINE_IS_RINGING',
           'CHANNEL_LINE_UP', 'CHANNEL_LINE_BUSY']
