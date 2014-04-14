from setuptools import setup, find_packages

def version():
  import os
  folder   = os.path.split(__file__)[0]
  mirai    = os.path.join(folder, "mirai")
  _version = os.path.join(mirai, "_version.py")
  env      = {}
  execfile(_version, env)
  return env['__version__']

print find_packages()
setup(
    name              = 'mirai',
    version           = version(),
    author            = 'Daniel Duckworth',
    author_email      = 'duckworthd@gmail.com',
    description       = "Twitter Futures in Python",
    license           = 'BSD',
    keywords          = 'futures concurrent finagle twitter',
    url               = 'http://github.com/duckworthd/mirai',
    packages          = find_packages(),
    classifiers       = [
      'Development Status :: 4 - Beta',
      'License :: OSI Approved :: BSD License',
      'Operating System :: OS Independent',
      'Programming Language :: Python',
    ],
    install_requires  = [
      "setuptools>=3.4.4",
      "futures>=2.1.6",
    ],
    test_requires     = [
      "nose>=1.3.1",
    ]
)
