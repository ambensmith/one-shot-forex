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
  { name: "CNBC Business", url: "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664" },
];

const GDELT_URL =
  "https://api.gdeltproject.org/api/v2/doc/doc?query=forex+OR+%22central+bank%22+OR+%22interest+rate%22&mode=artlist&maxrecords=15&format=json";

const CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json";

// --- Fetchers ---

async function fetchRSS(source) {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    const resp = await fetch(source.url, { signal: controller.signal });
    clearTimeout(timeout);
    if (!resp.ok) {
      const body = await resp.text().catch(() => "");
      console.warn(`RSS ${source.name} HTTP ${resp.status}: ${body.slice(0, 200)}`);
      return [];
    }
    const xml = await resp.text();
    return parseRSSXml(xml, source.name);
  } catch (e) {
    console.warn(`RSS ${source.name} failed: ${e.name}: ${e.message}`);
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

async function fetchGDELT(attempt = 0) {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    const resp = await fetch(GDELT_URL, { signal: controller.signal });
    clearTimeout(timeout);
    if (resp.status === 429 && attempt < 2) {
      const wait = (attempt + 1) * 6000; // 6s, 12s
      console.warn(`GDELT rate-limited, retrying in ${wait / 1000}s...`);
      await new Promise((r) => setTimeout(r, wait));
      return fetchGDELT(attempt + 1);
    }
    if (!resp.ok) {
      const body = await resp.text().catch(() => "");
      console.warn(`GDELT HTTP ${resp.status}: ${body.slice(0, 200)}`);
      return [];
    }
    const text = await resp.text();
    // GDELT sometimes returns rate-limit message as 200 with text body
    if (text.startsWith("Please limit")) {
      if (attempt < 2) {
        const wait = (attempt + 1) * 6000;
        console.warn(`GDELT soft rate-limit, retrying in ${wait / 1000}s...`);
        await new Promise((r) => setTimeout(r, wait));
        return fetchGDELT(attempt + 1);
      }
      console.warn("GDELT rate-limited after retries");
      return [];
    }
    const data = JSON.parse(text);
    const articles = data.articles || [];
    return articles.slice(0, 15).map((a) => ({
      headline: (a.title || "").trim(),
      source: "GDELT",
      url: a.url || null,
      summary: null,
      published_at: a.seendate
        ? parseGdeltDate(a.seendate)
        : null,
    }));
  } catch (e) {
    console.warn(`GDELT failed: ${e.name}: ${e.message}`);
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
    if (!resp.ok) {
      const body = await resp.text().catch(() => "");
      console.warn(`Calendar HTTP ${resp.status}: ${body.slice(0, 200)}`);
      return [];
    }
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
    let mergedIndex = -1;
    for (let i = 0; i < seenTokenSets.length; i++) {
      const seen = seenTokenSets[i];
      const intersection = [...tokens].filter((t) => seen.has(t)).length;
      const union = new Set([...tokens, ...seen]).size;
      if (union > 0 && intersection / union > 0.7) {
        mergedIndex = i;
        break;
      }
    }
    if (mergedIndex >= 0) {
      // Merge: track that multiple sources reported this story
      if (!unique[mergedIndex].sources.includes(item.source)) {
        unique[mergedIndex].sources.push(item.source);
        unique[mergedIndex].source_count = unique[mergedIndex].sources.length;
      }
    } else {
      item.source_count = 1;
      item.sources = [item.source];
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

// --- LLM Signal Generation ---

const PROMPT_TEMPLATE = `You are a forex market analyst. Analyze the following recent news headlines
and current market context for {instrument}. Provide a trading signal.

## Recent News
{news_headlines}

## Task
Assess the likely impact on {instrument} over the next 4-8 hours.
Consider:
1. Direct economic impact
2. Central bank policy implications
3. Risk sentiment shifts
4. Historical precedent for similar events

Respond ONLY in this exact JSON format, no other text:
{
  "direction": "long" | "short" | "neutral",
  "confidence": 0.0-1.0,
  "reasoning": "1-2 sentence explanation",
  "time_horizon": "short" | "medium" | "long",
  "key_factors": ["factor1", "factor2"]
}`;

const LLM_MODELS = [
  {
    key: "groq/llama-3.3-70b",
    provider: "groq",
    model: "llama-3.3-70b-versatile",
    base_url: "https://api.groq.com/openai/v1",
    env_key: "GROQ_API_KEY",
  },
  {
    key: "mistral/mistral-small",
    provider: "mistral",
    model: "mistral-small-latest",
    base_url: "https://api.mistral.ai/v1",
    env_key: "MISTRAL_API_KEY",
  },
  {
    key: "openrouter/deepseek-v3",
    provider: "openrouter",
    model: "deepseek/deepseek-chat-v3-0324:free",
    base_url: "https://openrouter.ai/api/v1",
    env_key: "OPENROUTER_API_KEY",
  },
];

async function callLLM(modelConfig, prompt) {
  const apiKey = process.env[modelConfig.env_key];
  if (!apiKey) return null;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30000);

  try {
    const resp = await fetch(`${modelConfig.base_url}/chat/completions`, {
      method: "POST",
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: modelConfig.model,
        messages: [{ role: "user", content: prompt }],
        temperature: 0.1,
        max_tokens: 500,
      }),
    });
    clearTimeout(timeout);
    if (!resp.ok) {
      const errText = await resp.text().catch(() => "");
      console.warn(`LLM ${modelConfig.key} HTTP ${resp.status}: ${errText.slice(0, 200)}`);
      return null;
    }
    const data = await resp.json();
    return data.choices?.[0]?.message?.content || null;
  } catch (e) {
    clearTimeout(timeout);
    console.warn(`LLM ${modelConfig.key} failed:`, e.message);
    return null;
  }
}

