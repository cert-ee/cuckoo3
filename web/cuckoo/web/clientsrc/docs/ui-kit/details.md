# Details

The details element in HTML takes away the need of making collapsible elements
programmatically. Details elements contain a summary and child content that can
be hidden or revealed by clicking on the summary block.

Example: hiding additional/secondary content:
```html
<details class="details">
  <summary>Click to reveal an image of a cat</summary>
  <img src="cat.jpg" alt="Pussycat" />
</details>
```

Attaching the details class ensure supporting styles to make its use slightly
easier. It is styled on top of best practice.

| class           | type     | description                      |
| --------------- | -------- | -------------------------------- |
| `.details`      | parent   | Defines a styled details block   |
| `.has-no-hover` | modifier | Disables hover effect on element | 

---
_file: `web/cuckoo/web/clientsrc/sass/_details.sass`_
