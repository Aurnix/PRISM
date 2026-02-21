# PRISM Account Dossier — Template Specification
## Field-by-Field Rendering Guide for Implementation

**Project:** PRISM (Predictive Revenue Intelligence & Signal Mapping)  
**Author:** Joseph Sherman  
**Version:** 1.0  
**Date:** February 2026  
**Purpose:** Formal specification for programmatic dossier generation. Every field defined with data source, rendering rules, and conditional logic.

---

## Overview

The Account Dossier is PRISM's primary output artifact — the document an AE reads before engaging a target account. It's designed to be consumed in under 3 minutes while providing sufficient depth for a prepared first conversation.

### Design Philosophy

The dossier is modeled after intelligence community analytical products (ICD 203 style). Key principles:

1. **Lead with the conclusion.** Executive summary first. Supporting evidence below.
2. **Confidence is explicit.** Every assessment carries a confidence tag. Never present interpolation as fact.
3. **Counter-signals are mandatory.** Every dossier must include what contradicts the hypothesis. This builds AE trust and prevents overconfidence.
4. **Gaps are documented.** What we don't know is as important as what we do. Missing data is flagged, not hidden.
5. **Actionable over comprehensive.** The dossier tells the AE what to DO, not just what we found.

### Rendering Format

**Phase 0 (Portfolio Demo):** Markdown with ASCII box-drawing characters. Terminal aesthetic. Monospace-friendly. Renders well in GitHub, VS Code, and terminal viewers.

**Future:** Dark-themed HTML/React dashboard with collapsible sections, color-coded confidence indicators, interactive signal timeline. The markdown version is the canonical format; the frontend is a skin.

### Visual Language

```
═══  Double line: Major section borders (top/bottom of document)
━━━  Heavy single: Section dividers
───  Light single: Sub-section dividers
├──  Tree branch: Hierarchy/committee maps
│    Vertical pipe: Continuation
█░   Block characters: Signal strength visualization
⚠️   Warning: Flags and alerts
★    Star: Key designations (champion, entry point)
□    Empty checkbox: Discovery questions / action items
```

---

## Document Structure

The dossier has 9 sections, rendered in fixed order. Some sections have conditional rendering rules (e.g., Section 3 is abbreviated if corpus quality is LOW).

```
HEADER & CLASSIFICATION
SECTION 1: EXECUTIVE SUMMARY
SECTION 2: SUBJECT PROFILE
SECTION 3: ORGANIZATIONAL INTELLIGENCE ASSESSMENT
SECTION 4: KEY PERSONNEL — BUYING COMMITTEE MAP
SECTION 5: SIGNAL TIMELINE
SECTION 6: WHY NOW — HYPOTHESIS
SECTION 7: RECOMMENDED PLAY
SECTION 8: COLLECTION GAPS & DISCOVERY QUESTIONS
SECTION 9: APPENDIX — RAW SIGNALS & SOURCES
FOOTER
```

---

## HEADER & CLASSIFICATION

### Rendering

```
═══════════════════════════════════════════════════════════════
                      P R I S M
      Predictive Revenue Intelligence & Signal Mapping
═══════════════════════════════════════════════════════════════

ACCOUNT DOSSIER
Classification: {tier_label}
Dossier ID: PRISM-{year}-{sequence_number}
Generated: {iso_timestamp}
Analyst Confidence: {overall_confidence}
Corpus Quality: {corpus_quality}
Prompt Chain Version: {prompt_version}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Field Definitions

| Field | Source | Format | Logic |
|-------|--------|--------|-------|
| `tier_label` | `AnalyzedAccount.priority_tier` | "TIER 1 — IMMEDIATE ACTION" / "TIER 2 — ACTIVE OUTREACH" / "TIER 3 — MONITOR & NURTURE" / "NOT QUALIFIED" | Direct mapping from tier |
| `year` | System clock | "2026" | 4-digit year |
| `sequence_number` | Auto-increment per year | "0247" | 4-digit zero-padded |
| `iso_timestamp` | System clock | "2026-02-20T14:32:00Z" | UTC ISO 8601 |
| `overall_confidence` | `ConfidenceAssessment.overall_confidence` | "HIGH" / "MEDIUM" / "LOW" | Uppercase |
| `corpus_quality` | `ContentCorpus.estimated_density` | "HIGH" / "MEDIUM" / "LOW" / "INSUFFICIENT" | If corpus doesn't meet minimum threshold, show "INSUFFICIENT" |
| `prompt_version` | Config | "v1.0" | Track which prompt templates generated this dossier |

---

## SECTION 1: EXECUTIVE SUMMARY

### Purpose
The single most important section. If the AE reads nothing else, this gives them enough to decide whether to engage and how.

### Rendering

```
SECTION 1: EXECUTIVE SUMMARY
─────────────────────────────
{executive_summary_paragraph}

