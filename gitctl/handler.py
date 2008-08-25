# -*- encoding: utf-8 -*-
"""Command handlers."""
import os

def gitctl_create(args):
    """Handles the 'gitctl create' command"""
    proj = args.project[0]
    
    if not args.skip_remote:
        # Create the remote bare repository
        pass
    
    if not os.path.exists(proj):
        os.makedirs(proj)
    
    os.chdir(proj)
    # git init
    # git remote add git@git.hexagonit.fi:%(proj).git
    # git fetch
    
    if not args.skip_local:
        # Create the local tracking branches
        # git checkout --track -b origin/primacontrol/production
        # git checkout --track -b origin/primacontrol/demo
        # git checkout --track -b origin/primacontrol/development
        pass

        

__all__ = ['gitctl_create']