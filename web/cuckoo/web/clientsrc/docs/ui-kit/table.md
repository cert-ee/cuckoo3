# Table

Tables lay out big sets of data in rows and columns, like a spreadsheet. In order
to make them accessible and easy to digest, some base styles have been added and
tables can be modified in a way to meet any use case. It's rich of modifiers
and subclasses.

Example: default table
```html
<table class="table">
  <thead>
    <tr>
      <th>Column 1</th>
      <th>Column 2</th>
      <th>Column 3</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Cell 1</td>
      <td>Cell 2</td>
      <td>Cell 3</td>
    </tr>
    <!-- more rows truncated for brevity -->
  </tbody>
</table>
```

Example: sortable styles
```html
<thead class="is-dark">
  <tr>
    <th class="has-sort"><a class="is-asc">Column 1</a></th>
    <th class="has-sort"><a class="is-desc">Column 2</a></th>
    <th>Column 3</th>
  </tr>
</thead>
```

Example: Sticky footer/header
```html
<table class="has-sticky-header has-sticky-footer">
  <thead>...</thead>
  <tbody>...</tbody>
  <tfoot>...</tfoot>
</table>
<thead class="is-dark">
  <tr>
    <th class="has-sort"><a class="is-asc">Column 1</a></th>
    <th class="has-sort"><a class="is-desc">Column 2</a></th>
    <th>Column 3</th>
  </tr>
</thead>
```

| class                         | type     | description                                                                          |
| ----------------------------- | -------- | ------------------------------------------------------------------------------------ |
| `.table`                      | parent   | appended on a table to give the base table styles                                    |
| `.has-border`                 | modifier | adds borders to the table cells                                                      |
| `.has-layout-fixed`           | modifier | changes table layout to fixed                                                        |
| `.has-sticky-header`          | modifier | when scrolled out of view, the `<thead>` scrolls with the page                       |
| `.has-sticky-footer`          | modifier | equivalent of sticky header, but with the `<tfoot>`                                  |
| `.has-striped-rows`           | modifier | enables odd/even rows                                                                |
| `th/td.is-auto-width`         | modifier | applies min-content rules on table cell                                              |
| `th/td.is-datetime`           | modifier | aliases is-auto-width                                                                |
| `th/td.is-mini`               | modifier | sets a very small width on a cell                                                    |
| `th/td.is-small`              | modifier | sets a small width on a cell                                                         |
| `th/td.is-medium`             | modifier | sets a medium width on a cell                                                        |
| `th/td.is-nowrap`             | modifier | disables content wrapping in a cell                                                  |
| `th/td.is-break`              | modifier | enables content wrapping in a cell                                                   |
| `th/td.is-vtop`               | modifier | vertical aligns content to the top                                                   |
| `th/td.is-vbttom`             | modifier | vertical aligns content to the bottom                                                |
| `th/td.has-ellipsis`          | modifier | breaks exceeding content with ellipsis in a cell                                     |
| `th.has-sort`                 | modifier | extra styles for sortable columns. use with child `<a>` with `.is-asc` or `.is-desc` |
| `thead.is-dark`               | modifier | adds a dark theme to the table heading                                               |
| `tr.has-background-red`       | modifier | makes the entire row red                                                             |
| `tr.is-shown`                 | modifier | adds a 'selected' state appearance (blue) to the table row                           |
| `tr.separator`                | modifier | Makes a row behave like a separator inside the table                                 |
| `tr.separator-bar`            | modifier | Like a separator, but it is slightly smaller                                         |
| `tr.separator-bar.is-beveled` | modifier | Adds a beveled appearance to the separator-bar                                       |

## Sorting tables; some extra work required
Tables won't sort out of themselves, some additional javascript or server-side
handling is required.

---
_file: `web/cuckoo/web/clientsrc/sass/_table.sass`_

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
  2.10 **[Table](./table.md)**  
  2.11 [Details](./details.md)  
  2.12 [Form](./form.md)  
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
