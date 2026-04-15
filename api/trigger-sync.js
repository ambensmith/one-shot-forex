/**
 * Vercel Serverless Function: Trigger the Position Sync workflow.
 * POST /api/trigger-sync
 *
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

  try {
    // Get the workflow ID
    const workflowResp = await ghFetch(
      token,
      `${GITHUB_API}/repos/${owner}/${repo}/actions/workflows`
    );
    const workflows = workflowResp.workflows || [];
    const syncWorkflow = workflows.find(
      (w) => w.name === "Position Sync" || w.path === ".github/workflows/sync.yml"
    );

    if (!syncWorkflow) {
      return res.status(404).json({ error: "Position Sync workflow not found" });
    }

    // Record timestamp before dispatch to help find the run
    const beforeDispatch = new Date().toISOString();

    // Dispatch the workflow
    const dispatchResp = await fetch(
      `${GITHUB_API}/repos/${owner}/${repo}/actions/workflows/${syncWorkflow.id}/dispatches`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          Accept: "application/vnd.github+json",
        },
        body: JSON.stringify({
          ref: "main",
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
    // Filter to only sync workflow runs
    const syncRuns = runs.filter((r) => r.workflow_id === syncWorkflow.id);
    if (syncRuns.length > 0) {
      runId = syncRuns[0].id;
    }

    if (!runId) {
      // Fallback: get the most recent sync run
      const fallbackResp = await ghFetch(
        token,
        `${GITHUB_API}/repos/${owner}/${repo}/actions/workflows/${syncWorkflow.id}/runs?event=workflow_dispatch&per_page=1`
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
        ? `Sync dispatched. Run ID: ${runId}`
        : "Sync dispatched but run ID not yet available. Poll /api/workflow-status.",
    });
  } catch (e) {
    console.error("Trigger sync error:", e);
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
