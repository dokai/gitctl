# -*- encoding: utf-8 -*-
"""Common utilities for gitctl."""

import os
import git
import shlex
import subprocess

from StringIO import StringIO
from ConfigParser import SafeConfigParser

def pretty(name, justification=30, fill='.'):
    """Returns a left justified representation of ``name``."""
    return name.ljust(justification, fill)

def project_path(proj, relative=False):
    """Returns the absolute project path unless relative=True, when a path
    relative to the current directory will be returned.
    """
    path = os.path.realpath(
        os.path.abspath(os.path.join(proj['container'], proj['name'])))
    if relative:
        prefix_len = len(os.path.commonprefix(os.path.realpath(os.getcwd()), path)) + 1
        path = path[prefix_len:]
    return path

def is_dirty(repository):
    """Returns True if the given repository has uncommited changes either in
    the working directory or the index.
    """
    g = isinstance(repository, git.Git) and repository or repository.git
    return len(g.diff().strip()) > 0 or \
           len(g.diff('--cached').strip()) > 0

def run(command, cwd=None):
    """Executes the given command."""
    if hasattr(command, 'startswith'):
        # Split the command into tokens, honoring any quoted parts
        lexer = shlex.shlex(command)
        lexer.whitespace_split = True
        command = list(lexer)

    pipe = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    retcode = pipe.wait()
    
    return retcode, pipe.stdout.read(), pipe.stderr.read()

def parse_config(config):
    """Parses the gitctl config file."""
    parser = SafeConfigParser({'upstream' : 'origin'})
    if len(parser.read([config, os.path.expanduser('~/.gitctl.cfg')])) == 0:
        raise ValueError('Invalid config file: %s' % config)
    
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
            'staging-branch' : '%s/%s' % (upstream, parser.get('gitctl', 'staging-branch')),
            'development-branch' : parser.get('gitctl', 'development-branch'),
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
           'type' : parser.get(sec, 'type').strip() }
        
        if parser.has_option(sec, 'container'):
            proj['container'] = parser.get(sec, 'container').strip()

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
    
    return projects

def generate_externals(projects):
    """Generates an externals configuration file."""
    config = SafeConfigParser()
    for project in projects:
        section = project.pop('name')
        config.add_section(section)
        for k, v in project.iteritems():
            config.set(section, k, v)
    buf = StringIO()
    config.write(buf)
    return buf.getvalue()