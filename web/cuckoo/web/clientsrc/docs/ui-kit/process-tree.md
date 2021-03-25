# Process tree

The process tree is an element that resembles an indented tree (like `.list.is-tree`),
but with some additional styling to interconnect various rows. The class name
'process tree' came up when making an indented computer-processes tree, but is
not the final iteration as there is still room for improvement.

Example: Display a process tree-like structure
```html
<ul class="process-tree">
  <li>
    <div class="columns is-divided">
      <div class="column is-auto">&nbsp;</div>
      <p class="column">Process 1</p>
    </div>
    <ul>
      <li>
        <div class="columns is-divided">
          <div class="column is-auto">&nbsp;</div>
          <p class="column">Process 1.1</p>
        </div>
      </li>
      <li>
        <div class="columns is-divided">
          <div class="column is-auto">&nbsp;</div>
          <p class="column">Process 1.2</p>
        </div>
      </li>
      <li>
        <div class="columns is-divided">
          <div class="column is-auto">&nbsp;</div>
          <p class="column">Process 1.3</p>
        </div>
      </li>
    </ul>
  </li>
</ul>
```

| class              | type   | description                                        |
| ------------------ | ------ | -------------------------------------------------- |
| `.process-tree`    | parent |                                                    |
| `.pid`             | child  | structural element that contains a process id      |
| `.duration`        | parent | structural element that contains a duration        |
| `.duration--inner` | child  | filled bar to display a relative duration duration |

---
_file: `web/cuckoo/web/clientsrc/sass/_process-tree.sass`_

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
  2.14 **[Process tree](./process-tree.md)**  
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
