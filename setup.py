from setuptools import setup, find_packages
import sys, os

version = '0.0'

setup(name='gitctl',
      version=version,
      description="Script to manage multiple Git repositories in a manne",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='git',
      author='Kai Lautaportti',
      author_email='kai.lautaportti@hexagonit.fi',
      url='',
      license='BSD',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=[
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
