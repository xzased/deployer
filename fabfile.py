import os
import json
import shutil
from fabric.api import task, require, local, prompt, env, lcd, prefix


@task
def setup():
    """
    Setup a fresh virtualenv as well as a few useful directories.
    """
    set_variables()
    install_environment()
    start_project()
    modify_settings()
    bootstrap()
    fab_template()
    conf_scripts()
    bootstrap()
    if env.theme:
        bootswatch()
    git()

@task
def set_variables():
    """
    Prompt and set project variables.
    """
    prompt('Project name:', key='project_name')
    prompt('User path:', key='path', default='%s/git' %  os.path.expanduser('~'))
    prompt('Hosts:', key='hosts', default=['node'])
    prompt('User:', key='user', default='deployer')
    prompt('Bootstrap:', key='bootstrap', default='3.2.0')
    prompt('Theme:', key='theme')
    env.project_path = '%s/%s' % (env.path, env.project_name)

@task
def start_project():
    """
    Start the django project.
    """
    require('project_name', provided_by=[set_variables])
    require('project_path', provided_by=[set_variables])
    with lcd(env.path), prefix('source ~/.virtualenvs/%s/bin/activate' % env.project_name):
        local('django-admin.py startproject %s;' % env.project_name)
        with lcd(env.project_path):
            local('mkdir -p static; mkdir -p media; mkdir -p templates;')
            local('mkdir -p %s/static;' % env.project_name)

def replace_and_write(source, destination, mode='w', replace=None):
    with open(source, 'r') as f:
        data = f.read()
        if replace:
            data = data.replace('$%s' % replace, env[replace])
    with open(destination, mode) as f:
        f.write(data)

@task
def modify_settings():
    """
    Modify Django settings.
    """
    require('project_name', provided_by=[set_variables])
    require('project_path', provided_by=[set_variables])
    settings_path = '%s/%s' % (env.project_path, env.project_name)
    settings = '%s/settings.py' % settings_path
    replace_and_write('django/django.conf', settings, mode='a')
    shutil.copy(settings, '%s/settings-dev.py' % settings_path)
    shutil.copy('django/urls-dev.template', '%s/urls-dev.py' % settings_path)

@task
def install_environment():
    """
    Create virtual environment, install Django.
    """
    require('project_name', provided_by=[set_variables])
    require('project_path', provided_by=[set_variables])
    require('project_name', provided_by=[set_variables])
    local('pyvenv ~/.virtualenvs/%s' % env.project_name)
    with prefix('source ~/.virtualenvs/%s/bin/activate' % env.project_name):
        local('pip install Django')

def fab_template():
    """
    Parse environment and install fabfile template.
    """
    require('project_path', provided_by=[set_variables])
    with open('environment.json', 'r') as f:
        json_data = json.loads(f.read())
    for key in json_data.keys():
        json_data[key] = env.get(key)
    with open('%s/environment.json' % env.project_path, 'w') as f:
        f.write(json.dumps(json_data))
    replace_and_write('fab/fabfile.template', '%s/fabfile.py' % env.project_path, replace='project_name')

@task
def conf_scripts():
    """
    Parse and copy nginx and uwsgi conf scripts.
    """
    require('project_name', provided_by=[set_variables])
    require('project_path', provided_by=[set_variables])
    nginx_dest = '%s/%s.conf' % (env.project_path, env.project_name)
    replace_and_write('conf/nginx.conf', nginx_dest, replace='project_name')
    uwsgi_dest = '%s/%s.ini' % (env.project_path, env.project_name)
    replace_and_write('conf/uwsgi.ini', uwsgi_dest, replace='project_name')
    kate_dest = '%s/.kateproject' % env.project_path
    replace_and_write('conf/kateproject', kate_dest, replace='project_name')

@task
def bootstrap():
    """
    Download and extract bootstrap.
    """
    require('bootstrap', provided_by=[set_variables])
    require('project_name', provided_by=[set_variables])
    bootstrap_base = 'https://github.com/twbs/bootstrap/releases/download/v%s' % env.bootstrap
    bootstrap_dist = 'bootstrap-%s-dist.zip' % env.bootstrap
    bootstrap_url = '%s/%s' % (bootstrap_base, bootstrap_dist)
    with lcd(env.project_path):
        local('wget %s' % bootstrap_url)
        local('unzip -j -o %s %s/css/* -d %s/static/css/' % (bootstrap_dist, bootstrap_dist.replace('.zip', ''), env.project_name))
        local('unzip -j -o %s %s/js/* -d %s/static/js/' % (bootstrap_dist, bootstrap_dist.replace('.zip', ''), env.project_name))
        local('unzip -j -o %s %s/fonts/* -d %s/static/fonts/' % (bootstrap_dist, bootstrap_dist.replace('.zip', ''), env.project_name))
        local('rm %s' % bootstrap_dist)

@task
def bootswatch():
    """
    Download and install bootswatch theme.
    """
    require('theme', provided_by=[set_variables])
    require('project_name', provided_by=[set_variables])
    with lcd(env.project_path):
        local('wget http://bootswatch.com/%s/bootstrap.min.css' % env.theme)
        local('mv bootstrap.min.css %s/static/css/bootstrap.min.css' % env.project_name)

@task
def git():
    """
    Initialize git.
    """
    require('project_path', provided_by=[set_variables])
    with lcd(env.project_path):
        local('git init')
    local('cp git/gitignore %s/.gitignore' % env.project_path)
    with lcd(env.project_path):
        local('git add -A; git commit -m "Initial commit."')