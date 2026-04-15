# Forex Sentinel — Design System

## 1. Visual Theme & Atmosphere

Forex Sentinel is an editorial trading dashboard — a system that explains itself. Where most trading interfaces default to dark, dense, terminal-like aesthetics, Sentinel takes the opposite approach: a light, airy canvas with generous whitespace, serif headings, and atmospheric colored shadows that communicate trading state without shouting. The overall impression should be closer to Kinfolk magazine or a Pentagram case study than to Bloomberg or TradingView.

The light background (`#FAFAF9` — warm off-white, not clinical pure white) sets the foundation. Text is rendered in deep warm charcoal (`#1C1917`) rather than pure black, softening the contrast just enough to feel inviting rather than harsh. The defining typographic choice is a serif/sans-serif pairing: **Playfair Display** for headings and narrative moments, **Inter** for everything functional. This immediately signals "this is a piece of work that explains itself" rather than "this is a trading terminal."

The most distinctive visual element is the **semantic shadow system**. Instead of block colors or heavy badges to communicate trade status (profitable, losing, pending), Sentinel uses colored `box-shadow` glows beneath cards and elements — like light bleeding through from behind. A profitable trade card sits on a soft emerald glow; a losing trade casts a rose shadow; a pending signal radiates warm amber. Cards also carry an almost imperceptible background tint in the same hue, so the color language works through atmosphere rather than decoration. The shadows are more saturated than the tints — the tint whispers, the shadow speaks.

**Key Characteristics:**
- Warm off-white canvas (`#FAFAF9`) — not sterile, not cream, just warm enough
- Playfair Display serif for headings — editorial authority, anti-fintech personality
- Inter for all functional text — clean, readable, shadcn-native
- Semantic colored shadows as the primary status communication channel
- Generous whitespace and breathing room — closer to a magazine than a terminal
- Conservative, rounded corners (8px–12px) — soft but not playful
- Bottom-anchored floating pill navigation — unconventional, space-efficient
- Narrative timeline drill-downs — trades tell their story chapter by chapter

## 2. Color Palette & Roles

### Foundation
- **Canvas** (`#FAFAF9`): Page background. A warm stone-white that prevents eye fatigue on light themes.
- **Surface** (`#FFFFFF`): Card and panel backgrounds. Pure white lifts elements off the canvas.
- **Text Primary** (`#1C1917`): Headings, strong labels, primary content. Deep warm charcoal — not black.
- **Text Secondary** (`#57534E`): Body text, descriptions, secondary content. Warm gray with enough contrast.
- **Text Tertiary** (`#A8A29E`): Captions, timestamps, muted metadata. Stone-toned for subtlety.
- **Text Inverse** (`#FAFAF9`): Text on dark backgrounds (e.g., pill nav).

### Brand
- **Sentinel Indigo** (`#4F46E5`): Primary brand accent. Used sparingly — active nav indicators, primary buttons, focus rings. A confident indigo that works on light backgrounds without feeling corporate.
- **Sentinel Indigo Light** (`#EEF2FF`): Tinted surface for brand-adjacent elements. Info badges, selected states.
- **Sentinel Indigo Hover** (`#4338CA`): Darker indigo for hover/press states.

### Semantic — Trading Status
Each semantic color exists in four roles: **shadow** (the primary communicator), **tint** (barely perceptible card background), **text** (for inline labels), and **border** (subtle edge reinforcement).

#### Profitable / Buy / Long
- **Shadow**: `rgba(34, 197, 94, 0.15)` — soft emerald glow
- **Tint**: `rgba(34, 197, 94, 0.04)` — whisper-level card background
- **Text**: `#15803D` — readable dark green for labels
- **Border**: `rgba(34, 197, 94, 0.20)` — subtle green edge
- **Accent**: `#22C55E` — for small indicator dots, sparklines

#### Loss / Sell / Short
- **Shadow**: `rgba(239, 68, 68, 0.15)` — soft rose glow
- **Tint**: `rgba(239, 68, 68, 0.04)` — whisper-level card background
- **Text**: `#DC2626` — readable red for labels
- **Border**: `rgba(239, 68, 68, 0.20)` — subtle red edge
- **Accent**: `#EF4444` — for indicator dots

#### Pending / Caution / Signal
- **Shadow**: `rgba(245, 158, 11, 0.15)` — soft amber glow
- **Tint**: `rgba(245, 158, 11, 0.04)` — whisper-level card background
- **Text**: `#B45309` — readable amber for labels
- **Border**: `rgba(245, 158, 11, 0.20)` — subtle amber edge
- **Accent**: `#F59E0B` — for indicator dots

#### Info / System / Pipeline
- **Shadow**: `rgba(99, 102, 241, 0.15)` — soft indigo glow
- **Tint**: `rgba(99, 102, 241, 0.04)` — whisper-level card background
- **Text**: `#4F46E5` — brand indigo for info labels
- **Border**: `rgba(99, 102, 241, 0.20)` — subtle indigo edge

#### Cooldown / Blocked / Inactive
- **Shadow**: `rgba(148, 163, 184, 0.15)` — muted slate glow
- **Tint**: `rgba(148, 163, 184, 0.04)` — barely visible gray
- **Text**: `#64748B` — cool slate for muted labels
- **Border**: `rgba(148, 163, 184, 0.20)` — subtle slate edge

### Neutral / Chrome
- **Border Default** (`#E7E5E4`): Standard borders for cards, dividers, table lines.
- **Border Subtle** (`#F5F5F4`): Very soft borders — used between timeline sections.
- **Border Strong** (`#D6D3D1`): Emphasized borders — used on active inputs, focused elements.
- **Background Hover** (`#F5F5F4`): Subtle hover state for interactive rows and list items.
- **Background Active** (`#EEEEEC`): Active/pressed state background.

