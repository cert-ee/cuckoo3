# Navbar

The navbar element is like the footer element making up for a well executed
solution to have a top nav bar for the primary navigation in the app. The navbar
contains links to the primary routes in the application. When the viewport is scaled
to mobile/tiny handheld proportions, it will make up for the interaction by adding
a hamburger-like menu.

Example: Defines a navbar
```html
<nav class="navbar">
  <div class="navbar-logo">
    <a class="navbar-link" href="/">
      <img src="/static/images/logo.svg" alt="Some logo" />
    </a>
    <a class="navbar-toggle" title="Expand menu">
      <span></span>
      <span></span>
      <span></span>
    </a>
  </div>
  <div class="navbar-start">
    <a href="/" class="navbar-link is-active">Home</a>
    <a href="/about" class="navbar-link">About</a>
    <a href="/products" class="navbar-link">Products</a>
  </div>
  <div class="navbar-end">
    <a class="navbar-link" href="/login">Log in</a>
    <a class="navbar-link" href="/signup">Sign up</a>
  </div>
</nav>
```

| class                    | type     | description                                                      |
| ------------------------ | -------- | ---------------------------------------------------------------- |
| `.navbar`                | parent   | Defines a navbar layout                                          |
| `.navbar-logo`           | child    | Reserves space for branding/logo purposes                        |
| `.navbar-start`          | child    | Contains left-hand `.navbar-link`'s                              |
| `.navbar-end`            | child    | Contains right-hand `.navbar-link`'s                             |
| `.navbar-toggle`         | child    | Modifier for initializing a collapsible menu                     |
| `.navbar-link`           | child    | Within `.navbar-start` and `.navbar-end`, these define the links |
| `.navbar-link.is-active` | modifier | Used on any `.navbar-link` to make it appear active              |

---
_file: `web/cuckoo/web/clientsrc/sass/_navbar.sass`_

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
  2.5 **[Navbar](./navbar.md)**  
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
