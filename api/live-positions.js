/**
 * Vercel Serverless Function: Live positions from Capital.com.
 * GET /api/live-positions
 *
 * Returns real-time position data, account balance, and current prices
 * directly from Capital.com REST API.
 *
 * Requires env vars: CAPITALCOM_API_KEY, CAPITALCOM_EMAIL, CAPITALCOM_PASSWORD
 */

const BASE_URL = "https://demo-api-capital.backend-capital.com";

const INSTRUMENT_TO_EPIC = {
  EUR_USD: "EURUSD", GBP_USD: "GBPUSD", USD_JPY: "USDJPY",
  USD_CHF: "USDCHF", AUD_USD: "AUDUSD", USD_CAD: "USDCAD",
  NZD_USD: "NZDUSD", EUR_GBP: "EURGBP", EUR_JPY: "EURJPY",
  GBP_JPY: "GBPJPY", XAU_USD: "GOLD", XAG_USD: "SILVER",
  BCO_USD: "OIL_CRUDE", WTICO_USD: "OIL_CRUDE", NATGAS_USD: "NATURALGAS",
};

const EPIC_TO_INSTRUMENT = {};
for (const [k, v] of Object.entries(INSTRUMENT_TO_EPIC)) {
  EPIC_TO_INSTRUMENT[v] = k;
}
EPIC_TO_INSTRUMENT["OIL_CRUDE"] = "BCO_USD";

function pipValue(instrument) {
  if (instrument.includes("JPY")) return 0.01;
  if (instrument.startsWith("XAU") || instrument === "GOLD") return 0.1;
  if (instrument.startsWith("XAG") || instrument === "SILVER") return 0.01;
  if (instrument.includes("NATGAS") || instrument === "NATURALGAS") return 0.001;
  if (instrument.startsWith("BCO") || instrument.startsWith("WTICO") || instrument === "OIL_CRUDE") return 0.01;
  return 0.0001;
}

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") return res.status(200).end();

  const apiKey = process.env.CAPITALCOM_API_KEY;
  const email = process.env.CAPITALCOM_EMAIL;
  const password = process.env.CAPITALCOM_PASSWORD;

  if (!apiKey || !email || !password) {
    return res.status(503).json({
      error: "Capital.com credentials not configured",
      positions: [],
      account: null,
    });
  }

  try {
    // Create session
    const sessionResp = await fetch(`${BASE_URL}/api/v1/session`, {
      method: "POST",
      headers: {
        "X-CAP-API-KEY": apiKey,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ identifier: email, password }),
    });

    if (!sessionResp.ok) {
      const text = await sessionResp.text();
      return res.status(502).json({ error: `Session failed: ${text}` });
    }

    const cst = sessionResp.headers.get("CST");
    const securityToken = sessionResp.headers.get("X-SECURITY-TOKEN");

    const authHeaders = {
      "X-SECURITY-TOKEN": securityToken,
      CST: cst,
      "Content-Type": "application/json",
    };

    // Fetch positions and account in parallel
    const [positionsResp, accountResp] = await Promise.all([
      fetch(`${BASE_URL}/api/v1/positions`, { headers: authHeaders }),
      fetch(`${BASE_URL}/api/v1/accounts`, { headers: authHeaders }),
    ]);

    // Parse positions
    const posData = positionsResp.ok ? await positionsResp.json() : { positions: [] };
    const rawPositions = posData.positions || [];

    // Parse account
    let account = null;
    if (accountResp.ok) {
      const accData = await accountResp.json();
      const accounts = accData.accounts || [];
      const acct = accounts.find((a) => a.preferred) || accounts[0];
      if (acct) {
        const bal = acct.balance || {};
        account = {
          balance: parseFloat(bal.balance || 0),
          unrealizedPL: parseFloat(bal.profitLoss || 0),
          currency: acct.currency || "EUR",
        };
      }
    }

    // Enrich positions with current prices
    const positions = [];
    for (const pos of rawPositions) {
      const position = pos.position || {};
      const market = pos.market || {};

      const epic = market.epic || "";
      const instrument = EPIC_TO_INSTRUMENT[epic] || epic;
      const direction = position.direction === "BUY" ? "long" : "short";
      const entryPrice = parseFloat(position.level || 0);
      const size = parseFloat(position.size || 0);
      const stopLevel = position.stopLevel ? parseFloat(position.stopLevel) : null;
      const profitLevel = position.profitLevel ? parseFloat(position.profitLevel) : null;
      const unrealizedPL = parseFloat(position.upl || 0);

      // Get current price
      let currentPrice = null;
      let bid = null;
      let ask = null;
      try {
        const priceResp = await fetch(`${BASE_URL}/api/v1/markets/${epic}`, {
          headers: authHeaders,
        });
        if (priceResp.ok) {
          const priceData = await priceResp.json();
          const snapshot = priceData.snapshot || {};
          bid = parseFloat(snapshot.bid || 0);
          ask = parseFloat(snapshot.offer || 0);
          currentPrice = (bid + ask) / 2;
        }
      } catch {
        // Price fetch failed, use entry as fallback
      }

      // Calculate distances
      const pv = pipValue(instrument);
      let distanceToSL = null;
      let distanceToTP = null;

      if (currentPrice && stopLevel) {
        distanceToSL = direction === "long"
          ? (currentPrice - stopLevel) / pv
          : (stopLevel - currentPrice) / pv;
      }
      if (currentPrice && profitLevel) {
        distanceToTP = direction === "long"
          ? (profitLevel - currentPrice) / pv
          : (currentPrice - profitLevel) / pv;
      }

      positions.push({
        dealId: position.dealId || "",
        instrument,
        direction,
        size,
        entryPrice,
        currentPrice,
        bid,
        ask,
        stopLevel,
        profitLevel,
        unrealizedPL: Math.round(unrealizedPL * 100) / 100,
        distanceToSL_pips: distanceToSL !== null ? Math.round(distanceToSL * 10) / 10 : null,
        distanceToTP_pips: distanceToTP !== null ? Math.round(distanceToTP * 10) / 10 : null,
      });
    }

    return res.status(200).json({
      positions,
      account,
      timestamp: new Date().toISOString(),
    });
  } catch (e) {
    console.error("Live positions error:", e);
    return res.status(500).json({ error: e.message });
  }
}
