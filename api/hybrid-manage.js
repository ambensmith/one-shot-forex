/**
 * Vercel Serverless Function: Manage hybrid configs directly via GitHub Contents API.
 * Reads/modifies frontend/public/data/hybrids.json in the repo — no workflow needed (~5s).
 *
 * POST /api/hybrid-manage
 * Body: { action: "toggle"|"delete"|"toggle-all", id?: number, is_active?: boolean }
 *
 * Requires env vars: GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO
 */

const GITHUB_API = "https://api.github.com";
const HYBRIDS_PATH = "frontend/public/data/hybrids.json";

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

  const { action, id, is_active } = req.body || {};

  if (!action || !["toggle", "delete", "toggle-all"].includes(action)) {
    return res.status(400).json({ error: "action must be 'toggle', 'delete', or 'toggle-all'" });
  }

  if ((action === "toggle" || action === "delete") && id == null) {
    return res.status(400).json({ error: "'id' is required for toggle/delete" });
  }

  try {
    // 1. Read current hybrids.json from repo
    const getResp = await fetch(
      `${GITHUB_API}/repos/${owner}/${repo}/contents/${HYBRIDS_PATH}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/vnd.github+json",
        },
      }
    );

    if (!getResp.ok) {
      return res.status(404).json({ error: "hybrids.json not found in repo" });
    }

    const fileData = await getResp.json();
    const sha = fileData.sha;
    const content = Buffer.from(fileData.content, "base64").toString("utf-8");
    const data = JSON.parse(content);
    let hybrids = data.hybrids || [];

    // 2. Apply the action
    let commitMsg;

    if (action === "toggle") {
      const target = hybrids.find((h) => h.id === id);
      if (!target) {
        return res.status(404).json({ error: `Hybrid with id ${id} not found` });
      }
      target.is_active = is_active ? 1 : 0;
      commitMsg = `${is_active ? "Activate" : "Deactivate"} hybrid: ${target.name}`;
    } else if (action === "delete") {
      const before = hybrids.length;
      hybrids = hybrids.filter((h) => h.id !== id);
      if (hybrids.length === before) {
        return res.status(404).json({ error: `Hybrid with id ${id} not found` });
      }
      data.hybrids = hybrids;
      commitMsg = `Delete hybrid config ${id}`;
    } else if (action === "toggle-all") {
      const active = is_active ? 1 : 0;
      hybrids.forEach((h) => { h.is_active = active; });
      commitMsg = `${is_active ? "Enable" : "Disable"} all hybrids`;
    }

    // 3. Write back via GitHub Contents API
    const newContent = Buffer.from(
      JSON.stringify(data, null, 2) + "\n",
      "utf-8"
    ).toString("base64");

    const putResp = await fetch(
      `${GITHUB_API}/repos/${owner}/${repo}/contents/${HYBRIDS_PATH}`,
      {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          Accept: "application/vnd.github+json",
        },
        body: JSON.stringify({
          message: commitMsg,
          content: newContent,
          sha,
        }),
      }
    );

    if (!putResp.ok) {
      const errText = await putResp.text();
      return res.status(putResp.status).json({
        error: `Failed to save: ${errText.slice(0, 200)}`,
      });
    }

    return res.status(200).json({
      status: "ok",
      message: commitMsg,
      hybrids: data.hybrids,
    });
  } catch (e) {
    console.error("Hybrid manage error:", e);
    return res.status(500).json({ error: e.message });
  }
}
