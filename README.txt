.. contents::

Git clone URL: git://github.com/dokai/gitctl.git

Change history
**************

1.0a1 (xxxx-xx-xx)
==================

 - Initial public release [dokai]


Purpose
*******

The purpose of this package is to facilitate a workflow similar to a
one that can be achieved using the ``svn:externals`` property in
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
repositories not under your immediate control.


Configuration file
******************

The configuration file is a simple INI-style text file which contains
a section per remote repository. Supported options are:

``url`` (mandatory)

    Full URL to the remote repository. For Subversion repositories you
    should give the URL to the directory that contains the standard
    ``trunk/tags/branches`` structure, which is currently the only
    supported repository layout.

``type`` (optional)

    The type of the remote repository. Valid values are ``git`` and
    ``svn``. Defaults to ``git``.

``branch`` (optional)

    The name of the branch that is checked out by default when first
    cloning the remote repository. Only applies to Git
    repositories. Defaults to ``master``.

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

The name of the configuration section will be used to name the working
directory. An example configuration file containing two repositories
follows::

    [my.project]
    url = git@github.com:someuser/my-project.git

    [other.project]
    url = https://svn.server.com/svn/other.project
    type = svn
    dir = some/path

This will clone the two projects in two directories: ``my.project``
and ``other.project``.


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
                          Configuration file. Defaults to: externals.cfg
    -d DIR, --dir=DIR     Default base directory where all the projects will be
                          placed. This can be overridden on a per-project basis
                          in the config file. Defaults to ./src relative to the
                          location of the given configuration file.

Without any arguments the ``gitctl`` attempts to read a
``externals.cfg`` configuration file from the current directory and
will clone / pull all the configured projects under ``$PWD/src``.


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


Contributors
************

 - Kai Lautaportti [dokai]
