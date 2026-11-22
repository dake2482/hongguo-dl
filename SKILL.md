---
name: hongguo-dl
description: 红果短剧整剧下载。给一个剧名即可完成全流程：搜索候选 → 用户确认第一集 → 批量下载全部剧集 → 校验文件。基于本地 hongguo-web 服务（免登录、1080p），服务未启动时自动拉起。
---

# 红果短剧下载

用户给出剧名 → 下载整部剧。三步工作流：**搜索 → 确认 → 下载**。

## 使用流程

### 1. 搜索

```bash
python3 scripts/hongguo.py search "剧名"
```

输出候选列表（剧名 / 总集数 / 热度 / series_id / **第一集播放地址** / 简介）。

### 2. 让用户确认

把候选列表里的**第一集播放地址**（`hongguoduanju.com/player/<series_id>/<vid>`）给用户打开核对，确认是这部剧再下载。同名/同设定的剧很多（例：「兽语」类至少 3 部，主角都叫林北），不要跳过确认。

### 3. 下载整剧

```bash
python3 scripts/hongguo.py download <series_id>              # 全部集
python3 scripts/hongguo.py download <series_id> --start 1 --end 5   # 只下区间
```

脚本会创建下载任务并轮询到完成，最后校验目录里的 mp4 数量与总大小，打印保存位置。
文件为 1080p HEVC MP4（`第N集.mp4`），保存目录由 hongguo-web 检出目录 `server/config/config.json` 的 `runtime.download.dir` 决定（默认其 `download/<剧名>/`，支持本机自定义绝对路径）；临时覆盖用环境变量 `HONGGUO_DOWNLOAD_DIR`。

中断接管：`python3 scripts/hongguo.py status <task_id>`（download 启动时会打印 task_id）。

## 服务管理

脚本首次运行时自动完成：查找/克隆 [hongguo-web](https://github.com/dake2482/hongguo-web) → 启动本地服务（127.0.0.1:8000）→ 获取 api_key。之后所有命令复用运行中的服务。

- 显式指定 hongguo-web 检出目录：环境变量 `HONGGUO_WEB_DIR`（默认依次找 `../hongguo-web`、`~/hongguo-web`、`~/.hongguo/hongguo-web`，都没有则克隆到最后一个位置）
- 换端口：`HONGGUO_PORT`（默认 8000）
- 用完关闭服务：`python3 scripts/hongguo.py stop`（也可以留着，很轻量）
- 服务日志：`$TMPDIR/hongguo-web.log`

## 依赖

| 依赖 | 说明 |
|---|---|
| Python 3.8+ | 本 skill 脚本运行时（纯标准库，无需 pip install） |
| Node 18+ | hongguo-web 服务端运行时。**零第三方依赖，不需要 npm install** |
| git | 仅首次自动克隆 hongguo-web 时需要 |
| 网络 | 需能直连 `*.fqnovel.com`（App 接口）与 `qznovelvod.com`（视频 CDN）；不需要任何账号 |
| 磁盘 | 1080p 一部剧约 200–500MB |
| ffmpeg | **不需要**（视频解密与封装为纯 JS 实现） |

全新机器（无任何部署）开箱即用：脚本自动克隆 hongguo-web 并拉起服务；若 8000 端口已有 hongguo-web 服务在跑（含用户手动部署的），健康检查通过后直接复用，不会重复启动。

## 排障

- 服务 60 秒未就绪 → 看 `$TMPDIR/hongguo-web.log`；端口被占用时用 `HONGGUO_PORT` 换端口
- 下载任务个别集失败 → 任务会列出失败集；重跑同一条 download 命令即可续传
- 搜索无结果 → 换更短的关键词（如全名搜不到时去掉标点只搜主干词）
- **突然全部空响应/取直链失败** → 大概率红果上游接口协议又变了（近期已变过两次）。处理：进 hongguo-web 检出目录 `git pull`，然后 `python3 scripts/hongguo.py stop` 停旧服务、重跑任意命令拉起新版；skill 本身不用改
- 全新服务器部署前网络自检：`curl -sS -o /dev/null -w "%{http_code}" https://api5-normal-sinfonlineb.fqnovel.com/` 返回 404 即接口可达（海外机器注意 CDN 可能有地域限制）
