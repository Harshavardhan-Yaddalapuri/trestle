---
name: Trestle
colors:
  surface: '#f8faf8'
  surface-dim: '#d8dad9'
  surface-bright: '#f8faf8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f2'
  surface-container: '#eceeec'
  surface-container-high: '#e6e9e7'
  surface-container-highest: '#e1e3e1'
  on-surface: '#191c1b'
  on-surface-variant: '#404943'
  inverse-surface: '#2e3130'
  inverse-on-surface: '#eff1ef'
  outline: '#707973'
  outline-variant: '#bfc9c1'
  surface-tint: '#2c694e'
  primary: '#0f5238'
  on-primary: '#ffffff'
  primary-container: '#2d6a4f'
  on-primary-container: '#a8e7c5'
  inverse-primary: '#95d4b3'
  secondary: '#3e6750'
  on-secondary: '#ffffff'
  secondary-container: '#bdeacd'
  on-secondary-container: '#426b54'
  tertiary: '#005236'
  on-tertiary: '#ffffff'
  tertiary-container: '#116c4a'
  on-tertiary-container: '#98eabf'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#b1f0ce'
  primary-fixed-dim: '#95d4b3'
  on-primary-fixed: '#002114'
  on-primary-fixed-variant: '#0e5138'
  secondary-fixed: '#c0edd0'
  secondary-fixed-dim: '#a4d1b4'
  on-secondary-fixed: '#002112'
  on-secondary-fixed-variant: '#264f39'
  tertiary-fixed: '#a1f4c8'
  tertiary-fixed-dim: '#86d7ad'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#f8faf8'
  on-background: '#191c1b'
  surface-variant: '#e1e3e1'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 57px
    fontWeight: '400'
    lineHeight: 64px
    letterSpacing: -0.25px
  display-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 45px
    fontWeight: '400'
    lineHeight: 52px
    letterSpacing: 0px
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '400'
    lineHeight: 40px
    letterSpacing: 0px
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '400'
    lineHeight: 36px
    letterSpacing: 0px
  title-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 22px
    fontWeight: '500'
    lineHeight: 28px
    letterSpacing: 0px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: 0.5px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: 0.25px
  label-lg:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.1px
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.5px
rounded:
  sm: 0.5rem
  DEFAULT: 1rem
  md: 1.5rem
  lg: 2rem
  xl: 3rem
  full: 9999px
spacing:
  none: '0'
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 48px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 32px
---

## Brand & Style
The design system is rooted in the Material 3 (Material You) philosophy, emphasizing personalization, accessibility, and organic movement. It targets users seeking a high-utility yet calming digital environment, specifically for productivity, wellness, or organizational tools. 

The visual style is **Corporate / Modern** with a heavy influence of **Organic Minimalism**. It leverages the "M3" algorithmic approach to color and layout, ensuring that every interface feels interconnected. The emotional goal is to evoke a sense of "digital breathing room"âusing expansive whitespace, large touch targets, and a palette derived from the natural world to reduce cognitive load and foster a focused, peaceful user experience.

## Colors
This design system utilizes a tonal palette centered on "Grass Green" and "Soft Earth." 

- **Primary:** A deep, forest-inspired green for key actions and brand presence.
- **Secondary:** A soft, desaturated mint for container backgrounds and tonal highlights.
- **Tertiary:** A mid-tone teal-green for accents that require distinction from the primary path.
- **Neutral:** A warm-tinted white (Off-white/Bone) to prevent screen fatigue and maintain a "paper-like" quality.

Color application follows the 60-30-10 rule, with the neutral base providing the vast majority of the surface area, secondary tones defining structural containers, and primary colors reserved for high-priority interactive elements.

## Typography
The typography system prioritizes legibility and a modern, friendly cadence. **Plus Jakarta Sans** serves as the display and headline face, offering soft, geometric curves that mirror the rounded UI elements. **Inter** is utilized for body text and labels to ensure maximum clarity in data-dense areas.

- **Scale:** Utilizes the standard M3 type scale.
- **Hierarchy:** Headlines should be generous in size to create clear entry points. 
- **Readability:** Body text maintains a 1.5x line height minimum to ensure an airy, accessible reading experience.

## Layout & Spacing
The layout follows a **Fluid Grid** model with strict adherence to an 8px base unit. 

- **Desktop:** 12-column grid with 24px gutters. Content is typically contained within a max-width of 1440px.
- **Tablet:** 8-column grid with 24px gutters.
- **Mobile:** 4-column grid with 16px margins.

The spacing philosophy emphasizes "Inner vs Outer" logic. Use `lg` (24px) for outer container padding and `md` (16px) for internal element grouping. Generous vertical spacing (`xxl`) is encouraged between distinct sections to reinforce the sense of calm.

## Elevation & Depth
This design system uses **Tonal Layers** as the primary method for conveying depth, supplemented by very soft, ambient shadows.

- **Level 0 (Surface):** The base background using the Neutral color.
- **Level 1 (Low Elevation):** Cards and containers that are slightly "lifted." These use a subtle tonal shift (Secondary Container color) and an ultra-diffused shadow: `0px 1px 3px rgba(0,0,0,0.05)`.
- **Level 2 (Hover/Active):** Increased shadow depth and slightly more saturated background color.
- **Level 3+ (Modals/Menus):** High elevation uses broader shadow spreads and "Scrim" overlays to push the surface to the foreground.

Avoid harsh borders. Depth should feel like layers of paper resting on top of one another.

## Shapes
Shapes are highly organic and friendly. The system utilizes **Pill-shaped** and extra-rounded corners to align with Material 3 standards.

- **Small Components (Buttons, Chips):** Fully rounded (Pill).
- **Medium Components (Cards, Menus):** 24px to 28px border radius.
- **Large Components (Modals, Bottom Sheets):** 32px top-corner radius.

This "extra-round" approach softens the digital interface, making it feel more tactile and approachable.

## Components
- **Buttons:** Use the "Filled" style for primary actions (Primary color, Pill-shaped). "Tonal" buttons use the Secondary color for low-emphasis actions.
- **Chips:** Highly rounded, used for filtering or selection. Active chips use the Primary color; inactive chips use a subtle neutral outline.
- **Cards:** No borders. Use Level 1 Elevation (Tonal lift) with 24px padding. Content within cards should follow the 8px spacing grid.
- **Input Fields:** Filled style with a thick bottom stroke or a fully outlined "Container" style with 12px roundedness. Use the Primary color for the focus state.
- **Navigation:** Use a Bottom Navigation Bar for mobile (M3 style with pill-shaped active indicator) and a Side Rail for desktop.
- **FAB (Floating Action Button):** A signature M3 element. Use a large, rounded-square (28px radius) FAB for the most important action on a screen, typically in the Primary or Tertiary color.