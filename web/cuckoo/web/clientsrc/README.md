# Cuckoo WebUI

## Compiling sass sources
```bash
# install sass dependency (see package.json)<sup>3</sup>
cd web/cuckoo/web/clientsrc
npm install
# run npm scripts to compile sass to css<sup>4</sup>
npm run sass # run once with development features active
npm run sass-watch # file watch mode
npm run sass-prod # run once with development features disabled and no source map
```

<sup>3</sup> Requires a TLS version of a recent node.js version  
<sup>4</sup> Input files live in `/sass`, outputs compiled css to `/static/css`.

1. See [UI development documentation](docs/index.md) for more information and example usage.
2. See [Getting started guide](docs/package/getting-started) for more information on how the development tools are set up.
