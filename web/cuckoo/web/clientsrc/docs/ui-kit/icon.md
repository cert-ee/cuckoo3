# Icon

The UI kit doesn't take any specific icon system into account. There is many
icon fonts and most projects will thrive on their own integrated/branded
styles. Aside  HTML entities and Emoji's, there is not much to account for. The
solution to this problem is instead of implementing an icon font, implement
a system that would suit any font kit, custom or a widely used package. This way,
the UI kit 'reserves' slots for icons. The idea is to place the icons inside the
placeholder as delivered by the kit. The placeholder takes care of sizing and vertical
alignment.

Example: using the icon class
```html
<p><span class="icon">&check;</span> That is correct!</p>
```

| class        | type     | description                                 |
| ------------ | -------- | ------------------------------------------- |
| `.icon`      | parent   | parent class to contain the icon            |
| `.is-small`  | modifier | makes the icon small in size                |
| `.is-medium` | modifier | makes the icon slightly bigger than default |
| `.is-big`    | modifier | makes the icon big in size                  |

---
_file: `web/cuckoo/web/clientsrc/sass/_icon.sass`_
