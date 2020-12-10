# Static cuckoo web UI mock server

## Server Installation & startup
```bash
# start server
(venv): python3 web/cuckoo/manage.py runserver
```

## UI Routing overview

| UI route <sup>1</sup> | Description                   | Template<sup>2</sup>     |
| --------------------- | ----------------------------- | ------------------------ |
| `/`                   | Dashboard/index/default route | `index.html`             |
| `/submit`             | Sample submission form        | `submit/index.html`      |
| `/submit/prepare`     | Analysis preparation form     | `submit/prepare.html`    |
| `/submit/processing`  | Analysis processing view      | `submit/processing.html` |
| `/analyses`           | Analyses overview             | `index.html`             |
| `/search`             | Result searching with filters | `index.html`             |
| `/settings`           | Application configuration     | `index.html`             |
| `/overview`           | UI kit reference              | `overview.html`          |

<sup>1</sup> Relative to serve point, url would be `localhost:8080/submit`  
<sup>2</sup> Templates live in `templates/`

## Compiling sass sources
```bash
# install sass dependency (see package.json)<sup>3</sup>
cd web/cuckoo/web/clientsrc
npm install
# run npm scripts to compile sass to css<sup>4</sup>
npm run sass
npm run sass-watch # file watch mode
```

<sup>3</sup> Requires a TLS version of a recent node.js version  
<sup>4</sup> Input files live in `/sass`, outputs compiled css to `/static/css`.

1. See [UI development documentation](docs/_concept.md) for more information and example usage.
2. See [UI Component overview](docs/overview.md) for a UI composition guide with element and component references and examples.
