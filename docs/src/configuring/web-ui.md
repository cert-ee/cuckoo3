# Setting up web UI

Cuckoo3 frontend is built with [Django](https://www.djangoproject.com/){:target=_blank}.   
Default settings can be overwritten in `~/.cuckoocwd/web/web_local_settings.py`.  
You can use the frontend in two ways - commandline or [Nginx](https://nginx.org/en/){:target=_blank} and [WSGI](https://uwsgi-docs.readthedocs.io/en/latest/){:target=_blank} / [ASGI](https://asgi.readthedocs.io/en/latest/){:target=_blank}.  

!!! note "Recommendation"
    We recommend ASGI from Cuckoo version 0.10.0 and on

## Generating static content
Before serving Cuckoo web server, you have to generate the static content.

**Steps**

1. Set `STATIC_ROOT` variable in `~/.cuckoocwd/web/web_local_settings.py`. Cuckoo user must have access to that path.

2. Build documentation for Cuckoo. You need to be in `cuckoo3` directory and have Python virtual environment active.

        cd docs
        python3.10 -m pip install -r requirements.txt
        mkdocs build
        cp -R site ../web/cuckoo/web/static/docs

3. Run Django `collectstatic` command. 

        cuckoo web djangocommand collectstatic

## Serving the web UI with Daphne(ASGI) and Nginx

!!! note "Requirements"

    Please make sure that you have:

    - installed all dependencies for [serving API and web - ASGI](../installing/dependencies.md#asgi){:target=_blank}  

Daphne is used as an ASGI application server and Nginx as a webserver.

**Steps**

1. Create a systemd service for Daphne

        sudo cat <<EOF > /etc/systemd/system/cuckoo-asgi.service
        [Unit]
        Description=Daphne ASGI Server
        After=network.target

        [Service]
        User=cuckoo
        Group=cuckoo
        WorkingDirectory=/home/cuckoo/cuckoo4/web/cuckoo/web
        ExecStart=/home/cuckoo/cuckoo4/venv/bin/daphne -p 9090 cuckoo.web.web.asgi:application
        Environment=CUCKOO_APP=web
        Environment=CUCKOO_CWD=/home/cuckoo/.cuckoocwd
        Environment=CUCKOO_LOGLEVEL=DEBUG
        Restart=always

        [Install]
        WantedBy=multi-user.target
        EOF

2. Enable and start ASGI service

        sudo systemctl enable cuckoo-asgi.service && \
        sudo systemctl start cuckoo-asgi.service

3. Create a new configuration for Nginx

        sudo cat <<EOF > /etc/nginx/sites-available/cuckoo-web.conf
        upstream _asgi_server {
            server 127.0.0.1:9090;
        }

        server {
            listen 8080;

            # Directly serve the static files for Cuckoo web. Copy
            # (and update these after Cuckoo updates) these by running:
            # 'cuckoo web djangocommand collectstatic'. The path after alias should
            # be the same path as STATIC_ROOT. These files can be cached. Be sure
            # to clear the cache after any updates.
            location /static {
                alias /opt/cuckoo3/static;
            }

            # Pass any non-static requests to the Cuckoo web wsgi application run
            # by uwsgi. It is not recommended to cache paths here, this can cause
            # the UI to no longer reflect the correct state of analyses and tasks.
            location / {
                proxy_set_header Host $host;  # Ensures Host header is preserved
                proxy_set_header X-Real-IP $remote_addr;
                proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                proxy_set_header X-Forwarded-Proto $scheme;
                client_max_body_size 1G;
                proxy_redirect off;
                proxy_pass http://_asgi_server;
            }
        }
        EOF

4. Create symlink to enable Nginx configuration.

        sudo ln -s /etc/nginx/sites-available/cuckoo-web.conf /etc/nginx/sites-enabled/cuckoo-web.conf

5. Delete Nginx default enabled configuration.

        sudo rm /etc/nginx/sites-enabled/default

6. Reload the new Nginx configuration.

        sudo systemctl reload nginx


## Serving the web UI with uWSGI(WSGI) and Nginx

!!! note "Requirements"

    Please make sure that you have:

    - installed all dependencies for [serving API and web - WSGI](../installing/dependencies.md#wsgi){:target=_blank}  

uWSGI is used as WSGI application server and Nginx as a webserver.

**Steps**

4. Generate uWSGI configuration.

        cuckoo web generateconfig --uwsgi > /home/cuckoo/cuckoo3/cuckoo-web.ini

5. Generate Nginx configuration.

        cuckoo web generateconfig --nginx > /home/cuckoo/cuckoo3/cuckoo-web.conf

6. Copy uWSGI  configuration to `/etc/uwsgi/apps-available`.

        sudo mv /home/cuckoo/cuckoo3/cuckoo-web.ini /etc/uwsgi/apps-available/

7. Create symlink to enable uWSGI configuration.

        sudo ln -s /etc/uwsgi/apps-available/cuckoo-web.ini /etc/uwsgi/apps-enabled/cuckoo-web.ini

8. Copy Nginx configuration to `/etc/nginx/sites-available`.

        sudo mv /home/cuckoo/cuckoo3/cuckoo-web.conf /etc/nginx/sites-available/

9. Create symlink to enable Nginx configuration.

        sudo ln -s /etc/nginx/sites-available/cuckoo-web.conf /etc/nginx/sites-enabled/cuckoo-web.conf

10. Delete Nginx default enabled configuration.

        sudo rm /etc/nginx/sites-enabled/default

11. Reload the new Nginx configuration.

        sudo systemctl reload nginx


## Commandline 

!!! warning "Unverified"

    This is from the old documentation and needs verification.  
    It may contain errors, bugs or outdated information.

This is a development server.  
You can start Cuckoo frontend from the commandline with the following command:

```bash
cuckoo web --host <listen ip> --port <listen port>
```
