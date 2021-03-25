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

---

### More docs

0. [Table of contents](../index.md)

1. _Package_  
  1.1 [Getting Started](../package/getting-started.md)  
  1.2 [Core concept](../package/concept.md)  

2. _UI Kit_  
  2.1 [Variables](./var.md)  
  2.2 [Reset](./reset.md)  
  2.3 [Typography](./typography.md)  
  2.4 [View](./view.md)  
  2.5 [Navbar](./navbar.md)  
  2.6 **[Container](./container.md)**  
  2.7 [Section](./section.md)  
  2.8 [Column](./column.md)  
  2.9 [Button](./button.md)  
  2.10 [Table](./table.md)  
  2.11 [Details](./details.md)  
  2.12 [Form](./form.md)  
  2.13 [List](./list.md)  
  2.14 [Process tree](./process-tree.md)  
  2.15 [Icon](./icon.md)  
  2.16 [Box](./box.md)  
  2.17 [Banner](./banner.md)  
  2.18 [Tab](./tab.md)  
  2.19 [Tag](./tag.md)  
  2.20 [Popover](./popover.md)  
  2.21 [JSON Expander](./json-expander.md)  
  2.22 [Footer](./footer.md)  
  2.23 [Misc](./misc.md)  
  2.24 [Helpers](./helpers.md)  

---
