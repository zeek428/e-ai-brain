export type HelpSection = {
  body: string[];
  heading: string;
};

export type HelpScreenshot = {
  alt: string;
  caption?: string;
  src: string;
};

export type HelpArticle = {
  key: string;
  keywords: string[];
  related?: string[];
  role: string;
  route?: string;
  sections: HelpSection[];
  screenshots?: HelpScreenshot[];
  summary: string;
  title: string;
};

export type HelpGroup = {
  articles: HelpArticle[];
  key: string;
  title: string;
};

export const helpGroups: HelpGroup[] = [
  {
    key: 'start',
    title: '快速开始',
    articles: [
      {
        key: 'getting-started',
        keywords: ['登录', '钉钉', '个人中心', '权限', '菜单'],
        related: ['account-profile', 'system-roles'],
        role: '所有已登录用户',
        route: '/welcome',
        screenshots: [
          {
            alt: '快速开始首页截图',
            caption: '首次进入后可从团队看板、顶部帮助入口和头像菜单开始熟悉系统。',
            src: '/help/screenshots/help-getting-started.png',
          },
        ],
        summary: '了解 AI Brain 的登录方式、菜单结构、角色权限和常用操作入口。',
        title: '快速开始',
        sections: [
          {
            heading: '首次进入',
            body: [
              '账号密码登录需要完成数字安全校验；钉钉登录不需要回答数字题。',
              '登录后会按当前角色展示可访问菜单。如果看不到某个菜单，通常是角色未授权，而不是页面丢失。',
              '顶部“帮助中心”和头像菜单中的“个人中心”适合处理日常自助问题。',
            ],
          },
          {
            heading: '推荐使用顺序',
            body: [
              '先在团队看板查看产品范围、交付负载和风险压力。',
              '再进入需求交付或产品资产处理具体需求、任务、Bug、知识和产品配置。',
              '出现接口异常、权限拒绝或执行失败时，优先查看审计与运行、执行诊断和帮助中心 FAQ。',
            ],
          },
        ],
      },
      {
        key: 'account-profile',
        keywords: ['个人中心', '密码', '邮箱', '手机号', '钉钉绑定', '解绑'],
        role: '所有已登录用户',
        route: '/account/profile',
        screenshots: [
          {
            alt: '个人中心页面截图',
            caption: '个人中心用于维护资料、本地密码和钉钉账号绑定状态。',
            src: '/help/screenshots/help-account-profile.png',
          },
        ],
        summary: '维护个人资料、本地密码和钉钉账号绑定关系。',
        title: '个人中心',
        sections: [
          {
            heading: '可以维护的信息',
            body: [
              '可修改显示名称、邮箱、手机号和登录密码；登录名用于识别账号，默认只读展示。',
              '钉钉账号卡片会展示绑定状态、企业名称和外部身份摘要，便于确认当前账号是否绑定正确。',
              'SSO-only 账号需要先设置本地密码，才能解除唯一的钉钉登录方式。',
            ],
          },
          {
            heading: '绑定钉钉',
            body: [
              '已有 AI Brain 账号应先用账号密码登录，再到个人中心发起钉钉绑定。',
              '如果提示账号冲突，说明该钉钉身份已经绑定到其他 AI Brain 用户，需要管理员在用户管理中确认或解绑。',
            ],
          },
        ],
      },
    ],
  },
  {
    key: 'workspace',
    title: '业务工作台',
    articles: [
      {
        key: 'dashboard',
        keywords: ['团队看板', '趋势', '风险', '产品范围', '治理优先级'],
        role: '具备团队看板读取权限的用户',
        route: '/welcome',
        screenshots: [
          {
            alt: '团队看板页面截图',
            caption: '团队看板汇总产品范围内的交付、风险、工程活跃和用户声音趋势。',
            src: '/help/screenshots/help-dashboard.png',
          },
        ],
        summary: '从管理视角查看交付、风险、工程活跃和用户声音。',
        title: '团队看板',
        sections: [
          {
            heading: '页面重点',
            body: [
              '顶部筛选用于切换产品范围和时间范围，所有指标和趋势会联动刷新。',
              '四个业务域分别覆盖交付负载、风险压力、工程活跃和用户声音。',
              '治理优先队列用于快速定位最需要处理的需求、任务、Bug、发布或反馈。',
            ],
          },
          {
            heading: '如何使用',
            body: [
              '管理者先看健康结论，再看趋势是否持续恶化，最后下钻到对应列表处理。',
              '如果趋势为空，通常表示当前产品或时间范围下缺少足够历史数据。',
            ],
          },
        ],
      },
      {
        key: 'assistant',
        keywords: ['AI 助手', '对话', '草案', '知识引用', '上下文'],
        role: '具备 AI 助手使用权限的用户',
        route: '/assistant',
        screenshots: [
          {
            alt: 'AI 助手页面截图',
            caption: 'AI 助手支持对话检索、上下文分析和草案生成。',
            src: '/help/screenshots/help-assistant.png',
          },
        ],
        summary: '通过对话方式检索上下文、生成草案和辅助分析。',
        title: 'AI 助手',
        sections: [
          {
            heading: '适合的场景',
            body: [
              '询问系统操作、需求背景、知识中心文档、研发任务和治理数据。',
              '让 AI 生成需求草案、任务拆解、测试建议或问题分析时，应尽量提供产品、版本和上下文。',
            ],
          },
          {
            heading: '注意事项',
            body: [
              'AI 输出需要人工确认后再进入正式业务流程。',
              '涉及数据变更、审批、写回或外部动作时，以页面按钮和审计记录为准。',
            ],
          },
        ],
      },
      {
        key: 'assistant-drafts',
        keywords: ['草案任务台', '草案', '转换', 'AI 助手'],
        role: '具备草案任务台权限的用户',
        route: '/assistant/drafts',
        screenshots: [
          {
            alt: '草案任务台页面截图',
            caption: '草案任务台集中展示 AI 助手生成的待处理草案和治理状态。',
            src: '/help/screenshots/help-assistant-drafts.png',
          },
        ],
        summary: '集中处理 AI 助手生成的需求、任务或知识沉淀草案。',
        title: '草案任务台',
        sections: [
          {
            heading: '核心流程',
            body: [
              '从草案列表查看来源、类型、状态和生成时间。',
              '人工校对内容后，再决定转换为需求、任务、知识沉淀或关闭草案。',
              '无法编辑的用户通常只有只读权限，需要联系管理员调整角色。',
            ],
          },
        ],
      },
    ],
  },
  {
    key: 'tasks',
    title: '任务中心',
    articles: [
      {
        key: 'scheduled-jobs',
        keywords: ['定时作业', '运行记录', '手动触发', '邮件通知'],
        role: '任务中心运维或管理员',
        route: '/tasks/scheduled-jobs',
        screenshots: [
          {
            alt: '定时作业页面截图',
            caption: '定时作业页用于维护作业配置、手动触发和查看运行记录。',
            src: '/help/screenshots/help-scheduled-jobs.png',
          },
          {
            alt: '定时作业运行结果详情刷新截图',
            caption: '运行结果详情标题栏可刷新当前运行状态、日志和结果动作写入记录。',
            src: '/help/screenshots/help-scheduled-job-run-detail.png',
          },
        ],
        summary: '管理定时作业、手动触发任务并查看运行记录。',
        title: '定时作业',
        sections: [
          {
            heading: '常用操作',
            body: [
              '在作业列表查看启停状态、下次运行时间、最近运行结果和产品归属。',
              '手动触发后页面会切到运行记录，并置顶展示新运行记录。',
              '打开运行结果详情后，可在标题栏点击“刷新”获取运行中的最新状态、日志和结果动作写入记录。',
              '邮件通知类动作依赖系统设置中的邮件发送配置。',
            ],
          },
        ],
      },
      {
        key: 'ai-capabilities',
        keywords: ['AI 能力配置', '能力', '模型', '动作'],
        role: '系统管理员或 AI 能力管理员',
        route: '/tasks/ai-capabilities',
        screenshots: [
          {
            alt: 'AI 能力配置页面截图',
            caption: 'AI 能力配置页用于维护可被任务、插件和助手调用的能力定义。',
            src: '/help/screenshots/help-ai-capabilities.png',
          },
        ],
        summary: '维护可被任务、插件和助手调用的 AI 能力定义。',
        title: 'AI 能力配置',
        sections: [
          {
            heading: '配置重点',
            body: [
              '能力名称、用途、输入输出和风险等级应保持清晰，方便角色授权和审计。',
              '高风险能力建议只开放给管理员或明确业务负责人。',
            ],
          },
        ],
      },
      {
        key: 'plugins',
        keywords: ['插件', 'MCP', '钉钉', 'Webhook', '外部事件', '诊断', '授权'],
        role: '系统管理员或插件管理员',
        route: '/tasks/plugins',
        screenshots: [
          {
            alt: '插件管理页面截图',
            caption: '插件管理页集中维护标准插件、连接、动作和执行器。',
            src: '/help/screenshots/help-plugins.png',
          },
        ],
        summary: '管理标准插件、授权配置、健康诊断和动作模板。',
        title: '插件管理',
        sections: [
          {
            heading: '使用建议',
            body: [
              '新增插件后先完成授权配置，再执行工具发现和健康诊断。',
              'GitHub、GitLab、Jenkins 和可观测性连接可配置 Webhook Secret 引用、允许事件和产品上下文；外部事件先验签、幂等入库，再由后台 Worker 处理。',
              '外部事件页只展示脱敏 Delivery 上下文，失败或死信事件可以人工重试。',
              '高风险动作需要明确业务场景、输入字段和审计摘要，避免把密钥或完整请求写入日志。',
            ],
          },
        ],
      },
    ],
  },
  {
    key: 'delivery',
    title: '需求交付',
    articles: [
      {
        key: 'requirements',
        keywords: ['需求管理', '审批', '生成任务', '全链路'],
        role: '产品、研发负责人、评审者；viewer 只读',
        route: '/delivery/requirements',
        screenshots: [
          {
            alt: '需求管理页面截图',
            caption: '需求管理页用于登记、审批和追踪需求全链路上下文。',
            src: '/help/screenshots/help-requirements.png',
          },
        ],
        summary: '登记、审批、关闭需求，并从需求生成 AI 研发任务。',
        title: '需求管理',
        sections: [
          {
            heading: '核心流程',
            body: [
              '新需求先进入草稿或待审批状态，补齐产品、版本、优先级和描述后提交评审。',
              '审批通过后可生成 AI 任务，任务会继承产品、版本和需求上下文。',
              '全链路用于查看需求、任务、评审、Bug、知识和审计之间的关联。',
            ],
          },
          {
            heading: '权限边界',
            body: [
              'viewer 可查看授权产品范围内的数据，但不能创建、审批、关闭或生成任务。',
              '如果按钮不可见或接口返回 FORBIDDEN，请检查角色权限和产品范围。',
            ],
          },
        ],
      },
      {
        key: 'rd-tasks',
        keywords: ['研发任务', 'AI Task', 'Agent 自治循环', '质量门禁', '执行上下文', '确认', 'Runner', '执行器'],
        role: '研发、评审者、管理员',
        route: '/delivery/rd-tasks',
        screenshots: [
          {
            alt: '研发任务页面截图',
            caption: '研发任务页展示 AI Task 状态、自治循环、质量门禁、执行上下文和人工确认点。',
            src: '/help/screenshots/help-rd-tasks.png',
          },
        ],
        summary: '跟踪 AI 研发任务状态、执行结果、人工确认和写回。',
        title: '研发任务',
        sections: [
          {
            heading: '状态理解',
            body: [
              'running 表示 AI 正在执行，waiting_review 表示等待人工确认，completed 表示流程完成。',
              '任务详情中可查看自治轮次、独立质量门禁和执行上下文清单；编码 Runner 返回成功不等于门禁通过。',
              '自治循环会把失败证据带入下一轮，预算耗尽、安全阻断或点击人工接管后停止继续派发。',
              '人工确认模式需确认后合入；自动提交也必须通过独立门禁，高风险变更仍转人工确认。',
            ],
          },
        ],
      },
      {
        key: 'rd-executor-policies',
        keywords: ['研发执行器策略', 'Codex', 'Claude', 'Agent 自治循环', '质量门禁', '自动提交', '人工确认'],
        role: '管理员或研发治理负责人',
        route: '/delivery/rd-executor-policies',
        screenshots: [
          {
            alt: '研发执行器策略页面截图',
            caption: '研发执行器策略页用于配置任务如何选择 Runner、知识上下文和提交方式。',
            src: '/help/screenshots/help-rd-executor-policies.png',
          },
        ],
        summary: '配置任务如何选择 Runner、自治预算、独立质量门禁和代码提交方式。',
        title: '研发执行器策略',
        sections: [
          {
            heading: '配置重点',
            body: [
              '策略通常按任务类型、产品和优先级匹配，决定使用哪个 Runner 和是否自动启动。',
              '自治模式配置最大轮次、总时长和可选 Token/费用预算，门禁失败且预算允许时才进入下一轮。',
              '代码提交方式建议默认人工确认；自动提交仍需平台独立门禁通过，迁移、高风险和受保护目录不会自动合入。',
            ],
          },
        ],
      },
      {
        key: 'versions',
        keywords: ['迭代版本', '版本', '分支', '发布'],
        role: '产品、研发和发布负责人',
        route: '/delivery/versions',
        screenshots: [
          {
            alt: '迭代版本页面截图',
            caption: '迭代版本页用于维护产品版本、交付范围和分支风险。',
            src: '/help/screenshots/help-versions.png',
          },
        ],
        summary: '维护产品迭代版本、研发分支和交付状态。',
        title: '迭代版本',
        sections: [
          {
            heading: '使用方式',
            body: [
              '把需求、研发任务、Bug、运维部署和发布记录归属到同一版本，便于查看交付范围和风险。',
              '需求测试完成后进入待发布，版本发布前需要在运维部署页发起部署并登记成功结果。',
              '暂无需求的版本进入全链路时会展示版本级空状态，而不是报错。',
            ],
          },
        ],
      },
      {
        key: 'bugs',
        keywords: ['Bug 管理', 'AI处理', '只读', '全链路'],
        role: '测试、研发、产品；viewer 只读',
        route: '/delivery/bugs',
        screenshots: [
          {
            alt: 'Bug 管理页面截图',
            caption: 'Bug 管理页用于筛选、分诊和追踪缺陷生命周期。',
            src: '/help/screenshots/help-bugs.png',
          },
        ],
        summary: '登记、分诊、推进和追踪 Bug 生命周期。',
        title: 'Bug 管理',
        sections: [
          {
            heading: '常用操作',
            body: [
              '可按产品、版本、状态、严重级别和来源筛选 Bug。',
              '具备写权限的用户可以登记、编辑、批量处理或推进 AI 任务。',
              'viewer 只能查看列表和全链路，页面不会展示写操作。',
            ],
          },
        ],
      },
    ],
  },
  {
    key: 'assets',
    title: '产品资产',
    articles: [
      {
        key: 'products',
        keywords: ['产品管理', '版本', '模块', 'Git 仓库', '相关系统', '产品接入向导'],
        role: '产品管理员；viewer 只读',
        route: '/assets/products',
        screenshots: [
          {
            alt: '产品接入向导页面截图',
            caption: '产品接入向导会把主数据、交付结构、知识空间、插件连接、权限范围和健康复检串联在一个弹窗内。',
            src: '/help/screenshots/assets-products-onboarding.png',
          },
          {
            alt: '产品成员权限页面截图',
            caption: '成员权限用于维护产品经理、研发负责人、开发、测试、运维和观察者等产品内职责，并派生产品数据范围。',
            src: '/help/screenshots/assets-products-members.png',
          },
        ],
        summary: '维护产品、版本、模块、Git 资源、相关系统和成员权限，是数据归属的基础。',
        title: '产品管理',
        sections: [
          {
            heading: '为什么重要',
            body: [
              '需求、任务、Bug、知识、代码巡检和看板指标都会依赖产品归属。',
              '产品范围也是角色数据权限的核心边界，建议保持产品编码和名称稳定。',
              'viewer 可以查看产品资产，但不能新增、编辑或删除。',
            ],
          },
          {
            heading: '接入新产品',
            body: [
              '点击“产品接入向导”可以按步骤检查产品主数据、版本模块、Git 资源、知识空间、插件连接、角色范围和系统健康。',
              '具备产品管理权限的用户可以从向导直接新增产品或配置当前页第一个产品；只读用户只能查看接入步骤和已有配置状态。',
              '接入完成后建议进入系统健康页复检产品初始化、知识质量、插件连接和权限诊断。',
            ],
          },
          {
            heading: '配置成员权限',
            body: [
              '在产品列表点击“配置”，进入“成员权限”区域后可以新增或移除产品成员。',
              '产品成员职责使用中文展示，包括产品经理、研发负责人、开发工程师、测试负责人、测试人员、运维/发布负责人和观察者。',
              '成员权限决定用户可见和可操作的产品数据范围；系统角色仍决定用户具备哪些功能能力。',
            ],
          },
        ],
      },
      {
        key: 'knowledge',
        keywords: ['知识中心', '空间', '目录', '上传', 'OCR', '多模态', '文档版本', '过期治理', 'Hybrid Search', 'RAG'],
        role: '知识管理员、研发、产品；viewer 按授权只读',
        route: '/assets/knowledge',
        screenshots: [
          {
            alt: '知识中心页面截图',
            caption: '知识中心工作台覆盖空间目录、版本化解析、多模态治理、检索和 RAG 问答。',
            src: '/help/screenshots/help-knowledge.png',
          },
        ],
        summary: '上传和治理产品知识，支持检索、RAG 问答、引用和知识沉淀。',
        title: '知识中心',
        sections: [
          {
            heading: '工作台结构',
            body: [
              '空间和目录用于组织知识归属，新文档和沉淀入库都必须选择知识空间。',
              '文档库用于上传、筛选、查看索引状态和打开详情。',
              '知识问答会基于 Hybrid Search 召回内容，并展示引用片段。',
              '多模态治理维护 OCR/版面/表格处理 Profile，并扫描临近过期、已过期或用户标记过期的版本。',
            ],
          },
          {
            heading: '上传注意事项',
            body: [
              '图片或需要 OCR 的文档需选择多模态解析 Profile；Provider 凭据只允许使用 env 引用，不在平台保存明文。',
              '新版本解析成功后才替换当前 active 版本，失败版本不会让旧知识立即不可检索。',
            ],
          },
        ],
      },
    ],
  },
  {
    key: 'governance',
    title: '运营治理',
    articles: [
      {
        key: 'devops',
        keywords: ['日志监控', 'Jenkins', 'GitLab', '发布', '在线日志'],
        role: '研发治理、运维或管理员',
        route: '/governance/devops',
        screenshots: [
          {
            alt: '日志监控页面截图',
            caption: '日志监控页用于查看工程指标、发布记录和在线日志风险。',
            src: '/help/screenshots/help-devops.png',
          },
        ],
        summary: '查看工程指标、发布记录和在线日志风险。',
        title: '日志监控',
        sections: [
          {
            heading: '管理重点',
            body: [
              '按产品查看代码提交、构建发布和在线日志趋势。',
              '异常波动应下钻到版本、任务、发布记录或代码巡检记录确认根因。',
            ],
          },
        ],
      },
      {
        key: 'deployments',
        keywords: ['运维部署', '部署单', '部署方案', 'SSH', 'Docker', 'Jenkins', '灰度', '蓝绿', '健康检查', '上线', '回滚'],
        role: '产品、研发、测试、发布运维或管理员',
        route: '/governance/deployments',
        screenshots: [
          {
            alt: '运维部署页面截图',
            caption: '发起部署会提示自动部署方案缺失，并引导到对应的方案与执行资源配置。',
            src: '/help/screenshots/help-deployments.png',
          },
        ],
        summary: '配置人工、SSH、Docker 或 Jenkins 方案；SSH/Docker 先完成 Runner 真实探测，再按提示完成授权与方案配置。',
        title: '运维部署',
        sections: [
          {
            heading: '部署流程',
            body: [
              '先在“部署方案”按产品和环境配置执行方式，再从测试完成或待发布需求发起部署单。',
              '方案可选择全量、灰度、分批或蓝绿发布，并配置严格部署窗口、健康检查和真实回滚动作。',
              'Runner Target 和 Jenkins Connection 必须先按产品、环境授权；未授权资源不会进入候选。',
              '人工部署由负责人登记结果；SSH 和 Docker 通过具备部署能力的本地 Runner 执行；Jenkins 通过集成连接触发并同步状态。',
              '部署 Runner 的“探测”会创建无副作用任务：SSH 仅连接后执行 true，Docker 仅检查 Engine 和 Compose 配置。探测成功仅在 10 分钟内可用于启动部署，心跳和目标上报不能替代该证据。',
              '部署单保存创建时的方案快照，Runner 的主机、私钥和本地目录等配置不会上传到平台。',
              '部署详情可查看预检、质量门禁、每波运行、步骤证据、健康检查、回滚、派发和审计；自动部署取消后会先进入取消中，收到外部终态后再完成取消。',
              '部署失败或回滚会把需求退回待发布，并生成部署失败来源的 Bug。',
              '只读用户可以查看授权产品的部署证据；创建、执行、取消和方案维护按独立权限显示。',
            ],
          },
        ],
      },
      {
        key: 'insights',
        keywords: ['用户洞察', '反馈', '迭代建议', '用户声音'],
        role: '产品、运营、管理员',
        route: '/governance/insights',
        screenshots: [
          {
            alt: '用户洞察页面截图',
            caption: '用户洞察页用于沉淀反馈、行为指标和迭代建议。',
            src: '/help/screenshots/help-insights.png',
          },
        ],
        summary: '沉淀用户反馈、行为指标和迭代建议；列表和详情会显示所属产品名称。',
        title: '用户洞察',
        sections: [
          {
            heading: '使用方式',
            body: [
              '负向反馈会进入治理视图，并可关联到迭代建议、需求或 Bug。',
              '建议定期按产品查看高频问题，避免反馈只停留在单条记录。',
              '列表和详情中的“所属产品”优先展示产品名称；没有可见产品配置时才显示产品 ID。',
            ],
          },
        ],
      },
      {
        key: 'audit-traces',
        keywords: ['审计', '执行诊断', 'trace_id', '全链路', '接口异常'],
        role: '管理员、审计员、研发治理人员',
        route: '/governance/audit',
        screenshots: [
          {
            alt: '审计与执行诊断页面截图',
            caption: '审计与执行诊断页用于按 trace、主体和事件排查关键操作。',
            src: '/help/screenshots/help-audit-traces.png',
          },
        ],
        summary: '排查关键操作、接口异常、AI 执行和全链路上下文。',
        title: '审计与执行诊断',
        sections: [
          {
            heading: '排障顺序',
            body: [
              '用户反馈错误码或 trace_id 时，先在审计与运行中按时间、主体或事件类型查找。',
              'AI 执行失败、任务卡住或写回异常时，再进入执行诊断查看运行链路。',
              '全链路只对有关联上下文的主体展示；没有需求上下文时页面会展示空状态或禁用入口。',
            ],
          },
        ],
      },
      {
        key: 'code-inspections',
        keywords: ['代码巡检', '质量安全', '产品维度', '全链路', '报告'],
        role: '研发治理、代码质量负责人、管理员',
        route: '/governance/code-inspections',
        screenshots: [
          {
            alt: '代码巡检页面截图',
            caption: '代码巡检页按产品展示质量安全报告、风险分布和治理待办。',
            src: '/help/screenshots/help-code-inspections.png',
          },
        ],
        summary: '按产品查看代码质量安全巡检报告、风险分布和治理待办。',
        title: '代码巡检',
        sections: [
          {
            heading: '页面重点',
            body: [
              '顶部产品范围会联动报告列表、风险分布和治理概览。',
              '未关联需求上下文的独立巡检报告不会直接打开需求全链路。',
              '严重发现建议先进入 Bug 或需求确认，再推进 AI 研发任务。',
            ],
          },
        ],
      },
    ],
  },
  {
    key: 'system',
    title: '系统管理',
    articles: [
      {
        key: 'system-users',
        keywords: ['用户管理', '登录方式', '钉钉', '外部身份', '停用'],
        role: '系统管理员',
        route: '/system/users',
        screenshots: [
          {
            alt: '用户管理页面截图',
            caption: '用户管理页用于维护账号资料、角色、状态和外部身份绑定。',
            src: '/help/screenshots/help-system-users.png',
          },
        ],
        summary: '维护用户资料、角色、启停状态和外部身份绑定。',
        title: '用户管理',
        sections: [
          {
            heading: '管理重点',
            body: [
              '用户列表会展示登录方式、钉钉绑定企业和本地密码状态。',
              '停用、删除或降权管理员时，系统会保护最后一个 active admin。',
              '钉钉绑定冲突可通过外部身份管理能力排查，但操作会写入审计。',
            ],
          },
        ],
      },
      {
        key: 'system-roles',
        keywords: ['角色管理', '菜单管理', '权限点', '权限诊断', 'viewer', '只读'],
        role: '系统管理员',
        route: '/system/roles',
        screenshots: [
          {
            alt: '角色与菜单页面截图',
            caption: '角色管理页用于维护角色、权限点、菜单入口和数据范围。',
            src: '/help/screenshots/help-system-roles.png',
          },
        ],
        summary: '维护角色、权限点、菜单入口和数据范围。',
        title: '角色与菜单',
        sections: [
          {
            heading: '配置原则',
            body: [
              '菜单可见不等于接口可写，后端权限点才是最终边界。',
              'viewer 默认只读，不能通过隐藏按钮以外的方式执行写操作。',
              '新增菜单后应同步角色授权、帮助文档和真实页面验证。',
            ],
          },
        ],
      },
      {
        key: 'system-health',
        keywords: ['系统健康', '配置体检', '依赖检查', 'SMTP', '钉钉', 'MinIO', 'pgvector', 'Redis', '模型网关'],
        related: ['system-settings', 'system-roles', 'model-gateway'],
        role: '系统管理员',
        route: '/system/health',
        screenshots: [
          {
            alt: '系统健康页面总览截图',
            caption: '系统健康页会把依赖状态、优先处理项、分类检查和修复入口统一到一个页面。',
            src: '/help/screenshots/system-health-overview.png',
          },
        ],
        summary: '统一查看平台依赖、核心配置、运行失败摘要和修复建议。',
        title: '系统健康',
        sections: [
          {
            heading: '页面重点',
            body: [
              '顶部展示整体状态、检查项总数、正常项、需关注项和阻断异常。',
              '优先处理区域会聚合最需要修复的依赖、配置或运行失败，支持直接跳转到对应配置页面。',
              '分类检查覆盖 PostgreSQL、Redis、pgvector、对象存储、SMTP、钉钉登录、钉钉 MCP、模型网关、知识质量、AI 执行器、作业运行、观测告警和产品初始化。',
            ],
          },
          {
            heading: '排查建议',
            body: [
              '先处理红色异常，再处理橙色或黄色待完善项。',
              '出现登录、插件、邮件或 AI 任务失败时，优先查看该页的最近错误和修复建议，再下钻到执行诊断、插件管理、系统设置或模型网关。',
            ],
          },
        ],
      },
      {
        key: 'execution-resources',
        keywords: ['执行资源授权', 'Runner Target', 'Jenkins', '产品范围', '部署环境'],
        related: ['deployments', 'system-health'],
        role: '系统管理员；发布负责人按产品只读',
        route: '/system/execution-resources',
        screenshots: [
          {
            alt: '执行资源授权页面截图',
            caption: '执行资源授权页按产品、环境和资源类型维护 Runner Target 与 Jenkins Connection 的可用范围。',
            src: '/help/screenshots/help-execution-resources.png',
          },
        ],
        summary: '把 Runner Target 或 Jenkins Connection 授权给指定产品和环境。',
        title: '执行资源授权',
        sections: [
          {
            heading: '授权边界',
            body: [
              '系统管理员选择产品、环境和资源类型后建立授权；Runner Target 同时固定 Runner 与目标编码。',
              '授权列表会标明 Runner 未在线、非部署信任域、未启用部署能力、目标未上报、未完成真实探测、探测失败或探测过期等原因；产品发布负责人只能在部署方案中看到当前产品、当前环境已授权且就绪的资源。',
              '授权记录不保存主机、私钥、密码或命令；停用授权会阻止新的方案绑定和部署启动，但保留历史证据。',
            ],
          },
        ],
      },
      {
        key: 'system-settings',
        keywords: ['系统设置', '邮件', 'SMTP', '测试收件人', '管理员邮箱'],
        role: '系统管理员',
        route: '/system/settings',
        screenshots: [
          {
            alt: '系统设置页面截图',
            caption: '系统设置页用于维护基础配置、邮件发送能力和安全确认。',
            src: '/help/screenshots/help-system-settings.png',
          },
        ],
        summary: '维护系统基础配置和邮件发送能力。',
        title: '系统设置',
        sections: [
          {
            heading: '邮件配置',
            body: [
              '发件邮箱、SMTP Host、端口、加密方式、用户名和 SMTP 密码/授权码必须匹配邮箱服务商要求。',
              'SMTP 密钥引用只用于引用外部密钥，例如 env:SMTP_PASSWORD；如果直接填写密码/授权码，可以留空。',
              '测试收件人会独立保存，不会自动覆盖为发件人邮箱。',
            ],
          },
          {
            heading: '安全要求',
            body: [
              '首次配置或变更邮件发送配置时需要管理员二次确认，后端会强制校验确认信息。',
              '密码和授权码不会明文回显，审计只记录是否配置、变更字段和已确认状态。',
              '点击发送测试邮件前，页面会先保存当前配置，再调用测试发送接口。',
            ],
          },
        ],
      },
      {
        key: 'model-gateway',
        keywords: ['模型网关', '模型', '供应商', 'Token', '延迟'],
        role: '系统管理员或 AI 平台管理员',
        route: '/system/model-gateway',
        screenshots: [
          {
            alt: '模型网关页面截图',
            caption: '模型网关页用于维护模型供应商、模型配置和调用元数据。',
            src: '/help/screenshots/help-model-gateway.png',
          },
        ],
        summary: '维护模型供应商、模型配置和调用元数据。',
        title: '模型网关',
        sections: [
          {
            heading: '配置原则',
            body: [
              '业务模块应通过模型网关调用模型，不直接依赖供应商 SDK。',
              '日志记录供应商、模型、用途、Token、延迟和状态，不默认保存完整提示词或输出。',
            ],
          },
        ],
      },
      {
        key: 'assistant-admin',
        keywords: ['AI助手快捷任务', '@ 能力', '动作引用', '角色配置'],
        role: '系统管理员或 AI 助手管理员',
        route: '/system/assistant-role-quick-tasks',
        screenshots: [
          {
            alt: 'AI 助手管理配置页面截图',
            caption: 'AI 助手管理配置页用于维护角色快捷任务和 @ 能力引用。',
            src: '/help/screenshots/help-assistant-admin.png',
          },
        ],
        summary: '配置不同角色可见的助手快捷任务和 @ 能力引用。',
        title: 'AI 助手管理配置',
        sections: [
          {
            heading: '配置建议',
            body: [
              '快捷任务应按角色职责配置，避免把管理员动作暴露给只读用户。',
              '@ 能力引用应写清输入要求、风险等级和结果去向。',
            ],
          },
        ],
      },
    ],
  },
  {
    key: 'faq',
    title: '常见问题',
    articles: [
      {
        key: 'faq',
        keywords: ['FORBIDDEN', 'Permission denied', 'DEFAULT_CREDENTIALS_DISABLED', 'SMTP', '登录失败'],
        role: '所有用户',
        summary: '汇总登录、权限、邮件、全链路和页面异常的常见处理方式。',
        title: '常见问题与错误码',
        sections: [
          {
            heading: '权限或菜单问题',
            body: [
              'FORBIDDEN 或 Permission denied 表示后端权限点拒绝。请确认当前角色是否具备对应菜单和接口权限。',
              '菜单看得到但接口拒绝，通常是菜单授权和权限点不一致，需要管理员在角色管理中修正。',
            ],
          },
          {
            heading: '登录问题',
            body: [
              'DEFAULT_CREDENTIALS_DISABLED 表示当前环境禁用了种子账号，请使用真实账号或让管理员启用本地测试开关。',
              '数字校验答错后页面会刷新题目，请重新输入新的答案后再登录。',
            ],
          },
          {
            heading: '邮件问题',
            body: [
              '测试邮件失败时先确认 SMTP Host、端口、SSL/TLS、用户名和授权码是否匹配邮箱服务商要求。',
              '阿里企业邮箱 SSL 发信通常使用 smtp.qiye.aliyun.com 和 465 端口，密码应填写安全密码或客户端专用密码。',
            ],
          },
        ],
      },
    ],
  },
];

export const helpArticles = helpGroups.flatMap((group) => group.articles);

export const helpArticleByKey = new Map(helpArticles.map((article) => [article.key, article]));

export function findHelpArticle(key: string | null | undefined) {
  if (!key) {
    return undefined;
  }
  return helpArticleByKey.get(key);
}

export function getArticleSearchText(article: HelpArticle) {
  return [
    article.title,
    article.summary,
    article.role,
    article.route,
    ...article.keywords,
    ...article.sections.flatMap((section) => [section.heading, ...section.body]),
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
}
