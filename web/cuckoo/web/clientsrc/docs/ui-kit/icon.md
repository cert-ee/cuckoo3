# Icon

The UI kit doesn't take any specific icon system into account. There is many
icon fonts and most projects will thrive on their own integrated/branded
styles. Aside  HTML entities and Emoji's, there is not much to account for. The
solution to this problem is instead of implementing an icon font, implement
a system that would suit any font kit, custom or a widely used package. This way,
the UI kit 'reserves' slots for icons. The idea is to place the icons inside the
placeholder as delivered by the kit. The placeholder takes care of sizing and vertical
alignment.

Example: using the icon class
```html
<p><span class="icon">&check;</span> That is correct!</p>
```

| class        | type     | description                                 |
| ------------ | -------- | ------------------------------------------- |
| `.icon`      | parent   | parent class to contain the icon            |
| `.is-small`  | modifier | makes the icon small in size                |
| `.is-medium` | modifier | makes the icon slightly bigger than default |
| `.is-big`    | modifier | makes the icon big in size                  |

---
_file: `web/cuckoo/web/clientsrc/sass/_icon.sass`_

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
  2.15 **[Icon](./icon.md)**  
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
