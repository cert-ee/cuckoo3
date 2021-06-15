# UI System
These documentation describe the features of the UI system and how they used to construct functional views. The system adapts some core concepts from existing frameworks such as naming conventions, responsive handling and layout structure. It is combined into this tailored UI kit that offers a modular building ground to build custom views to reflect functionality that is accessible, lightweight and robust.

## The package
The contents of the UI system can be divided into three categories:

1. Layout
  - Building blocks for content positioning. The structures defined in this category have effect on the arrangement of elements and how they scale.
2. Elements
  - Definition of usability blocks, such as buttons, lists and tables. These elements are the building blocks to create experiences.
3. Components
  - UI components that are built upon layout and element blocks. They form a single user interface component all combined, such as forms, navbars and tabs.

### Layout
Layout structures are built to contain application content. These elements are considered layout structures with their different respective features (in chronological order):

1. `.section`
  - Sections are page-wide containers.
2. `.container`
  - Containers center aligns their inner content in a context that adjusts its width to the user's viewport.
3. `.columns` (parent) and `.column` (direct child)
  - Columns place elements in a grid (horizontal by default and vertical as modifier). The columns class is implemented with a wide set of modifiers to alter the appearance, set alignment constraints and child element order.
4. `.box`
  - Boxes add context to content. They separate different parts using spacing or background/text colors.

The layout components are the backbone of the application UI. These elements are used widely across the package. The logical order in which they would appear in a new html doc:

```html
<!-- ... document head, navbar etc -->
<section class="section">
  <div class="container">
    <!-- base level structures, headers etc. -->
    <div class="columns">
      <div class="column">
        <!-- view elements / content -->
      </div>
      <!-- more columns -->
    </div>
  </div>
</section>
<!-- ... document footer content -->
```

### Elements
Elements are basic building blocks of the views. They represent the html tags, such as `<h1>, <ul>, <button>` etc. Without added classes, they appear unstyled and inherit the basic body styles. Using base classes and modifiers they can be styled to reflect multiple styles. For example, the `.button` element is an extensive feature-rich element to demo the idea:

```html
<!-- base class .button, minimal styles to have it appear as a clickable element -->
<button class="button"></button>
<!-- using modifiers to give function to a button instance -->
<button class="button is-success">Confirm</button>
<button class="button is-danger">Delete</button>
<button class="button is-primary">Finish</button>
<!-- using modifiers to change the size of buttons -->
<button class="button is-large">Large button</button>
<button class="button is-small">Small button</button>
```

(above example is not yet fully supported as of writing this documentation).

### Components
Components are collections of layout and element bricks that form UI functionality. Some of these components will modify child elements of a certain types, whereas others are their own implementation. What differs them from elements is that they use several classes to form their function. A navbar is an example of one of those components:

```html
<nav class="navbar">
  <div class="navbar-logo">
    <a class="navbar-link" href="/">
      <img src="/images/cuckoo-light.svg" alt="Cuckoo" />
    </a>
    <a class="navbar-toggle" title="Expand menu">
      <span></span>
      <span></span>
      <span></span>
    </a>
  </div>
  <div class="navbar-start">
    <a class="navbar-link" href="/">Dashboard</a>
    <a class="navbar-link is-active" href="/">Submit</a>
    <a class="navbar-link" href="/">Reports</a>
    <a class="navbar-link" href="/">Search</a>
  </div>
  <div class="navbar-end">
    <a class="navbar-link" href="/">Settings</a>
  </div>
</nav>
```

But a form is a component that supports integrated elements such als columns:

```html
<form class="form">
  <div class="columns">
    <div class="column">
      <div class="field">
        <label class="label">Left text field:</label>
        <div class="control">
          <input class="input" />
        </div>
      </div>
    </div>
    <div class="column">
      <div class="field">
        <label class="label">Right text field:</label>
        <div class="control">
          <input class="input" />
        </div>
      </div>
    </div>
  </div>
  <input type="submit" class="button" value="Finish" />
</form>
```

