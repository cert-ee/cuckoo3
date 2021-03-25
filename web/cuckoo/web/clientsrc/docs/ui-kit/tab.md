# Tab

Tabs are comparable to nav-bars, and to a certain extent they are - but tabs intent
to create depth in the application. In situations where there is a large data set
that should visually be broken down in several sub-sections, tabs offer this depth
to be created.

Example: markup for tabs
```html
<nav class="tabbar">
  <p class="tabbar-label">Pick a tab:</p>
  <a class="tabbar-link is-active" href="#tab1">Tab 1</a>
  <a class="tabbar-link" href="#tab2">Tab 2</a>
</nav>
<div id="tab1">
  <div class="banner is-yellow">
    <p>This is tab 1!</p>
  </div>
</div>
<div id="tab2" hidden>
  <div class="banner is-blue">
    <p>This is tab 2!</p>
  </div>
</div>
```

| class                         | type     | description                                          |
| ----------------------------- | -------- | ---------------------------------------------------- |
| `.tabbar`                     | parent   | Container that contains the tabs                     |
| `.tabbar-link`                | child    | Styles for an inactive tab                           |
| `.tabbar-label`               | child    | Styles for a tabbar label (non-link descriptor)      |
| `.has-background-transparent` | modifier | Gives tabbar transparent background                  |
| `.tabbar-link.is-active`      | modifier | Gives tab an active appearance                       |
| `.is-rounded`                 | modifier | Adds border-radius to tabs                           |
| `.is-rs-static`               | modifier | Hides inactive tabs when viewport has a mobile width |

## Interactive tabbars: some work required
When everything is rendered server-side, it's fairly easy to implement this tabs
system as a static version of itself. When asynchronous interactivity is expected,
some additional javascript can be written easily to support this:§

```
<ADD JAVASCRIPT EXAMPlE HERE?>
```

---
_file: `web/cuckoo/web/clientsrc/sass/_tab.sass`_

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
  2.10 **[Table](./table.md)**  
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