COMPOSITE SCORE: {composite_score} / 1.00
├── ICP Fit:          {icp_score}  ({icp_note})
├── Buying Readiness: {readiness_score}  ({readiness_note})
└── Timing:           {timing_score}  ({timing_note})
```

### Field Definitions

| Field | Source | Format | Logic |
|-------|--------|--------|-------|
| `executive_summary_paragraph` | LLM-generated (Stage 4 synthesis) | 3-5 sentences, plain prose | Must include: company identity (1 sentence), current situation assessment (1-2 sentences), recommended action (1 sentence). No jargon. No hedging. Direct. |
| `composite_score` | `AnalyzedAccount.composite_priority_score` | "0.82" | 2 decimal places |
| `icp_score` | `AnalyzedAccount.icp_fit_score` | "0.78" | 2 decimal places |
| `icp_note` | Generated from top ICP factors | Short parenthetical | e.g., "(Strong match on stack + stage)" — max 8 words |
| `readiness_score` | `AnalyzedAccount.buying_readiness_score` | "0.85" | 2 decimal places |
| `readiness_note` | Generated from top readiness factors | Short parenthetical | e.g., "(High pain coherence, new leader)" — max 8 words |
| `timing_score` | `AnalyzedAccount.timing_score` | "0.81" | 2 decimal places |
| `timing_note` | Generated from top timing factors | Short parenthetical | e.g., "(Fresh funding, urgency escalating)" — max 8 words |

### Generation Rules for Executive Summary

The LLM prompt for generating the executive summary paragraph should:
- Be written in third-person analytical voice ("The organization shows..." not "We found...")
- State the company's identity and relevant context in the first sentence
- State the core assessment (buying readiness + why) in 1-2 sentences
- End with a clear recommended action
- NOT use sales jargon or marketing language
- NOT hedge excessively — this is an assessment, not a disclaimer

**Example:**
> [Company] is a Series B SaaS company (est. 2021, ~180 employees, $42M raised) currently running QuickBooks Online with strong indicators of finance function scaling pain. New VP Finance appointed November 2025 combined with three open finance role postings and escalating operational urgency language in company blog content indicates an active evaluation window estimated at 30-60 days. Recommend immediate outreach via VP Finance with champion enablement approach.

---

## SECTION 2: SUBJECT PROFILE

### Purpose
Factual snapshot of the company. No analysis — just data. The AE should be able to glance at this and know the basics.

### Rendering

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 2: SUBJECT PROFILE
──────────────────────────
Company:        {company_name}
Domain:         {domain}
Founded:        {founded_year}
HQ:             {hq_location}
Headcount:      {headcount} ({headcount_trend})
Funding:        {funding_stage} — ${total_raised} total
Last Round:     {last_round_summary}
Industry:       {industry}
Revenue Est:    {revenue_estimate}

TECHNOLOGY STACK
├── Accounting/ERP:   {erp_accounting} {stack_alert}
├── CRM:              {crm}
├── Payments:         {payments}
├── Cloud:            {cloud_provider}
├── Dev Stack:        {dev_stack}
└── Recent Changes:   {stack_changes}

INVESTORS
{investor_list}
```

### Field Definitions

