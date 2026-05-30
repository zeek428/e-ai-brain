export type NavKey =
  | 'dashboard'
  | 'products'
  | 'requirements'
  | 'tasks'
  | 'bugs'
  | 'devops'
  | 'insights'
  | 'knowledge'
  | 'audit';

export type PagePanelKey = Exclude<NavKey, 'tasks'>;

export type Phase = {
  name: string;
  scope: string;
  state: 'active' | 'next' | 'later';
};

export type TaskRow = {
  type: string;
  label: string;
  status: string;
  owner: string;
};

export type PagePanel = {
  title: string;
  description: string;
  status: 'ready' | 'placeholder';
  statusLabel: string;
  items: Array<{
    label: string;
    value: string;
    detail: string;
  }>;
};

export const phases: Phase[] = [
  {
    name: 'MVP-A 基础 + GitLab 输入闭环',
    scope: '登录、产品配置、需求审批、产品详细设计、技术方案、MR 预览和 diff 快照。',
    state: 'active',
  },
  {
    name: 'MVP-B GitLab Review 闭环',
    scope: 'code_review 任务、结构化报告、人工确认、内部归档和不回写 GitLab。',
    state: 'next',
  },
  {
    name: 'MVP-C 知识与治理闭环',
    scope: '知识检索、知识沉淀审核、模拟 Issue 幂等和主体级审计。',
    state: 'later',
  },
];

export const taskRows: TaskRow[] = [
  {
    type: 'product_detail_design',
    label: '产品详细设计',
    status: 'waiting_review',
    owner: '产品负责人',
  },
  {
    type: 'technical_solution',
    label: '技术方案',
    status: 'draft',
    owner: '研发负责人',
  },
  {
    type: 'code_review',
    label: '内部 GitLab MR Code Review',
    status: 'snapshot_required',
    owner: 'Reviewer',
  },
];

export const pagePanels: Record<PagePanelKey, PagePanel> = {
  dashboard: {
    title: '首页看板',
    description: 'v1 MVP 先保留入口，完整 IT 团队指标看板在后续阶段接入。',
    status: 'placeholder',
    statusLabel: '占位',
    items: [
      { label: '需求总览', value: '待接入', detail: '后续聚合需求状态、任务进度和风险摘要。' },
      { label: '研发健康', value: '待接入', detail: '后续接入 GitLab、Jenkins 和线上日志指标。' },
      { label: 'AI 建议', value: '待接入', detail: '后续展示迭代规划建议和证据链。' },
    ],
  },
  products: {
    title: '产品管理',
    description: '后端已提供产品、版本、模块、Git 仓库和相关系统配置 API。',
    status: 'ready',
    statusLabel: 'API ready',
    items: [
      { label: '产品主数据', value: '可用', detail: '支持创建、查询、更新和 active_only 过滤。' },
      { label: '版本/模块', value: '可用', detail: '支持按产品维护版本和模块上下文。' },
      { label: 'Git 资源', value: '可用', detail: '支持内部 GitLab 仓库资源绑定。' },
    ],
  },
  requirements: {
    title: '需求管理',
    description: '后端已跑通需求创建、审批、驳回、关闭和审批后生成 AI 任务。',
    status: 'ready',
    statusLabel: 'API ready',
    items: [
      { label: '需求台账', value: '可用', detail: '支持列表、详情、按产品和状态过滤。' },
      { label: '审批流转', value: '可用', detail: '支持 approve、reject、close 状态动作。' },
      { label: '生成任务', value: '可用', detail: 'approved 需求可生成产品详细设计任务。' },
    ],
  },
  bugs: {
    title: 'Bug 管理',
    description: '当前是 v1.1/v1.2 预留入口，MVP 阶段只展示明确占位。',
    status: 'placeholder',
    statusLabel: '后续阶段',
    items: [
      { label: 'AI 自动测试 Bug', value: '待接入', detail: '后续由自动化测试任务沉淀。' },
      { label: '人工登记 Bug', value: '待接入', detail: '后续补充分派、修复、验证和关闭。' },
      { label: '重复归并', value: '待接入', detail: '后续按生命周期上下文聚合。' },
    ],
  },
  devops: {
    title: '研发运营看板',
    description: 'GitLab/Jenkins/线上日志真实运营采集属于后续增强。',
    status: 'placeholder',
    statusLabel: '后续阶段',
    items: [
      { label: 'GitLab 指标', value: '待接入', detail: 'MVP 已有 MR 预览和 diff 快照输入。' },
      { label: 'Jenkins 发布', value: '待接入', detail: '后续接入发布记录和上线检查。' },
      { label: '线上日志', value: '待接入', detail: '后续接入健康、错误率和延迟趋势。' },
    ],
  },
  insights: {
    title: '用户洞察/迭代规划',
    description: '当前预留入口，后续接入用户使用、反馈和 AI 迭代建议。',
    status: 'placeholder',
    statusLabel: '后续阶段',
    items: [
      { label: '使用趋势', value: '待接入', detail: '后续按产品和版本汇总用户行为。' },
      { label: '用户反馈', value: '待接入', detail: '后续支持反馈归属和证据链。' },
      { label: '规划建议', value: '待接入', detail: 'AI 建议必须经人工采纳后才转需求。' },
    ],
  },
  knowledge: {
    title: '知识中心',
    description: '后端已提供文档导入、权限过滤检索和知识沉淀候选审核接口。',
    status: 'ready',
    statusLabel: 'API ready',
    items: [
      { label: '文档导入', value: '可用', detail: '支持导入知识文档并记录索引状态。' },
      { label: '混合检索', value: '可用', detail: '检索前按角色执行权限过滤。' },
      { label: '沉淀审核', value: '可用', detail: '支持 approve/reject 候选知识。' },
    ],
  },
  audit: {
    title: '审计与运行',
    description: '后端已记录关键写操作、高影响 AI 动作和模型调用元数据。',
    status: 'ready',
    statusLabel: 'API ready',
    items: [
      { label: '审计查询', value: '可用', detail: '支持按任务、主体和事件类型过滤。' },
      { label: '模型日志', value: '可用', detail: '只记录 provider、model、tokens、latency 等元数据。' },
      { label: '健康检查', value: '可用', detail: 'Docker 内部依赖探测已修复。' },
    ],
  },
};
