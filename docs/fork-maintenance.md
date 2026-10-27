# local-customizations 分支维护手册

本文件记录 fork 自有分支 `local-customizations` 的维护事务：与上游的同步策略、GHCR 镜像构建、局域网部署更新流程、已知风险与维护台账。fork 的全部自研改动都在这个分支上，`master` 仅作上游镜像。

## 分支定位

- `master`：上游镜像分支，跟随 `upstream/master`，不做任何本地修改。同步方式见下文「上游同步策略」。
- `local-customizations`：fork 全部自研改动所在分支，基于最新 master 变基维护；push 自动触发 GHCR 镜像构建。
- 自研内容四类：
  1. **remote policy**：默认外部配置置空、移除硬编码远程默认（上游在 `applyCommonScalarSettings` 中的集中默认）与默认 ruleset 中的远程条目——空值即不加载任何远程模板/规则；reload 时清理残留的 `defaultExtConfig`。
  2. **GHCR 自主分发**：`.github/workflows/build-fork-ghcr.yml` 构建 linux/amd64 镜像发布到 `ghcr.io/geekxtop/subconverter-extended`。
  3. **部署配置**：docker-compose 指向 fork GHCR 镜像与本地 `MANAGED_CONFIG_PREFIX`。
  4. **回归测试与文档**：`tests/test_default_remote_policy.py`、`tests/test_fork_ghcr_workflow.py`、`tests/test_verify_amd64_manifest.py`，以及 `docs/superpowers/` 下的设计/计划文档与本手册。

## 上游同步策略（2026-10-27 确立）

- 上游曾强推重写 master 历史。此后对纯镜像的 `master` 做同步，**必须重置而非合并**：`git fetch upstream && git reset --hard upstream/master && git push --force-with-lease origin master`。合并会因历史重写产生约 95 个假冲突并永久污染 merge-base，不得使用。
- `local-customizations` 变基只重放 fork 自有提交：`git rebase --onto master <fork 起点> local-customizations`。**不要**让 rebase 重放旧上游历史——上游重写中被改掉/丢弃的旧提交会与 fork 提交一起被误重放（首次变基即因此重放了 8 个无关旧提交，已中止改用 `--onto`）。
- 当前 fork 提交链起点：旧 master tip `88e41ea`；变基前状态备份在本地分支 `backup/local-customizations-pre-rebase`（`7dd6f82`），确认无回滚需求后可删。
- 动机核对结论（2026-10-27）：除 fallback 语义方向一致外，上游未采纳 fork 任何一项动机（硬编码远程默认、示例配置远程默认、默认 ruleset 远程条目、reload 残留均仍在），fork 改动全部仍然必要。上游正往「默认配置与远程依赖分层」方向走（默认集中为单一常量、远程规则拆出可选 `rulesets_remote.txt`），分歧面在收窄。

## GHCR 镜像构建

- 触发：push 到 `local-customizations`（README 等路径豁免）或手动 `workflow_dispatch`。
- 流程：Python 回归基线（`unittest discover` 全目录，含上游测试）→ 依赖快照校验 → 构建 `ci-<sha>` 候选镜像（此步即编译门禁）→ 冒烟测试 → 校验分支头未前进 → 晋升 `latest` / `local-customizations` / `sha-<sha>` → 校验 amd64 manifest。
- 冒烟测试为 fork 自有内联步骤（2026-10-27 起）：容器按 digest 启动、`/version` 响应、容器内 TZ=Asia/Shanghai、`/base/Custom_OpenClash_Rules` 不存在、已移除的 revision 标签不存在、COCR 路由返回 404。
- 已知脆弱依赖：`scripts/ci/docker-build-args.sh` 仍为上游共有文件。上游若再删除（如本次删除 `.github/actions/`、冒烟脚本、`tests/fixtures/` 那样），构建会在对应步骤失败；届时应将其收编为 fork 自有文件。教训：**fork CI 只应依赖 fork 自有文件**。

## 局域网部署（192.168.100.105）

- 主机 `root@192.168.100.105`（Ubuntu），compose 目录 `/root/SubConverter-Extended`，容器名 `SubConverter-Extended`，镜像 `ghcr.io/geekxtop/subconverter-extended:latest`。
- 更新流程：
  1. 先确认分支 push 触发的构建已 success（`gh run list -R GeekXtop/SubConverter-Extended --workflow build-fork-ghcr.yml`）。
  2. `ssh root@192.168.100.105`，执行 `cd /root/SubConverter-Extended && docker compose pull && docker compose up -d`。
  3. 线上核验：容器 Up、镜像 `revision` 标签等于目标提交、`curl -s http://localhost:25500/version` 返回 200、容器内 TZ 与策略检查（无 COCR 产物、COCR 路由 404）通过。
- 回滚：`docker compose down` 后在 compose 中将镜像固定为旧 digest（如 `ghcr.io/geekxtop/subconverter-extended@sha256:<旧digest>`）再 `up -d`。

## 维护台账

### 2026-10-27 上游历史重写全量同步 + 变基 + CI 修复

- 上游（Aethersailor）强推重写 master。fork master 经核实为纯镜像（相对上游的全部「独有」提交均出自上游作者与 bot），重置到 `9c95d23` 并以 `--force-with-lease` 强推 origin。
- `local-customizations` 变基：11 个 fork 提交重放至新 master。冲突解决要点：settings.cpp 三处旧结构冲突取新基，fork 意图落在新集中点 `applyCommonScalarSettings`（删常量 + 换注释）；`resetReloadableSettings` 同时保留上游新增的 `beginSecuritySettingsLoad()` 与 fork 的 `defaultExtConfig.clear()`；三份 pref.example 置空默认；docker-compose 合并双方（fork 镜像行 + 上游安全档位注释）。
- 过程事故两起，均已修复并复核：① rebase 初次误重放 8 个旧上游提交，改 `--onto` 后解决；② 一次冲突解决脚本因换行符不匹配失败后 `git add` 无条件执行，带冲突标记的文件进入中途提交，已用 amend + `--onto` 重放修复。
- 新增提交 `test(local): adapt remote policy guard assertions to upstream restructure`：上游重构后 fallback 守卫由 `global.fallbackToDefaultExternalConfig` 改为 `settings.*` / `settings_->`，测试断言更新为访问方式无关写法。
- 构建失败一起：上游重写删除了 `.github/actions/` 全部本地 action、`scripts/run-*-smoke.py` 与 `tests/fixtures/`，fork 工作流引用的 `smoke-docker-image` action 随之消失（8 月构建时旧文件还在故未暴露）。冒烟步骤已内联为 fork 自有精简版，修复提交 `b8e6d07`，构建恢复绿色。
- 上游版本标签 88 个（v1.5.0–v1.10.5 等）推送至 origin。

### 2026-10-27 部署更新（192.168.100.105）

- 镜像：`local-7dd6f8205b8d`（2026-08-06 构建，digest `sha256:0809fab4…`）→ `local-b8e6d0786f0a`（digest `sha256:dd7c78ed…`）。
- 方式：`docker compose pull && docker compose up -d`，容器重建。
- 线上核验：容器 Up、revision 标签 = `b8e6d0786f0a5323d29120027ff658e4004bb34c`、`/version` HTTP 200、TZ=Asia/Shanghai、无 `/base/Custom_OpenClash_Rules`、COCR 路由 404。
- 本次部署同时完成了新分支代码（含 settings.cpp 改动）的首次真机验证。
