# Getting started

The CSS kit is standalone and basically requires just a css file to be included.
Optionally there is a source map, which is development and debugging related.

The variables, functions and various internal parameters are part of the SASS
core, and needs the compiler to take effect, keep that in mind when branding
the package with corporate styling.

To get started using the kit, simply reference the css file into the `<head>`
section of the page. A bare initial setup may look as follows (HTML5 compliant):

```html
<!doctype html>
<html lang="en-US">
  <head>
    <meta name="charset" content="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <link rel="stylesheet" type="text/css" href="/path/to/ui.css" />
    <title>My App</title>
  </head>
  <body>
    <!-- ... application code ... -->
  </body>
</html>
```

Where `/path/to/ui.css` obviously points to the location of the ui.css file. Also
note the viewport meta tag. For responsiveness, that is required to be defined, else
the responsive media queries will not take effect.

Very optionally, custom JS can be added. The UI kit on its own does not aim to
deliver JS code, although there are some examples included in this documentation
for easy and repetitive patterns. It may seem odd to not have any JS, but this should
encourage server-side rendering over client/browser-rendering which has a detrimental
effect on the performance and speed of the app.

It is a fairly good practice to develop server-first, which means that you'll look
into server-side solutions to a problem before resorting to Javascript. By clinging
to this thought, you'll likely find that a bare minimum of javascript translates into
handling asynchronous requests and custom UI implementations that have no direct
native counterpart (such as a show-and-hide tab system, search & select patterns or
realtime searching and indexing).

## Set up SASS
As mentioned above in order to develop on the core CSS, the SASS compiler is a vital
element of the CSS code base. To install these components, navigate inside the
cuckoo web directory (_`web/cuckoo/web`_) into the _`clientsrc`_ folder. This folder
looks like:

```
cuckoo/web/cuckoo/clientsrc  
 ├── README.md  
 ├─> docs  
 │   ├─ (UI documentation files)
 ├── package-lock.json  
 ├── package.json  
 └─> sass  
     ├── _banner.sass  
     ├── _box.sass  
     ├── _button.sass  
     ├── _column.sass  
     ├── _container.sass  
     ├── _details.sass  
     ├── _footer.sass  
     ├── _form.sass  
     ├── _func.sass  
     ├── _helpers.sass  
     ├── _icon.sass  
     ├── _json-expander.sass  
     ├── _list.sass  
     ├── _misc.sass  
     ├── _navbar.sass  
     ├── _popover.sass  
     ├── _process-tree.sass  
     ├── _reset.sass  
     ├── _section.sass  
     ├── _tab.sass  
     ├── _table.sass  
     ├── _tag.sass  
     ├── _typography.sass  
     ├── _var.sass  
     ├── _view.sass  
     ├── theme.sass  
     └── ui.sass  
```

After installing node.js and navigating into this directory run the `npm install`
command. This will install all the dependencies from the `package.json` file. This
will add a `node_modules` folder with all the dependencies. When successfully
installed, you can use the following commands:

```bash
$ npm run sass # runs the sass compiler once
$ npm run sass-watch # runs the sass compiler in watch mode (watches sass/*.sass for changes)
$ npm run sass-prod #  compile sass source with minimize compression and no source maps
```

The output source will be compiled to `[web directory]/static/css` for use and inclusion.

## Todo / Good to know
- Some dependencies contain just the source code for certain seperately included
third party libraries. These are copied by hand for now (e.g Chart.js and Fontawesome),
an extra npm script is needed to gather these source distributions from the modules folder
into the static directory. Will likely be a bash script, but is open for discussion.

- Node.js is not a requirement to compile the sass source. The solution included in
the cuckoo folder happens to be the node.js version as weapon of choice by the
core developer. Even though installing node and using this toolkit should not give
any problem, if it doesn't work or there are some unfounded opinionated biases around
node.js occuring internally, sass compilers come in any language and can/should have no
trivial side-effect to the output code.
