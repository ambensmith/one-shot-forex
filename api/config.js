/**
 * Vercel Serverless Function: Config management via GitHub API.
 * GET  /api/config — triggers get-config workflow
 * POST /api/config — triggers save-config workflow with overrides
 *
 * Requires env vars: GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO
 */

const GITHUB_API = "https://api.github.com";

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") return res.status(200).end();

  const token = process.env.GITHUB_TOKEN;
  const owner = process.env.GITHUB_OWNER;
  const repo = process.env.GITHUB_REPO;

  if (!token || !owner || !repo) {
    return res.status(500).json({
      error: "Missing GITHUB_TOKEN, GITHUB_OWNER, or GITHUB_REPO env vars",
    });
  }

  if (req.method === "GET") {
    return await dispatchWorkflow(token, owner, repo, "get-config", {}, res);
  }

  if (req.method === "POST") {
    const { overrides } = req.body || {};
    if (!overrides || typeof overrides !== "object") {
      return res.status(400).json({ error: "Body must include 'overrides' object" });
    }
    return await dispatchWorkflow(
      token, owner, repo, "save-config",
      { config_json: JSON.stringify(overrides) },
      res
    );
  }

  return res.status(405).json({ error: "GET or POST only" });
}

async function dispatchWorkflow(token, owner, repo, mode, extraInputs, res) {
  try {
    const workflowResp = await ghFetch(
      token,
      `${GITHUB_API}/repos/${owner}/${repo}/actions/workflows`
    );
    const workflows = workflowResp.workflows || [];
    const tradeWorkflow = workflows.find(
      (w) => w.name === "Trading Cycle" || w.path === ".github/workflows/trade.yml"
    );

    if (!tradeWorkflow) {
      return res.status(404).json({ error: "Trading Cycle workflow not found" });
    }

    const beforeDispatch = new Date().toISOString();

    const dispatchResp = await fetch(
      `${GITHUB_API}/repos/${owner}/${repo}/actions/workflows/${tradeWorkflow.id}/dispatches`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          Accept: "application/vnd.github+json",
        },
        body: JSON.stringify({
          ref: "main",
          inputs: { mode, stream: "all", force_market_open: "false", ...extraInputs },
        }),
      }
    );

    if (!dispatchResp.ok) {
      const errText = await dispatchResp.text();
      return res.status(dispatchResp.status).json({
        error: `Dispatch failed: ${errText}`,
      });
    }

    await new Promise((r) => setTimeout(r, 2500));

    const runsResp = await ghFetch(
      token,
      `${GITHUB_API}/repos/${owner}/${repo}/actions/runs?event=workflow_dispatch&per_page=5&created=>${beforeDispatch.slice(0, 19)}`
    );

    let runId = null;
    const runs = runsResp.workflow_runs || [];
    if (runs.length > 0) runId = runs[0].id;

    return res.status(200).json({
      status: "dispatched",
      run_id: runId,
      message: `${mode} workflow dispatched.`,
    });
  } catch (e) {
    console.error("Config dispatch error:", e);
    return res.status(500).json({ error: e.message });
  }
}

async function ghFetch(token, url) {
  const resp = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
    },
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`GitHub API ${resp.status}: ${text.slice(0, 200)}`);
  }
  return resp.json();
}
