import unittest
import gitctl
import tempfile
import shutil
import os

class GitControlTestCase(unittest.TestCase):

    def setUp(self):
        self.path = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.path)

class TestConfigParser(GitControlTestCase):
    
    def config(self, data):
        filename = os.path.join(self.path, 'gitexternals.cfg')
        open(filename, 'w').write(data)
        return filename

    def test_git_project_full_configuration(self):
        ctl = gitctl.GitControl()
        config = self.config("""\
[my.project]
type = git
url = git@github.com:dokai/my-project.git
treeish = insane-refactoring
dir = projects
""")
        projects = ctl.parse_config(config)

        self.assertEquals(1, len(projects))
        self.assertEquals('my.project', projects[0]['name'])
        self.assertEquals('git', projects[0]['type'])
        self.assertEquals('git@github.com:dokai/my-project.git', projects[0]['url'])
        self.assertEquals('insane-refactoring', projects[0]['treeish'])
        self.assertEquals('projects', projects[0]['container'])

    def test_git_project_defaults(self):
        ctl = gitctl.GitControl()
        config = self.config("""\
[my.project]
url = git@github.com:dokai/my-project.git
""")
        projects = ctl.parse_config(config)

        self.assertEquals(1, len(projects))
        self.assertEquals('my.project', projects[0]['name'])
        self.assertEquals('git', projects[0]['type'])
        self.assertEquals('git@github.com:dokai/my-project.git', projects[0]['url'])
        self.assertEquals('master', projects[0]['treeish'])
        self.failIf('container' in projects[0])

    def test_gitsvn_project_default_options(self):
        ctl = gitctl.GitControl()
        config = self.config("""\
[other.project]
url = https://svn.server.com/svn/other.project
type = git-svn
""")
        projects = ctl.parse_config(config)

        self.assertEquals(1, len(projects))
        self.assertEquals('other.project', projects[0]['name'])
        self.assertEquals('git-svn', projects[0]['type'])
        self.assertEquals('https://svn.server.com/svn/other.project', projects[0]['url'])
        self.failIf('svn-trunk' in  projects[0])
        self.failIf('svn-tags' in projects[0])
        self.failIf('svn-branches' in projects[0])
        self.failIf('treeish' in projects[0])
        self.failIf('container' in projects[0])

    def test_gitsvn_project_custom_layout(self):
        ctl = gitctl.GitControl()
        config = self.config("""\
[other.project]
url = https://svn.server.com/svn/other.project
type = git-svn
svn-trunk = project/trunk
svn-tags = project/tags
svn-branches = project/branches
""")
        projects = ctl.parse_config(config)

        self.assertEquals(1, len(projects))
        self.assertEquals('other.project', projects[0]['name'])
        self.assertEquals('git-svn', projects[0]['type'])
        self.assertEquals('https://svn.server.com/svn/other.project', projects[0]['url'])
        self.assertEquals('project/trunk', projects[0]['svn-trunk'])
        self.assertEquals('project/tags', projects[0]['svn-tags'])
        self.assertEquals('project/branches', projects[0]['svn-branches'])
        self.failIf('treeish' in projects[0])
        self.failIf('container' in projects[0])

    def test_gitsvn_clone_options(self):
        ctl = gitctl.GitControl()
        config = self.config("""\
[other.project]
url = https://svn.server.com/svn/other.project
type = git-svn
svn-clone-options =
    --username=dokai
    --no-metadata
    --prefix=foobar
""")
        projects = ctl.parse_config(config)

        self.assertEquals(1, len(projects))
        self.assertEquals('other.project', projects[0]['name'])
        self.assertEquals(['--username=dokai', '--no-metadata', '--prefix=foobar'],
                          projects[0]['svn-clone-options'])



    def test_gitsvn_project_trunk_only(self):
        ctl = gitctl.GitControl()
        config = self.config("""\
[other.project]
url = https://svn.server.com/svn/other.project
type = git-svn
svn-trunk = project/trunk
""")
        projects = ctl.parse_config(config)

        self.assertEquals(1, len(projects))
        self.assertEquals('other.project', projects[0]['name'])
        self.assertEquals('git-svn', projects[0]['type'])
        self.assertEquals('https://svn.server.com/svn/other.project', projects[0]['url'])
        self.assertEquals('project/trunk', projects[0]['svn-trunk'])
        self.failIf('svn-tags' in projects[0])
        self.failIf('svn-branches' in projects[0])
        self.failIf('treeish' in projects[0])
        self.failIf('container' in projects[0])


    def test_multiple_projects(self):
        ctl = gitctl.GitControl()
        config = self.config("""\
[my.project]
url = git@github.com:dokai/my-project.git

[foo.bar]
url = git@git.server.com:foobar/foo.bar.git

[other.project]
url = https://svn.server.com/svn/other.project
type = git-svn
""")
        projects = ctl.parse_config(config)

        self.assertEquals(3, len(projects))
        self.assertEquals(set(['my.project', 'foo.bar', 'other.project']),
                          set([p['name'] for p in projects]))


class TestGitCommand(GitControlTestCase):
    
    def test_git_clone(self):
        ctl = gitctl.GitControl()
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
        ctl = gitctl.GitControl()
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
        ctl = gitctl.GitControl()
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
        ctl = gitctl.GitControl()
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


def test_suite():
    return unittest.TestSuite([
            unittest.makeSuite(TestConfigParser),
            unittest.makeSuite(TestGitCommand),
            ])
