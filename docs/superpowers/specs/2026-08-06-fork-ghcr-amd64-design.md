# Fork GHCR AMD64 构建设计

## 目标

让 `GeekXtop/SubConverter-Extended` 的 `local-customizations` 分支在每次有效代码推送后，由 GitHub Actions 构建、测试并发布仅支持 `linux/amd64` 的 fork 镜像。本地环境只负责同步上游、维护定制和推送代码，不再承担完整 C++/Docker 构建。

## 现状与约束

- 上游工作流只自动监听 `dev`，且构建模式只认识 `dev`、`master`、PR 和 release tag。
- 上游镜像名称硬编码为 `aethersailor/subconverter-extended`，并依赖 fork 中不存在的 Docker Hub 凭据，不能直接用于 fork 发布。
- `master` 必须继续作为纯上游同步分支；fork 构建配置只存在于 `local-customizations`。
- 只构建 `linux/amd64`，不添加 ARM runner、QEMU 或多架构 manifest。
- 镜像发布到 `ghcr.io/geekxtop/subconverter-extended`，使用仓库自带 `GITHUB_TOKEN` 的 `packages: write` 权限，不新增长期凭据。

## 方案

新增独立的 `.github/workflows/build-fork-ghcr.yml`，不修改上游的 `build-dockerhub.yml`。工作流在 `local-customizations` push 和手动触发时运行，先执行 Python 回归测试和依赖快照校验，再使用现有 Dockerfile、锁定依赖和 Docker 构建参数构建 `linux/amd64` 镜像。

构建先发布只属于当前提交的候选镜像，随后以候选 digest 运行项目现有 Docker smoke test。只有 smoke test 通过、且远端 `local-customizations` 仍指向本次提交时，才把该 digest 提升为以下标签：

- `latest`
- `local-customizations`
- `sha-<12 位提交哈希>`

这样失败或已过时的工作流不会覆盖可部署标签，同时保留按提交回滚的入口。

## 本地部署配置

`docker-compose.yml` 的镜像改为 `ghcr.io/geekxtop/subconverter-extended:latest`。部署端通过 `docker compose pull` 和 `docker compose up -d` 获取 GitHub 已验证的镜像，不需要本地编译或重新打标签。

## 安全与同步边界

- 工作流仅申请 `contents: read` 和 `packages: write`。
- 不登录 Docker Hub，不引用或发布 `aethersailor/*` 镜像。
- 不向 `upstream` 写入，也不修改纯上游 `master`。
- 使用 concurrency 取消同一分支的旧运行，并在提升标签前再次校验远端分支 SHA。
- GHCR 包在首轮构建后设为 public，便于 Compose 无认证拉取。

## 验证标准

- 静态策略测试确认触发分支、唯一平台、GHCR 命名、权限、候选测试后提升顺序和 Compose 镜像。
- 本地全部 Python unittest、同步守卫和 `git diff --check` 通过。
- GitHub Actions 首轮运行成功，包含 Docker 内部 C++ 测试与现有 smoke test。
- GHCR 的 `latest` manifest 仅包含 `linux/amd64`，并对应 `local-customizations` 最新提交。
