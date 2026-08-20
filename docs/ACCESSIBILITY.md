# Accessibility standard

The voter guide targets [WCAG 2.2 Level AA](https://www.w3.org/TR/WCAG22/). Automated checks assist but cannot replace manual testing with keyboard and assistive technology.

## Required design and implementation practices

- Use semantic HTML, a logical heading hierarchy, labels for every input, and visible keyboard focus.
- Ensure all core paths work by keyboard alone; do not require dragging, hover, color-only meaning, or time-limited interaction.
- Meet contrast, text-resize, touch-target, responsive-layout, and focus-not-obscured requirements.
- Give errors in text, associate them with the affected control, and preserve entered non-sensitive form state where appropriate. The address field is cleared only after a request is complete under the privacy policy.
- Use plain language, define government terms, and keep official wording available alongside explanations.
- Provide text alternatives for non-decorative images, captions/transcripts for media, and accessible names for controls.
- Test the address-to-ballot journey with keyboard navigation, browser zoom, screen readers, mobile viewport sizes, and reduced-motion settings before each release.

## Release evidence

Each release must record automated accessibility results, manual test date, tester, browser/assistive-technology combination, known issues, and remediation owner. A critical issue in the ballot-resolution journey blocks release.
