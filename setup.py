from distutils.core import setup, Command


class PyTest(Command):
    user_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        import sys,subprocess
        errno = subprocess.call([sys.executable, 'runtests.py'])
        raise SystemExit(errno)


setup(
    name='pycbor',
    packages=['pycbor'],
    version=0.1,
    description='Encoding/decoding library for RFC 7049',
    author='Michael Mior',
    author_email='michael.mior@gmail.com',
    url='https://github.com/michaelmior/pycbor',

    cmdclass={'test': PyTest},
)
