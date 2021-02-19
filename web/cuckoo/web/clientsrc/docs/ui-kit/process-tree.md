# Process tree

The process tree is an element that resembles an indented tree (like `.list.is-tree`),
but with some additional styling to interconnect various rows. The class name
'process tree' came up when making an indented computer-processes tree, but is
not the final iteration as there is still room for improvement.

Example: Display a process tree-like structure
```html
<ul class="process-tree">
  <li>
    <div class="columns is-divided">
      <div class="column is-auto">&nbsp;</div>
      <p class="column">Process 1</p>
    </div>
    <ul>
      <li>
        <div class="columns is-divided">
          <div class="column is-auto">&nbsp;</div>
          <p class="column">Process 1.1</p>
        </div>
      </li>
      <li>
        <div class="columns is-divided">
          <div class="column is-auto">&nbsp;</div>
          <p class="column">Process 1.2</p>
        </div>
      </li>
      <li>
        <div class="columns is-divided">
          <div class="column is-auto">&nbsp;</div>
          <p class="column">Process 1.3</p>
        </div>
      </li>
    </ul>
  </li>
</ul>
```

| class              | type   | description                                        |
| ------------------ | ------ | -------------------------------------------------- |
| `.process-tree`    | parent |                                                    |
| `.pid`             | child  | structural element that contains a process id      |
| `.duration`        | parent | structural element that contains a duration        |
| `.duration--inner` | child  | filled bar to display a relative duration duration |

---
_file: `web/cuckoo/web/clientsrc/sass/_process-tree.sass`_
