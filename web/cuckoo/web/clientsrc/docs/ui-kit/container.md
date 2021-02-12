# Container

The container utility acts as a wrapper around content. Containers are sensitive
to responsive breakpoints and will scale accordingly, the content contained
within should be on block-level and resize naturally with the surrounding
parent container.

Example: Container wrappers
```html
  <div class="container is-fixed"><!-- main content goes here --></div>
  <div class="container is-fixed is-smol"><!-- smaller container box (works best for lots of text) --></div>
  <div class="container is-portal-view"><!-- max viewport width--></div>
```

| class             | type     | description                                                                    |
| ----------------- | -------- | ------------------------------------------------------------------------------ |
| `.container`      | parent   | Wrapping class around main content                                             |
| `.is-fixed`       | modifier | Responsive container box width fixed width breakpoints                         |
| `.is-smol`        | modifier | Additional modifier to `.is-fixed` that will have less width in the container. |
| `.is-portal-view` | modifier | Scaling container box that consumes max viewport width                         |

---
_file: `web/cuckoo/web/clientsrc/sass/_container.sass`_
