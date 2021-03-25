# Section

Sections are contextual full-width blocks that separates various sections
of content. One use case of those is for example to create an attention-block on
the top of the page, or line up repetitive content over the page.

Example: Attention-block header
```html
<section class="section has-background-white">
  <div class="container is-fixed is-smol">
    <h1>Welcome to this page</h1>
    <h3>We hope you will have a good time.</h3>
    <p><a class="button is-blue is-big">Let's go</a></p>
    <p class="has-half-opacity has-text-small">Disclamer: Clicking the button will not take you anywhere</p>
  </div>
</section>
```

| class                   | type     | description                                        |
| ----------------------- | -------- | -------------------------------------------------- |
| `.section`              | parent   | Defines a section block                            |
| `.is-big`               | modifier | Bigger variant of section block                    |
| `.is-full-page`         | modifier | Makes the section consume the full viewport height |
| `.with-navbar`          | modifier | Modifies `.is-full-page` to have a top-page-navbar |
| `.has-background-white` | modifier | Gives the section a white background               |
| `.has-background-dark`  | modifier | Makes the background dark                          |

---
_file: `web/cuckoo/web/clientsrc/sass/_section.sass`_

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
  2.7 **[Section](./section.md)**  
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
