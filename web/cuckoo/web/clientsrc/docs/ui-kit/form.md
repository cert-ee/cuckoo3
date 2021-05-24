# Form

Form fields are tiny portals that handle user input and interaction. They are
essential to situations where displayed content is dependent on some user actions
or one may want to have a form to capture some user information needed for other
processes in the application. HTML forms are well known, and the kit mainly
adds some aesthethic to those fields that make them either appear better or improve
the accessibility of their native counterparts. By default, inputs have their own
native layout, custom styling occurs when their respective classes are added.

Example: Basic form to demonstrate markup of forms
```html
<form class="form">
  <div class="field">
    <div class="control">
      <label class="label">Username:</label>
      <input class="input" type="text" />
    </div>
    <div class="control">
      <label class="label">Password:</label>
      <input class="input" type="password" />
    </div>
  </div>
  <input type="submit" class="button" />
</form>
```

Form elements are block-level components and will consume maximum horizontal space
of their parent. This is not always necessary, and for other situations, a horizontal
aligned field might be the better option.

Example: Horizontal form fields
```html
<div class="field is-horizontal">
  <label class="label">Username:</label>
  <div class="control">
    <input class="input" type="text" />
  </div>
  <label class="label">Password:</label>
  <div class="control">
    <input class="input" type="password" />
  </div>
  <div class="control">
    <input type="submit" class="button is-blue" value="Log in" />
  </div>
</div>
```

The way horizontal forms crop simple input into a single line, inline forms have
additional styling to horizontal forms and embeds form fields in a slightly more
clever way, and span maximum availabe content for all the childs in the form.

Example: Inline form fields
```html
<div class="field is-inline">
  <label class="label">Username</label>
  <div class="control">
    <input class="input" type="text" placeholder="John Doe" />
  </div>
  <label class="label">Password</label>
  <div class="control">
    <input class="input" type="password" placeholder="•••••" />
  </div>
  <div class="control field-end">
    <input type="submit" class="button is-blue" value="Log in" />
  </div>
</div>
```

Example: Checkboxes and radio's (type=radio can be radio=checkbox as well)
```html
<div class="field">
  <div class="control is-checkable">
    <input type="radio" value="1" id="radio-set-1" name="radio-set" checked />
    <label for="radio-set-1">Radio 1</label>
  </div>
  <div class="control is-checkable">
    <input type="radio" value="2" id="radio-set-2" name="radio-set" />
    <label for="radio-set-2">Radio 2</label>
  </div>
  <div class="control is-checkable">
    <input type="radio" value="3" id="radio-set-3" name="radio-set" />
    <label for="radio-set-3">Radio 3</label>
  </div>
</div>
```

Example: Select boxes
```html
<div class="field">
  <label class="label" for="foobarbaz">Foo, Bar or Baz?</label>
  <div class="control is-select">
    <select class="input" id="foobarbaz">
      <option value="1" selected>Foo</option>
      <option value="2">Bar</option>
      <option value="3">Baz</option>
    </select>
  </div>
</div>
```

Example: use addon to add an icon or symbol to a control field
```html
<div class="control has-addon">
  <strong class="addon">&infin;</strong>
  <input class="input" type="text" id="checkbox-addon-demo" />
</div>
```

| class                   | type     | description                                                          |
| ----------------------- | -------- | -------------------------------------------------------------------- |
| `.field`                | parent   | Wrapper for a form field                                             |
| `.control`              | parent   | Wrapper for a form input                                             |
| `.input`                | child    | Enables custom styling on native input elements                      |
| `.label`                | child    | Adds label text styles to a label element                            |
| `.control.is-select`    | modifier | Adds additional styling to `.control` to handle dropdowns            |
| `.control.is-file`      | modifier | Adds additional styling for `input[type=file]` elements              |
| `.file-trigger`         | child    | Append to `.is-file` control label to customize a file upload button |
| `.control.is-checkable` | modifier | Additional styling for label/checkbox/radio layouts                  |
| `.control.has-addon`    | modifier | Additional styling to use an icon as the label                       |
| `.addon`                | child    | Contains the addon markup                                            |
| `.field.is-inline`      | modifier | Creates a line of inputs next to each other                          |
| `.field.is-horizontal`  | modifier | Makes a field line up horizontally                                   |

---
_file: `web/cuckoo/web/clientsrc/sass/_form.sass`_

---

### More docs

0. [Table of contents](../index.md)

1. _Package_  
  1.1 [Getting Started](../package/getting-started.md)  
  1.2 [Core concept](../package/concept.md)  

2. _UI Kit_  
  2.1 [Variables](./var.md)  
  2.2 [Reset](./reset.md)  
  2.3 [Typography](./typography.md)  
  2.4 [View](./view.md)  
  2.5 [Navbar](./navbar.md)  
  2.6 [Container](./container.md)  
  2.7 [Section](./section.md)  
  2.8 [Column](./column.md)  
  2.9 [Button](./button.md)  
  2.10 [Table](./table.md)  
  2.11 [Details](./details.md)  
  2.12 **[Form](./form.md)**  
  2.13 [List](./list.md)  
  2.14 [Process tree](./process-tree.md)  
  2.15 [Icon](./icon.md)  
  2.16 [Box](./box.md)  
  2.17 [Banner](./banner.md)  
  2.18 [Tab](./tab.md)  
  2.19 [Tag](./tag.md)  
  2.20 [Popover](./popover.md)  
  2.21 [JSON Expander](./json-expander.md)  
  2.22 [Footer](./footer.md)  
  2.23 [Misc](./misc.md)  
  2.24 [Helpers](./helpers.md)  

---
