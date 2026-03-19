/**
 * Vercel Serverless Function: Fetch live news and categorize by instrument.
 * GET /api/news-fetch
 *
 * Fetches from BBC RSS, Reuters RSS, GDELT API, and ForexFactory calendar.
 * Deduplicates headlines, maps to forex/commodity instruments via keywords,
 * and returns categorized results.
 */

const INSTRUMENTS = {
  EUR_USD: {
    display_name: "EUR/USD", type: "forex",
    keywords: ["ecb", "european central bank", "eurozone", "euro area", "lagarde", "bundesbank", "federal reserve", "fed rate", "us dollar", "us inflation", "us jobs", "non-farm payrolls", "fomc"]
  },
  GBP_USD: {
    display_name: "GBP/USD", type: "forex",
    keywords: ["bank of england", "boe", "uk economy", "uk gdp", "uk inflation", "sterling", "british pound", "bailey"]
  },
  USD_JPY: {
    display_name: "USD/JPY", type: "forex",
    keywords: ["bank of japan", "boj", "yen", "intervention", "japan economy", "ueda", "risk sentiment", "risk off", "risk on"]
  },
  USD_CHF: {
    display_name: "USD/CHF", type: "forex",
    keywords: ["swiss national bank", "snb", "safe haven", "swiss franc"]
  },
  AUD_USD: {
    display_name: "AUD/USD", type: "forex",
    keywords: ["reserve bank australia", "rba", "china demand", "iron ore", "australian economy", "australia employment"]
  },
  XAU_USD: {
    display_name: "Gold", type: "commodity",
    keywords: ["gold", "safe haven", "real yields", "treasury yields", "geopolitical risk", "war", "conflict", "sanctions", "central bank gold"]
  },
  BCO_USD: {
    display_name: "Brent Crude", type: "commodity",
    keywords: ["oil", "opec", "crude", "petroleum", "saudi arabia", "iran", "pipeline", "energy crisis", "brent"]
  },
  WTICO_USD: {
    display_name: "WTI Crude", type: "commodity",
    keywords: ["wti", "us oil", "shale", "strategic petroleum reserve", "us production"]
  },
  XAG_USD: {
    display_name: "Silver", type: "commodity",
    keywords: ["silver", "industrial demand", "precious metals"]
  },
  NATGAS_USD: {
    display_name: "Natural Gas", type: "commodity",
    keywords: ["natural gas", "lng", "european energy", "gas pipeline", "gas storage"]
  },
  USD_CAD: {
    display_name: "USD/CAD", type: "forex",
    keywords: ["bank of canada", "boc", "canadian economy", "canada jobs"]
  },
  EUR_GBP: {
    display_name: "EUR/GBP", type: "forex",
    keywords: ["eu uk", "brexit", "euro pound"]
  },
};

const RSS_SOURCES = [
  { name: "BBC Business", url: "https://feeds.bbci.co.uk/news/business/rss.xml" },
  { name: "Reuters", url: "https://www.reutersagency.com/feed/" },
];

const GDELT_URL =
  "https://api.gdeltproject.org/api/v2/doc/doc?query=forex+OR+economy+OR+central+bank+OR+interest+rate&mode=artlist&maxrecords=30&format=json";

const CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json";

// --- Fetchers ---

async function fetchRSS(source) {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    const resp = await fetch(source.url, { signal: controller.signal });
    clearTimeout(timeout);
    if (!resp.ok) return [];
    const xml = await resp.text();
    return parseRSSXml(xml, source.name);
  } catch (e) {
    console.warn(`RSS ${source.name} failed:`, e.message);
    return [];
  }
}

function parseRSSXml(xml, sourceName) {
  const items = [];
  // Simple regex-based RSS parser (no dependencies needed)
  const itemRegex = /<item>([\s\S]*?)<\/item>/gi;
  let match;
  while ((match = itemRegex.exec(xml)) !== null && items.length < 20) {
    const block = match[1];
    const title = extractTag(block, "title");
    const link = extractTag(block, "link");
    const description = extractTag(block, "description");
    const pubDate = extractTag(block, "pubDate");

    if (title) {
      items.push({
        headline: title.trim(),
        source: sourceName,
        url: link || null,
        summary: description ? description.slice(0, 500) : null,
        published_at: pubDate ? new Date(pubDate).toISOString() : null,
      });
    }
  }
  return items;
}

function extractTag(xml, tag) {
  // Handle CDATA sections
  const cdataRegex = new RegExp(`<${tag}[^>]*><!\\[CDATA\\[([\\s\\S]*?)\\]\\]></${tag}>`, "i");
  const cdataMatch = xml.match(cdataRegex);
  if (cdataMatch) return cdataMatch[1];

  const regex = new RegExp(`<${tag}[^>]*>([\\s\\S]*?)</${tag}>`, "i");
  const m = xml.match(regex);
  return m ? m[1].replace(/<[^>]+>/g, "").trim() : null;
}

