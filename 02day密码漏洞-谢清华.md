# 登录系统安全改进前后对比

| 维度 | 改进前 | 改进后 |
|------|--------|--------|
| **源码密码泄露** | `app.py` 第 6~23 行硬编码 USERS 字典，明文包含 admin/admin123 | 用户数据移至独立 `data/users.json` 文件，`app.py` 不再包含任何用户凭据 |
| **Secret Key 硬编码** | `app.secret_key = "dev-key-2025"` 固定字符串，任何人都可伪造 session | 首次运行时自动 `secrets.token_hex(32)` 生成 64 字符随机密钥，持久化到 `.secret_key` 文件 |
| **登录页凭据泄露** | `login.html` 顶部 HTML 注释泄露管理员账号密码 | 注释已移除，登录页不包含任何凭据信息 |
| **注入防护** | 无任何输入清洗，`request.form.get("username")` 直接用于字典查询 | `sanitize_input()` 统一过滤：去空、去除 null 字节、用户名上限 50 字符 |
| **Session Cookie 安全** | 无任何 Cookie 安全属性配置 | `SESSION_COOKIE_HTTPONLY=True` + `SESSION_COOKIE_SAMESITE="Strict"` |
| **会话超时** | 无超时机制，登出前永久有效 | `PERMANENT_SESSION_LIFETIME=1800`（30 分钟自动过期） |
| **功能影响** | — | **零影响**：所有功能、界面、交互逻辑完全不变 |

## 改进成果总结

- **凭据隔离**：账号密码从代码硬编码改为独立文件存储，源码泄露不再直接导致账号失守
- **Secret Key** 从固定字符串改为随机生成，杜绝会话伪造风险
- **注入防护落地**：新增统一输入过滤函数，拦截空字节、超长输入等异常 payload
- **会话安全全面加固**：Cookie 增加 HttpOnly + SameSite 双重属性，30 分钟自动超时机制
- **前端信息泄露清零**：移除登录页调试注释，消除最易被利用的明文账号泄露入口
- **业务零侵入**：不改动任何功能逻辑，用户体验、页面交互、路由结构完全保持原样
