# Popover

Popovers can be described as tiny floating panels that pop 'over' other content
when they appear. A use case for wanting a popover is to display truncated content
or having a filter/one-way input that could be applied anywhere. Also think context-menu's,
copy confirmations, etc.

Example: Popover setting menu
```html
<div class="has-popover">
  <a class="is-link">Click me for more content</a>
  <div class="popover is-top">Here is more content!</div>
</div>
```

| class          | type     | description                                              |
| -------------- | -------- | -------------------------------------------------------- |
| `.popover`     | parent   | Makes up the popover                                     |
| `.has-popover` | modifier | Modifier class for the parent that contains the popover  |
| `.tooltip`     | parent   | Popover variant that resembles a tooltip                 |
| `.has-tooltip` | modifier | Modifier class for the parent that contains the tooltip  |
| `.in`          | modifier | When this class is added to the popover, it will display |
| `.is-top`      | modifier | Positions the popover to the top of the element          |

## Popovers and tooltips: some work required
The styles are present for a popover to be hidden and revealed. However, the interactive
implemetation to make it work is not by default included. The kit aims to be non-JS by
default to avoid complexity and leave javascript to the user who is using the kit.

---
_file: `web/cuckoo/web/clientsrc/sass/_popover.sass`_