| Field | Source | Format | Logic |
|-------|--------|--------|-------|
| `company_name` | `ResolvedAccount.company_name` | Plain text | As registered / commonly known |
| `domain` | `ResolvedAccount.domain` | "company.com" | No https:// prefix |
| `founded_year` | `CompanyEnrichment.founded_year` | "2021" | 4-digit year. "Unknown" if not available. |
| `hq_location` | `ResolvedAccount.hq_location` | "San Francisco, CA" | City, State/Country |
| `headcount` | `CompanyEnrichment.employee_count` | "~180" | Prefix with ~ (approximate). Use comma separator for 1000+. |
| `headcount_trend` | `CompanyEnrichment.employee_growth_6mo` or `12mo` | "▲ 34% YoY" / "▼ 12% YoY" / "Flat" | Arrow + percentage. Use YoY if available, else 6mo. "Unknown" if no data. |
| `funding_stage` | `ResolvedAccount.funding_stage` | "Series B" | Standard naming |
| `total_raised` | `ResolvedAccount.total_raised` | "$42M" | Abbreviated. M for millions, B for billions. |
| `last_round_summary` | Generated | "{date} — ${amount} ({lead_investor})" | e.g., "Sep 2025 — $28M Series B (Sequoia)" |
| `industry` | `ResolvedAccount.industry` | Plain text | Primary industry classification |
| `revenue_estimate` | `CompanyEnrichment.revenue_estimate` | "$15-25M ARR (estimated)" | Always label as estimated. "Unknown" if no data. |
| `erp_accounting` | `TechEnrichment.erp_accounting` | Plain text | e.g., "QuickBooks Online" |
| `stack_alert` | Generated | "⚠️ (migration signal detected)" or empty | Show alert if migration signals present in TechEnrichment.stack_changes_detected |
| `crm` | `TechEnrichment.crm` | Plain text | "Unknown" if not detected |
| `payments` | `TechEnrichment.payment_processor` | Plain text | e.g., "Stripe" |
| `cloud_provider` | `TechEnrichment.cloud_provider` | Plain text | e.g., "AWS" |
| `dev_stack` | `TechEnrichment.primary_languages` | Comma-separated | e.g., "React, Python, PostgreSQL" |
| `stack_changes` | `TechEnrichment.stack_changes_detected` | Plain text description | e.g., "Job posting references 'NetSuite evaluation' (Jan 2026)" or "None detected" |
| `investor_list` | `CompanyEnrichment.investors` | Comma-separated | Notable investors only. If >5, show top 5 + "(+N others)" |

### Conditional Rendering

- If `revenue_estimate` is unavailable, omit the line entirely (don't show "Unknown" for revenue — it's too common to be useful)
- If `investor_list` is empty, omit the INVESTORS sub-section
- If `stack_changes` is "None detected", show "None detected" (the absence is informative)

---

## SECTION 3: ORGANIZATIONAL INTELLIGENCE ASSESSMENT

### Purpose
This is PRISM's signature section — the Content Intelligence analysis. This is what no other tool produces. It presents the sub-semantic analysis of the organization's public communications.

### Rendering (Full — Corpus Quality HIGH or MEDIUM)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 3: ORGANIZATIONAL INTELLIGENCE ASSESSMENT
─────────────────────────────────────────────────
Source: Content Intelligence analysis of {n_items} items over {date_range}
Corpus Quality: {corpus_quality} ({n_items} items, {n_source_types} source types, {date_range})

BUYING JOURNEY POSITION: {journey_position_value} — {journey_label}
{journey_assessment_paragraph}

PAIN SIGNAL COHERENCE: {pain_coherence_score} — {pain_coherence_label}
Primary pain themes converge around:
  1. {pain_theme_1} (mentioned in {frequency_1})
  2. {pain_theme_2} (mentioned in {frequency_2})
  3. {pain_theme_3} (mentioned in {frequency_3})
Scattered signals: {scattered_signals}
Assessment: {pain_coherence_assessment}

ORGANIZATIONAL STRESS INDICATORS: {stress_level}
{stress_assessment_paragraph}

SOLUTION SOPHISTICATION: {sophistication_level}
{sophistication_assessment_paragraph}

STATED vs. ACTUAL PRIORITIES: {alignment_label} {alignment_alert}
{priority_alignment_paragraph}

NOTABLE ABSENCES:
- {absence_1}
- {absence_2}
- {absence_3}
```

### Rendering (Abbreviated — Corpus Quality LOW or INSUFFICIENT)

When corpus quality is LOW or INSUFFICIENT, Section 3 is drastically shortened:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 3: ORGANIZATIONAL INTELLIGENCE ASSESSMENT
─────────────────────────────────────────────────
⚠️ LIMITED ANALYSIS — INSUFFICIENT PUBLIC CONTENT

Corpus: {n_items} items from {n_source_types} source types ({date_range})
Minimum threshold: 10 items across 3+ months from 2+ source types
Status: Below minimum. Analysis confidence degraded.

AVAILABLE INDICATORS:
{whatever_signals_could_be_extracted}

ASSESSMENT: Low confidence. Firmographic and technographic signals 
only. Content Intelligence assessment not reliable with available 
corpus. Recommend manual research or outreach-based discovery.
```

### Field Definitions

