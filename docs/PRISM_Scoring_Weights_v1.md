# PRISM Scoring Weights — v1.0
## Complete Reference: Every Weight, Its Purpose, and Its Rationale

**Project:** PRISM (Predictive Revenue Intelligence & Signal Mapping)  
**Author:** Joseph Sherman  
**Version:** 1.0 — Initial hypothesis weights (pre-calibration)  
**Date:** February 2026  

---

## How Scoring Works

PRISM produces a **composite priority score** (0.0-1.0) for each target account by combining three independent sub-scores:

1. **ICP Fit Score** — "Is this the right company?" (static, changes slowly)
2. **Buying Readiness Score** — "Are they ready to buy right now?" (dynamic, changes weekly)
3. **Timing Score** — "Is the window open right now?" (volatile, changes daily)

Each sub-score is calculated from weighted components. The composite score determines the account's **priority tier**, which dictates the recommended action.

**Critical note:** These are v1 hypothesis weights. They represent informed starting assumptions based on B2B SaaS sales patterns, GTM research, and direct account management experience. After accumulating 30+ deal outcomes, the feedback loop recalibrates these weights based on actual conversion data. The initial weights are deliberately designed to slightly over-qualify (more false positives than false negatives) because a missed opportunity is more expensive than a wasted outreach.

---

## ICP Fit Score

### What It Measures
Whether the company structurally matches the profile of an ideal customer — independent of whether they're currently in a buying cycle. This score changes slowly (quarterly or less) because it's based on firmographic and technographic data, not behavioral signals.

### Buyer Perspective
The ICP score is designed from the **founder/C-suite decision-making frame**. At Series A-C companies, purchase decisions for finance infrastructure are driven by financial pressure and growth scaling pain, not by technical architecture preferences. The founder asks: "Can we afford this, will it save us money, and are we at the stage where we need it?" The tech stack matters as an indicator of the financial problem, not as the problem itself.

### Component Weights

```python
"icp": {
    "funding_stage_fit": 0.25,
    "growth_rate":       0.20,
    "tech_stack_fit":    0.20,
    "headcount_fit":     0.15,
    "industry_fit":      0.10,
    "geo_fit":           0.10,
}
```

### Component Details

#### funding_stage_fit: 0.25 (HIGHEST)

**What it measures:** Whether the company's funding stage indicates both the budget to purchase and the financial pressure that motivates purchase.

**Why it's highest:** This is the gating factor. A company cannot buy enterprise software without budget, and funding stage is the strongest proxy for available budget at private companies. But it's not just about having money — it's about the *stage-specific financial pressure* that creates urgency:

| Stage | Budget Available | Financial Pressure | Buying Probability |
|-------|-----------------|-------------------|-------------------|
| Pre-seed/Seed | Very low | Survival mode — spreadsheets are fine | Very low |
| Series A | Moderate | Starting to feel pain but often defer | Low-Medium |
| Series B | High | Board expects professionalization of finance | **HIGH** |
| Series C | High | Due diligence preparation, audit readiness critical | **HIGH** |
| Series D+ | Very high | Usually already committed to a stack | Medium (displacement only) |
| Public | Very high | Procurement process adds 6+ months | Low (different motion entirely) |

**Sweet spot:** Series B and C companies. They have money (from the raise), financial pressure (board expectations, audit prep, Series C due diligence), and haven't yet locked into enterprise tooling.

**Scoring logic:**
- Series B: 1.0
- Series C: 0.95
- Series A (>$5M raised): 0.70
- Series D: 0.50 (likely has existing solution — displacement play required)
- Seed (>$2M): 0.30
- Pre-seed / Bootstrapped: 0.10
- Public: 0.20 (different sales motion, long cycle)

#### growth_rate: 0.20

**What it measures:** How fast the company is scaling, measured by headcount growth rate (most reliably detectable) and/or revenue growth signals.

**Why it's weighted 0.20:** Growth is the *engine* of financial pain in scaling companies. A company growing 50% YoY is hitting every scaling wall simultaneously — their processes that worked at 50 people break at 100, their manual workarounds that took 2 hours now take 2 days, their QuickBooks account that handled 50 transactions/month now handles 5,000. Growth doesn't just indicate potential — it actively creates the urgency that makes companies buy.

A flat company at the same headcount and funding stage has already adapted to their current tooling. The pain isn't increasing. They'll buy eventually but there's no urgency, which means long sales cycles and frequent "not right now" outcomes.

