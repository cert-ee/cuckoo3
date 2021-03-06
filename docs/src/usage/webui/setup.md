# Web UI setup/configuration
Before the web UI can be used, it must first be set up.

The web UI and API and interface are both Django applications. Cuckoo has built-in settings for these. These can be overwritten
by modifying the following files:

- `$CWD/web/api_local_settings.py` (For the web API)
- `$CWD/web/web_local_settings.py` (For the web interface)

The web UI has its own subcommand:

    cuckoo web

The following is its help page:

```
Usage: cuckoo web [OPTIONS] COMMAND [ARGS]...

  Start the Cuckoo web interface (development server)

Options:
  -h, --host TEXT     Host to bind the development web interface server on
  -p, --port INTEGER  Port to bind the development web interface server on
  --autoreload        Automatically reload modified Python files
  --help              Show this message and exit.

Commands:
  djangocommand   Arguments for this command are passed to Django.
  generateconfig  Generate basic configurations for uWSGI and NGINX
```

#### Starting the web UI

The web UI can be started using the `cuckoo web` command. The following starts the Django development web server. 

`cuckoo web --host <listen ip> --port <listen port>`

#### Serving the web UI with uWSGI and NGINX

The `cuckoo web` command will start the Django development server. To actually serve the UI in production, it is advisable to use a
combination of uWSGI (to run web) and NGINX (to serve the running instance). Cuckoo can generate a basic configuration for both of these.

The `uwsgi-plugin-python3` system package or the `uwsgi` Python package must be installed in the virtualenv for this to work.

The generated configs will contain the paths of your Cuckoo install and virtualenv. Do not copy this following example configurations, generate them instead.

**Generating a uWSGI config**

    cuckoo web generateconfig --uwsgi

Example output:

```ini
; This is a basic uWSGI configuration generated by Cuckoo. It is
; recommended to review it and change it where needed. This configuration
; is meant to be used together with the generated NGINX configuration.
[uwsgi]
; To run this, the uwsgi-plugin-python3 system package must be installed or
; it must be run from a Python3 installation that has uwsgi installed.
plugins = python3,logfile
chdir = /home/cuckoo/cuckoo3/web/cuckoo/web
wsgi-file = web/wsgi.py
; The socket for NGINX to talk to. This should not listen on other
; addresses than localhost.
socket = 127.0.0.1:9090

; Verify that the users below are not root users and can read/write to/from 
; the Cuckoo CWD and installation. The configuration generator simply enters
; the user generating the configuration.
uid = cuckoo
gid = cuckoo

need-app = true
master = true
env = CUCKOO_APP=web
env = CUCKOO_CWD=/home/cuckoo/.cuckoocwd
env = CUCKOO_LOGLEVEL=debug

; Log uWSGI app and Cuckoo web logs to the following file. Change this to
; any path, but be sure the uid/gid user has write permissions to this path. 
logger = file:logfile=/tmp/cuckooweb-uwsgi.log

; The path of the Python 3 virtualenv Cuckoo is installed in.
virtualenv = /home/cuckoo/cuckoo3venv
```

**Generating a NGINX config**

Before we can generate the NGINX config, we must first determine a STATIC_ROOT.
This is the path where django will copy all its static files to. Set a path in `$CWD/web/web_local_settings.py`. 
As an example, we set it to `/tmp/static`.

After this, run the following command:

    cuckoo web djangocommand collectstatic

We can now generate the NGINX config.

    cuckoo web generateconfig --nginx

Example output:

```
# This is a basic NGINX configuration generated by Cuckoo. It is
# recommended to review it and change it where needed. This configuration
# is meant to be used together with the generated uWSGI configuration.
upstream _uwsgi_cuckoo_web {
    server 127.0.0.1:9090;
}

server {
    listen 127.0.0.1:8000;

    # Directly serve the static files for Cuckoo web. Copy 
    # (and update these after Cuckoo updates) these by running:
    # 'cuckoo web djangocommand collectstatic'. The path after alias should
    # be the same path as STATIC_ROOT. These files can be cached. Be sure
    # to clear the cache after any updates.
    location /static {
        alias /tmp/static;
    }
    
    # Pass any non-static requests to the Cuckoo web wsgi application run
    # by uwsgi. It is not recommended to cache paths here, this can cause
    # the UI to no longer reflect the correct state of analyses and tasks.
    location / {
        client_max_body_size 1G;
        proxy_redirect off;
        proxy_set_header X-Forwarded-Proto $scheme;
        include uwsgi_params;
        uwsgi_pass _uwsgi_cuckoo_web;
    }
}

```