import sys

try:
    from twisted.python import dist
except ImportError:
    raise SystemExit("twisted.python.dist module not found.  Make sure you "
                     "have installed the Twisted core package before "
                     "attempting to install any other Twisted projects.")

if sys.version_info[:2] != (2, 5):
    raise SystemExit("Python 2.5 is required =(. "
                     "You can install it anyway, but code isn't tested yet."
                     "with the Python 2.4.")

if __name__ == '__main__':
    if sys.version_info[:2] >= (2, 4):
        extraMeta = dict(
            classifiers=[
                "Development Status :: 4 - Beta",
                "Environment :: No Input/Output (Daemon)",
                "Intended Audience :: Developers :: Telecommunications Industry",
                "License :: OSI Approved :: MIT License",
                "Programming Language :: Python",
                "Topic :: Telephony :: Framework",
                "Topic :: Internet",
                "Topic :: Software Development :: Libraries :: Python Modules",
            ])
    else:
        extraMeta = {}

    dist.setup(
        twisted_subproject="fats",
        scripts=dist.getScripts("fats"),
        # metadata
        name="Twisted FATS",
        description="Twisted FATS contains FastAGI and AMI protocols implementation.",
        author="Twisted Matrix Laboratories",
        author_email="twisted-python@twistedmatrix.com",
        maintainer="Alexander Burtsev",
        maintainer_email="eburus@gmail.com",
        url="http://fats.burus.org",
        license="MIT",
        long_description="""\
Twisted framework based enhancement. Project contains protocols
implementation for the FastAGI and AMI. Allow to make your
Asterisk IP-PBX server faster and easy to use.
""",
        **extraMeta)
