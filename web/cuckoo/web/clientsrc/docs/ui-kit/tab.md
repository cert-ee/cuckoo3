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
