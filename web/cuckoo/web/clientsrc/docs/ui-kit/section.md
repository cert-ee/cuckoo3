# Section

Sections are contextual full-width blocks that separates various sections
of content. One use case of those is for example to create an attention-block on
the top of the page, or line up repetitive content over the page.

Example: Attention-block header
```html
<section class="section has-background-white">
  <div class="container is-fixed is-smol">
    <h1>Welcome to this page</h1>
    <h3>We hope you will have a good time.</h3>
    <p><a class="button is-blue is-big">Let's go</a></p>
    <p class="has-half-opacity has-text-small">Disclamer: Clicking the button will not take you anywhere</p>
  </div>
</section>
```

| class                   | type     | description                                        |
| ----------------------- | -------- | -------------------------------------------------- |
| `.section`              | parent   | Defines a section block                            |
| `.is-big`               | modifier | Bigger variant of section block                    | 
| `.is-full-page`         | modifier | Makes the section consume the full viewport height |
| `.with-navbar`          | modifier | Modifies `.is-full-page` to have a top-page-navbar |
| `.has-background-white` | modifier | Gives the section a white background               |
| `.has-background-dark`  | modifier | Makes the background dark                          |

---
_file: `web/cuckoo/web/clientsrc/sass/_section.sass`_