**Scoring logic:**
- Headcount growth >50% YoY: 1.0
- 30-50% YoY: 0.85
- 15-30% YoY: 0.60
- 5-15% YoY: 0.35
- Flat or declining: 0.10

**Data sources:** LinkedIn headcount (compare current vs. 6-12 months ago), job posting volume, Crunchbase employee data, "We're hiring!" content frequency.

#### tech_stack_fit: 0.20

**What it measures:** Whether the company's current technology stack indicates they're in the right position for the product — specifically, whether their current finance/accounting tooling creates pain that the product solves.

**Why it's weighted 0.20 (not higher):** The tech stack is the *mechanism* of the pain, not the pain itself. A founder doesn't say "our API architecture is inadequate" — they say "our month-end close takes 3 weeks and we can't get clean numbers to the board." The tech stack tells us whether the pain exists and how acute it is, but the decision to buy is driven by financial pressure (funding stage) and scaling urgency (growth rate).

That said, tech stack is the strongest *fit* indicator. A company on QuickBooks at 200 employees is almost certainly in pain. A company on NetSuite has either solved the problem or is locked in. A company on SAP/Oracle is in a completely different buying motion.

**Scoring logic:**
- QuickBooks/Xero + >100 employees: 1.0 (maximum pain)
- QuickBooks/Xero + 50-100 employees: 0.85
- Spreadsheets/manual (detected via job postings): 0.90 (greenfield opportunity)
- Early NetSuite (detected via migration signals): 0.70 (may be dissatisfied)
- Established NetSuite: 0.30 (displacement required)
- SAP/Oracle: 0.10 (enterprise motion, different ICP)
- Unknown: 0.50 (neutral — need more data)

**Migration signals (boost):** If job postings or content reference evaluating new tools, migrating, or switching — add 0.20 (capped at 1.0). These are active transition signals regardless of current stack.

**Data sources:** BuiltWith, job postings mentioning specific tools, blog/LinkedIn content referencing tooling, careers page tech stack descriptions.

#### headcount_fit: 0.15

**What it measures:** Whether the company is in the complexity zone where the product becomes necessary — not too small to need it, not too large to have already solved it.

**Why it's weighted 0.15:** Headcount is a threshold indicator, not a gradient. Below ~30 employees, the CEO or a bookkeeper handles finance in a spreadsheet and there's no pain worth solving with software. Above ~500, they typically have a mature finance team with established tooling. The 50-500 range is where pain exists, budget is available, and decisions can happen fast.

Within the sweet spot, the exact headcount matters less than other factors. A 150-person company and a 300-person company both feel scaling pain — the 300-person company's pain is more acute but they may also have more established solutions. Headcount is necessary but not sufficient.

**Scoring logic:**
- 100-300 employees: 1.0 (peak zone)
- 50-100 employees: 0.85
- 300-500 employees: 0.75
- 30-50 employees: 0.40 (may be early)
- 500-1000 employees: 0.35 (likely has solution)
- <30 employees: 0.10
- >1000 employees: 0.15 (enterprise motion)

**Data sources:** LinkedIn, Crunchbase, company About page.

#### industry_fit: 0.10

**What it measures:** Whether the company's industry creates specific accounting/finance complexity that the product addresses.

**Why it's weighted 0.10 (low):** For a horizontal fintech product (accounting automation), industry matters less than stage, stack, and growth. A SaaS company and an e-commerce company at the same stage with the same stack have similar finance pain. However, some industries have specific complexity multipliers:

**Scoring logic:**
- SaaS (revenue recognition complexity — ASC 606): 1.0
- Fintech (regulatory + transactional volume): 0.95
- E-commerce / Marketplace (multi-entity, high transaction volume): 0.90
- B2B Services (project-based revenue recognition): 0.75
- Healthcare / Life Sciences (compliance complexity): 0.70
- All other tech: 0.60
- Non-tech: 0.30

**Data sources:** Crunchbase industry tags, company description, product categories.

#### geo_fit: 0.10

**What it measures:** Whether the company's location aligns with the sales motion (time zones, in-person capability, legal jurisdiction, market norms).

**Why it's weighted 0.10 (lowest):** Geography has minimal impact on buying probability for a remote-first SaaS product. It matters for: sales motion logistics (can you do an on-site if needed?), legal/regulatory context (US GAAP vs. IFRS), and market expectations. But a perfect-fit company in Austin is not meaningfully less likely to buy than one in San Francisco.

