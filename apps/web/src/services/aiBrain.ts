const configuredApiBaseUrl = process.env.UMI_APP_API_BASE_URL ?? '';
const API_BASE_URL = configuredApiBaseUrl.endsWith('/')
  ? configuredApiBaseUrl.slice(0, -1)
  : configuredApiBaseUrl;

type ApiEnvelope<T> = {
  data: T;
};

export type LoginResponse = {
  access_token: string;
};

export type ProductResponse = {
  id: string;
};

export type VersionResponse = {
  id: string;
};

export type RequirementResponse = {
  id: string;
  status: string;
};

export type GeneratedTaskResponse = {
  task_id: string;
  task_status: string;
};

export type StartedTaskResponse = {
  id: string;
  status: string;
  review_id: string;
  current_step?: string;
};

export type TaskDetailResponse = {
  id: string;
  status: string;
  current_step?: string;
  output?: {
    kind?: string;
  };
};

export type LifecycleResponse = {
  status: string;
  summary: {
    downstream_count: number;
    risk_count: number;
  };
};

export type MvpWorkflowResult = {
  requirementId: string;
  taskId: string;
  reviewId: string;
  taskStatus: string;
  currentStep: string;
  downstreamCount: number;
  riskCount: number;
};

export async function apiRequest<T>(
  path: string,
  options: {
    method?: string;
    token?: string;
    body?: unknown;
  } = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    body: options.body ? JSON.stringify(options.body) : undefined,
    headers: {
      'Content-Type': 'application/json',
      ...(options.token ? { Authorization: `Bearer ${options.token}` } : {}),
    },
    method: options.method ?? 'GET',
  });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  const payload = (await response.json()) as ApiEnvelope<T>;
  return payload.data;
}

export async function runMvpWorkflow(): Promise<MvpWorkflowResult> {
  const suffix = Date.now().toString(36);
  const login = await apiRequest<LoginResponse>('/api/auth/login', {
    method: 'POST',
    body: { username: 'admin@example.com', password: 'admin123' },
  });
  const token = login.access_token;
  const product = await apiRequest<ProductResponse>('/api/products', {
    method: 'POST',
    token,
    body: {
      code: `demo-${suffix}`,
      name: `AI Brain Demo ${suffix}`,
      owner_team: 'AI Platform',
    },
  });
  const version = await apiRequest<VersionResponse>(`/api/products/${product.id}/versions`, {
    method: 'POST',
    token,
    body: { code: `v-${suffix}`, name: 'v1 MVP', status: 'active' },
  });
  const requirement = await apiRequest<RequirementResponse>('/api/requirements', {
    method: 'POST',
    token,
    body: {
      content: '从前端触发需求审批到产品详细设计人工确认点。',
      priority: 'P1',
      product_id: product.id,
      title: `前端演示需求 ${suffix}`,
      version_id: version.id,
    },
  });
  await apiRequest<RequirementResponse>(`/api/requirements/${requirement.id}/approve`, {
    method: 'POST',
    token,
    body: { comment: '前端演示流审批通过' },
  });
  const generated = await apiRequest<GeneratedTaskResponse>(
    `/api/requirements/${requirement.id}/generate-task`,
    {
      method: 'POST',
      token,
    },
  );
  const started = await apiRequest<StartedTaskResponse>(
    `/api/ai-tasks/${generated.task_id}/start`,
    {
      method: 'POST',
      token,
    },
  );
  const task = await apiRequest<TaskDetailResponse>(`/api/ai-tasks/${generated.task_id}`, {
    token,
  });
  const lifecycle = await apiRequest<LifecycleResponse>(
    `/api/lifecycle/context?subject_type=requirement&subject_id=${requirement.id}&direction=both&include_risks=true`,
    { token },
  );

  return {
    currentStep: task.current_step ?? started.current_step ?? 'unknown',
    downstreamCount: lifecycle.summary.downstream_count,
    requirementId: requirement.id,
    reviewId: started.review_id,
    riskCount: lifecycle.summary.risk_count,
    taskId: generated.task_id,
    taskStatus: task.status,
  };
}
