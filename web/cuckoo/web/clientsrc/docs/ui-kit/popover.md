# Popover

Popovers can be described as tiny floating panels that pop 'over' other content
when they appear. A use case for wanting a popover is to display truncated content
or having a filter/one-way input that could be applied anywhere. Also think context-menu's,
copy confirmations, etc.

Example: Popover setting menu
```html
<div class="has-popover">
  <a class="is-link">Click me for more content</a>
  <div class="popover is-top">Here is more content!</div>
</div>
```

| class          | type     | description                                              |
| -------------- | -------- | -------------------------------------------------------- |
| `.popover`     | parent   | Makes up the popover                                     |
| `.has-popover` | modifier | Modifier class for the parent that contains the popover  |
| `.tooltip`     | parent   | Popover variant that resembles a tooltip                 |
| `.has-tooltip` | modifier | Modifier class for the parent that contains the tooltip  |
| `.in`          | modifier | When this class is added to the popover, it will display |
| `.is-top`      | modifier | Positions the popover to the top of the element          |

## Popovers and tooltips: some work required
The styles are present for a popover to be hidden and revealed. However, the interactive
implemetation to make it work is not by default included. The kit aims to be non-JS by
default to avoid complexity and leave javascript to the user who is using the kit.

---
_file: `web/cuckoo/web/clientsrc/sass/_popover.sass`_

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
  2.20 **[Popover](./popover.md)**  
  2.21 [JSON Expander](./json-expander.md)  
  2.22 [Footer](./footer.md)  
  2.23 [Misc](./misc.md)  
  2.24 [Helpers](./helpers.md)  

---
