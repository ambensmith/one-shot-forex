/**
 * Vercel Serverless Function: Check GitHub Actions workflow run status.
 * GET /api/workflow-status?run_id=12345
 *
 * Returns: { status, conclusion, html_url }
 *
 * Requires env vars: GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO
 */

const GITHUB_API = "https://api.github.com";

export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  if (req.method === "OPTIONS") return res.status(200).end();

  const token = process.env.GITHUB_TOKEN;
  const owner = process.env.GITHUB_OWNER;
  const repo = process.env.GITHUB_REPO;

  if (!token || !owner || !repo) {
    return res.status(500).json({ error: "Missing GitHub env vars" });
  }

  const runId = req.query?.run_id;

  if (!runId) {
    // No run_id: return the most recent workflow_dispatch run
    try {
      const resp = await fetch(
        `${GITHUB_API}/repos/${owner}/${repo}/actions/runs?event=workflow_dispatch&per_page=1`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            Accept: "application/vnd.github+json",
          },
        }
      );
      if (!resp.ok) {
        return res.status(resp.status).json({ error: "Failed to fetch runs" });
      }
      const data = await resp.json();
      const runs = data.workflow_runs || [];
      if (runs.length === 0) {
        return res.status(200).json({ status: "none", message: "No workflow runs found" });
      }
      const run = runs[0];
      return res.status(200).json({
        run_id: run.id,
        status: run.status,
        conclusion: run.conclusion,
        html_url: run.html_url,
        created_at: run.created_at,
      });
    } catch (e) {
      return res.status(500).json({ error: e.message });
    }
  }

  try {
    const resp = await fetch(
      `${GITHUB_API}/repos/${owner}/${repo}/actions/runs/${runId}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/vnd.github+json",
        },
      }
    );

    if (!resp.ok) {
      return res.status(resp.status).json({ error: `Run ${runId} not found` });
    }

    const run = await resp.json();
    return res.status(200).json({
      run_id: run.id,
      status: run.status,
      conclusion: run.conclusion,
      html_url: run.html_url,
      created_at: run.created_at,
      updated_at: run.updated_at,
    });
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}
