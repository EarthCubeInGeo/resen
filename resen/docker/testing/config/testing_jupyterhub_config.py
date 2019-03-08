'''
    testing_jupyterhub_config.py

    A jupyterhub config file for running the jupyterhub docker image on a local
    machine. This config doesn't require authentication.

    Currently intended for testing purposes only.

'''


c = get_config()

# Use Jupyterlab instead of Jupyterhub or notebook server
c.Spawner.default_url = '/lab'

# Start the notebook server in the home jovyan directory
c.Spawner.notebook_dir = '/home/jovyan/'

# Don't use authentication locally
c.JupyterHub.authenticator_class = 'dummyauthenticator.DummyAuthenticator'
c.DummyAuthenticator.password = None

# Whitlelist jovyan user and make them a notebook adminstrator
c.Authenticator.whitelist = set(['jovyan'])
c.Authenticator.admin_users = set(['jovyan'])
c.JupyterHub.admin_access = True
