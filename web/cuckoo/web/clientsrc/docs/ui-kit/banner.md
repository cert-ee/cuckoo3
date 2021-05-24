# Banner

The banner element provides a way to flash messages to the user. Banners are
intended to display errors, warnings and confirmations.

This example displays a red banner containing an error:
```html
<div class="banner is-danger">
  <span class="banner-icon">&times;</span>
  <p> Something went wrong! <a class="has-text-small has-half-opacity pull-right" onclick="this.parentNode.remove();">&times;</a></p>
</div>
```

Banners are a subset of [`.columns`]("./columns.md") and [`.box`]("../box.md").
The column modifiers can therefore be used on the child elements within the banner.

| Class          | Type     | Description                                  |
| -------------- | -------- | -------------------------------------------- |
| `.banner`      | parent   | Creates a banner context                     |
| `.banner-icon` | child    | Reserves place for an icon within the parent |
| `.is-danger`   | modifier | Red/error style banner theme                 |
| `.is-red`      | modifier | _Alias for `.is-danger`_                     |
| `.is-warning`  | modifier | Yellow/warning style banner theme            |
| `.is-yellow`   | modifier | _Alias for `.is-warning`_                    |

---
_file: `web/cuckoo/web/clientsrc/sass/_banner.sass`_

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
  2.17 **[Banner](./banner.md)**  
  2.18 [Tab](./tab.md)  
  2.19 [Tag](./tag.md)  
  2.20 [Popover](./popover.md)  
  2.21 [JSON Expander](./json-expander.md)  
  2.22 [Footer](./footer.md)  
  2.23 [Misc](./misc.md)  
  2.24 [Helpers](./helpers.md)  

---
