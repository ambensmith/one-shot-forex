# Post-Development Checks

Things to verify, reconcile, or clean up after all dev sessions are complete. These are inconsistencies, ambiguities, and gotchas spotted during the design process that aren't blockers for building but need resolving before submission.

---

## 1. JSON vs Markdown in Trade Drill-Down

**The issue:** DATA_FLOW.md Stage 6 (RECORD) says "the frontend renders this JSON as clean, readable markdown" and includes a full markdown template. But the DESIGN.md narrative timeline drill-down renders structured JSON as styled React components — not markdown at all.

**What to check:**
- Session 10 (API): Does `/api/trades/{id}` return the raw trade record JSON, or does it pre-render markdown?
- Session 11 (Frontend): Does the timeline drill-down consume JSON fields directly (correct) or expect a markdown string?
- DATA_FLOW.md: The markdown template in Stage 6 should be removed or relabelled as "example of the content that the frontend will display" — it's not a rendering spec anymore.

**Correct approach:** API serves structured JSON. Frontend React components handle all rendering. No markdown involved in the drill-down. The DESIGN.md Section 8 is the spec for how each JSON field maps to a timeline chapter.

---

## 2. shadcn/ui References

**The issue:** The old codebase and several docs reference shadcn/ui as the component library. The DESIGN.md defines a custom design system (custom colors, Playfair Display typography, semantic shadows, bottom pill nav) that doesn't use shadcn's default styling or components.

**What to check:**
- Is shadcn/ui still installed and being used? If so, are the components restyled to match DESIGN.md, or are we building custom components?
- CLAUDE.md critical decision #9 has been updated, but grep the codebase for any remaining "shadcn" references in config, package.json, or component imports
- PROJECT_OVERVIEW.md still mentions "shadcn/ui" in several places — needs updating to match the actual frontend approach

**Decision needed:** Are we using shadcn/ui primitives (Radix-based, unstyled) reskinned to our design system, or building from scratch with plain Tailwind? Both are valid — but the choice affects Session 11's setup.

---

## 3. Old Frontend Code

**The issue:** `frontend/src/` contains the old frontend (8 screens, sidebar layout, dark theme, custom components). The new design is fundamentally different — light theme, 3-4 pages, bottom pill nav, narrative timelines.

**What to check:**
- Is any old component code worth salvaging? Likely candidates: `useStreamData.js` (data fetching hooks), `useLivePositions.js`, `useCountdown.js` (for next run countdown)
- The old `Layout.jsx` (sidebar nav) must be completely replaced — do not adapt it
- Old screens like `HybridBuilder.jsx`, `ModelComparison.jsx`, `RunHistory.jsx` are no longer in scope — can be deleted
- `package.json` dependencies: review what's installed vs what the new design needs

**Recommendation:** Start fresh in Session 11. Copy over useful hooks, delete everything else.

---

## 4. Navigation Item Count

**The issue:** DESIGN.md specifies 3 pages + settings icon in the pill nav (Dashboard, LLM Analysis, Strategies, gear icon). But the old app had 8 nav items and there may be pressure to add more later (e.g., a dedicated Equity page, a Run History page).

**What to check:**
- Is the pill nav design flexible enough for 5-6 items if needed? At 480px max width, 4 items fit comfortably. 6 would be tight.
- The equity curve is currently embedded in the Dashboard — should it be its own page if the data grows?
- Run History was a page in the old app — is it still needed, or is it covered by the closed trades table with filters?

**Decision needed post-build:** After Session 12, review whether 3+settings is sufficient or if the pill nav needs a 4th text item.

---

## 5. Polling vs WebSockets for Open Trades

**The issue:** DESIGN.md Section 9.1 specifies polling `/api/trades/open` every 30 seconds. The old app had `useLivePositions.js` which may have used a different approach. Session 11 says "never drifts."

**What to check:**
- Is 30-second polling sufficient for "never drifts"? Open trades show current price — if that's fetched from the broker, 30s may be fine. If users expect real-time ticking prices, polling won't cut it.
- Does the Capital.com API support WebSocket streaming for position updates? If so, a lightweight WS connection would be better than polling.
- What happens when the backend is mid-tick (running the pipeline)? Does the API still respond, or does SQLite lock block reads?

