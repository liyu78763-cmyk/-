const GITHUB_API_VERSION = "2022-11-28";

export default {
  async fetch() {
    return new Response("crossborder GitHub dispatch worker is running\n", {
      headers: { "content-type": "text/plain; charset=utf-8" },
    });
  },

  async scheduled(event, env, ctx) {
    ctx.waitUntil(dispatchGithubWorkflow(env));
  },
};

async function dispatchGithubWorkflow(env) {
  const config = readConfig(env);
  const endpoint =
    `https://api.github.com/repos/${encodeURIComponent(config.owner)}` +
    `/${encodeURIComponent(config.repo)}/actions/workflows/` +
    `${encodeURIComponent(config.workflow)}/dispatches`;

  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      accept: "application/vnd.github+json",
      authorization: `Bearer ${config.githubToken}`,
      "content-type": "application/json",
      "user-agent": "crossborder-dingtalk-cloudflare-dispatch/0.1",
      "x-github-api-version": GITHUB_API_VERSION,
    },
    body: JSON.stringify({
      ref: config.ref,
      inputs: {
        dry_run: config.dryRun,
      },
    }),
  });

  if (response.status !== 204) {
    const detail = await response.text();
    throw new Error(`GitHub workflow dispatch failed: ${response.status} ${detail}`);
  }
}

function readConfig(env) {
  const config = {
    githubToken: requireEnv(env, "GITHUB_TOKEN"),
    owner: env.GITHUB_OWNER || "liyu78763-cmyk",
    repo: env.GITHUB_REPO || "-",
    workflow: env.GITHUB_WORKFLOW || "daily-crossborder-news.yml",
    ref: env.GITHUB_REF || "main",
    dryRun: String(env.DRY_RUN || "false"),
  };

  if (!["true", "false"].includes(config.dryRun)) {
    throw new Error("DRY_RUN must be either true or false");
  }
  return config;
}

function requireEnv(env, name) {
  const value = env[name];
  if (!value) {
    throw new Error(`${name} is required`);
  }
  return value;
}
