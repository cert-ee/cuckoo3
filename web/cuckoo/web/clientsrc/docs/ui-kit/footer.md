# Footer

The footer element defines footer/tertiary content or defines the end of content.
The footer included in the core styles has been structured in a way that it will
or should be on the bottom of the page at all time, like a sticky element that gets
pushed further down whenever space is required for the main content. This requires
some implementation/mechanics, as shown in the example.

Example: Implementation of a sticky footer, in a view context:
```html
<div class="view">
  <main>
    ...
  </main>
  <div class="footer-push"></div>
</div>
<footer class="footer"></footer>
```

Example: Markup inside footer element
```html
<footer class="footer">
  <div class="footer-start">
    <!-- top-footer/floating content, like navs and links -->
  </div>
  <div class="footer-end">
    <!-- bottom-footer/bar content, like copyrights and logos -->
  </div>
</footer>
```

| class           | type   | description                          |
| --------------- | ------ | ------------------------------------ |
| `.footer`       | parent | defines footer block                 |
| `.footer-start` | child  | top content space for footer content |
| `.footer-end`   | child  | bottom bar of the footer element     |

---
_file: `web/cuckoo/web/clientsrc/sass/_footer.sass`_
