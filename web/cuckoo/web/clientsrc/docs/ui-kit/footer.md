# Footer

The footer element defines footer/tertiary content or defines the end of content.
The footer included in the core styles has been structured in a way that it will
or should be on the bottom of the page at all time, like a sticky element that gets
pushed further down whenever space is required for the main content. This requires
some implementation/mechanics, as shown in the example.

Example: Implementation of a sticky footer, in a view context:
```html
<div class="view">
  <main>
    ...
  </main>
  <div class="footer-push"></div>
</div>
<footer class="footer"></footer>
```

Example: Markup inside footer element
```html
<footer class="footer">
  <div class="footer-start">
    <!-- top-footer/floating content, like navs and links -->
  </div>
  <div class="footer-end">
    <!-- bottom-footer/bar content, like copyrights and logos -->
  </div>
</footer>
```

| class           | type   | description                          |
| --------------- | ------ | ------------------------------------ |
| `.footer`       | parent | defines footer block                 |
| `.footer-start` | child  | top content space for footer content |
| `.footer-end`   | child  | bottom bar of the footer element     |

---
_file: `web/cuckoo/web/clientsrc/sass/_footer.sass`_

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
  2.6 [Container](./container.md)  
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
  2.22 **[Footer](./footer.md)**  
  2.23 [Misc](./misc.md)  
  2.24 [Helpers](./helpers.md)  

---
