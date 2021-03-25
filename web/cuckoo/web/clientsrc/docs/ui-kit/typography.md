# Typography

By default, all paragraphing and headers have embedded extra styles to optimize
their font and reading egibility. But one solution won't fit all, and just like
the helpers, there are many typographic headers to mark up complex text styles
easily. This system avoids to have lots of styles needed to be written for specific
parts, as the css classes can be added to achieve the same effect.

Example: apply typographic rules
```html
<h1 class="has-text-center">Title</h2>
<h2 class="has-half-opacity">The story of the amazing frontend people</h2>
<p class="has-text-weight-light has-text-blue">Lorem ipsum dolor sit amet, consectetur adiscipling elit.</p>
```

| class                       | type     | description                               |
| --------------------------- | -------- | ----------------------------------------- |
| `.is-monospace`             | modifier | makes contained text monospaced           |
| `.code`                     | modifier | code definition styles                    |
| `.code-block`               | modifier | like `.code` but is optimized for a block |
| `.has-text-blue`            | modifier | makes text blue                           |
| `.has-text-red`             | modifier | makes text red                            |
| `.has-text-green`           | modifier | makes text green                          |
| `.has-text-yellow`          | modifier | makes text yellow                         |
| `.has-text-dark`            | modifier | makes text dark                           |
| `.has-text-black`           | modifier | makes text black                          |
| `.has-text-white`           | modifier | makes text white                          |
| `.has-text-light`           | modifier | makes text light in color                 |
| `.has-text-weight-hairline` | modifier | applies font weight 100                   |
| `.has-text-weight-thin`     | modifier | applies font weight 200                   |
| `.has-text-weight-light`    | modifier | applies font weight 300                   |
| `.has-text-weight-normal`   | modifier | applies font weight 400                   |
| `.has-text-weight-medium`   | modifier | applies font weight 500                   |
| `.has-text-weight-semibold` | modifier | applies font weight 600                   |
| `.has-text-weight-bold`     | modifier | applies font weight 700                   |
| `.has-text-weight-heavy`    | modifier | applies font weight 800                   |
| `.has-text-weight-black`    | modifier | applies font weight 900                   |
| `.is-error`                 | modifier | error markup styles                       |
| `.no-text-wrap`             | modifier | disables text wrapping                    |
| `.has-text-wrapped`         | modifier | enables text wrapping                     |
| `.has-text-left`            | modifier | left-aligns text                          |
| `.has-text-center`          | modifier | center-aligns text                        |
| `.has-text-right`           | modifier | right-aligns text                         |
| `.has-text-uppercased`      | modifier | makes all text uppercase                  |
| `.has-text-capitalized`     | modifier | capitalizes all contained text            |
| `.has-half-opacity`         | modifier | makes the text have a half opacity        |
| `.is-link`                  | modifier | anchor link styles                        |

---
_file: `web/cuckoo/web/clientsrc/sass/_typography.sass`_

---

### More docs

0. [Table of contents](../index.md)

1. _Package_  
  1.1 [Getting Started](../package/getting-started.md)  
  1.2 [Core concept](../package/concept.md)  

2. _UI Kit_  
  2.1 [Variables](./var.md)  
  2.2 [Reset](./reset.md)  
  2.3 **[Typography](./typography.md)**  
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
  2.24 [Helpers](./helpers.md)  

---
