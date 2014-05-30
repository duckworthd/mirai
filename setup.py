from setuptools import setup, find_packages

def version(name):
  import os
  folder   = os.path.split(__file__)[0]
  mirai    = os.path.join(folder, name)
  _version = os.path.join(mirai, "_version.py")
  env      = {}
  execfile(_version, env)
  return env['__version__']


if __name__ == '__main__':
  setup(
      name              = 'mirai',
      version           = version('mirai'),
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
      setup_requires    = [
        "setuptools>=3.4.4",
      ],
      install_requires  = [
        "futures>=2.1.6",
        "joblib>=0.7.1",
      ],
      tests_require     = [
        "nose>=1.3.1",
      ],
      test_suite = "nose.collector",
  )
