# UI System contents

## .view
`sass/_view.sass`  
The view class is a wrapping element around the main page content. It has some modifications that will help the footer to be sticky on the bottom when the page height is higher than the actual content height. It will  push down the footer when the content height exceeds the page height.

```html
<div class="view"><!-- code --></div>
```

## .container
`sass/_container.sass`  
Container centerizes bulk content. The container has a maximum width where the components are constrained within.

```html
<div class="container"><!-- code --></div>
```

## .section
`sass/_section.sass`  
Sections are structural elements to give a background color variation to big blocks of grouped content. Sections are stacked on top of each other, and should have a container class:

```html
<div class="section">
  <div class="container"><!-- code --></div>
</div>
```

| Modifier                      | Description                                                             |
| ----------------------------- | ----------------------------------------------------------------------- |
| `.is-full-page`               | 100 viewport units in height                                            |
| `[.is-full-page].with-navbar` | Addition to is-full-page; subtracts the navbar height to fit _exactly_. |
| `.has-background-white`       | container with white background                                         |
| `.has-background-dark`        | container with dark background                                          |

## .columns
`sass/_column.sass`  
The column system is a flexbox utility. It will place content blocks next to each other and automatically aligns it relative to its content. Using modifiers, the layout can be influenced to reflect the use case. Column containers are fluid in width so they can be use in a nested manner as well. Use modifiers to alter the alignment flow.

```html
<div class="columns is-between">
  <div class="column">A</div>
  <div class="column">B</div>
  <div class="column">C</div>
</div>
```

| Modifier       | Description                                                                |
| -------------- | -------------------------------------------------------------------------- |
| `.is-vertical` | vertically aligns the column context                                       |
| `.is-even`     | evenly distributes the column alignment                                    |
| `.is-between`  | aligns columns spreaded from start to end                                  |
| `.is-around`   | aligns columns spreaded from start to end originating from the center      |
| `.is-center`   | aligns all columns in the center                                           |
| `.is-left`     | aligns all columns on the left                                             |
| `.is-right`    | aligns all colums on the right                                             |
| `.is-divided`  | same as is-even?                                                           |
| `.is-vcenter`  | vertically aligns the columns in horizontal context to the relative center |
| `.is-vbottom`  | vertically aligns the columns in horizontal context to the relative bottom |
| `.is-vstretch` | stretches all the columns to equal vertical height                         |
| `.is-gapless`  | removes all the gaps between columns                                       |

## .box
`sass/_box.sass`  
The box is a wrapping element to quickly group smaller content. It appears as a box with its own style properties that cascade down into the inner content. This allows to create a level of depth in the application. Boxes within boxes will not have a shadow.

```html
<!-- a box -->
<div class="box"><!-- code --></div>
<!-- group of boxes -->
<div class="box is-combined"><!-- code --></div>
<div class="box"><!-- code --></div>
<div class="box"><!-- code --></div>
<div class="box"><!-- code --></div>
<!-- color variants -->
<div class="box has-background-light"><!-- code --></div>
```

| Modifier              | Description                                                                                                               |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| .has-background-light | a light background color on the box                                                                                       |
| .is-grouped           | add this class to the first box of multiple siblingized boxes to 'bind' them all together separated with a border per box |

## .form
`sass/_form.sass`  
To make HTML forms, some additional styling features have been added for ux and ui purposes. Labels and input fields are grouped together as single components that add backbone structures for icons and other grouping features. A basic html form and a structure example:

```html
<form class="form">
  <!-- input[text,number,email,url,date] -->
  <div class="field">
    <label class="label" for="myField">My field</label>
    <div class="control">
      <input class="input" id="myField" />
    </div>
  </div>
  <!-- input[radio,checkbox] -->
  <div class="field">
    <div class="control is-checkable">
      <input type="checkbox" id="myCheckbox" />
      <label class="label" for="myCheckbox">I agree, yes.</label>
    </div>
    <div class="control is-checkable">
      <input type="radio" id="myRadio1" name="" checked />
      <label class="label" for="myRadio1">I did not lie about agreeiing.</label>
    </div>
    <div class="control is-checkable">
      <input type="radio" id="myRadio2" name="" />
      <label class="label" for="myRadio2">I lied about agreeiing.</label>
    </div>
  </div>
  <!-- input[select] - also supports multiple attribute -->
  <div class="field">
    <label for="mySelect">Pick an option</label>
    <div class="control is-select">
      <select class="input">
        <option>Sedan</option>
        <option>Hatchback</option>
        <option>Minivan</option>
      </select>
    </div>
  </div>
  <!-- input[file] -->
  <div class="field">
    <div class="control is-file has-text-center">
      <label class="file-trigger" for="demo_file">Select file</label>
      <input type="file" class="input" id="demo_file" name="demo_file" data-enhance />
    </div>
  </div>
</form>
```

The [data-enhance] tag in the file pick field refers to a separate javascript initializer. To enable this, include the `ui.js` on the bottom of the `<body>` in the html file.

## .details
The details class is a native way of making an interactive collapsible element. It uses the HTML5 `<details>` block to create a context that can be hidden and revealed by toggling the summary component. It's implementation allows for eas

## .list
No base styles for a list have been included yet.

```html
<ul class="list"></ul>
```

