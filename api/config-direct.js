/**
 * Vercel Serverless Function: Direct config save via GitHub Contents API.
 * Writes config overrides directly to a JSON file in the repo — no workflow needed.
 * Much faster than the workflow-based approach (~5s vs ~2min).
 *
 * POST /api/config-direct
 * Body: { overrides: { "risk.max_risk_per_trade": 0.02, ... } }
 *
 * Requires env vars: GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO
 */

const GITHUB_API = "https://api.github.com";
const CONFIG_PATH = "data/config_overrides.json";

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") return res.status(200).end();
  if (req.method !== "POST") return res.status(405).json({ error: "POST only" });

  const token = process.env.GITHUB_TOKEN;
  const owner = process.env.GITHUB_OWNER;
  const repo = process.env.GITHUB_REPO;

  if (!token || !owner || !repo) {
    return res.status(500).json({
      error: "Missing GITHUB_TOKEN, GITHUB_OWNER, or GITHUB_REPO env vars",
    });
  }

  const { overrides } = req.body || {};
  if (!overrides || typeof overrides !== "object") {
    return res.status(400).json({ error: "Body must include 'overrides' object" });
  }

  try {
    // 1. Read existing config_overrides.json (if it exists)
    let existingOverrides = {};
    let sha = null;

    try {
      const getResp = await fetch(
        `${GITHUB_API}/repos/${owner}/${repo}/contents/${CONFIG_PATH}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: "application/vnd.github+json",
          },
        }
      );

      if (getResp.ok) {
        const fileData = await getResp.json();
        sha = fileData.sha;
        const content = Buffer.from(fileData.content, "base64").toString("utf-8");
        existingOverrides = JSON.parse(content);
      }
    } catch {
      // File doesn't exist yet — that's fine
    }

    // 2. Merge new overrides into existing
    const merged = { ...existingOverrides, ...overrides };

    // 3. Write back via GitHub Contents API
    const newContent = Buffer.from(
      JSON.stringify(merged, null, 2),
      "utf-8"
    ).toString("base64");

    const putBody = {
      message: `Update config overrides via UI`,
      content: newContent,
      ...(sha ? { sha } : {}),
    };

    const putResp = await fetch(
      `${GITHUB_API}/repos/${owner}/${repo}/contents/${CONFIG_PATH}`,
      {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          Accept: "application/vnd.github+json",
        },
        body: JSON.stringify(putBody),
      }
    );

    if (!putResp.ok) {
      const errText = await putResp.text();
      return res.status(putResp.status).json({
        error: `Failed to save config: ${errText.slice(0, 200)}`,
      });
    }

    return res.status(200).json({
      status: "ok",
      message: "Config saved directly. Changes take effect on next trading cycle.",
      overrides_count: Object.keys(merged).length,
    });
  } catch (e) {
    console.error("Config direct save error:", e);
    return res.status(500).json({ error: e.message });
  }
}
