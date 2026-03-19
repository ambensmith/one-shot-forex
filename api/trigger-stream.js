/**
 * Vercel Serverless Function: Trigger a GitHub Actions workflow.
 * POST /api/trigger-stream
 *
 * Body: { mode: "tick"|"reset"|"review"|"save-hybrid", stream?, hybrid?, period? }
 * Returns: { run_id, status }
 *
 * Requires env vars: GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO
 */

const GITHUB_API = "https://api.github.com";

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

  const { mode = "tick", stream = "all", hybrid, hybrid_id, hybrid_active, period = "7d" } = req.body || {};

  // Build workflow inputs
  const inputs = {
    mode,
    stream: mode === "tick" ? stream : "all",
    force_market_open: "true",
    review_period: period,
  };

  if (mode === "save-hybrid" && hybrid) {
    inputs.hybrid_json = typeof hybrid === "string" ? hybrid : JSON.stringify(hybrid);
  }

  if ((mode === "toggle-hybrid" || mode === "delete-hybrid") && hybrid_id != null) {
    inputs.hybrid_id = String(hybrid_id);
  }

  if ((mode === "toggle-hybrid" || mode === "toggle-all-hybrids") && hybrid_active != null) {
    inputs.hybrid_active = String(hybrid_active);
  }

  try {
    // Get the workflow ID
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

    // Record timestamp before dispatch to help find the run
    const beforeDispatch = new Date().toISOString();

    // Dispatch the workflow
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
          inputs,
        }),
      }
    );

    if (!dispatchResp.ok) {
      const errText = await dispatchResp.text();
      return res.status(dispatchResp.status).json({
        error: `Dispatch failed: ${errText}`,
      });
    }

    // Wait a moment for GitHub to register the run
    await new Promise((r) => setTimeout(r, 2500));

    // Find the run that was just created
    const runsResp = await ghFetch(
      token,
      `${GITHUB_API}/repos/${owner}/${repo}/actions/runs?event=workflow_dispatch&per_page=5&created=>${beforeDispatch.slice(0, 19)}`
    );

    let runId = null;
    const runs = runsResp.workflow_runs || [];
    if (runs.length > 0) {
      // Most recent workflow_dispatch run
      runId = runs[0].id;
    }

    if (!runId) {
      // Fallback: get the most recent run
      const fallbackResp = await ghFetch(
        token,
        `${GITHUB_API}/repos/${owner}/${repo}/actions/runs?event=workflow_dispatch&per_page=1`
      );
      const fallbackRuns = fallbackResp.workflow_runs || [];
      if (fallbackRuns.length > 0) {
        runId = fallbackRuns[0].id;
      }
    }

    return res.status(200).json({
      status: "dispatched",
      run_id: runId,
      message: runId
        ? `Workflow dispatched. Run ID: ${runId}`
        : "Workflow dispatched but run ID not yet available. Poll /api/workflow-status.",
    });
  } catch (e) {
    console.error("Trigger error:", e);
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
