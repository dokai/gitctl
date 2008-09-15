.. contents::
  
  .

Git clone URL: git://github.com/dokai/gitctl.git

Project page: http://github.com/dokai/gitctl


Change history
**************

2.0a1 (XXXX-XX-XX)
==================

 - Complete overhaul to implement (a particular) Git workflow process in
   addition to custom externals handling. This breaks backward compatibility
   with the 1.x version but provides somewhat equivalent functionality.
   [dokai]

1.0b1 (2008-06-12)
==================

 - Initial public release [dokai]


Purpose
*******

The purpose of this package is to implement a particular workflow for using
Git to manage a project that consists of multiple independent subprojects. The
original motivation is a zc.buildout driven system, but the implementation is
not dependent on this. This is not a 100% generic tool, but the workflow is
fairly common so it may be adaptable for other use cases also.

The workflow consists of using three pre-defined branches to model the
``development``, ``staging`` and ``production`` phases of code. We assume the
use of a canonical central repository that developers use to sync their
official changes. This repository is considered to be the canonical source and
provides the "official" state of the projects. Developers are free to use any
number of branches, tags and repositories as part of their daily work.

The code normally flows from ``development`` to ``staging`` to ``production``
and the package provides tools to facilitate this process. Each individual Git
repository is managed using any of the tools that Git provides.

In addition, the package provides a light-weight "externals" mechanism for
easily pulling in and managing the subprojects. This differs from the
functionality provided by ``git-submodule`` in that both pinned-down and open
dependencies can be defined. This resembles the way externals are handled in
Subversion. Also, the individual Git repositories are not aware of the
externals.


Configuration
*************

The package uses two different configuration files. The ``gitctl.cfg`` file
provides the higher level configuration and allows you to specify things like
the canonical repository and the names of your ``development``, ``staging``
and ``production`` branches. The ``gitexternals.cfg`` defines your project
specific configuration of required sub-components.

gitctl.cfg
**********

``upstream``

    The name used to refer to the canonical repository server, e.g. "origin".

``upstream-url``

    The address of the canonical repository server. This address needs to
    point to the server in a manner that supports pushing. Currently only SSH
    is tested. Example: git@my.gitserver.com

``branches``

    List of newline separated branches that will be tracked in the local
    repository. When the repositories are clone for each branch listed here a
    local tracking branch will be automatically created.

``development-branch``

    Name of the development branch. The above ``branches`` listing will be
    made to implicitly contain this branch.

``staging-branch``

    Name of the staging branch. The above ``branches`` listing will be made to
    implicitly contain this branch.

``production-branch``

    Name of the production branch. The above ``branches`` listing will be made
    to implicitly contain this branch.



``gitexternals.cfg``
********************

The externals configuration consists of one or more sections that have the
following properties. Each section name will be used to name the directory
where the external will be cloned into.

``url`` (mandatory)

    Full URL to the remote repository, e.g git@myserver.com:my.project.git

``type`` (optional)

    The type of the remote repository. Currently only ``git`` is supported.

``treeish`` (optional)

    The name of a "treeish" object that is checked out by default when first
    cloning the remote repository. The treeish object may refer, for example,
    to a branch or a tag. Defaults to ``master``.

``container`` (optional)

    The name of the directory where the project will be checked out
    into. An additional directory will be created under this one where
    the project files will be located so it is safe to use the same
    value for multiple projects. Relative paths are considered
    relative to the location of the config file.

An example configuration follows::

  [my.project]
  url = git@myserver.com:my.project.git
  type = git
  treeish = v1.0-dev
  container = src

This results in the my.project.git repository to be cloned into
./src/my.project and the v1.0-dev to be checked out into the working
directory.


``gitctl`` script
*****************

The ``gitctl`` script provides subcommands to implement the workflow. Each
subcommand provides additional options. See ``gitctl [subcommand] --help`` for
details::


  usage: gitctl [-h] [--config CONFIG] [--externals EXTERNALS]
  {status,create,update,branch,fetch,pending} ...

  Git workflow utility for managing projects containing multiple git
  repositories.

  positional arguments:
    {status,create,update,branch,fetch,pending}
                          Commands
      create              Initializes a new local repository and creates a
                          matching upstream repository.
      update              Updates the configured repositories by either pulling
                          existing ones or cloning new ones.
      status              Shows the status of each external project and alerts
                          if any are out of sync with the upstream repository.
      branch              Provides information and operates on the branches of
                          the projects.
      pending             Checks if there are any pending changes between two
                          consecutive states in the workflow.
      fetch               Updates the remote branches on all projects without
                          merging.

  optional arguments:
    -h, --help            show this help message and exit
    --config CONFIG       Location of the configuration file. If omitted the
                          following locations will be search: $PWD/gitctl.cfg,
                          ~/.gitctl.cfg.
    --externals EXTERNALS
                          Location of the externals configuration file. Defaults
                          to $PWD/gitexternals.cfg



Installation
************

Using setuptools::

  $ easy_install gitctl

Dependencies
************

 * Git_ (>= 1.5.5)
 * GitPython_ (> 1.4.1)

.. _Git: http://git-scm.org/
.. _GitPython: http://gitorious.org/projects/git-python

Contributors
************

 - Kai Lautaportti, Author [dokai]
