const routes = [
  {
    path: '/login',
    component: './Login',
    hideInMenu: true,
    layout: false,
  },
  {
    path: '/',
    redirect: '/welcome',
  },
  {
    path: '/welcome',
    name: '欢迎',
    icon: 'HomeOutlined',
    component: './Dashboard',
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
        name: '研发运营看板',
        icon: 'BarChartOutlined',
        component: './Devops',
      },
      {
        path: '/governance/insights',
        name: '用户洞察/迭代规划',
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