| Field | Source | Format | Logic |
|-------|--------|--------|-------|
| `n_items` | `ContentCorpus.total_items` | Integer | Total content items analyzed |
| `date_range` | `ContentCorpus.date_range` | "Aug 2025 — Feb 2026" | Month Year — Month Year |
| `n_source_types` | Count of distinct `ContentItem.source_type` | Integer | e.g., 4 (blog, linkedin, job_posting, press) |
| `corpus_quality` | `ContentCorpus.estimated_density` | "HIGH" / "MEDIUM" / "LOW" | Per corpus quality assessment |
| `journey_position_value` | `AnalyzedAccount.journey_position` | "0.52" | 2 decimal places |
| `journey_label` | `AnalyzedAccount.journey_position_label` | "ACTIVE EVALUATION" | Uppercase |
| `journey_assessment_paragraph` | LLM-generated (Stage 2 synthesis) | 2-4 sentences | Describes the narrative trajectory that led to this position assessment. References specific content shifts with approximate dates. |
| `pain_coherence_score` | `ContentIntelligenceSummary.pain_coherence_score` | "0.81" | 2 decimal places |
| `pain_coherence_label` | Generated from score | "HIGH" (>0.70) / "MODERATE" (0.40-0.70) / "LOW" (<0.40) | Threshold-based |
| `pain_theme_N` | `ContentIntelligenceSummary.primary_pain_themes[N]` | Plain text description | e.g., "Month-end close duration" |
| `frequency_N` | Generated from content analysis | "4/7 recent posts" or "mentioned in 3 sources" | Quantified frequency across corpus |
| `scattered_signals` | Generated from content analysis | Comma-separated list | Minor pain themes that don't cohere. e.g., "Hiring challenges (1/7), office culture (1/7)" |
| `pain_coherence_assessment` | LLM-generated | 1 sentence | e.g., "Pain is focused and defined, not diffuse." |
| `stress_level` | `ContentIntelligenceSummary.org_stress_level` | "LOW" / "MODERATE" / "ELEVATED" / "HIGH" | Uppercase |
| `stress_assessment_paragraph` | LLM-generated (Stage 2 synthesis) | 2-3 sentences | Describes specific stress indicators detected. References concrete evidence (language shifts, frequency changes, tone shifts). |
| `sophistication_level` | `ContentIntelligenceSummary.solution_sophistication` | "UNAWARE" / "FRUSTRATED" / "ARTICULATE" / "EVALUATING" / "DECIDED" | Uppercase |
| `sophistication_assessment_paragraph` | LLM-generated | 1-2 sentences | Describes evidence for sophistication level. Quotes specific language patterns if available. |
| `alignment_label` | "ALIGNED" or "MISALIGNED" | Based on `ContentIntelligenceSummary.stated_vs_actual_alignment` | |
| `alignment_alert` | "⚠️" if MISALIGNED, empty if ALIGNED | | Misalignment is a notable finding |
| `priority_alignment_paragraph` | LLM-generated | 2-3 sentences | Describes what's stated vs. what's actual. Only present if meaningful gap exists. If aligned, state: "Stated and actual priorities are consistent." |
| `absence_N` | `ContentIntelligenceSummary.notable_absences` | Plain text | Things conspicuously NOT discussed. Max 5 items. If none detected, show "No significant absences detected." |

### Generation Rules for Assessment Paragraphs

All paragraphs in Section 3 should:
- Be written in analytical intelligence voice (third person, present tense, declarative)
- Reference specific evidence ("Blog content shifted from X to Y between dates")
- Avoid hedging language ("might," "perhaps," "could be") — use confidence tags instead
- Be brief: 2-4 sentences maximum per paragraph
- Not repeat information stated in other sections

---

## SECTION 4: KEY PERSONNEL — BUYING COMMITTEE MAP

### Purpose
Map the identified buying committee members with role classification, approach strategy, and avoid-topics for each. This is the AE's cheat sheet for who to talk to and how.

### Rendering

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 4: KEY PERSONNEL — BUYING COMMITTEE MAP
────────────────────────────────────────────────

┌─ RECOMMENDED ENTRY POINT: {entry_point_name}, {entry_point_title}
│  Rationale: {entry_point_rationale}
│
{for each contact in buying_committee, ordered by relevance:}
├── {contact_name}, {contact_title} ★ {buying_role_label}
│   Tenure: {tenure_description} {new_role_alert}
│   Previous: {previous_role_description}
│   LinkedIn Activity: {linkedin_activity_level}
│   Buying Readiness: {individual_readiness_label} ({individual_readiness_score})
│   Messaging Resonance: {resonance_label}
│   │  → Talk about: {talk_about}
│   │  → Avoid: {avoid_topics}
│   │  → Likely objection: {likely_objection}
│   │  → Handle: {objection_response}
│   Confidence: {confidence_label} [{confidence_tag}]
│
{end for}
│
└── GAPS: {committee_gaps}

