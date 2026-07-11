const routes = [
  {
    path: '/login/dingtalk/callback',
    component: './DingTalkLoginCallback',
    hideInMenu: true,
    layout: false,
  },
  {
    path: '/login',
    component: './Login',
    hideInMenu: true,
    layout: false,
  },
  {
    path: '/account/profile',
    component: './AccountProfile',
    hideInMenu: true,
  },
  {
    path: '/help',
    name: '帮助中心',
    icon: 'QuestionCircleOutlined',
    component: './Help',
    hideInMenu: true,
  },
  {
    path: '/',
    redirect: '/login',
  },
  {
    path: '/welcome',
    name: '团队看板',
    icon: 'HomeOutlined',
    component: './Dashboard',
  },
  {
    path: '/assistant',
    name: 'AI 助手',
    icon: 'RobotOutlined',
    component: './Assistant',
  },
  {
    path: '/assistant/drafts',
    name: '草案任务台',
    icon: 'ProfileOutlined',
    component: './AssistantDrafts',
  },
  {
    path: '/tasks',
    name: '任务中心',
    icon: 'ProjectOutlined',
    routes: [
      {
        path: '/tasks',
        redirect: '/tasks/scheduled-jobs',
      },
      {
        path: '/tasks/scheduled-jobs',
        name: '定时作业',
        icon: 'ClockCircleOutlined',
        component: './ScheduledJobs',
      },
      {
        path: '/tasks/ai-capabilities',
        name: 'AI 能力配置',
        icon: 'RobotOutlined',
        component: './AiCapabilities',
      },
      {
        path: '/tasks/plugins',
        name: '插件管理',
        icon: 'ApiOutlined',
        component: './Plugins',
      },
    ],
  },
  {
    path: '/delivery',
    name: '需求交付',
    icon: 'DeploymentUnitOutlined',
    routes: [
      {
        path: '/delivery',
        redirect: '/delivery/requirements',
      },
      {
        path: '/delivery/requirements',
        name: '需求管理',
        icon: 'FileDoneOutlined',
        component: './Requirements',
      },
      {
        path: '/delivery/requirements/:requirementId/full-chain',
        component: './RequirementFullChain',
        hideInMenu: true,
      },
      {
        path: '/delivery/full-chain',
        component: './RequirementFullChain',
        hideInMenu: true,
      },
      {
        path: '/delivery/rd-tasks',
        name: '研发任务',
        icon: 'UnorderedListOutlined',
        component: './TaskCenter',
      },
      {
        path: '/delivery/rd-executor-policies',
        name: '研发执行器策略',
        icon: 'ControlOutlined',
        component: './RdExecutorPolicies',
      },
      {
        path: '/delivery/versions',
        name: '迭代版本',
        icon: 'BranchesOutlined',
        component: './IterationVersions',
      },
      {
        path: '/delivery/bugs',
        name: 'Bug 管理',
        icon: 'BugOutlined',
        component: './Bugs',
      },
    ],
  },
  {
    path: '/assets',
    name: '产品资产',
    icon: 'AppstoreOutlined',
    routes: [
      {
        path: '/assets',
        redirect: '/assets/products',
      },
      {
        path: '/assets/products',
        name: '产品管理',
        icon: 'AppstoreOutlined',
        component: './Products',
      },
      {
        path: '/assets/knowledge',
        name: '知识中心',
        icon: 'BookOutlined',
        component: './Knowledge',
      },
    ],
  },
  {
    path: '/governance',
    name: '运营治理',
    icon: 'ControlOutlined',
    routes: [
      {
        path: '/governance',
        redirect: '/governance/devops',
      },
      {
        path: '/governance/devops',
        name: '日志监控',
        icon: 'BarChartOutlined',
        component: './Devops',
      },
      {
        path: '/governance/deployments',
        name: '运维部署',
        icon: 'CloudServerOutlined',
        component: './Deployments',
      },
      {
        path: '/governance/insights',
        name: '用户洞察',
        icon: 'RobotOutlined',
        component: './Insights',
      },
      {
        path: '/governance/audit',
        name: '审计与运行',
        icon: 'SafetyCertificateOutlined',
        component: './Audit',
      },
      {
        path: '/governance/execution-traces',
        name: '执行诊断',
        icon: 'NodeIndexOutlined',
        component: './ExecutionTraces',
      },
      {
        path: '/governance/code-inspections',
        name: '代码巡检',
        icon: 'CodeOutlined',
        component: './CodeInspections',
      },
    ],
  },
  {
    path: '/system',
    name: '系统管理',
    icon: 'SettingOutlined',
    routes: [
      {
        path: '/system',
        redirect: '/system/users',
      },
      {
        path: '/system/users',
        name: '用户管理',
        icon: 'TeamOutlined',
        component: './Users',
      },
      {
        path: '/system/roles',
        name: '角色管理',
        icon: 'SafetyCertificateOutlined',
        component: './Roles',
      },
      {
        path: '/system/menus',
        name: '菜单管理',
        icon: 'MenuOutlined',
        component: './Menus',
      },
      {
        path: '/system/health',
        name: '系统健康',
        icon: 'DashboardOutlined',
        component: './SystemHealth',
      },
      {
        path: '/system/settings',
        name: '系统设置',
        icon: 'SettingOutlined',
        component: './SystemSettings',
      },
      {
        path: '/system/model-gateway',
        name: '模型网关',
        icon: 'ApiOutlined',
        component: './ModelGateway',
      },
      {
        path: '/system/assistant-role-quick-tasks',
        name: 'AI助手快捷任务',
        icon: 'RobotOutlined',
        component: './AssistantRoleQuickTasks',
      },
      {
        path: '/system/assistant-action-references',
        name: 'AI助手 @ 能力',
        icon: 'RobotOutlined',
        component: './AssistantActionReferences',
      },
    ],
  },
  {
    path: '/workspace',
    redirect: '/welcome',
    hideInMenu: true,
  },
  {
    path: '/tasks/management',
    redirect: '/delivery/rd-tasks',
    hideInMenu: true,
  },
  {
    path: '/workspace/tasks',
    redirect: '/delivery/rd-tasks',
    hideInMenu: true,
  },
  {
    path: '/workspace/dashboard',
    redirect: '/welcome',
    hideInMenu: true,
  },
  {
    path: '/dashboard',
    redirect: '/welcome',
    hideInMenu: true,
  },
  {
    path: '/chatbot',
    redirect: '/assistant',
    hideInMenu: true,
  },
  {
    path: '/products',
    redirect: '/assets/products',
    hideInMenu: true,
  },
  {
    path: '/requirements',
    redirect: '/delivery/requirements',
    hideInMenu: true,
  },
  {
    path: '/versions',
    redirect: '/delivery/versions',
    hideInMenu: true,
  },
  {
    path: '/bugs',
    redirect: '/delivery/bugs',
    hideInMenu: true,
  },
  {
    path: '/knowledge',
    redirect: '/assets/knowledge',
    hideInMenu: true,
  },
  {
    path: '/devops',
    redirect: '/governance/devops',
    hideInMenu: true,
  },
  {
    path: '/insights',
    redirect: '/governance/insights',
    hideInMenu: true,
  },
  {
    path: '/audit',
    redirect: '/governance/audit',
    hideInMenu: true,
  },
  {
    path: '/users',
    redirect: '/system/users',
    hideInMenu: true,
  },
  {
    path: '/roles',
    redirect: '/system/roles',
    hideInMenu: true,
  },
  {
    path: '/model-gateway',
    redirect: '/system/model-gateway',
    hideInMenu: true,
  },
  {
    path: '/ai-capabilities',
    redirect: '/tasks/ai-capabilities',
    hideInMenu: true,
  },
  {
    path: '/scheduled-jobs',
    redirect: '/tasks/scheduled-jobs',
    hideInMenu: true,
  },
  {
    path: '/plugins',
    redirect: '/tasks/plugins',
    hideInMenu: true,
  },
  {
    path: '/system/ai-capabilities',
    redirect: '/tasks/ai-capabilities',
    hideInMenu: true,
  },
  {
    path: '/system/scheduled-jobs',
    redirect: '/tasks/scheduled-jobs',
    hideInMenu: true,
  },
  {
    path: '/system/plugins',
    redirect: '/tasks/plugins',
    hideInMenu: true,
  },
  {
    path: '/list',
    redirect: '/assets/products',
    hideInMenu: true,
  },
  {
    path: '/*',
    component: './Exception404',
  },
];

export default routes;
