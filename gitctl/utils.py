# -*- encoding: utf-8 -*-
"""Common utilities for gitctl."""

import re
import os
import sys
import shlex
import logging
import subprocess

from operator import itemgetter
from StringIO import StringIO
from ConfigParser import SafeConfigParser

LOG = logging.getLogger('gitctl')
RE_SHA1_CHECKSUM = re.compile(r'^[a-fA-F0-9]{40}$')

def is_sha1(treeish):
    """Returns True if the given treeish looks like a SHA1 sum, False
    otherwise
    """
    return RE_SHA1_CHECKSUM.match(treeish) is not None

def pretty(name, justification=40, fill='.'):
    """Returns a left justified representation of ``name``."""
    return (name + ' ').ljust(justification, fill)

def project_path(proj, relative=False):
    """Returns the absolute project path unless relative=True, when a path
    relative to the current directory will be returned.
    """
    path = os.path.realpath(
        os.path.abspath(os.path.join(proj['container'], proj['name'])))
    if relative:
        prefix_len = len(os.path.commonprefix([os.path.realpath(os.getcwd()), path])) + 1
        path = path[prefix_len:]
    return path

def run(command, cwd=None):
    """Executes the given command."""
    if hasattr(command, 'startswith'):
        # Split the command into tokens, honoring any quoted parts
        lexer = shlex.shlex(command)
        lexer.whitespace_split = True
        command = list(lexer)

    #pipe = subprocess.Popen(command, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #retcode = pipe.wait()    
    #return retcode, pipe.stdout.read(), pipe.stderr.read()
    return subprocess.call(' '.join(command), shell=True, cwd=cwd)

def parse_config(configs):
    """Parses the gitctl config file."""
    parser = SafeConfigParser({'upstream' : 'origin'})
    if len(parser.read(configs)) == 0:
        raise ValueError('Invalid config file(s): %s' % ', '.join(configs))
    
    if not parser.has_section('gitctl'):
        raise ValueError('The [gitctl] section is missing')
    
    upstream = parser.get('gitctl', 'upstream')
    return {'upstream' : upstream,
            'upstream-url' : parser.get('gitctl', 'upstream-url'),
            'commit-email' : parser.get('gitctl', 'commit-email'),
            'commit-email-prefix' : parser.get('gitctl', 'commit-email-prefix'),
            'branches' : [('%s/%s' % (upstream, branch), branch)
                          for branch
                          in parser.get('gitctl', 'branches').split()],
            'staging-branch' : parser.get('gitctl', 'staging-branch'),
            'development-branch' : parser.get('gitctl', 'development-branch'),
            'production-branch' : parser.get('gitctl', 'production-branch'),
            }

def parse_externals(config):
    """Parses the gitctl externals configuration."""
    parser = SafeConfigParser({'type' : 'git'})
    if len(parser.read(config)) == 0:
        LOG.critical('Invalid externals configuration: %s', config)
        sys.exit(1)

    projects = []
    for sec in parser.sections():
        if not parser.has_option(sec, 'url'):
            LOG.critical('Section %s is missing the ``url`` option in the externals configuration', sec)
            sys.exit(1)
       
        proj = {
           'name' : sec.strip(),
           'url' : parser.get(sec, 'url').strip(),
           'type' : parser.get(sec, 'type').strip(),
           'container' : parser.get(sec, 'container').strip(),
           }

        if proj['type'] not in ('git', 'git-svn'):
            raise ValueError('Invalid type: %s. Supported types are "git" and "git-svn".' % proj['type'])

        if proj['type'] == 'git':
            proj['treeish'] = parser.get(sec, 'treeish').strip()
        elif proj['type'] == 'git-svn':
            for opt in 'svn-trunk', 'svn-tags', 'svn-branches':
                if parser.has_option(sec, opt):
                    proj[opt] = parser.get(sec, opt).strip()
            if parser.has_option(sec, 'svn-clone-options'):
                proj['svn-clone-options'] = parser.get(sec, 'svn-clone-options').split()

        projects.append(proj)
    
    
    return sorted(projects, key=itemgetter('name'))

def generate_externals(projects):
    """Generates an externals configuration file."""
    ext = StringIO()
    for project in projects:
        print >> ext, '[%s]' % project.pop('name')
        for key, value in project.iteritems():
            print >> ext, '%s = %s' % (key, value)
        print >> ext

    return ext.getvalue().strip()

def filter_projects(projects, selection):
    """Returns"""
    if len(selection) == 0:
        return projects
    
    existing = set(p['name'] for p in projects)
    if not selection.issubset(existing):
        LOG.error('Unknown project(s): %s', ', '.join(selection))
        sys.exit(1)
    else:
        return [p for p in projects if p['name'] in selection]
