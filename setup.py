#coding=utf8
__author__ = 'liming'

from setuptools import setup

setup(name='noveldumper',
      version='0.0.1',
      description='Dump novel from site to txt file',
      url='https://github.com/ipconfiger/noveldumper',
      author='Alexander.Li',
      author_email='superpowerlee@gmail.com',
      license='GNU Lesser General Public License v3.0',
      packages=['n2txt'],
      install_requires=[
          'click',
          'requests',
          'click',
          'lxml',
      ],
      entry_points = {
        'console_scripts': ['n2txt=n2txt.main:main'],
      },
      zip_safe=False)