const routes = [
  {
    path: '/login',
    component: './Login',
    hideInMenu: true,
    layout: false,
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
    path: '/tasks',
    name: '任务中心',
    icon: 'ProjectOutlined',
    routes: [
      {
        path: '/tasks',
        redirect: '/tasks/management',
      },
      {
        path: '/tasks/management',
        name: '任务管理',
        icon: 'UnorderedListOutlined',
        component: './TaskCenter',
      },
      {
        path: '/tasks/ai-capabilities',
        name: 'AI 能力配置',
        icon: 'RobotOutlined',
        component: './AiCapabilities',
      },
      {
        path: '/tasks/scheduled-jobs',
        name: '定时作业',
        icon: 'ClockCircleOutlined',
        component: './ScheduledJobs',
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
        path: '/system/model-gateway',
        name: '模型网关',
        icon: 'ApiOutlined',
        component: './ModelGateway',
      },
    ],
  },
  {
    path: '/workspace',
    redirect: '/welcome',
    hideInMenu: true,
  },
  {
    path: '/workspace/tasks',
    redirect: '/tasks/management',
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
