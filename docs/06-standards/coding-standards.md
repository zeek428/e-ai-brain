# 编码规范

## 通用原则

1. **可读性优先**: 代码是写给人看的
2. **一致性**: 遵循团队约定
3. **简洁性**: 简单直接的实现
4. **可维护性**: 易于理解和修改

## 命名规范

### 变量命名
```typescript
// 使用有意义的名称
const userCount = 10;  // Good
const n = 10;          // Bad

// 布尔值使用 is/has/can 前缀
const isValid = true;
const hasPermission = false;
const canEdit = true;

// 常量使用大写
const MAX_RETRY_COUNT = 3;
const API_BASE_URL = 'https://api.example.com';
```

### 函数命名
```typescript
// 使用动词开头
function getUser() {}
function createUser() {}
function deleteUser() {}
function calculateTotal() {}

// 布尔返回值使用 is/has/can
function isValidEmail() {}
function hasPermission() {}
```

### 类命名
```typescript
// 使用 PascalCase
class UserService {}
class OrderController {}
class PaymentGateway {}
```

## 代码组织

### 文件结构
```
src/
├── modules/
│   └── user/
│       ├── user.controller.ts    # 控制器
│       ├── user.service.ts       # 业务逻辑
│       ├── user.repository.ts    # 数据访问
│       ├── user.model.ts         # 数据模型
│       ├── user.dto.ts           # 数据传输对象
│       ├── user.types.ts         # 类型定义
│       └── user.test.ts          # 测试文件
```

### 函数长度
- 单个函数不超过 50 行
- 超过则拆分为多个函数

### 文件长度
- 单个文件不超过 400 行
- 超过则拆分为多个模块

## 前端开发约束

### 默认框架

前端应用默认采用 React + TypeScript，并以 Ant Design Pro 模板作为 `apps/web` 工程基础，模板来源为 `https://github.com/ant-design/ant-design-pro`。新增前端功能时，应优先使用 Ant Design Pro 的后台布局、路由、菜单和权限入口约定，并使用 `antd` 官方组件作为基础交互组件，包括但不限于按钮、表单、输入框、选择器、表格、列表、卡片、弹窗、抽屉、菜单、标签、统计数据和通知反馈。

### Ant Design Pro 模板使用规则

- Ant Design Pro 只作为工程模板和后台工作台结构起点；初始化后 `ai-brain` 前端必须成为本仓库内可独立安装、构建和部署的工程。
- 保留模板中有价值的 Layout、路由、菜单、权限入口、请求封装和页面脚手架约定。
- 删除模板自带的示例页面、mock 数据、示例账号和演示业务逻辑，避免混入正式业务。
- 前端主导航围绕首页 IT 团队看板、产品管理、需求管理、任务中心、Bug 管理、研发运营看板、用户洞察/迭代规划、知识中心、审计与运行组织。
- 业务模型、API 类型和页面字段以本项目 PRD、Spec 和 API 文档为准，不以模板示例为准。

### Ant Design 使用规则

- 默认从项目依赖中的 `antd` npm 包引入组件，不把本机 Ant Design 源码目录作为运行时依赖。
- `/Users/zeek/source/ant-design` 仅作为组件源码参考、样式评估或版本对照来源；`ai-brain` 前端必须能脱离该目录独立安装、构建和部署。
- 视觉定制优先使用 `ConfigProvider`、全局 token、组件 token 和组件 props。
- 页面级样式只补充业务布局、密度和少量视觉细节，避免大面积覆盖 `.ant-*` 内部结构。
- 自定义基础组件前先确认 Ant Design 是否已有等价组件；确需自定义时，也应沿用 Ant Design 的尺寸、圆角、状态色、禁用态和焦点态规则。
- 表单校验、加载态、禁用态、确认弹窗和错误提示应优先使用 Ant Design 的标准交互能力，避免每个页面重复实现。

## Git 提交规范

### 提交信息格式
```
<type>: <description>

type: feat | fix | refactor | docs | test | chore | perf
```

### 示例
```
feat: 添加用户登录功能

- 支持 手机号 + 验证码 登录
- 支持 微信授权 登录
- 添加登录日志记录
```

---
最后更新: 2026-05-29
