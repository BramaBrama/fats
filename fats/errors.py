# Copyright (c) 2006-2008 Alexander Burtsev
# See LICENSE for details

"""Collection of Asterisk specific error classes

@author: U{Alexander Burtsev<mailto:eburus@gmail.com>}

$Id: errors.py 24 2008-02-18 12:22:42Z burus $
"""



class AsteriskException(Exception):
    """
    Base Asterisk's exception
    """
    def __init__(self, result=None):
        self.result = result


class AGICommandTimeout(AsteriskException):
    """
    FastAGI command failure of some description
    """


class AGICommandFailure(AsteriskException):
    """
    FastAGI command failure of some description
    """

class FailureOnOpen(AGICommandFailure):
    """
    FastAGI command failure of some description
    """

class UndefinedTimeFormat(AsteriskException):
    """
    FastAGI time format error
    """

class AMIFailure(AsteriskException):
    """
    AMI command failure of some description
    """

class LoginFailed(AMIFailure):
    """
    """

class NoSuchChannel(AMIFailure):
    """
    """
