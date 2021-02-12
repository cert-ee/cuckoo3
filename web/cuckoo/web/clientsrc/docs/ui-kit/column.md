# Column
The column class defines a grid system based on flexbox properties. It is
defined in a manner that any grid or layout can be made using modifiers. This
eradicates separate css to be written for specific cases as the properties
are at hand defined in modifier classes to keep it simple.

Example: Bare 3-item horizontal grid setup
```html
<div class="columns">
  <div class="column"></div>
  <div class="column"></div>
  <div class="column"></div>
</div>
```

Example: min-width sidebar and max-width content using columns
```html
<main class="columns is-divided">
  <aside class="column is-auto">Sidebar</aside>
  <section class="column">Content</section>
</main>
```

Note that horizontal grids will snap to vertical grids on mobile-size viewports
(640 and lower)

| Class             | Type     | Description                                                                      | Translation                      |
| ----------------- | -------- | -------------------------------------------------------------------------------- | -------------------------------- |
| `.columns`        | parent   | Wrapper element around the columns                                               | `display: flex`                  |
| `.column`         | child    | Defines a column within a columns element                                        | `<flex child>`                   |
| `.column.is-full` | modifier | Forces column to be a full row in a horizontal context                           | `flex: 0 0 100%`                 |
| `.column.is-fill` | modifier | Forces column to take up maximum space in row                                    | `flex: 1`                        |
| `.column.is-auto` | modifier | Forces column to take up minimum space in row                                    | `flex: 0`                        |
| `.is-vertical`    | modifier | Makes the grid vertical                                                          | `flex-direction: column`         |
| `.is-even`        | modifier | Divides columns evenly while mainaining minimal content dimensions               | `justify-content: space-evenly`  |
| `.is-between`     | modifier | Divides columns from max-left to left-right in the same way is-even works        | `justify-content: space-between` |
| `.is-around`      | modifier | Divides columns with respect to left and right bounds                            | `justify-content: space-around`  |
| `.is-left`        | modifier | Aligns all columns to the left                                                   | `justify-content: flex-start`    |
| `.is-right`       | modifier | Aligns all columns to the right                                                  | `justify-content: flex-end`      |
| `.is-center`      | modifier | Aligns all the columns in the center                                             | `justify-content: flex-center`   |
| `.is-divided`     | modifier | Max space, max width, all evenly regardless content                              | -                                |
| `.is-vcenter`     | modifier | Vertically centers horizontal columns (reverse when `.is-vertical` is used)      | `align-items: center`            |
| `.is-vtop`        | modifier | Aligns columns vertically to the top (left when `.is-vertical` is used)          | `align-items: flex-start`        |
| `.is-vbottom`     | modifier | Aligns columns vertically to the bottom (right when `.is-vertical` is used)      | `align-items: flex-end`          |
| `.is-vstretch`    | modifier | Stretches out the columns to equal height (or width when `.is-vertical` is used) | `align-items: stretch`           |
| `.is-gapless`     | modifier | Removes horizontal gaps between columns                                          | -                                |
| `.has-tiny-gaps`  | modifier | Alters default gaps to tiny-er gaps                                              | -                                |

---
_file: `web/cuckoo/web/clientsrc/sass/_column.sass`_
