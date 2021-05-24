# Miscelaneous

Alongside all the components, there are some elements that aren't included by
default in the HTML markup realm. There is some extra support added for elements
that are useful for creating rich contexts.

| class               | type     | description                                                                              |
| ------------------- | -------- | ---------------------------------------------------------------------------------------- |
| `.ratio-1-1`        | parent   | An aspect ratio box that will always maintain its 1:1 ratio, regardless of child content |
| `.ratio-content`    | child    | Defines the content in `.ratio-1-1`                                                      |
| `.dot`              | parent   | An inline circle/dot, for any purpose where dots are needed, such as status indication   |
| `.dot.is-red`       | modifier | When used on `.dot`, it will make the dot red                                            |
| `.dot.is-yellow`    | modifier | When used on `.dot`, it will make the dot yellow                                         |
| `.dot.is-blue`      | modifier | When used on `.dot`, it will make the dot blue                                           |
| `.has-hover-fadein` | modifier | Reduces opacity by default, but will set opacity to 1 when hovered                       |

---
_file: `web/cuckoo/web/clientsrc/sass/_misc.sass`_

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
  2.22 [Footer](./footer.md)  
  2.23 **[Misc](./misc.md)**  
  2.24 [Helpers](./helpers.md)  

---
