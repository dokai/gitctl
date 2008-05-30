from setuptools import setup, find_packages

version = '1.0a1'

setup(name='gitctl',
      version=version,
      description="Script to manage multiple Git repositories in a manner similar to svn:externals.",
      long_description="""\
""",
      classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Topic :: Software Development :: Version Control',
        'Topic :: Software Development :: Build Tools',
        ], # Get strings from http://pypi.python.org/pypi?:action=list_classifiers
      keywords='git',
      author='Kai Lautaportti',
      author_email='kai.lautaportti@hexagonit.fi',
      url='',
      license='BSD',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=[
        'setuptools',
          # -*- Extra requirements: -*-
        ],
      test_suite='gitctl.tests.test_suite',
      entry_points="""
      # -*- Entry points: -*-
      [console_scripts]
      gitctl = gitctl:main
      """,
      )
