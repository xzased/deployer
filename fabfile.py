import os
import json
import shutil
from fabric.api import task, require, local


TEMPLATE_KEYS = ['project_name', 'user', 'hosts']

def setup():
    """
    Setup a fresh virtualenv as well as a few useful directories, then run
    a full deployment
    """
    require('path')
    run('mkdir -p %s/env; cd %s/env; pyvenv .' % (env.path, env.path), quiet=True)
    run('cd %s; mkdir -p releases; mkdir -p packages; mkdir -p media' % env.path)
    deploy()

def set_variables():
    """
    Prompt and set project variables.
    """
    prompt('Project name:', key='project_name')
    prompt('User path:', key='path', default='%s/git' %  os.path.expanduser('~'))
    prompt('Hosts:', key='hosts', default=['node'])
    prompt('User:', key='user', default='deployer')
    env.project_path = '%s/%s' % (env.path, env.project_name)


def start_project():
    """
    Start the django project.
    """
    require('path')
    require('project_name')

    local('workon %s; cd %s; django-admin.py startproject %s;' % (env.project_name, .path, env.project_name))

def install_environment():
    """
    Create virtual environment, install Django.
    """
    require('project_name')

    local('mkvirtualenv --no-site-packages --python=/usr/bin/python3 %s; pip install Django' % env.project_name)


def fab_template():
    """
    Parse environment and install fabfile template.
    """
    require('project_path', provided_by=[set_variables])
    with open('environment.json', 'r') as f:
        json_data = json.loads(f.read())
    [(json_data[key] = env.get(key)) for key in json_data.keys()]

    with open('%s/environment.json' % env.project_path, 'w') as f:
        f.write(json.dumps(json_data))

    shutil.copy('fabfile.template', '%s/fabfile.py' % env.project_path)

def collect():
    "Collect static files"
    require('release', provided_by=[deploy, setup])
    require('path')
    run('cd %s/releases/%s; source ../../env/bin/activate; ./manage.py collectstatic' % (env.path, env.release))

def owner():
    "Set owner to web user"
    require('path')
    sudo('chown -R http:http %s' % env.path)
    sudo('chmod -R g+w %s' % env.path)

def install_site():
    "Add the virtualhost file to apache"
    require('release', provided_by=[deploy, setup])
    require('project_name')
    sudo('cp %s/releases/%s/%s.conf /etc/nginx/conf.d/' % (env.path, env.release, env.project_name))
    sudo('cp %s/releases/%s/%s.ini /etc/uwsgi/' % (env.path, env.release, env.project_name))
    sudo('systemctl enable uwsgi@%s' % env.project_name)
    collect()
    owner()

def install_requirements():
    "Install the required packages from the requirements file using pip"
    require('release', provided_by=[deploy, setup])
    run('cd %s/env; source bin/activate; pip install -r ../releases/%s/requirements.txt' % (env.path, env.release))

def symlink_current_release():
    "Symlink our current release"
    require('release', provided_by=[deploy, setup])
    run('cd %s; rm releases/previous; mv releases/current releases/previous;' % env.path, quiet=True)
    run('cd %s; ln -s %s releases/current' % (env.path, env.release))

def sync():
    "Initialize the database"
    require('path')
    run('cd %s/releases/current; source ../../env/bin/activate; ./manage.py syncdb' % env.path)

def migrate():
    "Update the database"
    require('path')
    run('cd %s/releases/current; source ../../env/bin/activate; ./manage.py makemigrations; ./manage.py migrate' % env.path)

def restart_webserver():
    "Restart the web server"
    require('project_name')
    sudo('systemctl restart uwsgi@%s' % env.project_name)
    sudo('systemctl reload nginx')