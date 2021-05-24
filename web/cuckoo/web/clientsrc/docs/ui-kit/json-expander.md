# JSON Expander
This is an extra class that is derived from the idea of having a collapsible
list. Unlike is-tree classes from the list sections, this json-expander class
focusses on making a tree to display plain data objects, with the possibility
to do so recursively. It's appearance can be mostly styled using helpers and
customizers.

Example: JSON tree
```html
<ul class="json-expander is-monospace">
  <li>
    <details>
      <summary class="has-margin-bottom">
        <span class="is-array">benelux_countries</span>
      </summary>
      <ul>
        <li>
          <span class="has-half-opacity">0:</span>
          <span class="is-string">The Netherlands</span>
        </li>
        <li>
          <span class="has-half-opacity">1:</span>
          <span class="is-string">Belgium</span>
        </li>
        <li>
          <span class="has-half-opacity">2:</span>
          <span class="is-string">Luxembourg</span>
        </li>
      </ul>
    </details>
  </li>
</ul>
```

---
_file: `web/cuckoo/web/clientsrc/sass/_json-expander.sass`_

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
  2.21 **[JSON Expander](./json-expander.md)**  
  2.22 [Footer](./footer.md)  
  2.23 [Misc](./misc.md)  
  2.24 [Helpers](./helpers.md)  

---
