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

Very optionally, custom JS can be added. The CSS kit does not aim to deliver JS
code, although there is some examples included in this documentation for easy
and repetitive patterns. It may seem odd to not have any JS, but this should
encourage server-side rendering over inline-rendering which has a detrimental
effect on the performance and speed of the app.

In chapter 4, some pointers, examples and snippets are provided for simple interactions,
but it's left up to the user to implement those.
