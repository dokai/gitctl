from setuptools import setup, find_packages

import os.path

def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

version = '2.0a8'

setup(name='gitctl',
      version=version,
      description="A particular Git workflow implementation with a "
                  "development/staging/production code-flow model and support "
                  "for multiple repositories as part of a larger project.",
      long_description=read('README.rst'),
      classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Topic :: Software Development :: Version Control',
        'Topic :: Software Development :: Build Tools',
        ], # Get strings from http://pypi.python.org/pypi?:action=list_classifiers
      keywords='git workflow',
      author='Kai Lautaportti',
      author_email='kai.lautaportti@hexagonit.fi',
      url='http://github.com/dokai/gitctl',
      license='BSD',
      packages=find_packages(exclude=['ez_setup', 'tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=[
        'setuptools',
        'argparse',
        'GitPython==0.1.7',
        'mock',
        ],
      test_suite='gitctl.tests.test_suite',
      entry_points="""
      # -*- Entry points: -*-
      [console_scripts]
      gitctl = gitctl:main
      """,
      )
