# -*- encoding: utf-8 -*-
"""CLI command parsing."""

import argparse
import gitctl.handler

parser = argparse.ArgumentParser(prog='gitctl')

# Global parameters
parser.add_argument('--config', help='Location of the configuration file. Defaults to ~/.gitctl.cfg')
parser.add_argument('--externals', help='Location of the externals configuration file. Defaults to $PWD/gitexternals.cfg')
parser.set_defaults(
    externals='gitexternals.cfg',
    config='gitctl.cfg')

# Subparser for each command
cmd_parsers = parser.add_subparsers(help='Sub-commands help')

# 'gitctl create'
parser_create = cmd_parsers.add_parser('create', help='Initializes a new local repository and creates a matching upstream repository.')
parser_create.add_argument('--skip-remote', action='store_true', default=False,
                           help='Skip creating a bare remote repository')
parser_create.add_argument('--skip-local', action='store_true', default=False,
                           help='Skip creating local tracking branches')
parser_create.add_argument('project', nargs=1, help='Name of the project')
parser_create.set_defaults(func=gitctl.handler.gitctl_create)

# 'gitctl update'
parser_update = cmd_parsers.add_parser('update', help='Updates external projects.')
parser_update.add_argument('projects', nargs='*')
parser_update.add_argument('--rebase', action='store_true')
parser_update.set_defaults(
    func=gitctl.handler.gitctl_update,
    rebase=False)

# 'gitctl status'
parser_status = cmd_parsers.add_parser('status', help='Show the status of external projects.')
parser_status.add_argument('--no-fetch', action='store_true', help='Check the status without fetching from upstream first. This is faster, but may be unreliable.')
parser_status.set_defaults(
    func=gitctl.handler.gitctl_status,
    no_fetch=False)

# 'gitctl changes'
parser_changes = cmd_parsers.add_parser('changes', help='Show the changelog for production.')
parser_changes.add_argument('--diff', action='store_true', help='Display the diff of changes.')
parser_changes.add_argument('--show-config', action='store_true', help='Prints a new gitexternals configuration to stdout.')
parser_changes.set_defaults(
    diff=False,
    show_config=False,
    func=gitctl.handler.gitctl_changes)

# 'gitctl fetch'
parser_fetch = cmd_parsers.add_parser('fetch', help='Fetches all external projects.')
parser_fetch.set_defaults(func=gitctl.handler.gitctl_fetch)


__all__ = ['parser']