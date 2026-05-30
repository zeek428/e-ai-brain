export type Phase = {
  name: string;
  scope: string;
  state: 'active' | 'next' | 'later';
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