**Scoring logic:**
- US — Major tech hubs (SF, NYC, Austin, Seattle, Boston): 1.0
- US — Other: 0.90
- Canada: 0.80
- UK / Western Europe: 0.60 (IFRS complexity, GDPR considerations)
- Other English-speaking: 0.50
- Non-English-speaking: 0.30

**Data sources:** Crunchbase HQ location, LinkedIn company location.

---

## Buying Readiness Score

### What It Measures
Whether the company is psychologically and organizationally prepared to make a purchase decision right now. This is the **dynamic** score — it changes as new content is published, leaders are hired, and organizational language shifts. This is where PRISM's Content Intelligence layer does its primary work.

### Why It's the Heaviest Score in the Composite
ICP Fit tells you the company *could* buy. Timing tells you the window *might* be open. But Buying Readiness tells you whether the humans inside the organization have reached the psychological state where they will actually commit to a decision. A perfect-ICP company with fresh trigger events but low buying readiness will stall, defer, or say "not right now." A slightly off-ICP company with high buying readiness and strong timing will close fast.

The Content Intelligence layer exists primarily to power this score. Standard enrichment tools can approximate ICP fit and basic timing. No one else measures buying readiness at this depth.

### Component Weights

```python
"readiness": {
    "journey_position":          0.20,
    "pain_coherence":            0.20,
    "new_leader_signal":         0.20,
    "org_stress_indicators":     0.15,
    "solution_sophistication":   0.15,
    "active_evaluation_signals": 0.10,
}
```

### Component Details

#### journey_position: 0.20

**What it measures:** Where the organization sits on the buying journey continuum (0.0-1.0), derived from longitudinal content analysis. This maps from the RPMS narrative phase framework adapted to commercial context.

**Why it's weighted 0.20:** Journey position is the single most descriptive state variable. It tells you not just *whether* they have pain, but how far they've progressed from feeling pain to being ready to act on it. It directly determines which sales play to run — you don't pitch a demo to someone still in "status quo."

**Journey stages and scoring:**

| Position | Label | Description | Score |
|----------|-------|-------------|-------|
| 0.00-0.15 | STATUS QUO | No evidence of problem awareness. Content is about growth, product, culture — no finance pain signals. | 0.10 |
| 0.15-0.25 | PROBLEM AWARE | Beginning to feel pain. Occasional mentions of operational challenges. Language is frustrated but not solution-seeking. | 0.30 |
| 0.25-0.40 | SOLUTION EXPLORING | Actively researching. Job postings for finance roles, blog content about "improving operations," LinkedIn posts asking for recommendations. | 0.55 |
| 0.40-0.60 | ACTIVE EVALUATION | Something broke or a deadline is looming. Language shifts to urgent, specific, decisive. Vendor comparison signals. Direct references to evaluating tools. | 0.80 |
| 0.60-0.80 | DECISION READY | Outcome-focused language. "When we implement..." not "if we implement..." Internal requirements defined. Budget conversations happening. | 1.00 |
| 0.80-1.00 | POST-DECISION | Already bought something. In implementation. Relevant for expansion or competitive displacement on adjacent products only. | 0.40 |

**Velocity modifier:** If journey position has advanced 0.15+ in the last 60 days (detectable via content trajectory analysis), add 0.15 to score (capped at 1.0). Acceleration is itself a buying signal.

**Source:** Content Intelligence Layer — Stage 2 cross-corpus synthesis. This is a derived metric, not directly observable. It's the output of analyzing the *trajectory* of language across a content corpus over time.

#### pain_coherence: 0.20

**What it measures:** Whether the organization's pain signals are focused around a specific, defined problem or scattered across many unrelated complaints. Scored 0.0 (completely scattered) to 1.0 (laser-focused pain around a single defined problem).

**Why it's weighted 0.20 (tied for highest):** This is PRISM's most novel signal and arguably the most predictive Content Intelligence metric. 

The insight: companies that *know what's broken* buy solutions. Companies that feel vaguely bad don't. A company where the VP Finance, the blog, and the job postings are all orbiting the same pain point (month-end close, revenue recognition, audit readiness) has crystallized their problem. They're past the "something's wrong" phase and into "we know what we need to fix." That crystallization is what unlocks budget allocation, vendor evaluation, and purchase decisions.

Conversely, a company complaining about 12 different things — hiring, culture, product quality, customer support, AND finance operations — has diffuse pain. They might buy something eventually, but the sales cycle will be long, discovery-heavy, and prone to stalling because they haven't prioritized.

