# hongguo-dl · 红果短剧整剧下载 Skill

给一个剧名，完成全流程：**搜索 → 确认第一集 → 下载整部剧 → 校验文件**。

这是一个面向 AI 助手（ZCode / Claude Code 等）的 [Agent Skill](https://code.claude.com/docs/en/skills) 封装：把「具名下载红果短剧」这件事变成一句话的事。底层能力来自 [hongguo-web](https://github.com/dake2482/hongguo-web)（红果短剧网页版服务，App 接口路线，**免登录、1080p**），本仓库只做编排与命令行封装。

```
你：下载《能听懂兽语，我下山后爆火了》
AI：搜索 → 给你第一集链接确认 → 下载 73 集 → 汇报保存位置
```

## 快速开始

### 安装为 Skill

```bash
# ZCode
git clone https://github.com/dake2482/hongguo-dl ~/.zcode/skills/hongguo-dl

# Claude Code
git clone https://github.com/dake2482/hongguo-dl ~/.claude/skills/hongguo-dl
```

装好后对 AI 说「下载短剧《XXX》」即可，AI 会按 [SKILL.md](SKILL.md) 的工作流执行。

### 直接当命令行用

```bash
python3 scripts/hongguo.py search "能听懂兽语"          # 搜索候选 + 第一集播放地址
python3 scripts/hongguo.py download 7701387039249288217  # 下载整剧（73 集）
python3 scripts/hongguo.py download 7701387039249288217 --start 1 --end 5   # 只下前 5 集
python3 scripts/hongguo.py status dl_xxxxxxxx_1          # 接管进行中的任务
python3 scripts/hongguo.py stop                          # 停止本地服务
```

下载结果：1080p HEVC MP4（`第N集.mp4`），保存在 hongguo-web 检出目录的 `download/<剧名>/` 下。

## 工作流（AI 视角）

1. **search**：按剧名搜索，拿到候选（剧名 / 总集数 / 热度 / series_id / 第一集地址）
2. **确认**：把第一集播放地址给用户打开核对——红果同名与同设定的剧很多，不能跳过
3. **download**：创建批量下载任务，轮询到完成，最后校验 mp4 数量与大小并汇报保存位置

## 依赖

| 依赖 | 说明 |
|---|---|
| Python 3.8+ | 仅标准库，无需 pip install |
| Node 18+ | [hongguo-web](https://github.com/dake2482/hongguo-web) 服务端运行时。**零第三方依赖，不需要 npm install** |
| git | 仅首次自动克隆 hongguo-web 时需要 |
| 网络 | 需能直连 `*.fqnovel.com`（App 接口）与 `qznovelvod.com`（视频 CDN）；全程无需账号 |
| ffmpeg | **不需要**（视频解密与封装在 hongguo-web 内为纯 JS 实现） |

首次运行时脚本会自动完成：查找/克隆 hongguo-web → 启动本地服务（127.0.0.1:8000）→ 获取 api_key，之后所有命令复用该服务。

## 配置

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `HONGGUO_WEB_DIR` | 自动探测 | hongguo-web 检出目录（探测顺序：`../hongguo-web` → `~/hongguo-web` → `~/.hongguo/hongguo-web`，都没有则克隆） |
| `HONGGUO_PORT` | `8000` | 本地服务端口 |

服务日志在 `$TMPDIR/hongguo-web.log`。

## 常见问题

- **下载个别集失败**：任务会列出失败集，重跑同一条 download 命令即可续传。
- **服务起不来**：看日志；端口冲突时换 `HONGGUO_PORT`。
- **搜索不到**：换更短的关键词（去掉标点只搜主干词）。

## 许可

本仓库（skill 编排与脚本）以 [MIT](LICENSE) 发布。

运行时依赖的 [hongguo-web](https://github.com/dake2482/hongguo-web) 为独立项目（GPL-3.0，含上游 [jackotom/hongguo-drama](https://github.com/jackotom/hongguo-drama) 与 [tsukiyo-zero/hongguotv](https://github.com/tsukiyo-zero/hongguotv) 的衍生代码），本仓库不复制其代码，仅在运行时克隆并调用其本地 HTTP API。

本项目仅供个人学习与备份用途，请勿用于再分发；下载内容的版权归权利方所有。
