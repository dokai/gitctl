.. contents::

Git clone URL: git://github.com/dokai/gitctl.git

Project page: http://github.com/dokai/gitctl

Change history
**************

1.0b1 (2008-06-12)
==================

 - Initial public release [dokai]


Purpose
*******

The purpose of this package is to facilitate a workflow similar to a
one that can be achieved using the `svn:externals`_ property in
Subversion when using Git to manage the source code of multiple
projects.

The ``svn:externals`` property allows one part of a Subversion
repository to depend on other parts (or other repositories) so that
when checked out the dependent parts will be checked out also. Also,
updating the main checkout will update all the dependent
checkouts. Externals are often used to put together a composite
application which consists of multiple independent parts.

The package provides a single script -- ``gitctl`` -- which reads in a
configuration file and performs the appropriate clone / pull
operations on the repositories defined in it. For new repositories it
clones the remote repository and checks out the chosen branch in the
working directory. Subsequent script calls will pull in (with
--rebase) changes from the remote repository.

Also remote Subversion repositories are supported which will be cloned
and updated using ``git-svn``. This is useful if your composite
project consists of components that are hosted on Subversion
repositories.

.. _`svn:externals`: http://svnbook.red-bean.com/en/1.4/svn.advanced.externals.html

Configuration file
******************

The configuration file is a simple INI-style text file which contains
a section per remote repository. Supported options are:

``url`` (mandatory)

    Full URL to the remote repository. For Subversion repositories you
    should give the URL to the directory that contains the standard
    ``trunk/tags/branches`` structure. For non-standard layouts or
    single branch checkouts see the Subversion specific options
    ``svn-*`` below.

``type`` (optional)

    The type of the remote repository. Valid values are ``git`` and
    ``svn``. Defaults to ``git``.

``treeish`` (optional)

    The name of a "treeish" object that is checked out by default when
    first cloning the remote repository. Only applies to Git
    repositories. A treeish object may refer, for example, to a branch
    or a tag. Defaults to ``master``.

``dir`` (optional)

    The name of the directory where the project will be checked out
    into. An additional directory will be created under this one where
    the project files will be located so it is safe to use the same
    value for multiple projects. Relative paths are considered
    relative to the location of the config file. Note: if you want to
    check out all your projects under a single directory you can do so
    by using the ``--dir`` switch without having to specify the path
    in each section. This option will override the ``--dir`` switch
    value.

For Subversion repositories you can optionally use the following
options to define a non-standard repository layout. Omitting these
options will assume standard ``tags / branches / trunk`` layout.

``svn-trunk`` (optional)

    Either a relative or absolute repository path to the trunk.

``svn-tags`` (optional)

    Either a relative or absolute repository path to the tags.

``svn-branches`` (optional)

    Either a relative or absolute repository path to the branches.

``svn-clone-options`` (optional)

    Additional options that will be passed verbatim to the ``git-svn``
    command. This may be used, for example, to set the Subversion
    username with ``--username=USER``.

The name of the configuration section will be used to name the working
directory. An example configuration file containing two repositories
follows::

    [gitctl]
    url = git@github.com:dokai/gitctl.git

    [other.project]
    url = https://svn.server.com/svn/other.project
    type = svn
    dir = some/path

This will clone the two projects in two directories: ``./src/gitctl``
and ``./some/path/other.project``.


``gitctl`` script
*****************

The ``gitctl`` script provides a few options::

  $ gitctl --help
  usage: gitctl <options> [proj1 [proj2]]...
  
  By default all projects in the configuration file will be pulled from
  the remote repositories. However, if one or more project names are
  provided as arguments to the script only those projects will be
  pulled.
  
  options:
    -h, --help            show this help message and exit
    -c CONFIG, --config=CONFIG
                          Configuration file. Defaults to: gitexternals.cfg
    -d DIR, --dir=DIR     Default base directory where all the projects will be
                          placed. This can be overridden on a per-project basis
                          in the config file. Defaults to ./src relative to the
                          location of the given configuration file.

Without any arguments the ``gitctl`` attempts to read a
``gitexternals.cfg`` configuration file from the current directory and
will clone / pull all the configured projects in ``$PWD/src``.


Workflow
********

The script is most useful when you setup a new environment and saves
you a lot of typing if you were to clone each repository by hand. It
also provides a level of repeatability which can be useful.

You would most likely have the configuration file in the main project
repository and when setting up a new environment you would first clone
the main project repository and run ``gitctl`` afterwards to get the
dependent projects.

After this you can either manage each project manually, pushing and
pulling as you see fit or if you want you can use the ``gitctl``
script to pull all (or any given ones).

Installation
************

Using setuptools::

  $ easy_install gitctl

Dependencies
************

 * Git_ (>= 1.5.5)

.. _Git: http://git-scm.org/

Contributors
************

 - Kai Lautaportti, Author [dokai]
