# SubConverter-Extended 分支同步与默认远程配置设计

## 目标

让 fork 的上游同步与本地定制长期分离，同时把上游新加入的、会主动依赖 Aethersailor 远程资源的默认配置改为不自动加载，保留用户显式指定远程 URL 时的兼容能力。

## 已确认的仓库状态

- 当前 `master` 指向 `origin/master` 的 `a178233`，且是 `upstream/master` 的祖先。
- 上游已推进到 `88e41ea`（`v1.3.0` 之后的修订）。
- 当前工作区有六个未提交的本地定制文件：三个偏好示例、`docker-compose.yml`、`src/handler/interfaces.cpp`、`src/handler/settings.cpp`。
- 同目录项目采用“干净同步分支 + 本地定制分支”的模式；本项目采用 `master` 与 `local-customizations` 两个分支名。

## 分支模型

`master` 只跟随 `upstream/master`，并推送到 fork 的 `origin/master`。它不包含本地 fork 定制，便于查看上游差异和下一次快速前移。

`local-customizations` 从最新 `master` 构建，承载本地镜像、服务地址和默认配置策略等修改，推送到 `origin/local-customizations`。每次同步先快进 `master`，再将该分支变基到 `master`，冲突按下述配置策略解决。

## 默认远程配置策略

1. `base/pref.example.ini`、`base/pref.example.toml`、`base/pref.example.yml` 的 `default_external_config` 保持为空；注释明确说明空值表示不加载默认外部模板。
2. `src/handler/settings.cpp` 的 INI/TOML/YAML 读取路径不再把空值替换成 `Custom_OpenClash_Rules` 远程地址。用户在配置中显式填写的 URL 仍照常读取。
3. 上游新版 `base/snippets/rulesets.toml` 中会随示例配置自动加载的 `Custom_OpenClash_Rules` 远程规则项移除，保留不依赖该站点的内置 GEOSITE/GEOIP/FINAL 规则。
4. `src/handler/cocr_source_url.cpp` 的显式 COCR URL 识别与可选重写逻辑保留；它只有在用户/配置提供相应 URL 且启用 `fallback_enabled` 时才生效，不属于默认自动拉取。
5. 其他依赖项、文档链接和用户显式规则集示例不作无关改写。

## 冲突与安全处理

- 先把现有六个工作区修改提交到 `local-customizations`，再快进 `master`，确保任何同步操作都有可恢复提交。
- 变基时保留本地 Docker 镜像/前缀、空默认外部配置和无硬编码回退；吸收上游新增的配置字段和实现。
- 只向 `origin` 推送；不向 `upstream` 写入。

## 验收标准

- `master` 与 `upstream/master` 同一提交，工作区干净。
- `local-customizations` 基于 `master`，包含本地定制提交，并在 `origin/local-customizations` 可见。
- 自动化策略测试确认三种示例配置没有非空 `default_external_config`，运行时代码没有隐式 COCR 默认 URL，TOML 默认规则集没有活动的 COCR 远程条目。
- 项目可成功构建；已有兼容性/安全测试不回归。
