# Miscelaneous

Alongside all the components, there are some elements that aren't included by
default in the HTML markup realm. There is some extra support added for elements
that are useful for creating rich contexts.

| class               | type     | description                                                                              |
| ------------------- | -------- | ---------------------------------------------------------------------------------------- |
| `.ratio-1-1`        | parent   | An aspect ratio box that will always maintain its 1:1 ratio, regardless of child content |
| `.ratio-content`    | child    | Defines the content in `.ratio-1-1`                                                      |
| `.dot`              | parent   | An inline circle/dot, for any purpose where dots are needed, such as status indication   |
| `.dot.is-red`       | modifier | When used on `.dot`, it will make the dot red                                            |
| `.dot.is-yellow`    | modifier | When used on `.dot`, it will make the dot yellow                                         |
| `.dot.is-blue`      | modifier | When used on `.dot`, it will make the dot blue                                           |
| `.has-hover-fadein` | modifier | Reduces opacity by default, but will set opacity to 1 when hovered                       |

---
_file: `web/cuckoo/web/clientsrc/sass/_misc.sass`_
