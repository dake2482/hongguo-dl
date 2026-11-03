#!/usr/bin/env python3
"""红果短剧下载命令行封装（基于本地 hongguo-web 服务）。

用法：
  hongguo.py search <剧名>            搜索候选剧，展示 series_id 与第一集播放地址
  hongguo.py download <series_id> [--start N] [--end N] [--timeout 秒]
                                      整剧（或区间）批量下载并轮询到完成，最后校验文件
  hongguo.py status <task_id>         查询/接管一个进行中的下载任务
  hongguo.py stop                     停止本地 hongguo-web 服务

环境变量：
  HONGGUO_WEB_DIR   hongguo-web 仓库路径（缺省按 ../hongguo-web、~/hongguo-web、
                    ~/.hongguo/hongguo-web 顺序查找，最后不存在则自动 clone）
  HONGGUO_PORT      服务端口（默认 8000）

仅用 Python 标准库。
"""

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

REPO = "https://github.com/dake2482/hongguo-web"
DEFAULT_PORT = 8000
SERVER_LOG = os.path.join(os.environ.get("TMPDIR", "/tmp"), "hongguo-web.log")

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def port():
    try:
        return int(os.environ.get("HONGGUO_PORT", DEFAULT_PORT))
    except ValueError:
        return DEFAULT_PORT


def base():
    return f"http://127.0.0.1:{port()}"


def http(method, path, key=None, body=None, timeout=15):
    req = urllib.request.Request(base() + path, method=method)
    if key:
        req.add_header("x-api-key", key)
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, data=data, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------- 服务管理

def find_web_dir():
    env = os.environ.get("HONGGUO_WEB_DIR")
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for cand in ([env] if env else []) + [
        os.path.join(here, "..", "hongguo-web"),   # 与本 skill 同目录的检出
        os.path.expanduser("~/hongguo-web"),
        os.path.expanduser("~/.hongguo/hongguo-web"),
    ]:
        if os.path.isfile(os.path.join(cand, "server", "src", "main.js")):
            return os.path.abspath(cand)
    return None


def clone_web_dir():
    target = os.path.expanduser("~/.hongguo/hongguo-web")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    print(f"[setup] 克隆 hongguo-web 到 {target} …")
    r = subprocess.run(["git", "clone", "--depth", "1", REPO, target])
    if r.returncode != 0:
        sys.exit("[错误] 克隆 hongguo-web 失败，请检查网络或手动设置 HONGGUO_WEB_DIR")
    return target


