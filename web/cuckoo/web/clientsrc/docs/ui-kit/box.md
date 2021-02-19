# Box

Boxes define content-surrounding space with internal padding and an external vertical
margin for stacking. They are intended to put content in a certain context defined
by color. Boxes vary in color, size and appearance. Use boxes to categorize and
split different features or functionalities from one another. The box class is
layout-agnostic. So when a box needs to behave like a grid, the `.columns` class
can be attached to add that visual functionality.

Example:
```html
<div class="box has-background-green">
  <h3>Very positive and green content</h3>
  <p>...</p>
</div>

<div class="box has-background-red">
  <h3>Very negative and red content</h3>
  <p>...</p>
</div>
```

The boxes define a base class, and are extended on by other elements, such as
banners.

| Class                         | Type     | Description                                                       |
| ----------------------------- | -------- | ----------------------------------------------------------------- |
| `.box`                        | parent   | Defines boxed content                                             |
| `.box-title`                  | child    | Optional title styled for use in a box                            |
| `.box-title.is-red`           | modifier | makes the title red (when set on `.box-title`)                    |
| `.box-addon`                  | child    | Addon content. Requires `.has-addon` on the parent box construct. |
| `.is-inline`                  | modifier | Makes the box inline instead of block-level                       |
| `.is-big`                     | modifier | Makes the inner padding bigger                                    |
| `.is-grouped`                 | modifier | When set on the first box in a series, it will snap them together |
| `.has-background-light`       | modifier | Applies a light appearance to the box                             |
| `.has-background-blue`        | modifier | Applies a blue appearance to the box                              |
| `.has-background-red`         | modifier | Applies a red appearance to the box                               |
| `.has-background-dark`        | modifier | Applies a dark appearance to the box                              |
| `.has-background-black`       | modifier | Applies a black appearance to the box                             |
| `.has-background-green`       | modifier | Applies a green appearance to the box                             |
| `.has-background-yellow`      | modifier | Applies a yellow appearance to the box                            |
| `.has-background-stack-shade` | modifier | Applies opaque appearance to the box                              |
| `.has-background-fade`        | modifier | Applies light-to-dark opaque gradient appearance to the box       |
| `.has-inset-shadow`           | modifier | Applies an inner shadow to the box                                |
| `.has-shadow`                 | modifier | Applies surrounding box shadow                                    |
| `.has-border`                 | modifier | Applies a thin border to the box.                                 |
| `.has-addon`                  | modifier | Applies additional styles to support `.box-addon`                 |

---
_file: `web/cuckoo/web/clientsrc/sass/_box.sass`_
