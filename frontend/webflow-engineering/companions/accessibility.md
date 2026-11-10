# Accessibility

Target **WCAG 2.2 AA**. Webflow gives you good defaults and then makes it
easy to break them. Check the page, the template and the CMS content.

## Structure

- One `h1` per page; headings in order, never skipped for looks. In rich
  text, headings sit below the page `h1`.
- Use semantic elements: set the tag on `Div Block`s (`header`, `nav`,
  `main`, `section`, `footer`, `article`). One `main` per page.
- Add a **skip link** to the main content; make it visible on focus.
- Lists are real lists; buttons are real buttons (not a clickable div);
  links navigate, buttons act.

## Text alternatives

- Every meaningful `img` has descriptive alt text; decorative images have
  empty alt (`alt=""`) so they're skipped. Don't write "image of…".
- Alt for CMS images comes from an alt field, bound in the template
  (`cms-design.md`). Imports must carry it (`cms-import-docx.md`).
- Icon-only controls get an accessible name (`aria-label` or visually
  hidden text). Video has captions; background video decorative and
  pausable.

## Color, type, motion

- Text contrast ≥ 4.5:1 (3:1 for large text and UI boundaries). Check
  states too: hover, focus, disabled, on images and gradients.
- Never rely on color alone for meaning (errors, required, links).
- Body text is `rem`-based so zoom works; layout holds at 320px width and
  200% zoom without horizontal scroll.
- Interactions and Lottie respect `prefers-reduced-motion`: reduce or
  remove movement; nothing flashes more than three times a second; no
  auto-playing motion longer than 5s without a pause control.
- Targets ≥ 24×24 CSS px with spacing.

## Keyboard and focus

- Everything interactive is reachable and operable by keyboard in a
  logical order. **Never remove the focus outline** without a visible
  replacement of equal strength.
- Menus, dropdowns, tabs, sliders and modals: check keyboard behaviour
  and focus return; Webflow's native components cover much of this, custom
  ones do not. A custom modal must trap focus, close on Escape, and return
  focus.
- Don't hide content from assistive tech with `display:none` while still
  showing it, or the reverse. Use `aria-hidden` only on non-focusable
  content.

## Forms

- Every field has a visible `label` tied to the input (`for`/`id`);
  placeholders are not labels. Group related fields in a `fieldset` with a
  `legend`.
- Required fields are marked in text, not only color.
- Errors are specific, adjacent to the field, and announced
  (`aria-live` or `role="alert"`); success states too.
- Use the right input `type` and `autocomplete`. Never block paste or
  password managers. Add spam protection that doesn't depend on a visual
  puzzle alone.

## Landmarks and language

- Set the page language. Mark language changes in the content.
- Page titles are unique and descriptive (`seo-redirects.md`).
- Link text makes sense out of context; avoid repeated "click here".

## Checking

Run an automated pass (axe, Lighthouse) and a manual one: tab through the
whole page, zoom to 200%, turn on reduced motion, and use a screen reader
on the key flow. Automated tools catch a minority of problems. Say what
you checked and what you could not.

## Output

A list of findings by severity (Blocking = prevents use, e.g. keyboard
trap or missing form label; Should fix; Nit), with the element, the
fix and where to make it in the Designer. Separate what MCP tools
changed from what the user must click.
