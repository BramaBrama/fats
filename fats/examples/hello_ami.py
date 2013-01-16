"""

$Id: hello_ami.py 25 2008-02-18 15:34:56Z burus $
"""
from twisted.internet import reactor
from twisted.fats.ami import connectAMI

con = connectAMI('burus', 'top123secret')

def foo(res):
    print '@@', res
    return res

def get_ami(ami):
    ami.ping().addCallback(foo)
    return ami
    
con.addCallback(get_ami)


reactor.run()
