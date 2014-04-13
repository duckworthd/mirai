from setuptools import setup, find_packages

import mirai


setup(
    name = 'mirai',
    version = mirai.__version__,
    author = 'Daniel Duckworth',
    author_email = 'duckworthd@gmail.com',
    description = "Twitter Futures in Python",
    license = 'BSD',
    keywords = 'futures concurrent finagle twitter',
    url = 'http://github.com/duckworthd/mirai',
    packages = find_packages(),
    classifiers = [
      'Development Status :: 4 - Beta',
      'License :: OSI Approved :: BSD License',
      'Operating System :: OS Independent',
      'Programming Language :: Python',
    ],
    install_requires = [
      "futures",
    ],
)
