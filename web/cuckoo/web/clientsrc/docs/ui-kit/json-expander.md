# JSON Expander
This is an extra class that is derived from the idea of having a collapsible
list. Unlike is-tree classes from the list sections, this json-expander class
focusses on making a tree to display plain data objects, with the possibility
to do so recursively. It's appearance can be mostly styled using helpers and
customizers.

Example: JSON tree
```html
<ul class="json-expander is-monospace">
  <li>
    <details>
      <summary class="has-margin-bottom">
        <span class="is-array">benelux_countries</span>
      </summary>
      <ul>
        <li>
          <span class="has-half-opacity">0:</span>
          <span class="is-string">The Netherlands</span>
        </li>
        <li>
          <span class="has-half-opacity">1:</span>
          <span class="is-string">Belgium</span>
        </li>
        <li>
          <span class="has-half-opacity">2:</span>
          <span class="is-string">Luxembourg</span>
        </li>
      </ul>
    </details>
  </li>
</ul>
```

---
_file: `web/cuckoo/web/clientsrc/sass/_json-expander.sass`_
