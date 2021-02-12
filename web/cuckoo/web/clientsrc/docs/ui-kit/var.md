# Variables

A lot of constants are made easily accessible throughout the style sheet.
Changing these variables will change a whole lot about the appearance of the app,
making it unique and to give some basic branding options. Think of parameters like
size, colors and breakpoints.

| variable name           | description                                 | default value        |
| ----------------------- | ------------------------------------------- | -------------------- |
| `$blue`                 | Base blue color                             | `#2E94F1`            |
| `$red`                  | Base red color                              | `#FF0000`            |
| `$dark`                 | Dark color variant                          | `#0F485A`            |
| `$white`                | Base white tint                             | `#FFFFFF`            |
| `$black`                | Base black tint                             | `#000000`            |
| `$border`               | Base border color                           | `#CCCCCC`            |
| `$yellow`               | Base yellow                                 | `#FCC200`            |
| `$green`                | Base green                                  | `#82DB7A`            |
| `$light`                | Translucent black, gets darker when stacked | `rgba(0,0,0,.5)`     |
| `$light-matte`          | Matte color definition for light            | `#F2F2F2`            |
| `$row-odd`              | Background-color for odd table cell         | `#FFFFFF`            |
| `$row-even`             | Background-color for even table cell        | `#E8F0F1`            |
| `$code-light`           | Color for code block backgrounds            | `$light`             |
| `$code-light-text`      | Text color for light code blocks            | `$dark`              |
| `$code-dark`            | Color for code block backgrounds            | `$dark`              |
| `$code-dark-text`       | Text color for dark code blocks             | `$light-matte`       |
| `$gap`                  | Default gap size                            | 0.75rem              |
| `$radius`               | Default radius size                         | 0.2rem               |
| `$navbar-height`        | Fixed navbar height                         | 3.5625rem            |
| `$footer-height`        | Fixed footer height                         | 10rem                |
| `$breakpoint-large`     | Breakpoint for large viewports              | 90rem                |
| `$breakpoint-medium`    | Breakpoint for smaller viewports (laptops)  | 70rem                |
| `$breakpoint-small`     | Breakpoint for smaller viewports (tablets)  | 60rem                |
| `$breakpoint-mobile`    | Very tiny viewports                         | 40rem                |
| `$font-stack-default`   | System font stack                           | System font stack    |
| `$font-stack-monospace` | Monospace font stack                        | Monospace font stack |

---
_file: `web/cuckoo/web/clientsrc/sass/_var.sass`_
