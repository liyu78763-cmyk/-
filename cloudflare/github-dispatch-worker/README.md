# Cloudflare 备用触发器

这个 Worker 用作 GitHub Actions 定时任务的备用触发器。

- 触发时间：工作日北京时间 10:30
- 实际发送：仍由 GitHub Actions 执行
- 钉钉密钥：仍只保存在 GitHub Secrets
- GitHub Token：只放在 Cloudflare Worker Secret，不写进代码

## 需要的 GitHub Token

创建 Fine-grained personal access token：

- Repository access：只选择 `liyu78763-cmyk/-`
- Repository permissions：
  - `Actions`: `Read and write`
  - `Metadata`: 默认只读

## Cloudflare 部署步骤

进入本目录：

```powershell
cd cloudflare\github-dispatch-worker
```

登录 Cloudflare：

```powershell
npx wrangler login
```

保存 GitHub Token 到 Cloudflare Secret：

```powershell
npx wrangler secret put GITHUB_TOKEN
```

命令提示输入值时，粘贴 GitHub Token。不要把 Token 写进任何项目文件。

部署 Worker：

```powershell
npm install
npm run deploy
```

部署后，Cloudflare 会按 `wrangler.toml` 中的 cron 自动运行：

```text
30 2 * * 1-5
```

这是 UTC 时间，对应北京时间工作日 `10:30`。

## 以后如何更换 GitHub Token

只要 Secret 名称仍然叫 `GITHUB_TOKEN`，更换 Token 不需要改代码，也不影响 Worker 定时运行。

### 方法一：Cloudflare 网页后台

1. 打开 Cloudflare Dashboard。
2. 进入 `Workers & Pages`。
3. 选择 Worker：`crossborder-github-dispatch`。
4. 进入 `Settings`。
5. 找到 `Variables and Secrets`。
6. 找到 Secret：`GITHUB_TOKEN`。
7. 点击编辑或更新，把新的 GitHub Token 粘贴进去。
8. 保存并部署。

### 方法二：Wrangler 命令行

进入本目录：

```powershell
cd cloudflare\github-dispatch-worker
```

执行：

```powershell
npx wrangler secret put GITHUB_TOKEN
```

命令提示输入值时，粘贴新的 GitHub Token。这个命令会覆盖旧的 `GITHUB_TOKEN` Secret。

### 建议顺序

1. 先在 GitHub 创建新 Token，权限保持 `Actions: Read and write`。
2. 到 Cloudflare 更新 `GITHUB_TOKEN`。
3. 确认下一次触发正常后，再删除旧 Token。
4. 不要修改 Secret 名称；代码只读取 `GITHUB_TOKEN` 这个名字。

## 本地测试

本地测试不要使用真实发送，先把 `wrangler.toml` 中：

```toml
DRY_RUN = "false"
```

临时改成：

```toml
DRY_RUN = "true"
```

再执行：

```powershell
npx wrangler dev --test-scheduled
```

浏览器访问本地 scheduled 测试地址后，会触发 GitHub Actions 的 dry-run，不会发送钉钉。

测试完成后，把 `DRY_RUN` 改回 `"false"` 并重新部署。

## 工作原理

Worker 调用 GitHub REST API：

```text
POST https://api.github.com/repos/liyu78763-cmyk/-/actions/workflows/daily-crossborder-news.yml/dispatches
```

请求体：

```json
{"ref":"main","inputs":{"dry_run":"false"}}
```

项目的 GitHub Actions workflow 会使用当天 `run-key` 防重复。如果 GitHub 自带 schedule 已经发送成功，备用触发不会重复发送。