COMMITTEE DYNAMICS:
{committee_dynamics_paragraph}
```

### Field Definitions

| Field | Source | Format | Logic |
|-------|--------|--------|-------|
| `entry_point_name` | `BuyingCommittee.likely_champion` or highest-confidence contact | Name | The person to contact first |
| `entry_point_title` | Contact's title | Plain text | |
| `entry_point_rationale` | LLM-generated | 1 sentence | Why this person first. e.g., "New in role, actively posting about finance pain, highest individual readiness score." |
| `contact_name` | `ContactRecord.name` | Full name | |
| `contact_title` | `ContactRecord.title` | Full title | |
| `buying_role_label` | `ContactRecord.buying_role` | "LIKELY CHAMPION" / "LIKELY ECONOMIC BUYER" / "LIKELY TECHNICAL GATEKEEPER" / "USER" / "UNKNOWN ROLE" | Uppercase, prefixed with "LIKELY" for inferred roles |
| `tenure_description` | Calculated from `ContactRecord.start_date_current_role` | "4 months" / "2.1 years" / "Unknown" | Duration in current role |
| `new_role_alert` | `ContactRecord.is_new_in_role` | "(NEW IN ROLE ⚠️)" or empty | Show if tenure < 6 months |
| `previous_role_description` | `ContactRecord.previous_title` + `ContactRecord.previous_company` | "Senior Controller at [Company]" | "Unknown" if not available |
| `linkedin_activity_level` | `ContactRecord.linkedin_post_frequency` | "Active (2-3 posts/week)" / "Moderate (2-4 posts/month)" / "Minimal (occasional)" / "None detected" | Include approximate frequency |
| `individual_readiness_label` | Person-level `buying_readiness.stage` | "DECISION-READY" / "ACTIVE EVALUATION" / "SOLUTION-EXPLORING" / "PROBLEM-AWARE" / "NOT ASSESSED" | Uppercase |
| `individual_readiness_score` | Person-level `buying_readiness.confidence` | "0.72" | 2 decimal places. Show "N/A" if not assessed. |
| `resonance_label` | Person-level `messaging_resonance.primary` | "BUILDER" / "OPTIMIZER" / "RISK-MANAGER" / "VISIONARY" / "PRAGMATIST" | Uppercase |
| `talk_about` | Person-level `recommended_approach` | Comma-separated topics | Max 3-4 topics. Specific to this person, not generic. |
| `avoid_topics` | Person-level `recommended_avoid` | Short phrase | What NOT to say to this person. |
| `likely_objection` | Person-level `likely_objection` | 1 sentence in quotes | The most likely pushback from this specific person. |
| `objection_response` | Person-level `objection_response` | 1 sentence | How to handle it. |
| `confidence_label` | Person-level analysis confidence | "HIGH" / "MEDIUM" / "LOW" | |
| `confidence_tag` | Detailed confidence explanation | "EXTRACTED — multi-source corroborated" / "INTERPOLATED — limited personal content" / "INTERPOLATED — role-based assessment only" | Explains WHY this confidence level |
| `committee_gaps` | `BuyingCommittee.gaps` | Plain text | e.g., "No Staff Accountant / Controller identified. Likely exists but not publicly visible." |
| `committee_dynamics_paragraph` | LLM-generated (Stage 3 synthesis) | 2-3 sentences | Describes the relationship dynamics between committee members. Key insight: is the champion ahead of or behind the organization? Does the economic buyer appear aligned with the champion? Is there a potential blocker? |

### Ordering Rules

Contacts are rendered in this order:
1. Recommended entry point (first, with the tree-branch connector from the ENTRY POINT header)
2. Other committee members ordered by: Champion > Economic Buyer > Technical Gatekeeper > User > Unknown
3. Within the same role, higher confidence first

### Conditional Rendering

- If only 1 contact identified: Still render the section, but add to GAPS: "Limited committee visibility. Only one contact identified. Recommend asking in first conversation: 'Who else is involved in this decision?'"
- If 0 contacts identified (data failure): Render abbreviated section with firmographic-based role guesses: "Based on company size and stage, expect: CFO or VP Finance (economic buyer), Controller (likely champion), CTO (technical gatekeeper). No specific individuals identified. Manual research required."
- If person-level content analysis was not possible (no LinkedIn posts): Show "NOT ASSESSED" for buying readiness and resonance, with note: "No public content available for person-level analysis."

---

## SECTION 5: SIGNAL TIMELINE

### Purpose
Chronological visualization of all detected signals, most recent first. Provides the evidentiary basis for the Why Now hypothesis. The AE can scan this to understand the sequence of events.

### Rendering

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 5: SIGNAL TIMELINE
──────────────────────────
{for each signal, ordered by detected_date descending:}
{date}  {decay_bar} {decay_weight}  {signal_type_tag}: {description}
            Source: {source} | Confidence: {confidence}
{optional: blank line between signals for readability}
{end for}

Total signals: {n_signals} | Fresh (>0.70): {n_fresh} | Stale (<0.30): {n_stale}
```

