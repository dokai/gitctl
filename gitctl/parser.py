# -*- encoding: utf-8 -*-
"""CLI command parsing."""

import os
import argparse
import gitctl.command

parser = argparse.ArgumentParser(
    prog='gitctl',
    description='Git workflow utility for managing projects containing '
                'multiple git repositories.')

# Global parameters
parser.add_argument('--config', type=lambda x: [x],
    help='Location of the configuration file. If omitted the following '
         'locations will be search: $PWD/gitctl.cfg, ~/.gitctl.cfg.')
parser.add_argument('--externals',
    help='Location of the externals configuration file. Defaults to '
         '$PWD/gitexternals.cfg')
parser.set_defaults(
    externals='gitexternals.cfg',
    config=[os.path.expanduser('~/.gitctl.cfg'),
            os.path.abspath('gitctl.cfg')])

# Subparser for each command
cmd_parsers = parser.add_subparsers(help='Commands')

# 'gitctl create'
parser_create = cmd_parsers.add_parser('create',
    help='Initializes a new local repository and creates a matching '
         'upstream repository.')
parser_create.add_argument('project', nargs=1, help='Name of the project')
parser_create.add_argument('--message', '-m',
    help='Initial commit message. Defaults to "[gitctl] Project initialization.".')
parser_create.set_defaults(
    message='[gitctl] Project initialization.',
    func=gitctl.command.gitctl_create)

# 'gitctl update'
parser_update = cmd_parsers.add_parser('update',
    help='Updates the configured repositories by either pulling existing ones '
         'or cloning new ones.')
parser_update.add_argument('project', nargs='*',
    help='Name of a project to update. If omitted all projects in the '
         'externals configuration will be updated.')
parser_update.add_argument('--merge', action='store_true',
    help='Merge instead of rebasing after fetching the changes.')
parser_update.set_defaults(
    func=gitctl.command.gitctl_update,
    merge=False)

# 'gitctl status'
parser_status = cmd_parsers.add_parser('status',
    help='Shows the status of each external project and alerts if any are out '
         'of sync with the upstream repository.')
parser_status.add_argument('--no-fetch', action='store_true',
    help='Check the status without fetching from upstream first. This is '
         'faster, but may be unreliable if the remote branches are out-of-sync.')
parser_status.add_argument('project', nargs='*',
    help='Name of a project to check. If omitted all projects in the '
         'externals configuration will be checked.')
parser_status.set_defaults(
    func=gitctl.command.gitctl_status,
    no_fetch=False)

# 'gitctl branch'
parser_branch = cmd_parsers.add_parser('branch',
    help='Provides information and operates on the branches of the projects.')
parser_branch.add_argument('--list', action='store_true',
    help='Lists the currently checked out branches of each project. '
         'This is the default action')
parser_branch.add_argument('--checkout', metavar='BRANCH', nargs=1,
    help='Attempts to switch each project to the given branch. The project '
         'working directory must be clean or otherwise a warning will be issued.')
parser_branch.add_argument('project', nargs='*',
    help='Name of a project. If omitted all projects in the '
         'externals configuration will be handled.')
parser_branch.set_defaults(
    func=gitctl.command.gitctl_branch,
    list=True)

# 'gitctl pending'
parser_pending = cmd_parsers.add_parser('pending',
    help='Checks if there are any pending changes between two consecutive states '
         'in the workflow. ')
parser_pending.add_argument('--dev', action='store_true',
    help='Shows which projects have pending changes in the development branch '
         'that are missing from the staging branch. This is the default mode '
         'if one is not specified.')
parser_pending.add_argument('--staging', action='store_true',
    help='Shows which projects have pending changes in the staging branch that '
         'are missing from the production branch.')
parser_pending.add_argument('--production', action='store_true',
    help='Shows which projects have pending changes in their production '
         'branch that are newer than the pinned down versions. This only '
         'makes sense if run inside the production buildout.')
parser_pending.add_argument('--diff', action='store_true',
    help='Displays the diff of changes.')
parser_pending.add_argument('--show-config', action='store_true',
    help='Prints a new externals configuration to stdout that contains the '
         'HEAD version of the production branch of each project. This assumes '
         '--production.')
parser_pending.add_argument('--no-fetch', action='store_true',
    help='Do not fetch before checking changes. This is '
         'faster, but may be unreliable if the remote branches are out-of-sync.')
parser_pending.set_defaults(
    diff=False,
    show_config=False,
    staging=False,
    production=False,
    dev=True,
    no_fetch=False,
    func=gitctl.command.gitctl_pending)

# 'gitctl fetch'
parser_fetch = cmd_parsers.add_parser('fetch',
    help='Updates the remote branches on all projects without merging.')
parser_fetch.add_argument('project', nargs='*',
    help='Name of a project to fetch. If omitted all projects in the '
         'externals configuration will be fetched.')
parser_fetch.set_defaults(func=gitctl.command.gitctl_fetch)


__all__ = ['parser']