def healthy():
    try:
        with urllib.request.urlopen(base() + "/health", timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def ensure_server():
    if healthy():
        return api_key()
    web = find_web_dir() or clone_web_dir()
    if not shutil.which("node"):
        sys.exit("[错误] 未找到 node（需要 Node 18+）")
    print(f"[setup] 启动 hongguo-web 服务（{web}，日志 {SERVER_LOG}）…")
    with open(SERVER_LOG, "ab") as log:
        subprocess.Popen(
            ["node", "server/src/main.js"], cwd=web, stdout=log, stderr=log,
            stdin=subprocess.DEVNULL, start_new_session=True)
    deadline = time.time() + 60
    while time.time() < deadline:
        if healthy():
            return api_key()
        time.sleep(1)
    sys.exit(f"[错误] 服务 60 秒内未就绪，请查看日志：{SERVER_LOG}")


def api_key():
    # /api-key 免鉴权，返回（或签发）本地链路密钥
    d = http("GET", "/api-key")
    key = d.get("api_key")
    if not key:
        sys.exit("[错误] 获取 api_key 失败")
    return key


def cmd_stop(_):
    web = find_web_dir()
    if web is None:
        print("未找到 hongguo-web 检出目录（如需指定请设 HONGGUO_WEB_DIR）")
        return
    subprocess.run(["node", "server/src/main.js", "--stop"], cwd=web)
    print("已请求停止服务")


# ---------------------------------------------------------------- 命令

EP_URL = "https://hongguoduanju.com/player/{sid}/{vid}"


def cmd_search(args):
    if not args:
        sys.exit("用法: hongguo.py search <剧名>")
    query = " ".join(args)
    key = ensure_server()
    q = urllib.parse.quote(query)
    d = http("GET", f"/search?q={q}&limit=10", key=key, timeout=30)
    results = d.get("results") or []
    if not results:
        print(f"没有搜索结果：{query}")
        return
    print(f"搜索「{query}」共 {len(results)} 条：\n")
    for i, r in enumerate(results, 1):
        sid = r.get("series_id")
        vid = r.get("vid")
        print(f"[{i}] {r.get('title')}  （全{r.get('episode_cnt')}集"
              f"{' · ' + r['hot'] if r.get('hot') else ''}"
              f"{' · 评分' + r['score'] if r.get('score') else ''}）")
        print(f"    series_id: {sid}")
        if vid:
            print(f"    第一集播放地址: {EP_URL.format(sid=sid, vid=vid)}")
        if r.get("category"):
            print(f"    类型: {r['category']}")
        if r.get("abstract"):
            print(f"    简介: {r['abstract'][:70]}…")
        print()
    print("确认剧目后：python3 hongguo.py download <series_id>")


def cmd_download(args):
    if not args:
        sys.exit("用法: hongguo.py download <series_id> [--start N] [--end N] [--timeout 秒]")
    sid = args[0]
    payload = {"series_id": sid}
    timeout_s = 1800
    rest = args[1:]
    i = 0
    while i < len(rest):
        if rest[i] == "--start" and i + 1 < len(rest):
            payload["start"] = int(rest[i + 1]); i += 2
        elif rest[i] == "--end" and i + 1 < len(rest):
            payload["end"] = int(rest[i + 1]); i += 2
        elif rest[i] == "--timeout" and i + 1 < len(rest):
            timeout_s = int(rest[i + 1]); i += 2
        else:
            sys.exit(f"未知参数：{rest[i]}")

    key = ensure_server()
    d = http("POST", "/download/task", key=key, body=payload, timeout=60)
    t = d.get("task") or {}
    task_id = t.get("id")
    print(f"任务已创建: {task_id}")
    print(f"剧名: {t.get('title')}  共 {t.get('total')} 集")
    print(f"保存目录: {t.get('dir')}")
    print(f"（中断后可用 status 接管: python3 hongguo.py status {task_id}）\n")

    t = wait_task(key, task_id, timeout_s)
    report(t)


def wait_task(key, task_id, timeout_s):
    deadline = time.time() + timeout_s
    last_line = ""
    while time.time() < deadline:
        d = http("GET", f"/download/task?id={urllib.parse.quote(task_id)}", key=key, timeout=15)
        t = d.get("task") or {}
        line = f"  进度 {t.get('done')}/{t.get('total')}  状态 {t.get('status')}"
        if line != last_line:
            print(line, flush=True)
            last_line = line
        if t.get("status") in ("done", "failed"):
            return t
        time.sleep(5)
    sys.exit(f"[超时] 任务 {task_id} 未在 {timeout_s}s 内完成；可用 status 命令继续跟踪")


def cmd_status(args):
    if not args:
        sys.exit("用法: hongguo.py status <task_id>")
    key = ensure_server()
    try:
        d = http("GET", f"/download/task?id={urllib.parse.quote(args[0])}", key=key, timeout=15)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            sys.exit("任务不存在或已过期")
        raise
    t = d.get("task") or {}
    print(f"{t.get('done')}/{t.get('total')}  状态 {t.get('status')}  目录 {t.get('dir')}")
    if t.get("failed"):
        print("失败集:", t["failed"])
    if t.get("status") not in ("done", "failed"):
        wait_task(key, args[0], 3600)
    else:
        report(t)


def report(t):
    failed = t.get("failed") or []
    print(f"\n任务{t.get('status')}：{t.get('done')}/{t.get('total')}，失败 {len(failed)} 集")
    if failed:
        print("失败集:", failed)
    d = t.get("dir")
    if d and os.path.isdir(d):
        files = sorted(f for f in os.listdir(d) if f.endswith(".mp4"))
        size = sum(os.path.getsize(os.path.join(d, f)) for f in files)
        print(f"目录校验：{len(files)} 个 mp4，共 {size / 1_000_000:.1f} MB")
        print(f"保存位置: {d}")
    if failed:
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "search":
        cmd_search(args)
    elif cmd == "download":
        cmd_download(args)
    elif cmd == "status":
        cmd_status(args)
    elif cmd == "stop":
        cmd_stop(args)
    else:
        sys.exit(f"未知命令：{cmd}\n\n{__doc__}")


if __name__ == "__main__":
    main()
