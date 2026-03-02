import { useState } from "react";

const LAYERS = [
  {
    id: "sources",
    label: "DATA SOURCES",
    color: "#4a9eff",
    bgColor: "#0d1b2a",
    borderColor: "#1b3a5c",
    description: "External origins — you don't control these",
    items: [
      { name: "Company Blogs", type: "scraper", note: "RSS + HTML fallback" },
      { name: "Job Boards", type: "api", note: "Greenhouse, Lever (public APIs)" },
      { name: "Press / News", type: "scraper", note: "GlobeNewswire, PR Newswire, TechCrunch" },
      { name: "Apollo", type: "api", note: "Contacts, firmographics, emails" },
      { name: "BuiltWith", type: "api", note: "Tech stack detection" },
      { name: "LinkedIn", type: "api", note: "Proxycurl or manual upload" },
      { name: "G2 / Review Sites", type: "scraper", note: "Competitive signals" },
    ],
  },
  {
    id: "collection",
    label: "COLLECTION LAYER",
    color: "#f59e0b",
    bgColor: "#1a1708",
    borderColor: "#4a3a0a",
    description: "Adapters that fetch and store raw responses — one per source type",
    items: [
      { name: "Blog Scraper", note: "trafilatura + Playwright fallback" },
      { name: "Job Board Collector", note: "Greenhouse/Lever API clients" },
      { name: "Press Scraper", note: "Targeted news source scrapers" },
      { name: "Apollo Adapter", note: "API client, rate-limited" },
      { name: "TechStack Adapter", note: "BuiltWith/Wappalyzer API" },
      { name: "LinkedIn Adapter", note: "Proxycurl or manual ingest endpoint" },
    ],
  },
  {
    id: "raw",
    label: "RAW STORE",
    color: "#ef4444",
    bgColor: "#1a0808",
    borderColor: "#4a1010",
    description: "Exactly what came from the source — untouched. Your audit trail. Enables reprocessing.",
    items: [
      { name: "raw_responses", note: "source_type, account_slug, fetched_at, raw_json/raw_html, http_status, url" },
    ],
    isStorage: true,
    storageNote: "APPEND-ONLY — never update, never delete. If you re-scrape, add a new row.",
  },
  {
    id: "normalize",
    label: "NORMALIZATION LAYER",
    color: "#a855f7",
    bgColor: "#150a1e",
    borderColor: "#2d1548",
    description: "Transforms raw responses into your Pydantic models — one normalizer per source type",
    items: [
      { name: "Source Adapters → Pydantic Models", note: "Every source outputs the SAME model types" },
      { name: "Content Normalizer", note: "Raw HTML/JSON → ContentItem model" },
      { name: "Contact Normalizer", note: "Apollo JSON → Contact model" },
      { name: "Signal Extractor", note: "Raw data → typed Signal records" },
      { name: "Firmographic Normalizer", note: "Multiple sources → single Account record" },
    ],
  },
  {
    id: "normalized",
    label: "NORMALIZED STORE",
    color: "#22c55e",
    bgColor: "#0a1a0e",
    borderColor: "#14401e",
    description: "Your core database — structured, queryable, typed. This is what the analysis chain reads.",
    items: [
      { name: "accounts", note: "slug, domain, company_name, firmographics (JSONB), tech_stack (JSONB)" },
      { name: "contacts", note: "account_id FK, name, title, linkedin_url, buying_role" },
      { name: "content_items", note: "account_id FK, source_type (ENUM), url, title, author, publish_date, raw_text" },
      { name: "signals", note: "account_id FK, signal_type (ENUM), typed_data (JSONB), detected_date, confidence" },
    ],
    isStorage: true,
    storageNote: "PostgreSQL — accounts update in place, content_items and signals append-only",
  },
  {
    id: "analysis",
    label: "ANALYSIS ENGINE",
    color: "#ec4899",
    bgColor: "#1a0812",
    borderColor: "#4a1030",
    description: "Your proprietary layer — Content Intelligence chain + scoring",
    items: [
      { name: "Corpus Assembler", note: "Queries normalized store → builds analysis input" },
      { name: "Stage 1: Per-Item Extraction", note: "Semantic, pragmatic, tonal, structural" },
      { name: "Stage 2: Cross-Corpus Synthesis", note: "Patterns across all content over time" },
      { name: "Stage 3: Person-Level Analysis", note: "Per buying committee member" },
      { name: "Stage 4: Synthesis & Scoring", note: "Composite scores, why-now, play recs" },
      { name: "Scoring Engine", note: "ICP Fit + Buying Readiness + Timing → Tier" },
    ],
  },
  {
    id: "output",
    label: "ANALYSIS STORE + OUTPUT",
    color: "#06b6d4",
    bgColor: "#081a1e",
    borderColor: "#0a3a44",
    description: "Versioned analysis results — every run is a snapshot you can compare",
    items: [
      { name: "analyses", note: "account_id FK, corpus_snapshot_ids[], stage 1-4 results (JSONB), scores, cost" },
      { name: "dossiers", note: "analysis_id FK, dossier_id (PRISM-YYYY-NNNN), rendered markdown" },
    ],
    isStorage: true,
    storageNote: "APPEND-ONLY — new analysis = new row. Old analyses persist for diffing.",
  },
];

