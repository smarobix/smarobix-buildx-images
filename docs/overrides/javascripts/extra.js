// ---------------------------------------------------------------------------
// CURRENTLY INERT — kept deliberately.
//
// Material for MkDocs does not read `window.mermaidConfig`. It loads Mermaid
// from a CDN and calls `mermaid.initialize()` itself with its own `themeCSS`,
// and the string "mermaidConfig" appears nowhere in the shipped bundle, so
// nothing below has any effect on how diagrams render today.
//
// What actually styles the diagrams is the `--md-mermaid-*` block in
// overrides/stylesheets/extra.css. Material's themeCSS resolves those custom
// properties against the document, and custom properties are the only thing
// that crosses into the closed shadow root Mermaid renders into — which is
// also why per-node emphasis lives in the diagram source as a `classDef`
// rather than in CSS.
//
// This file is retained because the hook is cheap and may become live again:
// Material has read a global config in the past, a future version may do so,
// and a custom `mermaid.initialize()` in an override template would pick it
// up. If you make it live, note that `theme` here would fight the CSS above —
// decide which one owns the palette before enabling both.
//
// The previous comment claimed this forced the light theme "so diagrams stay
// readable on the white card background". Both halves are now wrong: it never
// forced anything, and the diagrams no longer sit on a white card.
// ---------------------------------------------------------------------------
window.mermaidConfig = {
  theme: "neutral"
};
