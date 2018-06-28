# coding: utf-8
# python setup.py develop --user

import sys
from setuptools import setup

requirements = [
]

setup(name='hitk',
      version='0.1',
      description=u'Tkinterを利用するpythonのサンプルコードが含まれます',
      author='Iwao Watanabe',
      author_email='iwaowatanabe+hitk@gmail.com',
      url='https://github.com/IwaoWatanabe/hitk',
      packages=['hitk'],
      install_requires=requirements,
      zip_safe=True,
     )
