# Button

The UI kit features an extensive way of declaring buttons. Buttons provide a well
understood way of providing interaction to the user of the interface. Buttons
are made up out of a lot of varieties to serve multiple purposes and define a
visual hierarchy in importance of the buttons. The style of the button is not
limited to a certain set of elements:

Example: Buttons
```html
<a class="button">This is a button</a>
<button class="button">This is a button</button>
<input type="submit" class="button" value="This is a button" />
<div class="button"><!-- however a bad practice, button styles still apply --></div>
```

Example: Button theming
```html
<a class="button is-red is-block">This is a button</a>
<a class="button is-dark is-small">This is a button</a>
<a class="button is-blue has-border">This is a button</a>

<a class="button is-danger">This is a button</a>
<a class="button is-warning">This is a button</a>
<a class="button is-info">This is a button</a>

<button disabled>Or use .is-disabled</button>
```

Example: coinjoined/grouped buttons:
```html
<div class="buttons-conjoined">
  <a class="button" href="#">Button 1</a>
  <a class="button" href="#">Button 2</a>
  <a class="button" href="#">Button 3</a>
  <a class="button" href="#">Button 4</a>
</div>

<div class="buttons-conjoined is-vertical">
  <a class="button" href="#">Button 1</a>
  <a class="button" href="#">Button 2</a>
  <a class="button" href="#">Button 3</a>
  <a class="button" href="#">Button 4</a>
</div>
```

Example: Icon buttons
```html
<a class="button is-green">
  <span class="button-icon">&check;</span>
</a>
```

Buttons are a base class, and in some situations inherits into other classes.

| Class                            | Type     | Description                                                                       |
| -------------------------------- | -------- | --------------------------------------------------------------------------------- |
| `.button`                        | parent   | Defines the base visual styles for a button                                       |
| `.is-gray`                       | modifier | Adds a gray theme to the button                                                   |
| `.is-gray`                       | modifier | Adds a gray theme to the button                                                   |
| `.is-blue`                       | modifier | Adds a blue theme to the button                                                   |
| `.is-info`                       | modifier | _Alias for `.is-blue`_                                                            |
| `.is-red`                        | modifier | Adds a red theme to the button                                                    |
| `.is-danger`                     | modifier | _Alias for `.is-red`_                                                             |
| `.is-dark`                       | modifier | Adds a dark theme to the button                                                   |
| `.is-white`                      | modifier | Adds a white theme to the button                                                  |
| `.is-yellow`                     | modifier | Adds a yellow theme to the button                                                 |
| `.is-warning`                    | modifier | _Alias for `.is-yellow`_                                                          |
| `.is-green`                      | modifier | Adds a green theme to the button                                                  |
| `.is-success`                    | modifier | Alias for _`.is-green`_                                                           |
| `.is-beveled`                    | modifier | Gradient appearance that adds a beveled look                                      |
| `.is-disabled`                   | modifier | Supporting style that indicates a disabled button                                 |
| `.has-border`                    | modifier | Adds a surrounding border to the button                                           |
| `.is-small`                      | modifier | Smaller size variant for the default button style                                 |
| `.is-block`                      | modifier | Adds `display: block` to change box model behavior                                |
| `.button-icon`                   | child    | Supporting styles for using an icon in a button                                   |
| `.buttons-conjoined`             | parent   | Buttons contained in an element with this class, will be gapless and in formation |
| `.buttons-conjoined.is-vertical` | modifier | Makes a top-to-bottom layout of conjoined buttons                                 |

---
_file: `web/cuckoo/web/clientsrc/sass/_button.sass`_
