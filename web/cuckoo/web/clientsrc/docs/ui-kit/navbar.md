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
