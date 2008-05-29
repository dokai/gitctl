from ConfigParser import SafeConfigParser

import subprocess
import os

class GitControl(object):
   """Helper class to facilite cloning/updating multiple git/git-svn
   repositories.
   """

   def __call__(self, config, container=None, *sections):
       projects = self.parse_config(config)

       if container is None:
           container = os.path.join(os.path.dirname(os.path.abspath(config)), 'src')
       else:
           container = os.path.abspath(container)

       if not os.path.isdir(container):
           os.makedirs(container)

       for proj in projects:
           if not sections or proj['name'] in sections:
               cmd, cwd = self.cmd(proj, container)
               retcode = subprocess.call(cmd, cwd=cwd)
               if retcode < 0:
                   # TODO: Error handling
                   pass

 
   def parse_config(self, config):
       """Parses a configuration file for project configurations."""
       parser = SafeConfigParser({'type' : 'git', 'branch' : 'master'})
       if len(parser.read(config)) == 0:
           raise ValueError('Invalid config file: %s' % config)

       projects = []
       for sec in parser.sections():
           for mandatory in ('url',):
               if not parser.has_option(sec, mandatory):
                   raise ValueError('Section %s is missing option %s' % (sec, mandatory))
           
           proj = {
               'name' : sec.strip(),
               'url' : parser.get(sec, 'url').strip(),
               'type' : parser.get(sec, 'type').strip() }

           if proj['type'] not in ('git', 'git-svn'):
               raise ValueError('Invalid type: %s. Supported types are "git" and "git-svn".' % proj['type'])

           if proj['type'] == 'git':
               proj['branch'] = parser.get(sec, 'branch').strip()

           projects.append(proj)

       return projects

   def cmd(self, project, container):
       """Returns a suitable (command, cwd) tuple to bring the given project
       up-to-date.
       """
       command = None
       cwd = None
       project_path = os.path.join(container, project['name'])

       # Update from upstream
       if os.path.exists(project_path):
           cwd = project_path
           if project['type'] == 'git':
               command = ['git', 'fetch', 'origin', project['branch']]
           else:
               command = ['git', 'svn', 'rebase']
       # Create a new repository
       else:
           if project['type'] == 'git':
               command = ['git', 'clone', project['url'], project_path]
           else:
               command = ['git', 'svn', 'clone', '-s', project['url'], project_path]

       return command, cwd


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
                      help='Base directory where all the projects will be placed. Defaults to the same directory where the configuration file is located in.')

    parser.set_defaults(config='externals.cfg')
    options, args = parser.parse_args()
    
    ctl = GitControl()
    ctl(options.config, options.container, *args)


if __name__ == '__main__':
    main()