### Field Definitions

| Field | Source | Format | Logic |
|-------|--------|--------|-------|
| `date` | `Signal.detected_date` | "2026-02-14" | ISO date format |
| `decay_bar` | `Signal.decay_weight` | Visual bar using █ and ░ | 10 characters wide. Filled blocks = decay weight × 10, rounded. e.g., 0.88 = "█████████░" |
| `decay_weight` | `Signal.decay_weight` | "0.88" | 2 decimal places |
| `signal_type_tag` | `Signal.signal_type` | Uppercase abbreviated tag | See signal type tag table below |
| `description` | `Signal.description` | Short description, max 80 chars | Truncate with "..." if longer |
| `source` | `Signal.source` | Source name | e.g., "Indeed scrape", "Company blog", "LinkedIn" |
| `confidence` | `Signal.confidence` | "EXTRACTED" / "INTERPOLATED" / "GENERATED" | Uppercase |

### Signal Type Tags

| Signal Type | Tag | Display |
|-------------|-----|---------|
| funding_round | FUNDING | "FUNDING: $28M Series B closed" |
| new_executive_finance | LEADERSHIP | "LEADERSHIP: VP Finance hired" |
| new_executive_other | LEADERSHIP | Same tag |
| job_posting_finance | JOB | "JOB: Controller posting (careers page)" |
| job_posting_technical | JOB | Same tag |
| tech_stack_change | TECH | "TECH: QuickBooks → NetSuite migration detected" |
| migration_signal | TECH | Same tag |
| blog_post_pain | CONTENT | "CONTENT: Blog post 'Scaling Our Operations for Series C'" |
| linkedin_post_pain | CONTENT | Same tag |
| earnings_mention | CONTENT | Same tag |
| press_release_relevant | PRESS | "PRESS: TechCrunch coverage of Series B" |
| pricing_page_visit | INTENT | "INTENT: Pricing page visited 3x in 7 days" |
| competitor_evaluation | COMPETE | "COMPETE: G2 comparison activity detected" |
| glassdoor_trend | CULTURE | "CULTURE: Glassdoor rating declined 0.4 in 6 months" |
| champion_departed | ALERT | "ALERT: Previous champion left the company" |

### Rendering Rules

- **Maximum signals shown:** 15 most recent. If more than 15, show 15 + "... and {N} older signals (see Appendix)"
- **Minimum signals shown:** All available, even if only 1-2
- **Stale signals** (decay_weight < 0.20): Still show but visually de-emphasize (all ░ blocks)
- **Negative signals** (champion_departed, window_closing): Prefix with "⚠️" before the signal type tag

---

## SECTION 6: WHY NOW — HYPOTHESIS

### Purpose
The synthesized narrative explaining why this account is ready to buy RIGHT NOW. This is the analytical conclusion — the "so what" of all the signals. The AE reads this and knows the story to tell internally and to the prospect.

### Rendering

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 6: WHY NOW — HYPOTHESIS
───────────────────────────────
PRIMARY HYPOTHESIS:
{why_now_narrative}

CONFIDENCE: {confidence_label}
Supporting signals: {n_supporting} | Corroborating sources: {n_sources}
Signal types: {signal_type_list}

