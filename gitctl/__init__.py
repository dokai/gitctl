from ConfigParser import SafeConfigParser

import subprocess
import sys
import os

class GitControl(object):
    """Helper class to facilitate cloning/updating multiple git/git-svn
    repositories.
    """

    def __call__(self, config, default_container=None, *sections):
        projects = self.parse_config(config)
        
        config_location = os.path.dirname(os.path.abspath(config))
        if default_container is None:
            default_container = os.path.join(config_location, 'src')
        else:
            default_container = os.path.abspath(default_container)
            
        for proj in projects:
            if not sections or proj['name'] in sections:
                # Allow the container to be overridden per project
                container = os.path.join(config_location, proj.get('container', default_container))
                if not os.path.isdir(container):
                    os.makedirs(container)

                for cmd, cwd in self.cmd(proj, container):
                   retcode = subprocess.call(cmd, cwd=cwd)
                   if retcode < 0:
                       print >> sys.stderr, 'Error running: %s' % ' '.join(cmd)
                       if cwd is not None:
                           print >> sys.stderr, 'Current directory: %s' % cwd
 
    def parse_config(self, config):
        """Parses a configuration file for project configurations."""
        parser = SafeConfigParser({'type' : 'git', 'branch' : 'master'})
        if len(parser.read(config)) == 0:
            raise ValueError('Invalid config file: %s' % config)

        projects = []
        for sec in parser.sections():
            if not parser.has_option(sec, 'url'):
                raise ValueError('Section %s is missing the url option %s' % sec)
           
            proj = {
               'name' : sec.strip(),
               'url' : parser.get(sec, 'url').strip(),
               'type' : parser.get(sec, 'type').strip() }
            
            if parser.has_option(sec, 'dir'):
                proj['container'] = parser.get(sec, 'dir').strip()

            if proj['type'] not in ('git', 'git-svn'):
                raise ValueError('Invalid type: %s. Supported types are "git" and "git-svn".' % proj['type'])

            if proj['type'] == 'git':
                proj['branch'] = parser.get(sec, 'branch').strip()

            projects.append(proj)

        return projects

    def cmd(self, project, container):
        """Returns a sequence of suitable (command, cwd) tuples to bring the
        given project up-to-date.
        """
        commands = []
        project_path = os.path.join(container, project['name'])

        # Update from upstream
        if os.path.exists(project_path):
            cwd = project_path
            if project['type'] == 'git':
                commands.append((['git', 'pull', '--rebase', 'origin'], project_path))
            else:
                commands.append((['git', 'svn', 'rebase'], project_path))
        # Create a new repository
        else:
            if project['type'] == 'git':
                commands.append((['git', 'clone', '--no-checkout', project['url'], project_path], None))
                commands.append((['git', 'checkout', project['branch']], project_path))
            else:
                commands.append((['git', 'svn', 'clone', '-s', project['url'], project_path], None))
                commands.append((['git', 'repack', '-d'], project_path))

        return commands


def main():
    from optparse import OptionParser

    usage = """%prog <options> [proj1 [proj2]]...

By default all projects in the configuration file will be pulled from
the remote repositories. However, if one or more project names are
provided as arguments to the script only those projects will be
pulled.
"""

    parser = OptionParser(usage=usage)
    parser.add_option('-c', '--config', dest='config',
                      help='Configuration file. Defaults to: %default')
    parser.add_option('-d', '--dir', dest='container', metavar='DIR',
                      help='Base directory where all the projects will be placed. '
                           'Defaults to ./src relative to the location of the '
                           'configuration file.')

    parser.set_defaults(config='externals.cfg')
    options, args = parser.parse_args()
    
    ctl = GitControl()
    ctl(options.config, options.container, *args)


if __name__ == '__main__':
    main()
