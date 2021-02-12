# Banner

The banner element provides a way to flash messages to the user. Banners are
intended to display errors, warnings and confirmations.

This example displays a red banner containing an error:
```html
<div class="banner is-danger">
  <span class="banner-icon">&times;</span>
  <p> Something went wrong! <a class="has-text-small has-half-opacity pull-right" onclick="this.parentNode.remove();">&times;</a></p>
</div>
```

Banners are a subset of [`.columns`]("./columns.md") and [`.box`]("../box.md").
The column modifiers can therefore be used on the child elements within the banner.

| Class          | Type     | Description                                  |
| -------------- | -------- | -------------------------------------------- |
| `.banner`      | parent   | Creates a banner context                     |
| `.banner-icon` | child    | Reserves place for an icon within the parent |
| `.is-danger`   | modifier | Red/error style banner theme                 |
| `.is-red`      | modifier | _Alias for `.is-danger`_                     |
| `.is-warning`  | modifier | Yellow/warning style banner theme            |
| `.is-yellow`   | modifier | _Alias for `.is-warning`_                    |

---
_file: `web/cuckoo/web/clientsrc/sass/_banner.sass`_
