# 升级与回滚

当前 schema 版本：**7**（以 `lingshu_ng/store/schema.py` 为准，测试会校验本文）。

## 规则
- 新版本打开旧 schema 的库时自动迁移（v5→v6、v6→v7 会整体重建派生索引，大库首次打开较慢）。
- 迁移后的库，旧版本程序可能拒绝打开：升级前先执行 `lingshu-ng backup`。
- 回滚：停服务，安装旧版本，用升级前的备份 `restore`（见 OPERATIONS.md）。

## 升级步骤
1. `lingshu-ng doctor` 确认当前库健康。
2. `lingshu-ng backup` 备份。
3. `pip install -U lingshu-ng`，启动后再跑一次 `doctor`。