## 3. Typography Rules

### Font Families
- **Serif (Display)**: `'Playfair Display', Georgia, 'Times New Roman', serif` — headings, narrative titles, pull quotes, trade story chapter headings. Loaded via Google Fonts at weights 400, 500, 600, 700.
- **Sans-Serif (Functional)**: `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif` — body text, labels, navigation, tables, buttons, data. The shadcn/ui default.
- **Monospace**: `'JetBrains Mono', 'SF Mono', 'Fira Code', monospace` — code blocks, JSON output, raw LLM responses, technical data.

### Hierarchy

| Role | Font | Size | Weight | Line Height | Letter Spacing | Usage |
|------|------|------|--------|-------------|----------------|-------|
| Page Title | Playfair Display | 36px (2.25rem) | 700 | 1.15 | -0.5px | Top-level page headings: "Dashboard", "LLM Analysis" |
| Section Heading | Playfair Display | 28px (1.75rem) | 600 | 1.20 | -0.3px | Major sections: "Open Trades", "Pipeline Activity" |
| Card Heading | Playfair Display | 22px (1.375rem) | 600 | 1.25 | -0.2px | Card titles, trade pair names in drill-down |
| Chapter Title | Playfair Display | 18px (1.125rem) | 500 | 1.30 | normal | Timeline chapter headings in narrative drill-down |
| Body Large | Inter | 16px (1rem) | 400 | 1.65 | normal | Primary reading text, narrative content, descriptions |
| Body | Inter | 14px (0.875rem) | 400 | 1.60 | normal | Standard body text, table cells, form content |
| Label | Inter | 14px (0.875rem) | 500 | 1.40 | normal | Form labels, table headers, nav items |
| Button | Inter | 14px (0.875rem) | 500 | 1.00 | 0.1px | Button text — slightly tracked for clarity |
| Caption | Inter | 12px (0.75rem) | 400 | 1.50 | normal | Timestamps, metadata, secondary info |
| Badge | Inter | 11px (0.6875rem) | 600 | 1.00 | 0.3px | Status badges, tags, small labels |
| Overline | Inter | 11px (0.6875rem) | 600 | 1.00 | 0.8px | Uppercase category labels above sections |
| Mono Body | JetBrains Mono | 13px (0.8125rem) | 400 | 1.70 | normal | LLM responses, JSON data, code snippets |
| Mono Small | JetBrains Mono | 11px (0.6875rem) | 400 | 1.60 | normal | Inline code, raw values, technical annotations |
| Data | Inter | 14px (0.875rem) | 500 | 1.40 | normal | Numeric data in tables — uses `font-variant-numeric: tabular-nums` |
| Data Large | Inter | 24px (1.5rem) | 600 | 1.20 | -0.3px | Hero metrics — account value, total P&L |

### Principles
- **Serif for personality, sans-serif for function.** Playfair Display appears only in headings and narrative contexts. It never appears in tables, buttons, navigation, or data displays. The moment you see a serif, you know you're reading something editorial — a title, a story heading, a pull quote.
- **Generous line heights for reading.** Body text at 1.60–1.65 line height. This is a dashboard that people read, not just scan. The narrative drill-downs especially need room to breathe.
- **Tabular numerics for data.** Any numeric data in tables, metrics, or financial displays uses `font-variant-numeric: tabular-nums` so columns align perfectly.
- **Restrained weight range.** Inter uses 400 (body), 500 (labels/buttons), 600 (badges/data emphasis). Playfair uses 500–700. No ultra-bold anywhere — the design speaks through space and shadow, not weight.

## 4. Component Stylings

### Cards
The primary content container. Cards communicate status through their shadow and tint, not through borders or header bars.

**Standard Card**
- Background: `#FFFFFF`
- Border: `1px solid #E7E5E4`
- Radius: `10px`
- Padding: `24px`
- Shadow (resting): `0 1px 3px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02)`
- Shadow (hover): `0 4px 16px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04)`
- Transition: `box-shadow 0.2s ease, transform 0.2s ease`
- Hover transform: `translateY(-1px)`

**Semantic Card (e.g., profitable trade)**
- Background: semantic tint (e.g., `rgba(34, 197, 94, 0.04)`)
- Border: semantic border (e.g., `rgba(34, 197, 94, 0.20)`)
- Shadow (resting): `0 4px 24px [semantic shadow], 0 1px 3px rgba(0, 0, 0, 0.04)`
- Shadow (hover): shadow opacity increases from 0.15 → 0.22, translateY(-1px)

### Buttons

**Primary**
- Background: `#4F46E5` (Sentinel Indigo)
- Text: `#FFFFFF`
- Padding: `10px 20px`
- Radius: `8px`
- Font: Inter 14px weight 500, letter-spacing 0.1px
- Shadow: `0 1px 3px rgba(79, 70, 229, 0.3), 0 1px 2px rgba(0, 0, 0, 0.06)`
- Hover: `#4338CA` background, shadow intensifies
- Transition: `all 0.15s ease`

**Secondary / Ghost**
- Background: `transparent`
- Text: `#1C1917`
- Border: `1px solid #E7E5E4`
- Padding: `10px 20px`
- Radius: `8px`
- Hover: background `#F5F5F4`, border `#D6D3D1`

**Semantic Button (e.g., "Close Trade")**
- Background: `transparent`
- Text: semantic text color
- Border: semantic border color
- Hover: fills with semantic tint, shadow appears in semantic color

### Badges / Pills
Badges use tinted backgrounds with matching text — never solid colored blocks.

