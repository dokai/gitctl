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
                print 'Processing %s (%s)' % (proj['name'], proj['url'])
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
        parser = SafeConfigParser({'type' : 'git', 'treeish' : 'master'})
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
                proj['treeish'] = parser.get(sec, 'treeish').strip()
            elif proj['type'] == 'git-svn':
                for opt in 'svn-trunk', 'svn-tags', 'svn-branches':
                    if parser.has_option(sec, opt):
                        proj[opt] = parser.get(sec, opt).strip()
                if parser.has_option(sec, 'svn-clone-options'):
                    proj['svn-clone-options'] = parser.get(sec, 'svn-clone-options').split()

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
                commands.append((['git', 'checkout', project['treeish']], project_path))
            else:
                _cmd = ['git', 'svn', 'clone']

                if 'svn-trunk' in project:
                    _cmd.extend(['-T', project['svn-trunk']])
                if 'svn-tags' in project:
                    _cmd.extend(['-t', project['svn-tags']])
                if 'svn-branches' in project:
                    _cmd.extend(['-b', project['svn-branches']])

                if len(_cmd) == 3:
                    # Use the standard Subversion layout
                    _cmd.append('-s')

                _cmd.extend(project.get('svn-clone-options', []))
                _cmd.extend([project['url'], project_path])

                commands.append((_cmd, None))
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
                      help='Default base directory where all the projects will be placed. '
                           'This can be overridden on a per-project basis in the config file. '
                           'Defaults to ./src relative to the location of the given '
                           'configuration file.')

    parser.set_defaults(config='gitexternals.cfg')
    options, args = parser.parse_args()
    
    ctl = GitControl()
    ctl(options.config, options.container, *args)


if __name__ == '__main__':
    main()
