# Web API setup/configuration
Before the web API can be used, it must first be set up. The web API cannot be used without API authentication. 
This means one of the steps is API key generation.

The web API and interface are both Django applications. Cuckoo has built-in settings for these. These can be overwritten
by modifying the following files:

- `$CWD/web/api_local_settings.py` (For the web API)
- `$CWD/web/web_local_settings.py` (For the web interface)

The web API has its own subcommand:

    cuckoo api

The following is its help page:

```
Usage: cuckoo api [OPTIONS] COMMAND [ARGS]...

  Start the Cuckoo web API (development server)

Options:
  -h, --host TEXT     Host to bind the development web API server on
  -p, --port INTEGER  Port to bind the development web API server on
  --autoreload        Automatically reload modified Python files
  --help              Show this message and exit.

Commands:
  djangocommand  Arguments for this command are passed to Django.
  token          List, create, and delete API tokens.

```


To start using the API, perform the following steps:

#### Applying migrations

**1. Try starting the web API using the following command.**

        cuckoo api

If you have never started and performed these steps before, the following message should appear:

```
Django database migrations required. Run 'cuckoo --cwd /home/cuckoo/.cuckoocwd api djangocommand migrate' to perform the migration.
```

The API uses a database to store the created users/api keys. No correct database exists yet. By default the used database will be SQLite and stored in `$CWD/web/api.db`.

**2. Apply the required migrations.**

Run the command suggested in the previous step:

    cuckoo api djangocommand migrate

This should result in one or more migrations being applied. If this is succesful, continue to the next step.

#### API key creation

**Create one or more API keys.**

The API keys can be managed by a cuckoo api subcommand: `cuckoo api token`. Its help output is the following:

```
Usage: cuckoo api token [OPTIONS]

  List, create, and delete API tokens.

Options:
  -l, --list            List all current API tokens and their owners
  -c, --create TEXT     Create a new API token for a given owner name
  --admin               Grant admin priviles to API token being created
  -d, --delete INTEGER  Delete the specified token by its token ID
  --clear               Delete all API tokens
  --help                Show this message and exit.
```

Create an API using the following command:

    cuckoo api token --create <owner name>

Output similar to this will appear:

`Created key cb60aa0d689d7f0281a5ae4d661544927273b087 with ID: 1`

This is the key that should be send in an Authentication header when using the API.
The header format must be: `Authentication: token <api key>`.

Example: 

```bash
curl "http://127.0.0.1:8090/analyses" -H "Authentication: token cb60aa0d689d7f0281a5ae4d661544927273b087"
```

All API keys can be listed using: `cuckoo api token --list`

Output example:

```
|   Key ID | Owner   | Is admin   | Created on       | API Key                                  |
|----------|---------|------------|------------------|------------------------------------------|
|        1 | example | False      | 2021-07-06 15:56 | cb60aa0d689d7f0281a5ae4d661544927273b087 |
```


#### Starting the API

The API can be started using the `cuckoo api` command. The following starts the Django development web server. 

`cuckoo api --host <listen ip> --port <listen port>`