COUNTER-SIGNALS:
{for each counter_signal:}
⚠️ {counter_signal_description}
{end for}
```

### Field Definitions

| Field | Source | Format | Logic |
|-------|--------|--------|-------|
| `why_now_narrative` | `WhyNowHypothesis.narrative` | 2-3 paragraphs | The full analytical narrative. See generation rules below. |
| `confidence_label` | `ConfidenceAssessment.overall_confidence` | "HIGH" / "MEDIUM" / "LOW" | Uppercase |
| `n_supporting` | Count of `WhyNowHypothesis.supporting_signals` | Integer | |
| `n_sources` | Count of distinct sources across supporting signals | Integer | |
| `signal_type_list` | Distinct signal types in supporting signals | Comma-separated, lowercase | e.g., "funding, leadership, hiring, content, tech_change" |
| `counter_signal_description` | `ConfidenceAssessment.counter_signals[N]` | 1-2 sentences per counter-signal | Each counter-signal explains what contradicts the hypothesis and why it matters |

### Generation Rules for Why Now Narrative

The why_now_narrative is the highest-value LLM output in the system. Rules:

1. **Structure:** Chronological story arc. "X happened, which led to Y, which created Z condition, which means the buying window is open NOW because of W."
2. **Specificity:** Reference specific dates, specific signals, specific people by role.
3. **Causality:** Connect the signals into a causal chain, not just a list. Why does the funding round + new leader + hiring activity + content trajectory = buying window?
4. **Window estimate:** End with an estimated buying window ("30-60 days," "60-90 days") based on the signal freshness and urgency indicators.
5. **Length:** 2-3 paragraphs. Not more. AEs won't read a page of text.
6. **Voice:** Analytical, confident, specific. Not hedged, not salesy, not generic.

### Counter-Signal Rules

**Counter-signals are MANDATORY.** Every dossier must have at least one counter-signal, even if the hypothesis is high-confidence. If the LLM analysis doesn't surface counter-signals, force it with a dedicated counter-signal prompt.

Minimum: 1 counter-signal. Maximum: 5. If more than 5, include only the 3 most significant and note "Additional counter-signals in Appendix."

Counter-signals should be genuinely useful, not token disclaimers. "We can't be 100% sure" is not a counter-signal. "No direct competitor evaluation signals detected — they may be earlier in evaluation than other signals suggest" IS a counter-signal.

---

## SECTION 7: RECOMMENDED PLAY

### Purpose
Actionable recommendations. What should the AE DO with this intelligence?

### Rendering

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 7: RECOMMENDED PLAY
────────────────────────────
PLAY: {play_name}
{play_description}

SEQUENCE:
{for each step in sequence:}
{step_number}. {step_description}
   Angle: {angle_description}
{end for}

TIMELINE: {timeline_estimate}
ENTRY POINT: {entry_point_summary}
FALLBACK: {fallback_summary}
```

### Field Definitions

| Field | Source | Format | Logic |
|-------|--------|--------|-------|
| `play_name` | `AnalyzedAccount` via play selection matrix | Uppercase descriptive name | e.g., "DIRECT SOLUTION — CHAMPION ENABLEMENT" |
| `play_description` | Play matrix description | 1-2 sentences | Why this play was selected for this specific account |
| `sequence` | Play matrix + LLM-generated angles | Numbered steps | 3-5 steps maximum. Each step includes the action AND the specific angle for this account. |
| `timeline_estimate` | Play matrix | "2-week accelerated sequence" / "3-day sprint" / "3-month nurture" | |
| `entry_point_summary` | From Section 4 | "{Name} ({Title}) via {channel}" | e.g., "Jane Smith (VP Finance) via LinkedIn direct" |
| `fallback_summary` | LLM-generated | 1 sentence | What to do if primary approach fails. e.g., "CTO approach via technical content if champion is unresponsive after 2 weeks." |

### Rendering Rules

- **Sequence steps** should be specific to THIS account, not generic templates. Reference specific signals, specific people, specific content.
- **Angles** within sequence steps should reflect the messaging resonance profile of the target contact.
- **Do NOT include email copy.** The dossier provides the angle and talking points. The AE (or a separate tool) writes the actual message.
- **Maximum 5 sequence steps.** If the play requires more, the first 5 are shown and the rest are noted: "Extended sequence details in Appendix."

---

## SECTION 8: COLLECTION GAPS & DISCOVERY QUESTIONS

### Purpose
Honest documentation of what we don't know. Turns gaps into discovery questions the AE can ask in their first conversation.

### Rendering

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 8: COLLECTION GAPS & DISCOVERY QUESTIONS
─────────────────────────────────────────────────
UNKNOWN — Prioritize in first conversation:

{for each discovery_question:}
□ {question}
{end for}

