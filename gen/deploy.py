# -*- coding: utf-8 -*-
"""deploy.py -- 双部署编排（解耦：只搬运产物，不碰生成逻辑）

用法（gen/ 目录下）:
  python -I deploy.py gh            # dist-mirror -> ai-db-weekly 仓 gh-pages 分支 + 开通 GitHub Pages
  python -I deploy.py gh --dry-run  # 只做分支构建，不 push 不开通
  python -I deploy.py cf            # dist -> wrangler pages deploy（需先 npx wrangler login 一次）

前置:
  gh  : dist-mirror/ 已由 build.py --mirror 产出；git push 可达（Clash 在线）
  cf  : dist/ 已由 build.py 产出；wrangler 已登录；CF 项目名在 config.deploy.cf_project
"""
import argparse, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SLUG = "zqf20096327/ai-db-weekly"

def run(cmd, cwd=None, check=True, **kw):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, encoding="utf-8", errors="replace", **kw)
    if check and p.returncode != 0:
        sys.exit(f"FAIL {' '.join(cmd[:3])}...\n{p.stdout}\n{p.stderr}")
    return p

def deploy_gh(dry):
    src = os.path.join(REPO, "dist-mirror")
    if not os.path.isdir(src): sys.exit("dist-mirror/ 不存在：先跑 python -I build.py --mirror")
    tmp = tempfile.mkdtemp(prefix="ghpages_")
    try:
        run(["git", "worktree", "add", "--detach", tmp], cwd=REPO)          # 挂临时 worktree
        run(["git", "branch", "-D", "gh-pages"], cwd=tmp, check=False)      # 产物分支每次全量重建（干跑残留也清）
        run(["git", "checkout", "--orphan", "gh-pages"], cwd=tmp)           # 孤儿分支=无历史，仓库不背 220MB 负担
        run(["git", "rm", "-rf", "."], cwd=tmp, check=False)
        for item in os.listdir(src):
            s = os.path.join(src, item)
            shutil.copytree(s, os.path.join(tmp, item), dirs_exist_ok=True) if os.path.isdir(s) \
                else shutil.copyfile(s, os.path.join(tmp, item))
        run(["git", "add", "-A"], cwd=tmp)
        run(["git", "-c", "core.autocrlf=false", "commit", "-m", "deploy: 站点产物（镜像变体 noindex）"], cwd=tmp)
        n = int(run(["git", "ls-files"], cwd=tmp).stdout.strip().count("\n") or 0) + 1
        print(f"gh-pages 分支就绪：{n} 个文件")
        if dry: print("dry-run：未 push"); return
        run(["git", "push", "-f", "origin", "gh-pages"], cwd=tmp)
        p = run(["gh", "api", "-X", "POST", f"repos/{SLUG}/pages",
                 "-f", "source[branch]=gh-pages", "-f", "source[path]=/"], check=False)
        if p.returncode != 0:                        # 已开通(409)也必须 PUT 切源，别信旧源配置
            p2 = run(["gh", "api", "-X", "PUT", f"repos/{SLUG}/pages",
                      "-f", "source[branch]=gh-pages", "-f", "source[path]=/"], check=False)
            if p2.returncode != 0: print("WARN Pages 开通/更新:", p2.stdout, p2.stderr)
        info = run(["gh", "api", f"repos/{SLUG}/pages"], check=False)
        url = ""
        try: url = json.loads(info.stdout).get("html_url", "")
        except Exception: pass
        print("GH Pages 就绪：" + (url or "（稍等构建，gh api repos/%s/pages 可查）" % SLUG))
    finally:
        run(["git", "worktree", "remove", "--force", tmp], cwd=REPO, check=False)

def deploy_cf():
    src = os.path.join(REPO, "dist")
    if not os.path.isdir(src): sys.exit("dist/ 不存在：先跑 python -I build.py")
    cfg = json.load(open(os.path.join(HERE, "config.json"), encoding="utf-8"))
    proj = (cfg.get("deploy") or {}).get("cf_project") or "dbhub"
    print(f"wrangler 上传 {src} -> CF Pages 项目 {proj}（首次会自动建项目，域名=/{proj}.pages.dev）")
    run(["npx", "--yes", "wrangler", "pages", "deploy", src, "--project-name", proj,
         "--commit-dirty=true"], cwd=REPO)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", choices=["gh", "cf"])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    deploy_gh(a.dry_run) if a.target == "gh" else deploy_cf()

if __name__ == "__main__":
    main()
