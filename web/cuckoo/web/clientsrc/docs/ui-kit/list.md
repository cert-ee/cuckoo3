# List

As common as lists are, the package implements some varieties that derive
from native list elements.

Example: basic lists
```html
<ul class="list">
  <li>Foo</li>
  <li>Bar</li>
  <li>Baz</li>
</ul>

<ul class="list is-reset">
  <li>Foo</li>
  <li>Bar</li>
  <li>Baz</li>
</ul>

<ul class="list is-horizontal">
  <li>Foo</li>
  <li>Bar</li>
  <li>Baz</li>
</ul>
```

Example: Tree diagram
```html
<ul class="list is-tree-diagram">
  <li>
    <span>Parent</span>
    <ul>
      <li>
        <span>Child</span>
      </li>
      <li>
        <span>Child</span>
        <ul>
          <li>
            <span>Child</span>
          </li>
        </ul>
      <li>
        <span>Child</span>
      </li>
    </ul>
  </li>
</ul>
```

| class              | type     | description                                                                  |
| ------------------ | -------- | ---------------------------------------------------------------------------- |
| `.list`            | parent   | Base class for stylized lists                                                |
| `.is-reset`        | modifier | Resets all initial styles from a list                                        |
| `.is-tree`         | modifier | applies styles for an indented tree list                                     |
| `.is-horizontal`   | modifier | Makes a list left-to-right instead of top-to-bottom, with separation symbols |
| `.is-index`        | modifier | List variant that will form a contents index                                 |
| `.is-tree-diagram` | modifier | List variant that renders parent-child relations as individual nodes         |

---
_file: `web/cuckoo/web/clientsrc/sass/_list.sass`_
