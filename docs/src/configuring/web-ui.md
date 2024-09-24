# Setting up web UI

Cuckoo3 frontend is built with [Django](https://www.djangoproject.com/){:target=_blank}.   
Default settings can be overwritten in `~/.cuckoocwd/web/web_local_settings.py`.  
You can use the frontend in two ways - commandline or [Nginx](https://nginx.org/en/){:target=_blank} and [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/){:target=_blank}.

## Commandline 

!!! warning "Unverified"

    This is from the old documentation and needs verification.  
    It may contain errors, bugs or outdated information.

This is a development server.  
You can start Cuckoo frontend from the commandline with the following command:

```bash
cuckoo web --host <listen ip> --port <listen port>
```

## Serving the web UI with Nginx And uWSGI 

!!! note "Requirements"

    Please make sure that you have:

    - installed all dependencies for [serving API and web](../installing/dependencies.md#serving-api-and-web){:target=_blank}  

If you want to serve Cuckoo in an environment such as development, testing, staging or production, you need to use uWSGI and Nginx.  
uWSGI is used as an application server and Nginx as a webserver.

**Steps**

1. Set `STATIC_ROOT` variable in `~/.cuckoocwd/web/web_local_settings.py`. Cuckoo user must have access to that path.

2. Build documentation for Cuckoo. You need to be in `cuckoo3` directory and have Python virtual environment active.

        cd docs
        python3.10 -m pip install -r requirements.txt
        mkdocs build
        cp -R site ../web/cuckoo/web/static/docs

3. Run Django `collectstatic` command. 

        cuckoo web djangocommand collectstatic

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