async function fetchGDELT() {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    const resp = await fetch(GDELT_URL, { signal: controller.signal });
    clearTimeout(timeout);
    if (!resp.ok) return [];
    const data = await resp.json();
    const articles = data.articles || [];
    return articles.slice(0, 20).map((a) => ({
      headline: (a.title || "").trim(),
      source: "GDELT",
      url: a.url || null,
      summary: null,
      published_at: a.seendate
        ? parseGdeltDate(a.seendate)
        : null,
    }));
  } catch (e) {
    console.warn("GDELT failed:", e.message);
    return [];
  }
}

function parseGdeltDate(d) {
  try {
    const s = d.slice(0, 14); // YYYYMMDDTHHmmss
    const dt = new Date(
      `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}T${s.slice(9, 11)}:${s.slice(11, 13)}:${s.slice(13, 15)}Z`
    );
    return dt.toISOString();
  } catch {
    return null;
  }
}

async function fetchCalendar() {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    const resp = await fetch(CALENDAR_URL, { signal: controller.signal });
    clearTimeout(timeout);
    if (!resp.ok) return [];
    const data = await resp.json();
    if (!Array.isArray(data)) return [];
    return data
      .filter((e) => e.impact === "High" || e.impact === "Medium")
      .slice(0, 30)
      .map((e) => {
        let headline = `[${e.country || ""}] ${e.title || ""}`;
        if (e.actual) {
          headline += ` Actual: ${e.actual}`;
          if (e.forecast) headline += ` (Forecast: ${e.forecast})`;
        }
        return {
          headline,
          source: "Economic Calendar",
          url: null,
          summary: `Impact: ${e.impact}. ${e.country || ""} economic event.`,
          published_at: e.date || null,
        };
      });
  } catch (e) {
    console.warn("Calendar failed:", e.message);
    return [];
  }
}

// --- Dedup ---

function deduplicateHeadlines(items) {
  const unique = [];
  const seenTokenSets = [];

  for (const item of items) {
    const tokens = new Set(item.headline.toLowerCase().split(/\s+/));
    let isDup = false;
    for (const seen of seenTokenSets) {
      const intersection = [...tokens].filter((t) => seen.has(t)).length;
      const union = new Set([...tokens, ...seen]).size;
      if (union > 0 && intersection / union > 0.7) {
        isDup = true;
        break;
      }
    }
    if (!isDup) {
      unique.push(item);
      seenTokenSets.push(tokens);
    }
  }
  return unique;
}

// --- Instrument mapping ---

function mapHeadline(headline) {
  const lower = headline.toLowerCase();
  const matched = [];
  for (const [symbol, info] of Object.entries(INSTRUMENTS)) {
    for (const kw of info.keywords) {
      if (lower.includes(kw.toLowerCase())) {
        matched.push(symbol);
        break;
      }
    }
  }
  return matched;
}

// --- Handler ---

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  if (req.method === "OPTIONS") return res.status(200).end();

  try {
    // Fetch all sources in parallel
    const [rss1, rss2, gdelt, calendar] = await Promise.all([
      fetchRSS(RSS_SOURCES[0]),
      fetchRSS(RSS_SOURCES[1]),
      fetchGDELT(),
      fetchCalendar(),
    ]);

    const allItems = [...rss1, ...rss2, ...gdelt, ...calendar];
    const deduped = deduplicateHeadlines(allItems);

    // Map to instruments
    const instrumentMap = {};
    const mappedHeadlineSet = new Set();

    for (const item of deduped) {
      const instruments = mapHeadline(item.headline);
      for (const inst of instruments) {
        if (!instrumentMap[inst]) instrumentMap[inst] = [];
        instrumentMap[inst].push(item);
        mappedHeadlineSet.add(item.headline);
      }
    }

    const unmapped = deduped.filter((i) => !mappedHeadlineSet.has(i.headline));

    // Source counts
    const sourceCounts = {};
    for (const item of deduped) {
      sourceCounts[item.source] = (sourceCounts[item.source] || 0) + 1;
    }

    // Build instrument summaries
    const instruments = Object.entries(instrumentMap)
      .map(([symbol, items]) => ({
        symbol,
        display_name: INSTRUMENTS[symbol]?.display_name || symbol,
        type: INSTRUMENTS[symbol]?.type || "unknown",
        headline_count: items.length,
        headlines: items.map((i) => ({
          headline: i.headline,
          source: i.source,
          published_at: i.published_at,
          url: i.url,
        })),
      }))
      .sort((a, b) => b.headline_count - a.headline_count);

    res.status(200).json({
      fetched_at: new Date().toISOString(),
      summary: {
        total_fetched: allItems.length,
        after_dedup: deduped.length,
        mapped_count: mappedHeadlineSet.size,
        unmapped_count: unmapped.length,
        instruments_active: Object.keys(instrumentMap).length,
        source_counts: sourceCounts,
      },
      instruments,
      unmapped: unmapped.map((i) => ({
        headline: i.headline,
        source: i.source,
        published_at: i.published_at,
      })),
    });
  } catch (e) {
    console.error("News fetch error:", e);
    res.status(500).json({ error: "Failed to fetch news", detail: e.message });
  }
}
