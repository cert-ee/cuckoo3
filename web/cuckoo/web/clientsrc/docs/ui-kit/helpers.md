# Helpers

One UI kit on itself can never achieve perfect-fit solutions because no use case
is ever the same. There will come situations where you just may need that one
tiny tweak to remove a padding, add a border or disable border roundings. To
satisfy such demands, traditional 'reset' helper classes have been implemented
to change tiny properties whenever needed. They need to be added to parent
classes to take effect. Some of those helpers are multi-directional, which means
that there is a few alternatives to target a side or direction. This is an overview
of all helper classes inside the package:

Example: Removing vertical padding on a box using no-padding helpers:
```html
<div class="box has-background-red no-padding-x">...</div>
```

| class                     | type     | description                                                                        |
| ------------------------- | -------- | ---------------------------------------------------------------------------------- |
| **padding**               |          |                                                                                    |
| `.has-padding`            | modifier | Adds padding to an element                                                         |
| `.has-padding-x`          | modifier | Adds horizontal padding to an element                                              |
| `.has-padding-y`          | modifier | Adds vertical padding to an element                                                |
| `.has-padding-top`        | modifier | Adds top padding to an element                                                     |
| `.has-padding-right`      | modifier | Adds right padding to an element                                                   |
| `.has-padding-bottom`     | modifier | Adds bottom padding to an element                                                  |
| `.has-padding-left`       | modifier | Adds left padding to an element                                                    |
| `.no-padding`             | modifier | Removes padding from an element                                                    |
| `.no-padding-x`           | modifier | Removes horizontal padding from an element                                         |
| `.no-padding-y`           | modifier | Removes vertical padding from an element                                           |
| `.no-padding-top`         | modifier | Removes top padding from an element                                                |
| `.no-padding-right`       | modifier | Removes right padding from an element                                              |
| `.no-padding-bottom`      | modifier | Removes bottom padding from an element                                             |
| `.no-padding-left`        | modifier | Removes left padding from an element                                               |
| **margin**                |          |                                                                                    |
| `.has-margin`             | modifier | Adds margin to an element                                                          |
| `.has-margin-x`           | modifier | Adds horizontal margin to an element                                               |
| `.has-margin-y`           | modifier | Adds vertical margin to an element                                                 |
| `.has-margin-top`         | modifier | Adds top margin to an element                                                      |
| `.has-margin-right`       | modifier | Adds right margin to an element                                                    |
| `.has-margin-bottom`      | modifier | Adds bottom margin to an element                                                   |
| `.has-margin-left`        | modifier | Adds left margin to an element                                                     |
| `.no-margin`              | modifier | Removes margin from an element                                                     |
| `.no-margin-x`            | modifier | Removes horizontal margin from an element                                          |
| `.no-margin-y`            | modifier | Removes vertical margin from an element                                            |
| `.no-margin-top`          | modifier | Removes top margin from an element                                                 |
| `.no-margin-right`        | modifier | Removes right margin from an element                                               |
| `.no-margin-bottom`       | modifier | Removes bottom margin from an element                                              |
| `.no-margin-left`         | modifier | Removes left margin from an element                                                |
| **border**                |          |                                                                                    |
| `.has-border`             | modifier | Adds borders to an element                                                         |
| `.has-border-x`           | modifier | Adds horizontal borders to an element                                              |
| `.has-border-y`           | modifier | Adds vertical borders to an element                                                |
| `.has-border-top`         | modifier | Adds top border to an element                                                      |
| `.has-border-right`       | modifier | Adds right border to an element                                                    |
| `.has-border-bottom`      | modifier | Adds bottom border to an element                                                   |
| `.has-border-left`        | modifier | Adds left margin to an element                                                     |
| `.no-border`              | modifier | Removes all borders from an element                                                |
| `.no-border-x`            | modifier | Removes horizontal borders from an element                                         |
| `.no-border-y`            | modifier | Removes vertical borders from an element                                           |
| `.no-border-top`          | modifier | Removes top border from an element                                                 |
| `.no-border-right`        | modifier | Removes right border from an element                                               |
| `.no-border-bottom`       | modifier | Removes bottom border from an element                                              |
| `.no-border-left`         | modifier | Removes left border from an element                                                |
| **border-radius**         |          |                                                                                    |
| `.no-radius`              | modifier | removes the border-radius of an element                                            |
| `.no-radius-left`         | modifier | removes the lefthand border-radiuses of an element                                 |
| `.no-radius-right`        | modifier | removes the righthand border-radiuses of an element                                |
| **auxiliary**             |          |                                                                                    |
| `.hidden`                 | modifier | Completely hides an element from the DOM renderer                                  |
| `.is-disabed, [disabled]` | modifier | Additional styles that resemble disabled / inactive elements                       |
| `.clear-box`              | modifier | Clearfix utility for working with floating content                                 |
| `.pull-right`             | modifier | Floats an element to the right of its box context (use `.clear-box` on its parent) |
| `.no-line-break`          | modifier | Disables line-breaking on content                                                  |
| `.has-line-break`         | modifier | Enforces line breaking on content                                                  |
| `.is-sticky`              | modifier | enables position: sticky on an element, making it stick when scrolled out of view  |
| `.no-overflow`            | modifier | applies `overflow: hidden` to target container                                     |
| `.no-overflow-x`          | modifier | applies `overflow-x: hidden` to target container                                   |
| `.no-overflow-y`          | modifier | applies `overflow-y: hidden` to target container                                   |

---
_file: `web/cuckoo/web/clientsrc/sass/_helpers.sass`_

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
  2.23 [Misc](./misc.md)  
  2.24 **[Helpers](./helpers.md)**  

---