**Status Badge**
- Background: semantic tint at 0.08 opacity (slightly stronger than card tint)
- Text: semantic text color
- Padding: `2px 8px`
- Radius: `6px`
- Font: Inter 11px weight 600, letter-spacing 0.3px
- Border: none — the tint does the work

**Instrument Tag**
- Background: `#F5F5F4`
- Text: `#57534E`
- Padding: `2px 8px`
- Radius: `6px`
- Font: Inter 11px weight 600, letter-spacing 0.5px, uppercase

### Tables
Tables are the workhorse of the dashboard. They should feel open and readable.

- Header: Inter 12px weight 600, uppercase, letter-spacing 0.5px, color `#A8A29E`, border-bottom `1px solid #E7E5E4`
- Row: padding `16px 12px` (generous vertical padding)
- Row hover: background `#F5F5F4`
- Row border: `1px solid #F5F5F4` (very subtle — rows separated by whisper-thin lines)
- Expandable rows: chevron icon on the right, clicking opens the narrative drill-down inline below the row
- Active/expanded row: semantic tint background, semantic shadow on the expanded content area

### Inputs & Forms
- Background: `#FFFFFF`
- Border: `1px solid #E7E5E4`
- Radius: `8px`
- Padding: `10px 14px`
- Font: Inter 14px weight 400
- Focus: border `1px solid #4F46E5`, ring `0 0 0 3px rgba(79, 70, 229, 0.1)`
- Label: Inter 14px weight 500, color `#1C1917`, margin-bottom `6px`
- Placeholder: color `#A8A29E`

## 5. Layout Principles

### Spacing System
Base unit: **4px**. All spacing values are multiples of 4.

| Token | Value | Usage |
|-------|-------|-------|
| `space-1` | 4px | Tight gaps — between icon and label |
| `space-2` | 8px | Small gaps — between badge elements, inline items |
| `space-3` | 12px | Default gap — between form elements, list items |
| `space-4` | 16px | Standard padding — card inner padding sides |
| `space-5` | 20px | Button padding horizontal |
| `space-6` | 24px | Card padding — the default content inset |
| `space-8` | 32px | Section gap — between cards in a grid |
| `space-10` | 40px | Large section gap — between major page sections |
| `space-12` | 48px | Page top padding |
| `space-16` | 64px | Maximum section separation |

### Grid & Container
- **Max content width**: `1200px`, centered with auto margins
- **Page padding**: `48px` top, `32px` sides (desktop), `20px` sides (mobile)
- **Card grid**: CSS Grid with `gap: 32px`, responsive columns via `auto-fill, minmax(340px, 1fr)`
- **Content width for narrative**: max `720px` — long-form drill-down content should not stretch across the full width. Centered or left-aligned within the expanded area.

### Whitespace Philosophy
- **Magazine, not terminal.** Every element should have enough room to breathe. When in doubt, add more space, not less.
- **Vertical rhythm matters.** Sections are separated by `40–64px`. Cards have `24px` internal padding. Table rows have `16px` vertical padding. These are intentionally generous — they make the data feel curated rather than crammed.
- **Content width controls readability.** Narrative content (drill-downs, LLM reasoning) is constrained to ~720px width. Data content (tables, grids) can use the full width. This dual-width approach mirrors editorial design where body text is narrower than full-bleed images.
- **The bottom 80px is reserved.** The floating pill navigation occupies the bottom of the viewport. All page content must have `padding-bottom: 96px` minimum to prevent the nav from obscuring content.

## 6. Depth & Elevation

Sentinel uses a layered shadow system where **color carries meaning** and **depth carries importance**.

| Level | Name | Shadow Value | Usage |
|-------|------|-------------|-------|
| 0 | Flat | None | Page canvas, inline text, backgrounds |
| 1 | Whisper | `0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02)` | Resting cards, subtle lift |
| 2 | Lifted | `0 4px 16px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.04)` | Hovered cards, active elements |
| 3 | Floating | `0 8px 32px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.04)` | Dropdowns, popovers, floating pill nav |
| 4 | Modal | `0 16px 48px rgba(0,0,0,0.12), 0 4px 16px rgba(0,0,0,0.06)` | Modals, overlays |

### Semantic Shadow Overrides
When a card or element has a trading status, the neutral shadow at Levels 1–2 is **replaced** by the semantic shadow. The second layer (the small, close neutral shadow) remains for grounding.

**Example — Profitable trade card (resting):**
```css
box-shadow: 0 4px 24px rgba(34, 197, 94, 0.15), 0 1px 3px rgba(0, 0, 0, 0.04);
background: rgba(34, 197, 94, 0.04);
border: 1px solid rgba(34, 197, 94, 0.20);
```

**Example — Profitable trade card (hovered):**
```css
box-shadow: 0 8px 32px rgba(34, 197, 94, 0.22), 0 2px 8px rgba(0, 0, 0, 0.04);
transform: translateY(-1px);
```

### Shadow Intensity for Confidence
Signal confidence can be communicated through shadow opacity. A high-confidence signal uses the full 0.15 shadow opacity. A low-confidence signal uses 0.08. This creates a visual "brightness" to confident signals without introducing a new color.

- **High confidence (>70%)**: semantic shadow at 0.15 opacity
- **Medium confidence (40–70%)**: semantic shadow at 0.10 opacity
- **Low confidence (<40%)**: semantic shadow at 0.06 opacity

## 7. Navigation — Bottom Floating Pill Bar

The primary navigation is a floating pill bar fixed to the bottom of the viewport, centered horizontally. This is the most distinctive UI pattern in Sentinel.

