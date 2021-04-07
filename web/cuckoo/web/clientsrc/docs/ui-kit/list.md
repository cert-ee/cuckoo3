# List

As common as lists are, the package implements some varieties that derive
from native list elements.

Example: basic lists
```html
<ul class="list">
  <li>Foo</li>
  <li>Bar</li>
  <li>Baz</li>
</ul>

<ul class="list is-reset">
  <li>Foo</li>
  <li>Bar</li>
  <li>Baz</li>
</ul>

<ul class="list is-horizontal">
  <li>Foo</li>
  <li>Bar</li>
  <li>Baz</li>
</ul>
```

Example: Tree diagram
```html
<ul class="list is-tree-diagram">
  <li>
    <span>Parent</span>
    <ul>
      <li>
        <span>Child</span>
      </li>
      <li>
        <span>Child</span>
        <ul>
          <li>
            <span>Child</span>
          </li>
        </ul>
      <li>
        <span>Child</span>
      </li>
    </ul>
  </li>
</ul>
```

Example: Strings list
```html
<ul class="list is-strings-list">
  <li class="is-odd">String 1</li>
  <li>String 2</li>
  <li>String 3</li>
</ul>

Or take control of the item counter;

<ul class="list is-strings-list">
  <li data-count="4" class="is-odd">String 1</li>
  <li data-count="5">String 2</li>
  <li data-count="6">String 3</li>
</ul>
```

| class              | type     | description                                                                  |
| ------------------ | -------- | ---------------------------------------------------------------------------- |
| `.list`            | parent   | Base class for stylized lists                                                |
| `.is-reset`        | modifier | Resets all initial styles from a list                                        |
| `.is-tree`         | modifier | applies styles for an indented tree list                                     |
| `.is-horizontal`   | modifier | Makes a list left-to-right instead of top-to-bottom, with separation symbols |
| `.is-index`        | modifier | List variant that will form a contents index                                 |
| `.is-tree-diagram` | modifier | List variant that renders parent-child relations as individual nodes         |
| `.is-strings-list` | modfier  | List variant optimized for using with lists of strings                       |

---
_file: `web/cuckoo/web/clientsrc/sass/_list.sass`_
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
  2.13 **[List](./list.md)**  
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
