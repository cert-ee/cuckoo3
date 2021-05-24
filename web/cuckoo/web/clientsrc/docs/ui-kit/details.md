# Details

The details element in HTML takes away the need of making collapsible elements
programmatically. Details elements contain a summary and child content that can
be hidden or revealed by clicking on the summary block.

Example: hiding additional/secondary content:
```html
<details class="details">
  <summary>Click to reveal an image of a cat</summary>
  <img src="cat.jpg" alt="Pussycat" />
</details>
```

Attaching the details class ensure supporting styles to make its use slightly
easier. It is styled on top of best practice.

| class           | type     | description                      |
| --------------- | -------- | -------------------------------- |
| `.details`      | parent   | Defines a styled details block   |
| `.has-no-hover` | modifier | Disables hover effect on element |

---
_file: `web/cuckoo/web/clientsrc/sass/_details.sass`_

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
  2.11 **[Details](./details.md)**  
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
