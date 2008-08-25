import unittest
import tempfile
import shutil
import os

import gitctl
import gitctl.command


class GitControlTestCase(unittest.TestCase):

    def setUp(self):
        self.path = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.path)

    def config(self, data):
        filename = os.path.join(self.path, 'gitexternals.cfg')
        open(filename, 'w').write(data)
        return filename


class TestConfigParser(GitControlTestCase):
    
    def test_git_project_full_configuration(self):
        config = self.config("""\
[my.project]
type = git
url = git@github.com:dokai/my-project.git
treeish = insane-refactoring
dir = projects
""")
        ctl = gitctl.GitControl(config)

        self.assertEquals(1, len(ctl.projects))
        self.assertEquals('my.project', ctl.projects[0]['name'])
        self.assertEquals('git', ctl.projects[0]['type'])
        self.assertEquals('git@github.com:dokai/my-project.git', ctl.projects[0]['url'])
        self.assertEquals('insane-refactoring', ctl.projects[0]['treeish'])
        self.assertEquals('projects', ctl.projects[0]['container'])

    def test_git_project_defaults(self):
        config = self.config("""\
[my.project]
url = git@github.com:dokai/my-project.git
""")
        ctl = gitctl.GitControl(config)

        self.assertEquals(1, len(ctl.projects))
        self.assertEquals('my.project', ctl.projects[0]['name'])
        self.assertEquals('git', ctl.projects[0]['type'])
        self.assertEquals('git@github.com:dokai/my-project.git', ctl.projects[0]['url'])
        self.assertEquals('master', ctl.projects[0]['treeish'])
        self.failIf('container' in ctl.projects[0])

    def test_gitsvn_project_default_options(self):
        config = self.config("""\
[other.project]
url = https://svn.server.com/svn/other.project
type = git-svn
""")
        ctl = gitctl.GitControl(config)

        self.assertEquals(1, len(ctl.projects))
        self.assertEquals('other.project', ctl.projects[0]['name'])
        self.assertEquals('git-svn', ctl.projects[0]['type'])
        self.assertEquals('https://svn.server.com/svn/other.project', ctl.projects[0]['url'])
        self.failIf('svn-trunk' in  ctl.projects[0])
        self.failIf('svn-tags' in ctl.projects[0])
        self.failIf('svn-branches' in ctl.projects[0])
        self.failIf('treeish' in ctl.projects[0])
        self.failIf('container' in ctl.projects[0])

    def test_gitsvn_project_custom_layout(self):
        config = self.config("""\
[other.project]
url = https://svn.server.com/svn/other.project
type = git-svn
svn-trunk = project/trunk
svn-tags = project/tags
svn-branches = project/branches
""")
        ctl = gitctl.GitControl(config)

        self.assertEquals(1, len(ctl.projects))
        self.assertEquals('other.project', ctl.projects[0]['name'])
        self.assertEquals('git-svn', ctl.projects[0]['type'])
        self.assertEquals('https://svn.server.com/svn/other.project', ctl.projects[0]['url'])
        self.assertEquals('project/trunk', ctl.projects[0]['svn-trunk'])
        self.assertEquals('project/tags', ctl.projects[0]['svn-tags'])
        self.assertEquals('project/branches', ctl.projects[0]['svn-branches'])
        self.failIf('treeish' in ctl.projects[0])
        self.failIf('container' in ctl.projects[0])

    def test_gitsvn_clone_options(self):
        config = self.config("""\
[other.project]
url = https://svn.server.com/svn/other.project
type = git-svn
svn-clone-options =
    --username=dokai
    --no-metadata
    --prefix=foobar
""")
        ctl = gitctl.GitControl(config)

        self.assertEquals(1, len(ctl.projects))
        self.assertEquals('other.project', ctl.projects[0]['name'])
        self.assertEquals(['--username=dokai', '--no-metadata', '--prefix=foobar'],
                          ctl.projects[0]['svn-clone-options'])



    def test_gitsvn_project_trunk_only(self):
        config = self.config("""\
[other.project]
url = https://svn.server.com/svn/other.project
type = git-svn
svn-trunk = project/trunk
""")
        ctl = gitctl.GitControl(config)

        self.assertEquals(1, len(ctl.projects))
        self.assertEquals('other.project', ctl.projects[0]['name'])
        self.assertEquals('git-svn', ctl.projects[0]['type'])
        self.assertEquals('https://svn.server.com/svn/other.project', ctl.projects[0]['url'])
        self.assertEquals('project/trunk', ctl.projects[0]['svn-trunk'])
        self.failIf('svn-tags' in ctl.projects[0])
        self.failIf('svn-branches' in ctl.projects[0])
        self.failIf('treeish' in ctl.projects[0])
        self.failIf('container' in ctl.projects[0])


    def test_multiple_projects(self):
        config = self.config("""\
[my.project]
url = git@github.com:dokai/my-project.git

[foo.bar]
url = git@git.server.com:foobar/foo.bar.git

[other.project]
url = https://svn.server.com/svn/other.project
type = git-svn
""")
        ctl = gitctl.GitControl(config)

        self.assertEquals(3, len(ctl.projects))
        self.assertEquals(set(['my.project', 'foo.bar', 'other.project']),
                          set([p['name'] for p in ctl.projects]))