### Structure
```
┌──────────────────────────────────────────────────┐
│                   Page Content                     │
│                                                    │
│                                                    │
│                                                    │
│  ┌─────────────────────────────────────────────┐  │ ← Account summary panel (z-index: 40)
│  │  £12,450.00            +3.2% all time       │  │    slides up from behind pill
│  └─────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────┐  │ ← Pill nav (z-index: 50)
│  │  Dashboard   LLM Analysis   Strategies  ⌃   │  │    always visible, floating
│  └─────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

### Pill Bar
- Position: `fixed`, bottom `20px`, centered with `left: 50%; transform: translateX(-50%)`
- Background: `#1C1917` (dark warm charcoal — contrasts the light page)
- Radius: `16px` (pill-shaped)
- Padding: `6px 8px`
- Shadow: Level 3 floating shadow
- Z-index: `50`
- Backdrop: `blur(12px)` with slight transparency (`rgba(28, 25, 23, 0.92)`)
- Max width: `480px` (desktop), full width minus padding on mobile

### Nav Items (inside pill)
- Font: Inter 13px weight 500
- Color (inactive): `rgba(250, 250, 249, 0.5)` — muted inverse text
- Color (active): `#FAFAF9` — bright inverse text
- Active indicator: pill-shaped background `rgba(250, 250, 249, 0.12)` behind active item, radius `10px`
- Padding: `10px 16px`
- Transition: `color 0.15s ease, background 0.15s ease`
- Hover (inactive): color brightens to `rgba(250, 250, 249, 0.75)`

### Chevron / Expand Toggle
- Position: rightmost element in the pill bar
- Icon: chevron-up (Lucide `ChevronUp`), 18px
- Color: `rgba(250, 250, 249, 0.5)`
- Rotation: animates 180° when panel is open
- Transition: `transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)`

