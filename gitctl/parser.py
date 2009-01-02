# -*- coding: utf-8 -*-
"""CLI command parsing."""

import os
import argparse
import gitctl.command
import pkg_resources

entrypoint = pkg_resources.iter_entry_points('console_scripts', 'gitctl').next()

parser = argparse.ArgumentParser(
    prog='gitctl',
    description='Git workflow utility for managing projects containing '
                'multiple git repositories.',
    version='%%(prog)s %s' % entrypoint.dist.version)

# Global parameters
parser.add_argument('--config', type=lambda x: [x],
    help='Location of the configuration file. If omitted the following '
         'locations will be search: $PWD/gitctl.cfg, ~/.gitctl.cfg.')
parser.add_argument('--externals',
    help='Location of the externals configuration file. Defaults to '
         '$PWD/gitexternals.cfg')
parser.add_argument('--verbose', action='store_true', help='Prints more verbose output about repositories.')
parser.set_defaults(
    verbose=False,
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
    help='Updates the configured repositories by either attempting a fast-forward '
         'merge on existing project branches or cloning new projects.')
parser_update.add_argument('project', nargs='*',
    help='Name of a project to update. If omitted all projects in the '
         'externals configuration will be updated.')
parser_update.add_argument('--from-file', '-f', 
    type=argparse.FileType('r'), default=None,
    help='the file with a list of projects')
parser_update.set_defaults(
    func=gitctl.command.gitctl_update,
    )

# 'gitctl path'
parser_path = cmd_parsers.add_parser('path',
    help='Shows the path to the project directory.')
parser_path.add_argument('project', nargs="*",
    help='Name of a project to show the path.')
parser_path.add_argument('--relative', action='store_true',
    help='Whether the path should be relative.')
parser_path.add_argument('--from-file', '-f', 
    type=argparse.FileType('r'), default=None,
    help='the file with a list of projects')
parser_path.set_defaults(
    func=gitctl.command.gitctl_path,
    )

# 'gitctl sh'
parser_sh = cmd_parsers.add_parser('sh',
    help='Executes shell command for specified projects.')
parser_sh.add_argument('project', nargs="*",
    help='Name of a project.')
parser_sh.add_argument('--from-file', '-f', 
    type=argparse.FileType('r'), default=None,
    help='the file with a list of projects')
parser_sh.add_argument('--command', '-c',
    type=str, default="echo 'no command specified'",
    help='the file with a list of projects')
parser_sh.set_defaults(
    func=gitctl.command.gitctl_sh,
    )

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
parser_status.add_argument('--from-file', '-f', 
    type=argparse.FileType('r'), default=None,
    help='the file with a list of projects')
parser_status.add_argument('--commits', action='store_true', help='Displays a summary of the commits that differ a branch from another')
parser_status.add_argument('--limit', type=int, help='Limits the number of commits shown in the summary. Ignored with --commits.')
parser_status.set_defaults(
    func=gitctl.command.gitctl_status,
    commits=False,
    limit=-1,
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
parser_branch.add_argument('--from-file', '-f', 
    type=argparse.FileType('r'), default=None,
    help='the file with a list of projects')
parser_branch.set_defaults(
    func=gitctl.command.gitctl_branch,
    list=True)

# 'gitctl pending'
parser_pending = cmd_parsers.add_parser('pending',
    help='Checks if there are any pending changes in the production branches '
         'compared to the pinned down versions in externals configuration. ')
parser_pending.add_argument('--show-config', action='store_true',
    help='Prints a new externals configuration to stdout that contains the '
         'HEAD version of the production branch of each project.')
parser_pending.add_argument('--no-fetch', action='store_true',
    help='Do not fetch before checking changes. This is '
         'faster, but may be unreliable if the remote branches are out-of-sync.')
parser_pending.add_argument('--from-file', '-f', 
    type=argparse.FileType('r'), default=None,
    help='the file with a list of projects')
parser_pending.set_defaults(
    show_config=False,
    no_fetch=False,
    func=gitctl.command.gitctl_pending)

# 'gitctl fetch'
parser_fetch = cmd_parsers.add_parser('fetch',
    help='Updates the remote branches on all projects without merging.')
parser_fetch.add_argument('project', nargs='*',
    help='Name of a project to fetch. If omitted all projects in the '
         'externals configuration will be fetched.')
parser_fetch.add_argument('--from-file', '-f', 
    type=argparse.FileType('r'), default=None,
    help='the file with a list of projects')
parser_fetch.set_defaults(func=gitctl.command.gitctl_fetch)

__all__ = ['parser']