class TestGitCommand(GitControlTestCase):
    
    def test_git_clone(self):
        ctl = gitctl.GitControl(self.config(""))
        project = {
            'name' : 'my.project',
            'url' : 'git@github.com:dokai/my-project.git',
            'treeish' : 'master',
            'type' : 'git',
            }
        project_path = os.path.join(self.path, 'my.project')
        commands = ctl.cmd(project, self.path)
        self.assertEquals(2, len(commands))

        self.assertEquals(['git', 'clone', '--no-checkout', project['url'], project_path],
                          commands[0][0])
        self.failUnless(commands[0][1] is None)

        self.assertEquals(['git', 'checkout', project['treeish']], commands[1][0])
        self.assertEquals(project_path, commands[1][1])

    def test_git_pull(self):
        ctl = gitctl.GitControl(self.config(""))
        project_path = os.path.join(self.path, 'my.project')

        project = {
            'name' : 'my.project',
            'url' : 'git@github.com:dokai/my-project.git',
            'treeish' : 'master',
            'type' : 'git',
            }

        os.makedirs(project_path)
        commands = ctl.cmd(project, self.path)

        self.assertEquals(1, len(commands))
        self.assertEquals(['git', 'pull', '--rebase', 'origin'], commands[0][0])
        self.assertEquals(project_path, commands[0][1])

    
    def test_gitsvn_clone(self):
        ctl = gitctl.GitControl(self.config(""))
        project_path = os.path.join(self.path, 'my.project')

        project = {
            'name' : 'my.project',
            'url' : 'https://svn.server.com/my.project',
            'type' : 'git-svn',
            'svn-trunk' : 'trunk',
            'svn-tags' : 'tags',
            'svn-branches' : 'branches',
            }

        commands = ctl.cmd(project, self.path)

        self.assertEquals(2, len(commands))
        self.assertEquals(['git', 'svn', 'clone', '-T', 'trunk', '-t', 'tags', '-b', 'branches', 'https://svn.server.com/my.project', project_path], commands[0][0])
        self.assertEquals(None, commands[0][1])
        self.assertEquals(['git', 'repack', '-d'], commands[1][0])
        self.assertEquals(project_path, commands[1][1])

    def test_gitsvn_rebase(self):
        ctl = gitctl.GitControl(self.config(""))
        project_path = os.path.join(self.path, 'my.project')

        project = {
            'name' : 'my.project',
            'url' : 'https://svn.server.com/my.project',
            'type' : 'git-svn',
            'svn-trunk' : 'trunk',
            'svn-tags' : 'tags',
            'svn-branches' : 'branches',
            }

        os.makedirs(project_path)
        commands = ctl.cmd(project, self.path)

        self.assertEquals(1, len(commands))
        self.assertEquals(['git', 'svn', 'rebase'], commands[0][0])
        self.assertEquals(project_path, commands[0][1])


class TestArgumentParser(unittest.TestCase):
    
    def test_gitctl_create_with_defaults(self):
        args = gitctl.command.parser.parse_args('create my.project'.split())
        self.assertEquals(args.project, ['my.project'])
        self.assertEquals(args.skip_remote, False)
        self.assertEquals(args.skip_local, False)
    
    def test_gitctl_create_with_options(self):
        args = gitctl.command.parser.parse_args('create my.project --skip-remote --skip-local'.split())
        self.assertEquals(args.project, ['my.project'])
        self.assertEquals(args.skip_remote, True)
        self.assertEquals(args.skip_local, True)


def test_suite():
    return unittest.TestSuite([
            unittest.makeSuite(TestConfigParser),
            unittest.makeSuite(TestGitCommand),
            unittest.makeSuite(TestArgumentParser),
            ])