**Scoring logic:**
- 1 dominant pain theme across 60%+ of content with finance relevance: 1.0
- 1-2 related themes across 40-60% of content: 0.80
- 2-3 themes with moderate coherence: 0.55
- Scattered complaints, no dominant theme: 0.30
- No detectable pain signals: 0.10

**Source:** Content Intelligence Layer — Stage 2 cross-corpus synthesis. Calculated by analyzing thematic clustering across all content items, weighted by recency and source authority.

#### new_leader_signal: 0.20

**What it measures:** Whether a key decision-maker in a relevant role (VP Finance, CFO, Controller) is new in their position (typically <6 months).

**Why it's weighted 0.20 (tied for highest):** This is the strongest single discrete signal in B2B SaaS sales, supported by extensive industry data and direct experience. A new finance leader creates a perfect buying storm:

1. **They were hired to fix something.** Companies don't hire a VP Finance because everything is running smoothly. The hire itself is evidence of recognized pain.
2. **They have a mandate to make changes.** The board/CEO gave them budget and authority. This is their window to act.
3. **They want to put their stamp on the function.** New leaders adopt new tools — it's how they establish credibility and demonstrate impact.
4. **They haven't committed to a toolset yet.** Everything is open for evaluation in the first 6 months.
5. **They bring knowledge from their previous company.** If they used a competitor at their last job, they're a warm lead or a competitive displacement opportunity. If they used your product, they're a potential champion.

The critical insight: the buying window for a new leader is **30-180 days from start date**. Before 30 days, they're still learning. After 180 days, they've likely committed to a direction. The sweet spot is 60-120 days — they understand the problems, have political capital to make changes, and haven't yet locked in decisions.

**Scoring logic:**
- New leader (30-120 days in role) in VP Finance/Controller: 1.0
- New leader (30-120 days) in CFO role: 0.95
- New leader (<30 days) — too early: 0.60
- New leader (120-180 days) — window narrowing: 0.70
- New leader (180-365 days) — may have already decided: 0.35
- No new leader detected: 0.00 (this component contributes nothing — which is fine, other components carry the score)

**Important:** This is a binary signal with temporal decay, not a gradient. Either there's a new leader or there isn't. When present, it's one of the strongest signals in the system. When absent, the account can still score well on other readiness components.

**Source:** LinkedIn (tenure detection), Apollo (title + start date), company announcements, press releases.

#### org_stress_indicators: 0.15

**What it measures:** Behavioral and linguistic indicators of organizational stress that predict increased likelihood of purchasing decisions. This captures the *velocity* of pain — not just "do they hurt?" but "is it getting worse?"

**Why it's weighted 0.15:** Organizational stress is a *modifier* rather than a primary signal. Moderate stress with clear pain coherence is a strong buying state. High stress without pain coherence means chaos — they might buy, but they might also churn quickly or make a bad decision. The stress signal is most valuable when it *corroborates* other readiness indicators.

**What constitutes organizational stress (detectable from public content):**

1. **Language compression:** Blog posts getting shorter, more operational, less aspirational over time. Shift from thought-leadership to problem-solving tone.
2. **Publication frequency changes:** Either increasing (urgency to communicate) or decreasing (too busy to publish — also a signal).
3. **Defensive language:** Framing content around "challenges" rather than "opportunities." More hedging language.
4. **Urgency markers:** Words like "immediately," "critical," "before [deadline]," "can't afford to wait."
5. **Internal focus shift:** Content pivoting from external-facing (customer stories, market positioning) to internal-facing (process improvement, team updates, operational changes).
6. **Glassdoor deterioration:** Declining ratings, reviews mentioning overwork, mentions of "growing pains" or "scaling challenges."

**Scoring logic:**
- Multiple stress indicators detected, escalating over time: 1.0
- Clear stress signals present, stable: 0.70
- Mild stress indicators: 0.40
- No detectable stress: 0.10
- Positive signals (confidence, expansion language): 0.05 (not zero — confident companies still buy, just different play)

**Source:** Content Intelligence Layer — Stage 2 cross-corpus synthesis, specifically the organizational stress indicators analysis. Also incorporates Glassdoor trend data when available.

#### solution_sophistication: 0.15

**What it measures:** How articulate the organization (and specifically the likely champion) is about their own problem and what a solution would look like.

**Why it's weighted 0.15:** Solution sophistication directly predicts sales cycle length and conversion methodology. A highly sophisticated buyer has already done the education work — they know what they need, they can articulate requirements, and they can drive an internal evaluation process. An unsophisticated buyer needs nurturing, education, and a longer runway.