ENRICHMENT GAPS:
{for each enrichment_gap:}
□ {gap_description}
{end for}
```

### Field Definitions

| Field | Source | Format | Logic |
|-------|--------|--------|-------|
| `discovery_question` | LLM-generated based on gaps | Question format | Questions the AE should ask in first conversation. These are NOT sales qualification questions — they're intelligence-gathering questions to fill specific gaps in the dossier. |
| `enrichment_gap` | System-generated based on failed/missing enrichment branches | Descriptive statement | Which data sources failed or returned insufficient data. |

### Generation Rules

**Discovery questions** should:
- Be specific to the gaps in THIS dossier, not generic BANT qualification
- Be phrased as natural conversation questions, not interrogation
- Prioritized: most important gaps first
- Maximum 8 questions (AE won't remember more)

**Enrichment gaps** should:
- Document which enrichment branches returned insufficient data
- Be technical enough for the GTM Engineer to know what to fix, but readable enough for the AE to understand what's missing
- Maximum 5 gaps listed

---

## SECTION 9: APPENDIX — RAW SIGNALS & SOURCES

### Purpose
Full evidentiary record. For audit, review, and recalibration purposes. Most AEs won't read this, but it's there for the AE who wants to verify a specific claim or for the GTM Engineer reviewing dossier quality.

### Rendering

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SECTION 9: APPENDIX — RAW SIGNALS & SOURCES
───────────────────────────────────────────
{for each signal, ordered chronologically:}
SIGNAL: {signal_type} | {detected_date}
  Description: {full_description}
  Source: {source_url_or_description}
  Detected: {detected_date}
  Decay Weight: {decay_weight} (as of {dossier_generation_date})
  Confidence: {confidence_tag}
  Contributed to: {which_scores_this_affected}

{end for}

CONTENT CORPUS SUMMARY:
  Total items analyzed: {n_items}
  Source breakdown: {source_type_counts}
  Date range: {date_range}
  Corpus quality assessment: {quality}
  
ANALYSIS METADATA:
  LLM Provider: {provider}
  Model: {model}
  Prompt Chain Version: {version}
  Analysis Date: {date}
  Total tokens consumed: {tokens}
  Estimated analysis cost: ${cost}
```

### Rendering Rules

- Include ALL signals, not just the top 15 from Section 5
- Include source URLs where available (for blog posts, LinkedIn posts, job postings)
- Include the analysis cost — transparency about what the dossier cost to generate

---

## FOOTER

### Rendering

```
═══════════════════════════════════════════════════════════════
END DOSSIER | PRISM-{year}-{sequence_number} | Generated by PRISM v{system_version}
{disclaimer}
═══════════════════════════════════════════════════════════════
```

### Disclaimer Text

```
Analysis based on publicly available information. Confidence 
assessments are probabilistic, not deterministic. Counter-signals 
and collection gaps should be considered before acting. Scoring 
weights are v1.0 (pre-calibration). This dossier does not 
constitute a guarantee of buying intent or deal outcome.
```

---

## Rendering Decision Matrix

For different tier levels and corpus qualities, the dossier rendering varies:

| Tier | Corpus Quality | Sections Rendered | Notes |
|------|---------------|-------------------|-------|
| Tier 1 | HIGH | All 9 sections, full detail | Maximum effort dossier |
| Tier 1 | MEDIUM | All 9 sections, full detail | Same as HIGH — Tier 1 always gets full treatment |
| Tier 1 | LOW | All 9 sections, Section 3 abbreviated | Flag corpus limitation prominently |
| Tier 2 | HIGH/MEDIUM | All 9 sections, full detail | Same format as Tier 1 |
| Tier 2 | LOW | Sections 1-2, abbreviated 3, 4-6, abbreviated 7, 8 | Skip Appendix |
| Tier 3 | Any | Sections 1-2 only + signal list | "Abbreviated Dossier" header. No full analysis. |
| Not Qualified | Any | No dossier generated | Log decision, don't spend LLM tokens |

---

## Example: Minimal Dossier (Tier 3)

```
═══════════════════════════════════════════════════════════════
                      P R I S M
      Predictive Revenue Intelligence & Signal Mapping
═══════════════════════════════════════════════════════════════

ACCOUNT DOSSIER — ABBREVIATED
Classification: TIER 3 — MONITOR & NURTURE
Dossier ID: PRISM-2026-0251
Generated: 2026-02-20T15:01:00Z
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EXECUTIVE SUMMARY
─────────────────
[Company] is a Series A SaaS company (~60 employees, $8M raised) 
with limited public content and no detected finance-specific pain 
signals. ICP fit is moderate (right stage, small headcount) but 
no current buying indicators detected. Recommend adding to 
monitoring list for trigger event detection.

COMPOSITE SCORE: 0.31 / 1.00
├── ICP Fit:          0.52  (Stage fit, low headcount)
├── Buying Readiness: 0.18  (No pain signals detected)
└── Timing:           0.28  (No recent triggers)

SUBJECT PROFILE
───────────────
Company:        [Name]
Domain:         [domain.com]
Headcount:      ~60 (▲ 22% YoY)
Funding:        Series A — $8M total
Industry:       SaaS

DETECTED SIGNALS: 1
2025-10-15  ██░░░░░░░░ 0.22  FUNDING: $8M Series A (Lead Investor)

RECOMMENDATION: Monitor. Re-evaluate on trigger event.

═══════════════════════════════════════════════════════════════
END DOSSIER | PRISM-2026-0251 | Generated by PRISM v0.1
═══════════════════════════════════════════════════════════════
```

---

*This specification is the canonical reference for dossier generation. All fields, rendering rules, and conditional logic defined here.*
