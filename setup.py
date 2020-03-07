# coding: utf-8
# python -m pip install future
# python setup.py develop --user

import sys
from setuptools import setup

requirements = [
]

if sys.version_info < (3, 0):
    requirements.append('futures')

if sys.platform == 'darwin':
    requirements.append('PyObjC')

if sys.platform == 'win32':
    requirements.append('pyreadline')

# IDLEで動作させるときには以下のコメントを外して実行します
# for tt in ('develop', '--user'): sys.argv.append(tt)

with open('README.rst') as fh:
    long_description = fh.read()
    
if __name__ == '__main__':
  setup(name='hitk',
      version='0.1.2',
      description=u'Includes python sample code using Tkinter',
      author='Iwao Watanabe',
      author_email='iwaowatanabe+hitk@gmail.com',
      url='https://github.com/IwaoWatanabe/hitk',
      packages=['hitk','hitk.cli'],
      install_requires=requirements,
      license="MIT",
      classifiers=[
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.6',
        'License :: OSI Approved :: MIT License',
      ],
      long_description=long_description,
      entry_points = {
        'console_scripts': [
            'tkapp = hitk.launcher:run',
        ],
      },
      zip_safe=True,
     )

# python 3.4 には setuptools が含まれないことがあるので、次の要領で導入します
# curl https://bootstrap.pypa.io/ez_setup.py | python3 - --user

