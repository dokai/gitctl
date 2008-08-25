# -*- encoding: utf-8 -*-
"""CLI command parsing."""

import argparse

parser = argparse.ArgumentParser(prog='gitctl')

# Global parameters
parser.add_argument('--config')
parser.add_argument('--externals')

# Subparser for each command
cmd_parsers = parser.add_subparsers()

# 'gitctl create'
parser_create = cmd_parsers.add_parser('create')
parser_create.add_argument('--skip-remote', action='store_true', default=False,
                           help='Skip creating a bare remote repository')
parser_create.add_argument('--skip-local', action='store_true', default=False,
                           help='Skip creating local tracking branches')
parser_create.add_argument('project', nargs=1, help='Name of the project')

# 'gitctl update'
parser_update = cmd_parsers.add_parser('update')
parser_update.add_argument('projects', nargs='*')

# 'gitctl pending'
parser_pending = cmd_parsers.add_parser('pending')

# 'gitctl status'
parser_status = cmd_parsers.add_parser('status')

# 'gitctl push'
parser_push = cmd_parsers.add_parser('push')

# 'gitctl fetch'
parser_fetch = cmd_parsers.add_parser('fetch')

# 'gitctl pull'
parser_pull = cmd_parsers.add_parser('pull')

__all__ = ['parser']