### .list.is-tree
The list tree variant represents a nested tree, e.g for displaying file trees or other nested content. it can layout child-parent structures and make them collapsible (doesn't require any extra javascript, although an additional JS enhancement is available to resolve some general UX problems).

The source for such a tree may look like this:
```html
<ul class="list is-tree">
  <li class="is-parent">
    <input type="checkbox" id="folder-1" class="list-collapse" />
    <label for="folder-1">Folder 1</label>
    <ul>
      <li>file-1</li>
      <li>file-2</li>
      <li>file-3</li>
    </ul>
  </li>
</ul>
```

1. When the checkbox (with the class name list-collapse (!)) is 'checked', it will cause it's preceding element to respond to its checked state. Using css, it will hide or reveal the sibling list element.
2. The `<label>` tag after the checkbox is related to the checkbox using the `for` attribute. It should match with the id of the row checkbox. The label tag can hold any html, it is used here to indicate the 'label' of the tree list instead of its usual form usage.
3. Optionally, add `data-enhance` to the root `<ul>` tag. This will initialize an enhancer that will add extra usability improvements (such as opening parents when child checkboxes has been pre-checked).

## Table
Tabular data can be displayed through a minimal styling. Odd and even rows are included, but most of these accesibility features can be added to the table using modifiers.

```html
<table class="table {has-sticky-header}">
  <thead class="{is-dark}">
    <tr>
      <th>Table header</th>
      <th>Table header</th>
      <th>Table header</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Table cell</td>
      <td>Table cell</td>
      <td>Table cell</td>
    </tr>
    <tr>
      <td>Table cell</td>
      <td>Table cell</td>
      <td>Table cell</td>
    </tr>
    <tr>
      <td>Table cell</td>
      <td>Table cell</td>
      <td>Table cell</td>
    </tr>
  </tbody>
</table>
```

| Modifier              | Description                                                               |
| --------------------- | ------------------------------------------------------------------------- |
| `.has-sticky-header`  | Snaps the table to the top, making the tbody the vertical scrolling area. |
| **`<thead>`**         |                                                                           |
| `.is-dark`            | Dark context on the table heading.                                        |
| **`<th>`**            |                                                                           |
| `.has-sort`           | Adds styles for sorting icon support in table heading.                    |
| `[.has-sort].is-desc` | Sort state for descending column cells.                                   |
| `[.has-sort].is-asc`  | Sort state for ascending column cells.                                    |

### Column sorting assist
Extra utilities have been added to implement sorting behavior. Sorting a table head needs this markup:

```html
<!-- previous table markup -->
<thead>
  <tr>
    <th class="has-sort"><a href="#">Indeterminate (none) sorter.</a></th>
    <th class="has-sort is-asc"><a href="#">Ascending sort state.</a></th>
    <th class="has-sort is-desc"><a href="#">Descending sort state.</a></th>
</thead>
<!-- rest of table markup -->
```

**Please note** that adding these classes do not 'sort' the contents. Extra javascript or performing the sort in the backend is required. These classes  assist the view to reflect sorting behavior.

## Javascript enhancement
Some parts of the UI can be enhanced using the included javascript library. It offers some support that improve the UX of a component. The `ui.js` file should be included on the bottom of the `<body>` of the template in order to be utilized.

The idea is that a JS enhancement is considered component-specific and they will attach to an element using a reference in the html tag. For example, the file input on its own lacks some support of proper user feedback, so the file input enhancer adds some more visual feedback that follows the stylesheet rather than the native built-in functionality. To initialize this enhancer, you add `data-enhance` to the `<input>` tag, like so:

```html
... form code ...
<input type="file" data-enhance />
```

At the bottom of `ui.js` in the DOMContentLoaded handler, a queryselector picks up on the `data-enhance` attribute being present on that input tag and applies the `FileInputHandler` to that element.

This goes for any element that has a supported enhancer, this also allows for creating custom enhancements. They can be added into `ui.js` by using the `applyHandler` function. A list of supported enhancers:

| Selector / Component                | Enhancer        | Description                                                |
| ----------------------------------- | --------------- | ---------------------------------------------------------- |
| `.navbar .navbar-toggle`            | handleNavbar    | Initializes hamburger menu behavior for small viewports    |
| `.input[type="file"][data-enhance]` | handleFileInput | Initializes UX feedback improvement for file input control |
| `.list.is-tree[data-enhance]`       | handleListTree  | Auto-open parent lists for nested checked checkboxes       |
| `.tabbar[data-enhance]`             | handlePageTabs  | Initializes direct tab selectors with related elements. Use href in .tabbar-link like `#myTab` to toggle the div with id `myTab` to display when clicked on it, hiding the other linked tabs. |

## Javascript utilities
Next to default enhancers, `ui.js` also implements common javascript utilities. These utilities can be used to perform micro actions like toggling visibility or create interactive tabs. These are tiny interactions that can be triggered without many effort and custom code, in a repetitive and modular fashion. For example, to toggle the visibility of a certain element, call the utility in the `onclick` handler:

```html
<p id="toggle-text" hidden>This text can be toggled</p>

<!-- method 1: automatic toggling based on current state (hidden attribute) -->
<button onclick="toggleVisibility('#toggle-text');">Toggle text</button>
<button onclick="toggleVisibility('#toggle-text', true);">Show text</button>
<button onclick="toggleVisibility('#toggle-text', false);">Hide text</button>

<!-- method 2: Toggle using element properties, like the checked state of a checkbox or radio: -->
<div class="control">
  <input type="checkbox" class="input" id="myCheckbox" onclick="toggleVisibility('#toggle-text', this.checked)" />
  <label for="myCheckbox" class="label">Display text</label>
</div>
```