const FlowArrow = ({ color = "#ffffff" }) => (
  <div style={{ display: "flex", justifyContent: "center", padding: "6px 0" }}>
    <svg width="24" height="28" viewBox="0 0 24 28">
      <line x1="12" y1="0" x2="12" y2="20" stroke={color} strokeWidth="2" strokeDasharray="4,3" />
      <polygon points="6,18 12,27 18,18" fill={color} />
    </svg>
  </div>
);

const LayerCard = ({ layer, isExpanded, onToggle }) => {
  return (
    <div
      style={{
        border: `1px solid ${layer.borderColor}`,
        borderLeft: `3px solid ${layer.color}`,
        borderRadius: "6px",
        backgroundColor: layer.bgColor,
        overflow: "hidden",
        transition: "all 0.2s ease",
      }}
    >
      <div
        onClick={onToggle}
        style={{
          padding: "14px 18px",
          cursor: "pointer",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: "12px",
        }}
      >
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
            <span
              style={{
                fontFamily: "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace",
                fontSize: "13px",
                fontWeight: 700,
                color: layer.color,
                letterSpacing: "1.5px",
              }}
            >
              {layer.label}
            </span>
            {layer.isStorage && (
              <span
                style={{
                  fontSize: "10px",
                  fontFamily: "monospace",
                  padding: "2px 8px",
                  borderRadius: "3px",
                  backgroundColor: `${layer.color}15`,
                  color: layer.color,
                  border: `1px solid ${layer.color}30`,
                  letterSpacing: "0.5px",
                }}
              >
                PERSISTED
              </span>
            )}
          </div>
          <div
            style={{
              fontSize: "12.5px",
              color: "#8899aa",
              fontFamily: "'IBM Plex Sans', -apple-system, sans-serif",
              lineHeight: 1.4,
            }}
          >
            {layer.description}
          </div>
        </div>
        <span
          style={{
            color: "#556677",
            fontSize: "18px",
            fontFamily: "monospace",
            lineHeight: 1,
            paddingTop: "2px",
            transform: isExpanded ? "rotate(0deg)" : "rotate(-90deg)",
            transition: "transform 0.2s ease",
          }}
        >
          ▾
        </span>
      </div>

      {isExpanded && (
        <div style={{ padding: "0 18px 14px 18px" }}>
          {layer.storageNote && (
            <div
              style={{
                fontSize: "11px",
                fontFamily: "monospace",
                color: layer.color,
                backgroundColor: `${layer.color}10`,
                border: `1px solid ${layer.color}20`,
                padding: "8px 12px",
                borderRadius: "4px",
                marginBottom: "10px",
                lineHeight: 1.5,
              }}
            >
              ⚡ {layer.storageNote}
            </div>
          )}
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            {layer.items.map((item, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "baseline",
                  padding: "6px 10px",
                  backgroundColor: "#ffffff05",
                  borderRadius: "4px",
                  gap: "12px",
                  flexWrap: "wrap",
                }}
              >
                <span
                  style={{
                    fontFamily: "monospace",
                    fontSize: "12px",
                    color: "#c8d6e5",
                    fontWeight: 500,
                    whiteSpace: "nowrap",
                  }}
                >
                  {item.name}
                </span>
                <span
                  style={{
                    fontSize: "11px",
                    color: "#667788",
                    fontFamily: "'IBM Plex Sans', -apple-system, sans-serif",
                    textAlign: "right",
                  }}
                >
                  {item.note}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default function PRISMArchitecture() {
  const [expanded, setExpanded] = useState({
    sources: true,
    collection: false,
    raw: true,
    normalize: false,
    normalized: true,
    analysis: false,
    output: true,
  });

  const toggle = (id) => setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));

  const keyInsights = [
    {
      title: "TWO STORAGE LAYERS",
      text: "Raw store keeps exactly what you fetched (audit trail, reprocessing). Normalized store is structured for your analysis chain. Don't skip raw — when you improve normalizers later, you reprocess from raw instead of re-scraping.",
    },
    {
      title: "APPEND-ONLY WHERE IT MATTERS",
      text: "content_items, signals, and analyses never update in place. New data = new rows. This gives you version history for free and makes diffing between analysis runs possible.",
    },
    {
      title: "ONE INTERFACE FOR ALL SOURCES",
      text: "Every source adapter outputs the same Pydantic models (ContentItem, Contact, Signal, Account). The analysis chain never knows where data came from. Add a new source = write one adapter, zero changes downstream.",
    },
    {
      title: "CORPUS SNAPSHOT = REPRODUCIBILITY",
      text: "Each analysis record stores which content_item IDs and signal IDs it analyzed. Re-running the same analysis on the same corpus produces the same result. New data = new analysis row, not overwritten results.",
    },
  ];

  return (
    <div
      style={{
        backgroundColor: "#0a0e14",
        color: "#c8d6e5",
        minHeight: "100vh",
        fontFamily: "'IBM Plex Sans', -apple-system, sans-serif",
        padding: "32px 24px",
      }}
    >
      <div style={{ maxWidth: "720px", margin: "0 auto" }}>
        {/* Header */}
        <div style={{ marginBottom: "32px" }}>
          <div
            style={{
              fontFamily: "'JetBrains Mono', 'SF Mono', monospace",
              fontSize: "10px",
              color: "#4a9eff",
              letterSpacing: "3px",
              marginBottom: "8px",
            }}
          >
            PRISM v1 — DATA ARCHITECTURE
          </div>
          <h1
            style={{
              fontSize: "22px",
              fontWeight: 600,
              color: "#e8f0f8",
              margin: "0 0 8px 0",
              fontFamily: "'IBM Plex Sans', -apple-system, sans-serif",
              lineHeight: 1.3,
            }}
          >
            Pipeline & Storage Block Diagram
          </h1>
          <p style={{ fontSize: "13px", color: "#667788", margin: 0, lineHeight: 1.6 }}>
            Data flows top to bottom. Three persistence layers (red, green, cyan) — each with different
            write semantics. Click any layer to expand details.
          </p>
        </div>

        {/* Pipeline */}
        <div style={{ display: "flex", flexDirection: "column" }}>
          {LAYERS.map((layer, i) => (
            <div key={layer.id}>
              <LayerCard
                layer={layer}
                isExpanded={expanded[layer.id]}
                onToggle={() => toggle(layer.id)}
              />
              {i < LAYERS.length - 1 && <FlowArrow color={LAYERS[i + 1].color + "60"} />}
            </div>
          ))}
        </div>

        {/* Key Architecture Decisions */}
        <div style={{ marginTop: "36px" }}>
          <div
            style={{
              fontFamily: "'JetBrains Mono', 'SF Mono', monospace",
              fontSize: "11px",
              color: "#f59e0b",
              letterSpacing: "2px",
              marginBottom: "16px",
            }}
          >
            KEY ARCHITECTURE CONSTRAINTS
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {keyInsights.map((insight, i) => (
              <div
                key={i}
                style={{
                  padding: "14px 16px",
                  backgroundColor: "#0d1520",
                  border: "1px solid #1a2535",
                  borderRadius: "6px",
                }}
              >
                <div
                  style={{
                    fontFamily: "monospace",
                    fontSize: "11px",
                    fontWeight: 700,
                    color: "#f59e0b",
                    letterSpacing: "0.5px",
                    marginBottom: "6px",
                  }}
                >
                  {insight.title}
                </div>
                <div style={{ fontSize: "12.5px", color: "#8899aa", lineHeight: 1.6 }}>
                  {insight.text}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Data Flow Summary */}
        <div
          style={{
            marginTop: "32px",
            padding: "18px",
            backgroundColor: "#0d1520",
            border: "1px solid #1a2535",
            borderRadius: "6px",
          }}
        >
          <div
            style={{
              fontFamily: "monospace",
              fontSize: "11px",
              color: "#06b6d4",
              letterSpacing: "2px",
              marginBottom: "14px",
            }}
          >
            DATA FLOW — ONE SENTENCE PER LAYER
          </div>
          <div style={{ fontFamily: "monospace", fontSize: "12px", lineHeight: 2.2, color: "#8899aa" }}>
            <span style={{ color: "#4a9eff" }}>SOURCES</span>
            {" → you fetch from external origins on a schedule"}
            <br />
            <span style={{ color: "#f59e0b" }}>COLLECTORS</span>
            {" → one adapter per source, handles auth/rate-limits/pagination"}
            <br />
            <span style={{ color: "#ef4444" }}>RAW STORE</span>
            {" → exact response saved (audit trail, enables reprocessing)"}
            <br />
            <span style={{ color: "#a855f7" }}>NORMALIZERS</span>
            {" → raw → Pydantic models (every source outputs same types)"}
            <br />
            <span style={{ color: "#22c55e" }}>NORMALIZED STORE</span>
            {" → structured PostgreSQL tables your analysis chain reads"}
            <br />
            <span style={{ color: "#ec4899" }}>ANALYSIS ENGINE</span>
            {" → Content Intelligence chain + scoring (your proprietary layer)"}
            <br />
            <span style={{ color: "#06b6d4" }}>ANALYSIS STORE</span>
            {" → versioned snapshots of every analysis run + rendered dossiers"}
          </div>
        </div>

        {/* PostgreSQL note */}
        <div
          style={{
            marginTop: "24px",
            padding: "14px 16px",
            backgroundColor: "#22c55e08",
            border: "1px solid #22c55e20",
            borderRadius: "6px",
          }}
        >
          <div style={{ fontSize: "12.5px", color: "#8899aa", lineHeight: 1.7 }}>
            <span style={{ color: "#22c55e", fontWeight: 600 }}>All three storage layers live in one PostgreSQL instance.</span>
            {" "}Separate tables, not separate databases. Raw store is a single table with JSONB. Normalized store is your 4 core tables (accounts, contacts, content_items, signals). Analysis store is 2 tables (analyses, dossiers). Total: 7 tables. That's it. You don't need a data warehouse, a data lake, or separate analytical infrastructure at this scale."}
          </div>
        </div>

        <div
          style={{
            marginTop: "24px",
            textAlign: "center",
            fontSize: "10px",
            color: "#334455",
            fontFamily: "monospace",
            letterSpacing: "1px",
            padding: "12px",
          }}
        >
          PRISM v1 DATA ARCHITECTURE — J. SHERMAN — FEB 2026
        </div>
      </div>
    </div>
  );
}
