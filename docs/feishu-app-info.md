# 飞书应用信息

> 本文档记录飞书自建应用的基本信息。**App Secret 等敏感信息不得提交到 Git**，请使用团队密钥管理系统（如1Password/Vault）存储。

**项目代号**: pe-kb
**环境**: dev / staging / production
**应用名称规范**: `[项目代号]-[环境]` (例: pe-kb-dev)

---

## 应用基本信息

| 字段 | 值 |
|-----|---|
| App ID | `cli_xxxxxxxxxxxxxxxx` |
| App Secret | `[存储于密钥管理系统]` |
| 应用名称 | pe-kb-dev |
| 创建日期 | |
| 创建人 | |

---

## 权限申请状态

### P0 权限（Step 2 必须）

| 权限 scope | 用途 | 申请状态 | 审批通过日期 |
|-----------|------|---------|-------------|
| `wiki:wiki:readonly` | 读取知识空间 | 待申请 | |
| `docx:document:readonly` | 读取文档内容 | 待申请 | |
| `drive:drive:readonly` | 读取云空间 | 待申请 | |
| `drive:file:metadata:read` | 读取文件元信息 | 待申请 | |
| `drive:permission:member:read` | 读取文档成员权限 | 待申请 | |

### P1 权限（Step 8 前需要）

| 权限 scope | 用途 | 申请状态 | 审批通过日期 |
|-----------|------|---------|-------------|
| `contact:user.base:readonly` | 读取用户基本信息 | 待申请 | |
| `im:message.group_at_msg` | 接收群@消息 | 待申请 | |
| `im:message.p2p_msg` | 接收单聊消息 | 待申请 | |
| `im:message:send_as_bot` | 发送消息 | 待申请 | |

---

## 密钥管理说明

**App Secret 存储位置**: [待填写，如: 1Password - PE Knowledge Base - feishu-app-secret]

**访问权限**:
- 技术负责人: 可读
- 开发人员: 不可直接访问，通过环境变量注入

**密钥轮换**: 如需更新Secret，请更新密钥管理系统并通知相关人员更新本地配置。

---

## 后续步骤

1. [ ] 在[飞书开放平台](https://open.feishu.cn/)创建应用
2. [ ] 获取 App ID 和 App Secret
3. [ ] 提交 P0 权限申请
4. [ ] 等待审批（预计 1-3 工作日）
5. [ ] 将 App Secret 存入密钥管理系统
6. [ ] 更新本文档，标记各项权限审批状态

---

**文档状态**: 草稿
**最后更新**: 2026-04-18