**Recommendation:** Start with polling in Session 11. Upgrade to WebSocket if needed — it's an optimisation, not a design change.

---

## 6. Strategy Descriptions

**The issue:** DESIGN.md Section 9.3 says strategy descriptions should be "written for a university assessor — what it does, why it works, weaknesses." But `/api/strategies` presumably returns whatever description is in the strategy code/config.

**What to check:**
- Where do strategy descriptions live? In the code? In config YAML? In the database?
- Are the current descriptions assessor-friendly prose, or terse developer notes?
- Session 12 needs well-written descriptions — these may need to be authored manually, not pulled from code

**Recommendation:** Write the 4 strategy descriptions as part of Session 12. Store them in config or hardcode in the frontend — they're static content, not dynamic data.

---

## 7. Account Summary Panel Data Source

**The issue:** The pill nav's expandable account summary shows total account value and overall P&L percentage. But it's not clear which API endpoint provides this.

**What to check:**
- Does `/api/equity` return the current total? Or just historical snapshots?
- Does the backend track total account value, or does it need to be fetched from Capital.com's account endpoint?
- The old `capitalcom_client.py` likely has an account balance method — verify it's exposed through the API

**Action needed:** May need a `GET /api/account` endpoint (or add account balance to an existing endpoint) in Session 10.

---

## 8. Empty States

**The issue:** If the system has just been deployed with a fresh database, every page is empty. The DESIGN.md specifies one empty state ("No open trades...") but doesn't cover all pages.

**What to check after build:**
- Dashboard: no trades, no bias data, no equity curve — what does the user see?
- LLM Analysis: no headlines, no signals, no relevance assessments
- Strategies: strategies exist but no signals or trades yet
- Account summary panel: £0 balance, 0% P&L

**Recommendation:** Each page should have a meaningful empty state that explains what will appear and when. These are also useful for the report screenshots if the system hasn't generated trades yet.

---

## 9. Prompt Version Tracking in UI

**The issue:** DESIGN.md Section 9.2 shows a version badge next to each prompt name ("Relevance Prompt (v3)"). The editable prompts section says "version increments" after save.

**What to check:**
- Does the `PUT /api/prompts/{name}` endpoint handle versioning? Does it create a new version row or update in place?
- The `prompts` table has `version` and `is_active` columns — is the backend logic implemented to increment version and set old versions inactive?
- Can the user view previous versions, or just the current one?

**Decision needed:** For MVP, just show current version with version number badge. Version history browsing is a nice-to-have.

---

## 10. Responsive Testing

**The issue:** DESIGN.md Section 11 defines 4 breakpoints and mobile adaptations. But with the submission deadline, responsive may be deprioritised.

**What to check after build:**
- Does the pill nav work on mobile (full-width, touch targets)?
- Do tables scroll horizontally on small screens?
- Does the timeline drill-down remain readable on mobile?
- Does the university submission require mobile support, or is desktop-only acceptable?

**Recommendation:** Build desktop-first. Test mobile briefly. Fix only breaking layout issues — don't polish mobile for submission.

---

## 11. Font Loading Performance

**The issue:** Three Google Fonts families (Playfair Display, Inter, JetBrains Mono) across multiple weights is a meaningful payload.

**What to check after build:**
- Is there a visible flash of unstyled text (FOUT) on page load?
- Are fonts loaded with `display: swap` to prevent blocking render?
- Total font payload: Playfair (400-700) + Inter (400-600) + JetBrains Mono (400) — estimate ~200-300KB

**Recommendation:** Use `<link rel="preload">` for the primary fonts (Inter 400, Playfair 700). Load secondary weights async. JetBrains Mono can lazy-load since it's only used in drill-downs and prompt editors.

---

## 12. Color Accessibility

**The issue:** The semantic shadow/tint system is subtle by design (0.04 opacity tints, 0.15 opacity shadows). This may be too subtle for users with reduced color perception.

**What to check after build:**
- Are the semantic text colors (#15803D green, #DC2626 red, #B45309 amber) sufficient contrast on white backgrounds? Check against WCAG AA.
- Is direction communicated through text/icons as well as color? (e.g., "LONG ▲" not just green)
- Does the trade drill-down rely solely on shadow color to communicate status, or is there redundant text?

**Recommendation:** The design already pairs color with text labels and directional arrows — verify this is consistent throughout.
