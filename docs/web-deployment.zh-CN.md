# Vibio SEO Next.js 网页版部署

网页版使用 Next.js App Router、React、Tailwind CSS 与 TypeScript。页面、多模型代理、隐私门禁、知识加载和 URL 审计都运行在 Vercel Node.js Functions 中；仓库中的 Python runtime 继续服务原始 Skill，但不参与网页部署。

模型采用 BYOK。部署项目不需要配置 DeepSeek、MiMo 或其他模型 API Key。

## 本地运行

需要 Node.js 20.9 或更高版本。

```bash
npm install
npm run dev
```

浏览器访问 `http://localhost:3000`。页面和 `/api/*` Route Handlers 由同一个 Next.js 进程提供。

## Vercel 控制台

1. 把所有新增文件提交到 Git；`git ls-files src/app/api/analyze/route.ts` 必须能输出路径。
2. 在 Vercel 中导入当前 Git 仓库，Root Directory 保持仓库根目录。
3. Framework Preset 选择 Next.js。`vercel.json` 只用于明确框架，不再声明 Python entrypoint。
4. 不要添加模型 API Key 环境变量。用户在页面中输入 Key，Key 仅随本次请求转发给所选官方接口。
5. 部署后检查 `/api/health`，再用低额度测试 Key 完成一次小范围运行。

已登录 Vercel CLI 时也可以执行：

```bash
vercel
vercel --prod
```

## 运行边界

- “自动跑全流程”由当前浏览器逐阶段编排，页面需保持打开；公开 URL 在正常流程中只抓取一次，限流或网络失败后续跑会重试，证据恢复时会重新运行已完成阶段。
- 默认依次生成审计、关键词、计划、修复草案、内容和链接产物；只有存在明确下滑信号时才运行恢复，只有已上线变更或可比测量证据时才运行复盘。
- 自动流程仅使用已配置的模型、公开 URL 和上传证据。界面不会把 GSC、GA4、CRM、CMS 或代码仓库显示为已连接，除非后续真正实现对应的 OAuth/API 连接器。
- URL 审计最多抓取 10 页，每个响应最多 2 MiB；它检查 HTTP 源码，不执行 JavaScript。
- 抓取器拒绝本机、私网、链路本地、凭据 URL 与混合 DNS，并把请求固定到已验证的公网 IP。
- 证据包最多 6 个文本文件，前端限制为总计 90 KiB；服务端上限为 96 KiB。
- API Key 不写入项目历史、日志或服务端存储，只在当前浏览器会话和单次服务端请求内存在。
- 项目与报告历史存放在当前浏览器的 `localStorage`，没有跨设备同步。
- 首版不直接部署代码、不修改 CMS、不发送外联、不操作 GSC 或广告账户。

## 发布前检查

```bash
npm run typecheck
npm test
npm run build
pytest -q
python scripts/validate_repo.py --strict
python scripts/eval_runner.py --strict
git diff --check
```
