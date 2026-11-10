# Styling system: classes, variables, components

Read the site's existing classes and variables first (SKILL.md §2). On an
existing site the current system wins; everything below is the default for
new ground. Renames in Webflow are site-wide and hard to undo, so never
rename silently.

## Class naming (default: Client-First)

Unless NFN supplies a house system, use Client-First conventions:

- **Structure classes**: `page-wrapper`, `main-wrapper`, `section_[name]`,
  `padding-global`, `container-large|medium|small`, `padding-section-*`.
- **Custom classes**: `[section]_[element]` with one underscore, e.g.
  `hero_heading`, `blog-card_image`. Lowercase, hyphens within a word,
  underscore between component and element.
- **Utility classes**: `text-size-large`, `text-weight-bold`,
  `margin-bottom`, `margin-top`, `hide`, `max-width-medium`. Reusable
  across the site, one purpose each.
- **Global classes** hold layout and typography shared by many elements;
  **custom classes** hold what is unique to one component.
- Name by **role**, not looks: `button-primary`, not `blue-button`.
- Never leave default names (`Div Block 12`, `Heading 3`) on shipped
  elements. Never style by ID. Avoid inline styles on the element.

## Global vs combo classes

- A **combo class** modifies a base class (`button` + `is-secondary`).
  Name modifiers with an `is-` prefix. Keep to **one combo class** per
  element where possible; two is a smell, three means a new class.
- Don't build a combo on top of a different component's class.
- When the same combo appears on many elements, promote it to a utility or
  a variant (a component property).
- Style the **base class** for the common case, and the combo only for the
  difference. Editing a base class changes every element that uses it —
  check usage before you do.

## Variables

- Use variables for color, size, spacing, radius and font families; modes
  for dark/light or brand themes. Name by purpose
  (`color/text/primary`, `space/section`), not by value (`blue-500`
  only inside the primitive layer).
- Two layers: **primitives** (raw values) and **semantic** tokens that
  reference them. Elements use the semantic tokens.
- Before creating one, read the existing variables (`data_variable_tool`)
  and reuse. Never duplicate a value under a second name.
- Hard-coded colors, sizes or spacing that a variable owns are a defect.

## Layout and responsiveness

- Build with **flex/grid and the site's spacing system**, not absolute
  positioning or fixed pixel heights. Use `rem`/`%`/`vw` and `min`/`max`
  rather than per-breakpoint overrides where you can.
- Design the base breakpoint first, then override downward only for what
  actually changes. Check 1920, desktop, tablet, mobile landscape,
  mobile portrait.
- Use `padding-global` and a container for horizontal rhythm instead of
  per-section margins.

## Components

- Make a **component** for anything repeated or edited in one place:
  navbar, footer, card, CTA, form block. Keep content in **properties**
  (text, image, link, visibility) rather than forcing editors into the
  inner structure.
- Use **variants** for styling differences, not duplicated components.
- Before editing a component, say it affects every instance. Unlink an
  instance only on purpose.
- Name components in Title Case by role (`Card / Blog`, `Section / Hero`).

## Cleanup (only when asked)

Report first: unused classes, near-duplicate classes, default-named
elements, hard-coded values. Offer a plan and get a yes before any bulk
rename or delete. Never delete a class that the live site may still use
without checking the pages and CMS templates that reference it.

## Output

State which system you matched or chose, list the classes/variables/
components you created or changed, and flag anything inconsistent you did
not touch. Anything the tools can't do (Designer-only) goes in a
"you click" list.
