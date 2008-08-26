# -*- encoding: utf-8 -*-
"""Command handlers."""
import os
import shlex
import logging
import subprocess

LOG = logging.getLogger('gitctl')

def assert_clean_working_dir():
    """Asserts that the given working has no uncommited changes."""

def run(command, cwd=None):
    """Executes the given commands."""
    if hasattr(command, 'startswith'):
        # Split the command into tokens, honoring any quoted parts
        lexer = shlex.shlex(command)
        lexer.whitespace_split = True
        command = list(lexer)
    print 'Running: %s in %s' % (' '.join(command), cwd)
    return subprocess.call(command,
                           cwd=cwd,
                           stdout=open(os.devnull, 'w'),
                           stderr=subprocess.STDOUT)


def parse_config(config):
    """Parses the gitctl config file."""

def parse_externals(config):
    """Parses the gitctl externals configuration."""

def gitctl_create(args):
    """Handles the 'gitctl create' command"""
    project_path = os.path.realpath(os.path.join(os.getcwd(), args.project[0]))
    project_name = os.path.basename(project_path)
    config = parse_config(args.config)
    
    if not os.path.exists(project_path):
        raise RuntimeError('Project path does not exist!')
    
    # TODO: Assert that project does not exist at git.hexagonit.fi
    # TODO: Read the git upstream hostname and names of initial branches from
    #       the configuration file. Also the commit message address.
    
    # Set up the remote bare repository
    initialize_remote = (
        'ssh', 'git@git.hexagonit.fi',
        'mkdir -p %(project)s.git && '
        'cd %(project)s.git && '
        'git --bare init && '
        'echo %(project)s > description && '
        'echo \'. /usr/share/doc/git-core/contrib/hooks/post-receive-email\' > hooks/post-receive && '
        'chmod a+x hooks/post-receive && '
        'git config hooks.mailinglist commit@hexagonit.fi && '
        'git config hooks.emailprefix "[GIT] "' % { 'project' : project_name },
        )
    run(initialize_remote)
    
    initialize_local = (
        # Initialize the local repository and create the first commit
        'git init',
        'git add .',
        'git commit -m "gitctl: project initialization"',
        # Create the local branches
        'git branch primacontrol/development',
        'git branch primacontrol/demo',
        'git branch primacontrol/production',
        # Push initial version to upstream
        'git remote add origin git@git.hexagonit.fi:%s.git' % project_name,
        'git push origin primacontrol/development',
        'git push origin primacontrol/demo',
        'git push origin primacontrol/production',
        'git fetch',
        # Set up the local branches to track the remote ones
        'git branch -f --track primacontrol/production origin/primacontrol/production',
        'git branch -f --track primacontrol/demo origin/primacontrol/demo',
        'git branch -f --track primacontrol/development origin/primacontrol/development',
        # Check out development branch and get rid of master
        'git checkout primacontrol/development',
        'git branch -d master',
        )
    for cmd in initialize_local:
        run(cmd, cwd=project_path)


__all__ = ['gitctl_create']