## Naming conventions
Writing views with HTML requires some human form of readability. This boils down to how css classes are named, and how variations are applied. Practically, if we would have a box and display it on the screen, all we should need is:

```html
<div class="box"></div>
```

To give that box more definition to add a different background color and apply more spacing between the border and the inner content, assign a _modifier_ to the base box class:

```html
<div class="box is-red is-large"></div>
```

Note the `is-` prefix in the classes. Using these verbs, the class names in itself start to reflect the function of it and presents itself as an extension on top of a base class. As a human, reading 'box is red is large' is straight forward to visually get an idea of what that element is representing in the UI. This concept is fairly similar to Atomic Design principles, which you can read more about in [this write down by Brad Frost](https://bradfrost.com/blog/post/atomic-web-design/).

These were simple examples, but the entirety of classes included are based on this concept of naming all the structural elements. This helps into making HTML look less complex and easier to build features rather than spend a lot of time styling elements.

## Modifiers
While the above ensures less complexity in markup, there still will be situations where the layout does not look consistent due to margin/padding and other parameters of that variant. The setup of the UI to handle these edge-cases within a layout is to work with extra classes called modifiers. They exists on a global level, and on element specific levels. Modifiers exist to add or remove certain properties to make them fit greatly in the content. Most of these modifiers simply alter one or two css properties on top of a parent base style.

_Example: fit a columns layout tightly into a box element using modifiers_  
```html
<div class"box no-margin-x">
  <div class="columns is-divided no-padding no-margin">
    <div class="column is-auto no-padding-left">Column 1</div>
    <div class="column is-fill no-padding-right">Column 2</div>
  </div>
</div>
```

Also for these classes, a fair sense of straight forward readability is implemented for optimal code clarity and contributes to the HTML output being overridden. If the output seems to large or bulky, one can always try and run a minimiation tool over the output as post-processing. Such methodics are currently not included in the package, but may solve such problems or at least decrease the size of the output.

## Modularity
The `.sass` build code is leveraging some techniques with variables for entities such as colors, gaps and breakpoints. These can be tweaked to desired needs. However this is currently implemented with sass, it is not unlikely this will change to css variables so the tweaking can be applied using pure css, and the sass overhead will dissapear eventually completely. This depends on browser support for those features being stable enough to provide the experience independently.

---

### More docs

0. [Table of contents](../index.md)

1. _Package_  
  1.1 [Getting Started](./getting-started.md)  
  1.2 **[Core concept](./concept.md)**  

2. _UI Kit_  
  2.1 [Variables](../ui-kit/var.md)  
  2.2 [Reset](../ui-kit/reset.md)  
  2.3 [Typography](../ui-kit/typography.md)  
  2.4 [View](../ui-kit/view.md)  
  2.5 [Navbar](../ui-kit/navbar.md)  
  2.6 [Container](../ui-kit/container.md)  
  2.7 [Section](../ui-kit/section.md)  
  2.8 [Column](../ui-kit/column.md)  
  2.9 [Button](../ui-kit/button.md)  
  2.10 [Table](../ui-kit/table.md)  
  2.11 [Details](../ui-kit/details.md)  
  2.12 [Form](../ui-kit/form.md)  
  2.13 [List](../ui-kit/list.md)  
  2.14 [Process tree](../ui-kit/process-tree.md)  
  2.15 [Icon](../ui-kit/icon.md)  
  2.16 [Box](../ui-kit/box.md)  
  2.17 [Banner](../ui-kit/banner.md)  
  2.18 [Tab](../ui-kit/tab.md)  
  2.19 [Tag](../ui-kit/tag.md)  
  2.20 [Popover](../ui-kit/popover.md)  
  2.21 [JSON Expander](../ui-kit/json-expander.md)  
  2.22 [Footer](../ui-kit/footer.md)  
  2.23 [Misc](../ui-kit/misc.md)  
  2.24 [Helpers](../ui-kit/helpers.md)  

---