### Account Summary Panel (Expandable)
- Position: `fixed`, same horizontal centering as pill, bottom aligned so its bottom edge sits behind the pill
- Z-index: `40` (behind the pill)
- Background: `#292524` (slightly lighter than pill — creates visible layering)
- Radius: `14px 14px 16px 16px` (top corners slightly tighter to complement the pill overlap; bottom corners match the pill's 16px)
- Padding: `16px 24px 20px 24px` (extra bottom padding because pill overlaps)
- Width: matches pill width

**Collapsed state:**
- `transform: translateY(100%)` — fully hidden behind the pill
- `opacity: 0`

**Expanded state:**
- `transform: translateY(-8px)` — slides up, peeking out above the pill by its own height plus a small gap
- `opacity: 1`
- Transition: `transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.2s ease`

**Panel Content:**
- Left side: Account total — Inter 18px weight 600, color `#FAFAF9`, `tabular-nums`
- Right side: Overall P&L percentage — Inter 14px weight 500, colored with semantic text color (green if positive, red if negative)
- Optional center: small sparkline showing recent equity curve

## 8. Narrative Timeline Drill-Down

When a trade row is expanded, it reveals a **vertical timeline** that tells the full story of how that trade came to be. This is the centrepiece of Sentinel's UI — where the editorial design philosophy is most visible.

### Timeline Structure — LLM-Sourced Trade
Maps to trade record fields: `headlines_analysed`, `signal`, `challenge`, `price_context_at_signal`, `bias_at_trade`, `risk_decision`, `entry`, `exit`
```
○─── Headlines Analysed                         ← from trade_record.headlines_analysed
│    4 headlines from Finnhub, 2 from BBC RSS    
│    Each headline + source + relevance reasoning
│                                                
○─── Market Context                              ← from trade_record.price_context_at_signal
│    Price: 1.0852 │ 24h: +0.23% │ Ranging      
│                                                
○─── Signal Generation                           ← from trade_record.signal
│    SHORT EUR/USD │ Confidence: 72%             
│    Reasoning as prose, key factors, risk factors
│                                                
○─── Counter-Argument Challenge                  ← from trade_record.challenge
│    Conviction after challenge: 45%             
│    Recommendation: Reduce size                  
│    Counter-argument + alternative as prose      
│                                                
○─── Directional Bias                            ← from trade_record.bias_at_trade
│    Bearish (0.65) since 06:00 │ Aligned: Yes   
│    5 contributing signals over 4 hours          
│                                                
○─── Risk Decision                               ← from trade_record.risk_decision
│    Approved │ Size: 1 unit │ Risk: £50         
│    SL: 1.0790 │ TP: 1.0943                    
│    All checks passed                            
│                                                
○─── Entry                                       ← from trade_record.entry
│    Price: 1.0852 │ 10:08 UTC                   
│    Broker ref: DEAL-12345                       
│                                                
◌─── Outcome                                     ← from trade_record.exit (pending if open)
     P&L: -£6.20 (-62 pips) │ Stop loss hit     
     Duration: 4h 20m                             
```

### Timeline Structure — Strategy-Sourced Trade
Strategy trades skip the LLM-specific chapters (Headlines, Signal Generation, Challenge). Instead:
```
○─── Strategy: Momentum                          ← from trade_record.signal (source = "strategy:X")
│    Parameters: lookback 12m, short window 1m   
│    Direction: LONG │ Confidence: 65%           
│    Reasoning: 12-month return +3.2%...          
│                                                
○─── Market Context                              ← same as LLM
│                                                
○─── Directional Bias                            ← same as LLM
│                                                
○─── Risk Decision                               ← same as LLM
│                                                
○─── Entry                                       ← same as LLM
│                                                
◌─── Outcome                                     ← same as LLM
```

### Timeline Rail (left side)
- Width: `2px`
- Color (completed section): `#D6D3D1` (neutral stone)
- Color (pending section): `#E7E5E4`, rendered as `2px dashed` (lighter, dashed to signal incompleteness)
- Position: `24px` from left edge of the drill-down container

### Timeline Nodes
**Completed:**
- Size: `12px` diameter circle
- Fill: `#FFFFFF`
- Border: `2px solid #D6D3D1`
- When hovered: border color shifts to semantic color of the trade

**Active / Current:**
- Size: `12px` diameter circle
- Fill: semantic accent color (e.g., `#22C55E` for profitable)
- Border: none
- Pulsing animation: `box-shadow` semantic glow pulses gently (2s cycle, 0.1–0.2 opacity range)

**Pending:**
- Size: `12px` diameter circle
- Fill: `transparent`
- Border: `2px dashed #D6D3D1`

### Chapter Content (right side of timeline)
- Left margin: `48px` from left edge (giving `24px` clearance from the timeline rail)
- Max width: `720px`

**Chapter Heading:**
- Font: Playfair Display 18px weight 500
- Color: `#1C1917` (completed) or `#A8A29E` (pending)
- Margin-bottom: `8px`

**Chapter Body (completed):**
- Font: Inter 14px weight 400, line-height 1.60
- Color: `#57534E`
- Contains rendered markdown — headlines as a clean list, LLM reasoning as prose, risk parameters as a small data table
- Code/JSON blocks: JetBrains Mono 13px, background `#F5F5F4`, radius `6px`, padding `12px 16px`

**Chapter Body (pending):**
- Font: Inter 14px weight 400, italic
- Color: `#A8A29E`
- Text: "Awaiting [stage name]..." or "Trade not yet closed"

### Chapter Spacing
- Gap between chapters: `32px`
- Internal chapter padding: `0 0 32px 0` (bottom padding creates rhythm)
- Divider between chapters: none — the timeline rail provides visual continuity

### Confidence Display (within chapters)
When a chapter includes a confidence score, display it as a horizontal bar:
- Width: `120px`
- Height: `4px`
- Background track: `#E7E5E4`
- Fill: semantic accent color, width proportional to confidence
- Radius: `2px`
- Label: "82% confidence" in Inter 12px weight 500, semantic text color

## 9. Page-Level Specs

These define the layout and composition of each page. They map directly to Session 11 (Dashboard) and Session 12 (LLM Analysis + Strategies) in SESSIONS.md, and the API endpoints in DATA_FLOW.md.

### Navigation Structure (3 pages + settings)

The bottom floating pill nav contains exactly these items:
1. **Dashboard** — `/` — open/closed trades, bias overview, equity curve
2. **LLM Analysis** — `/llm` — pipeline activity, headlines, signals, editable prompts
3. **Strategies** — `/strategies` — strategy cards, signals, recent trades
4. **Settings** (gear icon, no label) — `/settings` — system config, prompt management overflow

### 9.1 Dashboard Page (`/`)

**Data sources:** `GET /api/trades/open`, `GET /api/trades/closed`, `GET /api/trades/{id}`, `GET /api/bias`, `GET /api/equity`

**Layout (top to bottom):**

```
┌──────────────────────────────────────────────────────────────┐
│  [Playfair] Dashboard                                        │
│  [Inter caption] Last updated 2 minutes ago                  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │ EUR/USD │ │ GBP/USD │ │ USD/JPY │ │ ...     │          │
│  │ ▼ Bear  │ │ ▲ Bull  │ │ — Neutral│ │         │          │
│  │ 0.65    │ │ 0.42    │ │ 0.20    │ │         │          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
│  ← scrollable row of 8 bias cards →                         │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  [Playfair] Open Trades                                      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Instrument │ Direction │ Entry │ Current │ P&L │ ... │   │
│  │ EUR/USD    │ SHORT ▼   │ 1.085 │ 1.082   │ +30 │  ⌄  │   │
│  │  └─ [expanded: narrative timeline drill-down]        │   │
│  │ GBP/USD    │ LONG ▲    │ 1.265 │ 1.268   │ +25 │  ⌄  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  [Playfair] Closed Trades                                    │
│                                                              │
│  ┌─ Filters ─────────────────────────────────────────────┐  │
│  │ [All] [Won] [Lost]  │  Pair: [Any ▾]  │  Source: [Any ▾] │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Instrument │ Direction │ P&L    │ Duration │ Source  │   │
│  │ USD/JPY    │ LONG ▲    │ +£12   │ 4h 20m   │ LLM    │   │
│  │ EUR/GBP    │ SHORT ▼   │ -£8    │ 2h 15m   │ Strat  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  [Playfair] Equity                                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  [equity curve line chart — recharts]                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  [96px bottom padding for pill nav]                          │
└──────────────────────────────────────────────────────────────┘
```

#### Bias Cards (horizontal scrollable row)
- Horizontally scrolling row of 8 small cards, one per instrument
- Card size: `140px × 80px`
- Each card shows: instrument name (Inter 12px weight 600, uppercase), direction arrow (▲/▼/—), bias label ("Bullish"/"Bearish"/"Neutral" in Inter 11px), strength as a thin bar (same as confidence bar: 4px height, semantic color fill)
- Semantic shadow + tint applied per card based on direction (bullish = profitable colors, bearish = loss colors, neutral = cooldown colors)
- Scroll container: `overflow-x: auto`, `gap: 12px`, `padding: 4px` (so shadows aren't clipped)
- No scrollbar visible — use `scrollbar-width: none` / `::-webkit-scrollbar { display: none }`

#### Open Trades Table
- Polls `GET /api/trades/open` every 30 seconds
- Columns: Instrument, Direction, Entry Price, Current Price, P&L (pips), P&L (£), Source, Duration, Expand chevron
- Direction cell: "LONG ▲" in semantic profitable text color, "SHORT ▼" in semantic loss text color
- P&L cells: semantic text color (green if positive, red if negative), `tabular-nums`
- Each row is expandable — clicking the chevron or the row itself opens the **narrative timeline drill-down** (Section 8) inline below the row
- Expanded row: the row itself gets the semantic tint background, and the expanded content area below it gets a semantic shadow
- Empty state: "No open trades. The system is monitoring for signals." in Inter 14px italic, `#A8A29E`

#### Closed Trades Table
- Fetches `GET /api/trades/closed` with query params from filters
- Filter bar: pill-shaped toggle buttons for Won/Lost/All, dropdown selects for Instrument and Source
- Filter toggle buttons: active state uses semantic tint + text (Won = profitable, Lost = loss), inactive = ghost button styling
- Columns: Instrument, Direction, P&L (pips), P&L (£), Duration, Source, Closed At, Expand chevron
- Same expandable row behavior as open trades
- Pagination: simple "Load more" button at bottom if >20 trades, not page numbers

#### Equity Curve
- Full-width card containing a Recharts `<AreaChart>` or `<LineChart>`
- Line color: `#4F46E5` (brand indigo)
- Fill below line: `rgba(79, 70, 229, 0.06)` — very subtle
- Axes: Inter 11px, `#A8A29E`
- Grid lines: `#F5F5F4` — whisper-thin
- Tooltip: white card with Level 2 shadow, showing date + equity value
- Height: `240px`
- If no data: "Equity data will appear after the first trade closes." placeholder

### 9.2 LLM Analysis Page (`/llm`)

**Data sources:** `GET /api/llm/activity`, `GET /api/signals/recent`, `GET /api/prompts`, `PUT /api/prompts/{name}`

**Layout (top to bottom):**

```
┌──────────────────────────────────────────────────────────────┐
│  [Playfair] LLM Analysis                                     │
│  [Inter caption] Pipeline activity from the last 12 hours    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  [Playfair] Recent Headlines                                 │
│  [Overline] GROUPED BY SOURCE                                │
│                                                              │
│  Finnhub (12)        BBC (4)        ECB (2)      Fed (1)    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ headline │  │ headline │  │ headline │  │ headline │   │
│  │ headline │  │ headline │  │          │  │          │   │
│  │ headline │  │ headline │  │          │  │          │   │
│  │ +9 more  │  │ +1 more  │  │          │  │          │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  [Playfair] Relevance Assessments                            │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ "ECB signals pause..."  →  EUR/USD, EUR/GBP          │   │
│  │ Reasoning: ECB policy directly affects EUR...         │   │
│  │                                                       │   │
│  │ "US jobs data beats..."  →  USD/JPY, USD/CHF, ...    │   │
│  │ Reasoning: Strong employment supports USD...          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  [Playfair] Generated Signals                                │
│                                                              │
│  ┌─ EUR/USD ──────────────────────────────────────────┐     │
│  │ Direction: SHORT ▼  │  Confidence: ████░░ 72%      │     │
│  │ Reasoning: ECB pause signal from 3 sources...       │     │
│  │ Challenge: Reduce size (conviction 0.45)            │     │
│  └────────────────────────────────────────────────────┘     │
│  [semantic shadow on each signal card]                       │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  [Playfair] Prompts                                          │
│  [Inter caption] Edit the prompts used in each pipeline stage│
│                                                              │
│  ┌─ Relevance Prompt (v3) ──────────────────────────────┐   │
│  │ [editable textarea with mono font]                    │   │
│  │                                                       │   │
│  │                        [Save] [Reset to default]      │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ Signal Prompt (v2) ──────────────────────────────────┐  │
│  │ [editable textarea with mono font]                    │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ Challenge Prompt (v1) ───────────────────────────────┐  │
│  │ [editable textarea with mono font]                    │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  [96px bottom padding]                                       │
└──────────────────────────────────────────────────────────────┘
```

#### Headlines by Source
- Source groups displayed as columns in a responsive grid (`auto-fill, minmax(220px, 1fr)`)
- Each group: source name as overline label (Inter 11px weight 600, uppercase, `#A8A29E`) with count badge
- Headlines as a compact list: headline text in Inter 14px weight 400, truncated to 2 lines, timestamp in Inter 12px caption below
- If >5 headlines per source, show first 5 then a "+N more" link that expands the list
- Clicking a headline could highlight its relevance assessments below (optional progressive enhancement)

#### Relevance Assessments
- List of assessment items, each in a subtle card (standard card, no semantic shadow — these are informational)
- Each item: headline text (Inter 14px weight 500), arrow (→), instrument tags (Instrument Tag styling), reasoning below in Inter 14px weight 400 `#57534E`
- Assessments where no instruments were found: muted style, "No relevant instruments" in `#A8A29E`

#### Generated Signals
- One card per instrument that received a signal
- Card uses semantic shadow based on direction (long = profitable, short = loss, neutral = cooldown)
- Content: instrument as Card Heading (Playfair 22px), direction + confidence bar, reasoning as prose (Inter 14px, max-width 720px), key factors as a subtle inline list, challenge result as a separate sub-section with lighter background (`#F5F5F4`)
- If challenge recommendation was "reject": card uses cooldown/inactive shadow and a strikethrough or "Rejected" badge

#### Editable Prompts
- One expandable section per prompt (Relevance, Signal, Challenge)
- Section header: prompt name in Playfair 18px weight 500 + version badge (Inter 11px)
- Textarea: JetBrains Mono 13px, background `#F5F5F4`, border `1px solid #E7E5E4`, radius `8px`, min-height `200px`, padding `16px`
- Focus state: border `#4F46E5`, ring `0 0 0 3px rgba(79,70,229,0.1)`
- Save button: Primary button style. Reset button: Ghost button style
- After save: brief success indicator (green checkmark, fades after 2s) and version increments

### 9.3 Strategies Page (`/strategies`)

**Data sources:** `GET /api/strategies`, `GET /api/signals/recent?source=strategy`

**Layout (top to bottom):**

```
┌──────────────────────────────────────────────────────────────┐
│  [Playfair] Strategies                                       │
│  [Inter caption] Traditional quantitative trading strategies  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─ Momentum ────────────────────────────────────────────┐  │
│  │  [Playfair heading]  Momentum                         │  │
│  │  [Inter body] Measures the tendency of assets that     │  │
│  │  have been rising to continue rising...                │  │
│  │                                                       │  │
│  │  [Overline] HOW IT WORKS                              │  │
│  │  [Inter body] Compares 12-month return against         │  │
│  │  1-month return. Combined positive signal = long...    │  │
│  │                                                       │  │
│  │  [Overline] PARAMETERS                                │  │
│  │  Lookback: 12 months  │  Short window: 1 month        │  │
│  │                                                       │  │
│  │  [Overline] RECENT SIGNALS                            │  │
│  │  ┌──────────────────────────────────────────────┐     │  │
│  │  │ EUR/USD │ LONG ▲ │ 65% │ 2h ago             │     │  │
│  │  │ USD/JPY │ SHORT ▼│ 58% │ 2h ago             │     │  │
│  │  └──────────────────────────────────────────────┘     │  │
│  │                                                       │  │
│  │  [Overline] TRADES FROM THIS STRATEGY                 │  │
│  │  2 total │ 1 won │ 1 lost │ +£4.20 net                │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─ Carry ───────────────────────────────────────────────┐  │
│  │  [same structure as above]                            │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─ Breakout ────────────────────────────────────────────┐  │
│  │  ...                                                  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─ Mean Reversion ──────────────────────────────────────┐  │
│  │  ...                                                  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  [96px bottom padding]                                       │
└──────────────────────────────────────────────────────────────┘
```

#### Strategy Cards
- One large card per strategy, stacked vertically with `32px` gap
- Standard card styling (white background, `#E7E5E4` border, 10px radius, Level 1 shadow)
- Card heading: Playfair Display 22px weight 600
- Strategy description: Inter 16px weight 400, line-height 1.65, `#57534E` — written for someone reading the university report, not a developer. Should explain what the strategy does and why it might work. Max-width `720px`.
- "How it works" section: separated by overline label, Inter 14px, explains the calculation in plain English
- Parameters: displayed as a row of key-value pairs in a subtle inline layout (Inter 12px weight 500 label, Inter 14px weight 400 value)
- Recent signals: compact mini-table inside the card — Instrument, Direction, Confidence bar, Time ago
- Trade summary: a single line showing total trades, won, lost, net P&L — uses semantic text color for P&L

#### Strategy descriptions
These should be written to be **accessible to a non-technical reader** (university assessor). Each description should cover: what the strategy observes, what pattern it looks for, why this pattern has historically predicted price movement, and what its weaknesses are. This is part of the "system explains itself" editorial philosophy.

### 9.4 Settings Page (`/settings`)

Minimal page — not a primary workflow, but needed for configuration.

- System status: pipeline last run time, next scheduled run, connection status for Capital.com / Groq / Finnhub
- Risk parameters: read-only display of current config values (max positions, daily loss limit, correlation groups)
- Links: GitHub repo, API docs

Standard card layout, no semantic shadows. Inter throughout — no Playfair needed on this page (it's purely functional).

## 10. Do's and Don'ts

### Do
- Use Playfair Display **only** for headings and narrative chapter titles — it should feel special, not ubiquitous
- Use Inter for all functional UI — tables, buttons, nav, labels, form inputs, data
- Communicate trade status through colored shadows and subtle tints, not solid background colors
- Keep card backgrounds white or near-white — let the shadow carry the semantic color
- Use generous padding (24px+ on cards, 16px on table rows) — the dashboard should breathe
- Constrain narrative/reading content to ~720px width for comfortable reading
- Use `tabular-nums` for any numeric data in tables or metrics
- Layer shadows: semantic colored shadow (far, diffused) + neutral grounding shadow (close, tight)
- Keep the bottom 96px of the page clear for the floating pill nav
- Animate state transitions — shadow color changes, expand/collapse, hover lifts — with ease curves at 0.15–0.3s

### Don't
- Don't use solid green/red/amber block backgrounds for status — use tints at ≤0.04 opacity and shadows at ~0.15 opacity
- Don't use Playfair Display in tables, buttons, navigation, or form inputs — it's reserved for editorial moments
- Don't use pure black (`#000000`) for text — always use the warm charcoal (`#1C1917`) or secondary (`#57534E`)
- Don't use pure white (`#FFFFFF`) for the page background — use `#FAFAF9` warm off-white for the canvas
- Don't pack information densely — when in doubt, increase spacing
- Don't use sidebar navigation — the floating pill bar at the bottom is the navigation pattern
- Don't use border-radius larger than `16px` except for the pill nav itself
- Don't use font weights above 700 anywhere — the design speaks through space and shadow, not boldness
- Don't skip the semantic shadow on trade-related cards — every trade element should glow its status
- Don't use colored text as the only status indicator — always pair with shadow/tint for accessibility

## 11. Responsive Behavior

### Breakpoints
| Name | Width | Key Changes |
|------|-------|-------------|
| Mobile | <640px | Single column, pill nav goes full-width (minus 16px padding), page title reduces to 28px |
| Tablet | 640–1024px | Two-column card grid, pill nav at 420px width |
| Desktop | 1024–1280px | Full layout, pill nav at 480px, narrative content at 720px max |
| Large Desktop | >1280px | Centered content with generous side margins, max container 1200px |

### Typography Scaling
| Role | Desktop | Mobile |
|------|---------|--------|
| Page Title | 36px Playfair | 28px Playfair |
| Section Heading | 28px Playfair | 22px Playfair |
| Card Heading | 22px Playfair | 18px Playfair |
| Body Large | 16px Inter | 16px Inter (unchanged) |
| Body | 14px Inter | 14px Inter (unchanged) |

### Mobile Adaptations
- **Pill nav**: Expands to `calc(100% - 32px)` width, bottom `12px`
- **Account summary panel**: Same width as pill, content stacks vertically (amount on top, P&L below)
- **Card grid**: Single column, cards stretch full width
- **Tables**: Horizontal scroll with sticky first column (instrument name)
- **Timeline drill-down**: Timeline rail moves to `12px` from left, chapter content margin reduces to `36px`
- **Page padding**: `20px` sides, `32px` top

### Touch Considerations
- All interactive elements have minimum `44px` touch target
- Pill nav items have `44px` minimum height
- Table rows have `52px` minimum height on touch devices
- Chevron toggle has `44px` tap area

## 12. Agent Prompt Guide

When generating UI for Forex Sentinel, follow these rules for consistent output.

### Quick Color Reference
- Page background: `#FAFAF9`
- Card background: `#FFFFFF`
- Heading text: `#1C1917`
- Body text: `#57534E`
- Muted text: `#A8A29E`
- Primary accent: `#4F46E5`
- Border: `#E7E5E4`
- Profitable: shadow `rgba(34,197,94,0.15)`, tint `rgba(34,197,94,0.04)`, text `#15803D`
- Loss: shadow `rgba(239,68,68,0.15)`, tint `rgba(239,68,68,0.04)`, text `#DC2626`
- Pending: shadow `rgba(245,158,11,0.15)`, tint `rgba(245,158,11,0.04)`, text `#B45309`
- Info: shadow `rgba(99,102,241,0.15)`, tint `rgba(99,102,241,0.04)`, text `#4F46E5`
- Cooldown: shadow `rgba(148,163,184,0.15)`, tint `rgba(148,163,184,0.04)`, text `#64748B`

### Quick Typography Reference
- Page Title: Playfair Display 36px / 700 / -0.5px
- Section Heading: Playfair Display 28px / 600 / -0.3px
- Card Heading: Playfair Display 22px / 600 / -0.2px
- Chapter Title: Playfair Display 18px / 500
- Body Large: Inter 16px / 400 / line-height 1.65
- Body: Inter 14px / 400 / line-height 1.60
- Label: Inter 14px / 500
- Button: Inter 14px / 500 / letter-spacing 0.1px
- Caption: Inter 12px / 400
- Badge: Inter 11px / 600 / letter-spacing 0.3px
- Data: Inter 14px / 500 / tabular-nums
- Data Large: Inter 24px / 600 / -0.3px
- Mono: JetBrains Mono 13px / 400

### Quick Radius Reference
- Buttons: `8px`
- Cards: `10px`
- Badges: `6px`
- Pill Nav: `16px`
- Confidence bars, micro elements: `2px`

### Example Component Prompts

**Trade Card:**
"Create a card with white background, 1px solid rgba(34,197,94,0.20) border, 10px radius. Shadow: 0 4px 24px rgba(34,197,94,0.15), 0 1px 3px rgba(0,0,0,0.04). Background tint: rgba(34,197,94,0.04). Title in Playfair Display 22px weight 600, color #1C1917. Body in Inter 14px weight 400, color #57534E. Status badge: rgba(34,197,94,0.08) background, #15803D text, Inter 11px weight 600, 6px radius."

**Page Header:**
"Create a page header with Playfair Display 36px weight 700, color #1C1917, letter-spacing -0.5px. Subtitle in Inter 16px weight 400, color #57534E, line-height 1.65. Below, an overline label in Inter 11px weight 600, color #A8A29E, letter-spacing 0.8px, uppercase."

**Bottom Pill Nav:**
"Create a fixed bottom navigation bar: background rgba(28,25,23,0.92), backdrop-filter blur(12px), border-radius 16px, padding 6px 8px, centered at bottom 20px. Nav items in Inter 13px weight 500. Active item has rgba(250,250,249,0.12) pill background with 10px radius and white text. Inactive items at 50% opacity. Chevron-up icon on the right."

**Timeline Chapter (Completed):**
"Vertical timeline node: 12px circle, white fill, 2px solid #D6D3D1 border. Chapter heading in Playfair Display 18px weight 500, color #1C1917. Body in Inter 14px weight 400, color #57534E, line-height 1.60, max-width 720px."

**Timeline Chapter (Pending):**
"Vertical timeline node: 12px circle, transparent fill, 2px dashed #D6D3D1 border. Chapter heading in Playfair Display 18px weight 500, color #A8A29E. Body in Inter 14px italic weight 400, color #A8A29E: 'Awaiting signal generation...'"

### Iteration Guide
1. Always check: is this a heading/narrative moment (→ Playfair Display) or a functional/data moment (→ Inter)?
2. Always check: does this element have a trading status? If yes, apply the semantic shadow + tint + border triple.
3. Cards should never have colored backgrounds beyond the whisper-level tint (0.04 opacity max).
4. The floating pill nav must be accounted for — all page content needs 96px bottom padding.
5. When displaying numeric data, always use `font-variant-numeric: tabular-nums`.
6. Shadows transition on hover — resting state at ~0.15 opacity, hover at ~0.22, with 0.2s ease transition.
7. Narrative content (LLM reasoning, trade stories) is constrained to 720px max-width for readability.
8. The page background is NEVER pure white — always `#FAFAF9`.
9. Text is NEVER pure black — always `#1C1917` or lighter.
10. Border-radius defaults: 8px buttons, 10px cards, 6px badges, 16px pill nav.