Both convert, but at very different rates and with very different plays. The weight reflects that sophistication *improves* conversion probability but isn't required for it.

**Sophistication levels:**

| Level | Language Pattern | Sales Implication | Score |
|-------|-----------------|-------------------|-------|
| UNAWARE | No problem-related language | Not a current lead — nurture | 0.05 |
| FRUSTRATED | "This is painful" / "We need to fix this" | Needs education on solutions | 0.30 |
| ARTICULATE | "We need X capability with Y integration" | Shorten discovery, go direct | 0.65 |
| EVALUATING | "We're comparing A vs B on these criteria" | Match their evaluation framework | 0.85 |
| DECIDED | "We've chosen our approach, now implementing" | Expansion/displacement only | 1.00 |

**Source:** Content Intelligence Layer — Stage 3 person-level analysis (champion's LinkedIn posts, blog contributions) and Stage 2 cross-corpus synthesis (job descriptions with specific tool/capability requirements).

#### active_evaluation_signals: 0.10

**What it measures:** Direct evidence that the company is currently evaluating vendors or solutions in the relevant category.

**Why it's weighted 0.10 (lowest readiness component):** Despite seeming like the most "obvious" buying signal, active evaluation signals get the lowest weight for two important reasons:

1. **By the time you detect them, you're often late.** If they're already on G2 comparing tools, they may have been in vendor conversations for weeks. You're entering a competitive process rather than creating one.
2. **Highest false positive rate.** Pricing page visits could be a competitor, journalist, existing customer, or employee checking their own plan. G2 browsing could be casual research. Job postings mentioning specific tools could be describing existing stack, not desired future state.

Active evaluation signals are most valuable as *corroborating evidence* for other readiness indicators, not as standalone signals.

**What counts:**
- G2/Capterra review activity for competing products (if detectable)
- Pricing page visits (if website intent data available)
- Job postings specifying the product category as a required skill
- Content explicitly mentioning vendor evaluation
- RFP signals (rare in SMB, more common in enterprise)

**Scoring logic:**
- Multiple direct evaluation signals: 1.0
- Single strong evaluation signal (vendor comparison content): 0.75
- Indirect signals (job posting mentions category): 0.45
- No evaluation signals detected: 0.00

**Source:** Third-party intent data (Bombora, G2 — if integrated), website intent (if available), job postings, content analysis.

---

## Timing Score

### What It Measures
Whether the current moment is the right moment to reach out — independent of company fit and buying readiness. A company could be a perfect fit with high readiness, but if their last trigger event was 8 months ago and there's no fresh urgency, the window may have closed.

### Why Timing Matters Separately
Timing captures **signal freshness** and **urgency concentration**. It answers: "Even if everything else looks good, is there a reason to act *this week* rather than next quarter?" In B2B sales, timing is often the difference between a "let's schedule a call" and a "interesting, let's revisit in Q3."

### Component Weights

```python
"timing": {
    "trigger_event_recency": 0.35,
    "signal_freshness_avg":  0.25,
    "urgency_indicators":    0.25,
    "window_closing_signals": 0.15,
}
```

### Component Details

#### trigger_event_recency: 0.35 (HIGHEST)

**What it measures:** The freshness of the most recent discrete trigger event — a specific, identifiable event that opened or widened a buying window.

**Why it's highest:** The single most recent trigger event is the strongest timing signal. Sales is about momentum, and a fresh trigger event creates momentum. A funding round 3 weeks ago means money just hit the bank and the CEO is planning where to invest it. A VP Finance hired 2 months ago means they're deep in assessment mode. The recency of the trigger matters more than the average freshness of all signals because it represents the *current* energy state of the opportunity.

**Trigger event types and peak timing:**

| Trigger Event | Peak Window | Half-Life | Max Relevance |
|---------------|-------------|-----------|---------------|
| Funding round closed | 30-60 days | 90 days | 180 days |
| New executive in finance role | 60-120 days | 150 days | 365 days |
| Job posting for finance roles | 7-30 days | 45 days | 90 days |
| Tech stack change detected | 7-14 days | 30 days | 60 days |
| Earnings call mentioning relevant pain | 14-30 days | 45 days | 90 days |
| Competitor contract likely up for renewal | 30-60 days | 60 days | 120 days |
| Regulatory deadline approaching | 30-60 days before | N/A | Deadline date |

**Scoring logic:** Uses the signal decay function. Score = decay_weight of the most recent trigger event.

**Source:** Crunchbase (funding), LinkedIn (leadership changes), job boards (hiring), BuiltWith (tech changes), content analysis (earnings/press).

#### signal_freshness_avg: 0.25

**What it measures:** The mean decay-weighted freshness across ALL detected signals for the account. This captures signal *concentration* — whether there's a cluster of recent activity or signals spread thinly over a long period.

**Why it's weighted 0.25:** While the most recent trigger event matters most, the *density* of recent signals provides important context. A company with 5 signals all from the last 30 days is showing concentrated activity — something is happening right now. A company with 5 signals spread across 12 months has ongoing mild indicators but no concentrated momentum.

**Scoring logic:** Average the decay weights of all signals. If all signals are fresh (last 30 days), average is high. If signals are spread out, average is lower.

- Average decay weight >0.80: 1.0 (concentrated recent activity)
- 0.60-0.80: 0.80
- 0.40-0.60: 0.55
- 0.20-0.40: 0.30
- <0.20: 0.10 (stale signals)

**Source:** Calculated from all signals in the signal table for the account.

#### urgency_indicators: 0.25

**What it measures:** Language-based urgency signals detected by the Content Intelligence layer — words, phrases, and patterns that indicate time pressure.

**Why it's weighted 0.25 (equal to signal freshness):** Urgency indicators capture something that structured data cannot — the *felt* time pressure inside the organization. A company might have a funding round 60 days ago (moderate trigger) but their blog just published "Why We're Rebuilding Our Finance Stack Before Series C" (extreme urgency). The language tells you more about the actual decision timeline than the event calendar does.

**What constitutes urgency:**
- Deadline language: "before Q3," "by year-end," "ahead of our audit"
- Urgency words: "immediately," "critical," "can't wait," "overdue"
- Problem escalation: Pain described as "growing," "worsening," "unsustainable"
- Hiring urgency: "urgent hire," "immediate start," multiple simultaneous finance postings
- Competitive urgency: "falling behind," "competitors are already"

**Scoring logic:**
- Multiple urgency indicators across multiple content sources: 1.0
- Clear urgency in at least one authoritative source (leadership post, blog): 0.75
- Mild urgency signals: 0.40
- No urgency detected: 0.10

**Source:** Content Intelligence Layer — extracted from Stage 1 per-item tonal analysis and Stage 2 trajectory analysis.

#### window_closing_signals: 0.15

**What it measures:** Evidence that the buying window is about to close — either because they're about to commit to a competitor, because a deadline is passing, or because the internal momentum is fading.

**Why it's weighted 0.15 (lowest timing component):** Window closing signals are the rarest and hardest to detect, but when present, they're critically important. They don't increase the opportunity — they create urgency to *act now or lose it*. The lower weight reflects their rarity, not their importance. When detected, they should trigger immediate escalation regardless of composite score.

**What constitutes window closing:**
- Job posting for "[Competitor Product] Administrator" — they've chosen
- Blog announcing a new finance tool implementation — decision made
- Leadership LinkedIn post about "our new finance stack" — done deal
- Significant time elapsed since last trigger (>6 months) — momentum died
- Champion departed the company — internal advocate lost
- RFP deadline passed — evaluation window closed

**Scoring logic:**
- Window actively closing (competitor chosen, implementation announced): 0.0 (opportunity is closing — flag as URGENT: LAST CHANCE)
- Early window-close warning (champion activity decreasing, momentum stalling): 0.40
- No window-closing signals: 1.0 (window appears open)

**Important:** Note the inverted scoring. The *absence* of window-closing signals is good (score = 1.0). The *presence* of window-closing signals is bad (score decreases). This is different from other components where presence = good.

**Special behavior:** When window_closing_signals score drops below 0.30, trigger an URGENT flag on the account regardless of composite score. This flag tells the AE: "Act now or write this off."

**Source:** Content analysis, job posting monitoring, LinkedIn tracking, BuiltWith tech stack changes.

---

## Composite Score Calculation

### Formula

```python
composite_score = (
    icp_fit_score      * 0.25 +
    readiness_score     * 0.50 +
    timing_score        * 0.25
)
```

### Weight Rationale

```python
"composite": {
    "icp_fit":          0.25,
    "buying_readiness":  0.50,  # DOMINANT
    "timing":           0.25,
}
```

**Buying readiness at 0.50 (dominant):** This is deliberately the heaviest weight because it represents PRISM's primary analytical contribution. ICP fit can be approximated by any enrichment tool. Timing signals are available from intent data providers. But the depth of buying readiness analysis — journey position, pain coherence, organizational stress indicators, person-level language analysis — is what PRISM uniquely provides. Weighting it at 0.50 means the system's output is driven by its proprietary intelligence layer, not by data anyone can buy.

It's also the most predictive component. In practice, the company's psychological and organizational state determines whether a deal closes more than any other factor. The right company at the wrong stage of readiness produces stalled deals, extended timelines, and "we'll revisit next quarter" outcomes. The *ready* company — even with slightly off-ICP characteristics — produces fast closes.

**ICP fit at 0.25:** Necessary but not sufficient. Ensures we're targeting companies that could plausibly be customers, but doesn't dominate the score. A company with 0.90 ICP fit and 0.30 readiness should score lower than a company with 0.60 ICP fit and 0.90 readiness.

**Timing at 0.25:** The urgency multiplier. Ensures fresh signals elevate accounts and stale signals suppress them. Equal weight with ICP fit because timing is just as important as fit — but both are subordinate to readiness.

---

## Priority Tier Thresholds

```python
"tiers": {
    "tier_1": 0.70,   # IMMEDIATE ACTION
    "tier_2": 0.45,   # ACTIVE OUTREACH
    "tier_3": 0.25,   # MONITOR & NURTURE
    # Below 0.25:       NOT QUALIFIED
}
```

### Tier Definitions

#### Tier 1: Immediate Action (composite >= 0.70)

**What it means:** This account has strong ICP fit, high buying readiness, and fresh timing signals. An AE should engage within 48 hours.

**Expected characteristics:** High pain coherence, recent trigger event, likely a new leader in a relevant role OR advanced journey position. Content Intelligence produces a high-confidence dossier with clear why-now hypothesis.

**Recommended action:** Generate full dossier. Route to assigned AE. Execute recommended play immediately.

**Calibration note:** Tier 1 threshold is deliberately set at 0.70 rather than higher because v1 weights are uncalibrated. It's better to surface a few marginal accounts to AEs than to miss genuine opportunities. After calibration, this threshold may tighten to 0.75-0.80 based on actual conversion rates.

#### Tier 2: Active Outreach (composite >= 0.45)

**What it means:** This account shows meaningful buying signals but is either earlier in the buying journey, has lower ICP fit, or has less fresh timing. Worth pursuing but lower urgency than Tier 1.

**Expected characteristics:** Moderate pain coherence, some trigger events (but potentially less recent), journey position in the "problem aware" to "solution exploring" range. Content Intelligence produces a useful dossier but may have lower confidence or more collection gaps.

**Recommended action:** Generate dossier. Queue for outreach within the current week. Play selection may favor nurture/education approaches over direct solution pitches.

#### Tier 3: Monitor & Nurture (composite >= 0.25)

**What it means:** This account is in the right neighborhood but isn't ready to buy right now. Either ICP fit is borderline, readiness is low, or timing signals are stale. Worth keeping on the radar.

**Recommended action:** Add to monitoring list. Check for new trigger events weekly/monthly. Add to content nurture sequences. Generate abbreviated dossier (executive summary + signal list only, skip full analysis).

#### Not Qualified (composite < 0.25)

**What it means:** Insufficient signals to justify outreach or monitoring. Either poor ICP fit, no detectable readiness, or no relevant timing signals.

**Recommended action:** Archive. Do not generate dossier. Re-evaluate only if a major trigger event surfaces through the re-engagement monitor.

---

## Signal Decay Configuration

All signals lose relevance over time. The decay function models this with three parameters per signal type:

- **Peak:** Days after detection when the signal is at maximum relevance
- **Half-life:** Days after peak at which relevance drops to 50%
- **Max relevance:** Days after detection at which signal relevance drops to 0

```python
SIGNAL_DECAY_CONFIG = {
    # Signal type:             (peak_days, half_life_days, max_relevance_days)
    
    # Financial events
    "funding_round":            (30,   90,   180),
    
    # Leadership changes
    "new_executive_finance":    (60,   150,  365),
    "new_executive_other":      (45,   90,   180),
    "champion_departed":        (7,    30,   60),   # Negative signal — decays fast
    
    # Hiring signals
    "job_posting_finance":      (14,   45,   90),
    "job_posting_technical":    (14,   45,   90),
    "job_posting_urgent":       (7,    21,   45),
    
    # Tech stack signals
    "tech_stack_change":        (7,    30,   60),
    "migration_signal":         (14,   45,   90),
    
    # Content signals
    "blog_post_pain":           (7,    30,   90),
    "linkedin_post_pain":       (3,    14,   30),
    "earnings_mention":         (14,   45,   90),
    "press_release_relevant":   (7,    30,   60),
    
    # Behavioral signals (if available)
    "pricing_page_visit":       (1,    7,    21),
    "content_engagement":       (3,    14,   30),
    "g2_research_activity":     (7,    21,   45),
    
    # Competitive signals
    "competitor_evaluation":    (7,    30,   60),
    "competitor_contract_renewal": (30, 60,  120),
    
    # Slow-moving signals
    "glassdoor_trend":          (30,   90,   180),
}
```

### Decay Function

```python
def calculate_decay_weight(signal_type: str, signal_date: date, current_date: date) -> float:
    """
    Returns 0.0-1.0 weight based on signal freshness.
    
    Ramp up to peak, then exponential decay.
    """
    peak, half_life, max_days = SIGNAL_DECAY_CONFIG[signal_type]
    age_days = (current_date - signal_date).days
    
    if age_days > max_days:
        return 0.0  # Signal is dead
    if age_days < 0:
        return 0.0  # Future-dated signal (data error)
    if age_days <= peak:
        # Ramp up to peak (signal needs time to mature)
        return min(1.0, age_days / peak) if peak > 0 else 1.0
    
    # Exponential decay after peak
    decay_age = age_days - peak
    return max(0.0, 0.5 ** (decay_age / half_life))
```

---

## Recalibration Protocol

### When to Recalibrate
After accumulating **30+ deal outcomes** (mix of closed-won, closed-lost, and stalled). This is the minimum for statistically meaningful pattern detection.

### What Gets Recalibrated
1. **Component weights** within each sub-score (e.g., does pain_coherence deserve more or less than 0.20?)
2. **Composite weights** (does readiness really deserve 0.50?)
3. **Scoring logic** within components (are the headcount ranges right?)
4. **Tier thresholds** (is 0.70 the right cutoff for Tier 1?)
5. **Signal decay parameters** (do funding signals really peak at 30 days?)

### Recalibration Method
For each component:
1. Calculate the **conversion rate** for accounts where the component scored above vs. below median
2. Calculate the **correlation** between component score and deal velocity (days to close)
3. Calculate the **false positive rate** (high component score but no engagement)
4. Adjust weight proportional to predictive power

Components that strongly predict closed-won outcomes get higher weights. Components with high false positive rates get lower weights. This is basic logistic regression applied to the scoring model.

### Human Override
Recalibration is algorithmic but not autonomous. Weight changes are proposed and reviewed by a human before deployment. The system outputs a recalibration report showing proposed changes, the evidence supporting each change, and the expected impact on tier distribution.

---

## Appendix: Complete Weight Summary

### Quick Reference Table

| Score | Component | Weight | Category |
|-------|-----------|--------|----------|
| **ICP Fit** | funding_stage_fit | 0.25 | Financial |
| | growth_rate | 0.20 | Financial |
| | tech_stack_fit | 0.20 | Technical |
| | headcount_fit | 0.15 | Structural |
| | industry_fit | 0.10 | Contextual |
| | geo_fit | 0.10 | Contextual |
| **Readiness** | journey_position | 0.20 | Content Intelligence |
| | pain_coherence | 0.20 | Content Intelligence |
| | new_leader_signal | 0.20 | Behavioral |
| | org_stress_indicators | 0.15 | Content Intelligence |
| | solution_sophistication | 0.15 | Content Intelligence |
| | active_evaluation_signals | 0.10 | Behavioral |
| **Timing** | trigger_event_recency | 0.35 | Temporal |
| | signal_freshness_avg | 0.25 | Temporal |
| | urgency_indicators | 0.25 | Content Intelligence |
| | window_closing_signals | 0.15 | Temporal |
| **Composite** | icp_fit | 0.25 | — |
| | buying_readiness | 0.50 | — |
| | timing | 0.25 | — |

### Content Intelligence Dependency

Of the 16 total scoring components, **6 are powered by the Content Intelligence layer** (marked above). These 6 components collectively influence approximately **60% of the composite score weight** (accounting for their position in the composite calculation). This confirms that PRISM's analytical differentiation — the proprietary content analysis engine — is the primary driver of scoring output, not commodity data enrichment.

---

*This document is versioned. All weight changes require documentation of rationale and recalibration evidence.*  
*v1.0 — Initial hypothesis weights. Pre-calibration. February 2026.*