function parseLLMSignal(response) {
  if (!response) return null;
  let text = response.trim();
  // Strip markdown code fences
  if (text.startsWith("```")) {
    const lines = text.split("\n").filter((l) => !l.trim().startsWith("```"));
    text = lines.join("\n");
  }
  try {
    const data = JSON.parse(text);
    return data;
  } catch {
    const start = text.indexOf("{");
    const end = text.lastIndexOf("}") + 1;
    if (start >= 0 && end > start) {
      try {
        return JSON.parse(text.slice(start, end));
      } catch {
        return null;
      }
    }
    return null;
  }
}

async function generateSignals(instrumentMap) {
  const signals = [];

  // Process instruments in parallel
  const entries = Object.entries(instrumentMap);
  const signalPromises = entries.map(async ([symbol, items]) => {
    const headlines = items.map((i) => {
      const tag = i.source_count > 1
        ? ` [${i.source_count} sources: ${i.sources.join(", ")}]`
        : ` [1 source: ${i.source}]`;
      return `- ${i.headline}${tag}`;
    }).slice(0, 10).join("\n");
    const prompt = PROMPT_TEMPLATE
      .replace(/{instrument}/g, symbol)
      .replace("{news_headlines}", headlines);

    // Run ALL available models in parallel for comparison
    const modelResults = await Promise.all(
      LLM_MODELS.map(async (model) => {
        const response = await callLLM(model, prompt);
        const parsed = parseLLMSignal(response);
        if (parsed && parsed.direction) {
          return {
            instrument: symbol,
            display_name: INSTRUMENTS[symbol]?.display_name || symbol,
            direction: parsed.direction,
            confidence: parseFloat(parsed.confidence) || 0,
            reasoning: parsed.reasoning || "",
            key_factors: parsed.key_factors || [],
            time_horizon: parsed.time_horizon || "short",
            model: model.key,
            headline_count: items.length,
            created_at: new Date().toISOString(),
          };
        }
        return null;
      })
    );

    return modelResults.filter(Boolean);
  });

  const results = await Promise.all(signalPromises);
  return results.flat();
}

// --- Handler ---

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  if (req.method === "OPTIONS") return res.status(200).end();

  const generateSignalsFlag = req.query?.signals !== "false";

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

    // Generate LLM signals if requested and we have mapped headlines
    let signals = [];
    if (generateSignalsFlag && Object.keys(instrumentMap).length > 0) {
      signals = await generateSignals(instrumentMap);
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
          sources: i.sources || [i.source],
          source_count: i.source_count || 1,
          published_at: i.published_at,
          url: i.url,
        })),
      }))
      .sort((a, b) => b.headline_count - a.headline_count);

    // Build per-model comparison summary from live signals
    const modelComparison = LLM_MODELS.map((m) => {
      const modelSignals = signals.filter((s) => s.model === m.key);
      const bd = {};
      for (const s of modelSignals) {
        bd[s.direction] = (bd[s.direction] || 0) + 1;
      }
      return {
        key: m.key,
        provider: m.provider,
        model: m.model,
        signal_count: modelSignals.length,
        direction_breakdown: bd,
        avg_confidence: modelSignals.length > 0
          ? +(modelSignals.reduce((sum, s) => sum + s.confidence, 0) / modelSignals.length).toFixed(2)
          : 0,
      };
    });

    // Primary signal per instrument = highest confidence from any model
    const primarySignals = Object.keys(instrumentMap).map((symbol) => {
      const instrSignals = signals.filter((s) => s.instrument === symbol);
      if (instrSignals.length === 0) {
        return {
          instrument: symbol,
          display_name: INSTRUMENTS[symbol]?.display_name || symbol,
          direction: "neutral",
          confidence: 0,
          reasoning: "All LLM providers failed to generate a signal",
          key_factors: [],
          time_horizon: "short",
          model: "none",
          headline_count: instrumentMap[symbol].length,
          created_at: new Date().toISOString(),
        };
      }
      return instrSignals.reduce((best, s) => s.confidence > best.confidence ? s : best);
    });

    res.status(200).json({
      fetched_at: new Date().toISOString(),
      summary: {
        total_fetched: allItems.length,
        after_dedup: deduped.length,
        mapped_count: mappedHeadlineSet.size,
        unmapped_count: unmapped.length,
        instruments_active: Object.keys(instrumentMap).length,
        signals_generated: primarySignals.length,
        models_active: modelComparison.filter((m) => m.signal_count > 0).length,
        source_counts: sourceCounts,
      },
      instruments,
      signals: primarySignals,
      all_signals: signals,
      model_comparison: modelComparison,
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
