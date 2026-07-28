/* global NodeFilter, URL, console, document, fetch, process, setTimeout, window */
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { chromium } from 'playwright';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(scriptDir, '..');
const repositoryRoot = path.resolve(webRoot, '..', '..');
const timeoutMs = Number(process.env.RD_E2E_TIMEOUT_SECONDS ?? '2400') * 1000;

function requiredEnvironment(name) {
  const value = String(process.env[name] ?? '').trim();
  if (!value) {
    throw new Error(`${name} is required`);
  }
  return value;
}

function checkedIdentifier(name, required = true) {
  const value = String(process.env[name] ?? '').trim();
  if (!value && !required) {
    return undefined;
  }
  if (!value) {
    throw new Error(`${name} is required`);
  }
  if (value.length > 160 || !/^[A-Za-z0-9._:/-]+$/.test(value)) {
    throw new Error(`${name} is invalid`);
  }
  return value;
}

function checkedBaseUrl(name, fallback) {
  const value = String(process.env[name] ?? fallback).trim();
  const parsed = new URL(value);
  if (!['http:', 'https:'].includes(parsed.protocol)) {
    throw new Error(`${name} must use http or https`);
  }
  return parsed.origin;
}

function checkedArtifactDirectory() {
  const value = requiredEnvironment('RD_E2E_ARTIFACT_DIR');
  const resolved = path.resolve(value);
  if (!path.isAbsolute(value) || resolved === repositoryRoot || resolved.startsWith(`${repositoryRoot}${path.sep}`)) {
    throw new Error('RD_E2E_ARTIFACT_DIR must be an absolute path outside the repository');
  }
  return resolved;
}

function parseMathChallenge(question) {
  const match = String(question).match(/(-?\d+)\s*([+\-×xX*÷/])\s*(-?\d+)\s*=\s*\?/);
  if (!match) {
    throw new Error('Unsupported login safety challenge');
  }
  const left = Number(match[1]);
  const right = Number(match[3]);
  switch (match[2]) {
    case '+':
      return String(left + right);
    case '-':
      return String(left - right);
    case '*':
    case 'x':
    case 'X':
    case '×':
      return String(left * right);
    case '/':
    case '÷':
      if (right === 0 || left % right !== 0) {
        throw new Error('Unsafe division login challenge');
      }
      return String(left / right);
    default:
      throw new Error('Unsupported login safety challenge operator');
  }
}

const sleep = (milliseconds) => new Promise((resolve) => {
  setTimeout(resolve, milliseconds);
});

async function poll(label, action, predicate, timeout = 30000) {
  const startedAt = Date.now();
  let latest;
  while (Date.now() - startedAt < timeout) {
    latest = await action();
    if (predicate(latest)) {
      return latest;
    }
    await sleep(250);
  }
  throw new Error(`${label} did not reach durable state`);
}

function routeOnly(value) {
  try {
    const parsed = new URL(value);
    return `${parsed.pathname}${parsed.search}`;
  } catch {
    return String(value).replace(/https?:\/\/[^/\s]+/gi, '[origin]');
  }
}

function redact(value, secrets, origins) {
  let redacted = String(value ?? '');
  for (const secret of secrets) {
    if (secret) {
      redacted = redacted.split(secret).join('[masked]');
    }
  }
  for (const origin of origins) {
    if (origin) {
      redacted = redacted.split(origin).join('[origin]');
    }
  }
  return redacted
    .replace(/Bearer\s+[A-Za-z0-9._~-]+/gi, 'Bearer [masked]')
    .replace(/((?:access|refresh)[_-]?token|password)\s*[:=]\s*\S+/gi, '$1=[masked]');
}

async function main() {
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) {
    throw new Error('RD_E2E_TIMEOUT_SECONDS must be a positive number');
  }
  if ((process.env.RD_E2E_REVIEW_CHANNEL ?? 'browser').trim().toLowerCase() !== 'browser') {
    throw new Error('RD_E2E_REVIEW_CHANNEL must be browser');
  }
  const versionId = checkedIdentifier('RD_E2E_VERSION_ID');
  const runId = checkedIdentifier('RD_E2E_RUN_ID');
  const taskId = checkedIdentifier('RD_E2E_TASK_ID', false);
  const decisionRequestId = checkedIdentifier('RD_E2E_DECISION_REQUEST_ID', false);
  if (!taskId && !decisionRequestId) {
    throw new Error('RD_E2E_TASK_ID or RD_E2E_DECISION_REQUEST_ID is required');
  }
  const username = requiredEnvironment('RD_E2E_REVIEWER_USERNAME');
  const password = requiredEnvironment('RD_E2E_REVIEWER_PASSWORD');
  const webUrl = checkedBaseUrl('AI_BRAIN_WEB_URL', 'http://127.0.0.1:5173');
  const apiUrl = checkedBaseUrl('AI_BRAIN_API_URL', 'http://127.0.0.1:8000');
  const artifactDir = checkedArtifactDirectory();
  const secrets = [username, password];
  const origins = [webUrl, apiUrl];
  const consoleIssues = [];
  const httpIssues = [];
  const evidence = {
    actions: {
      decision: false,
      review: false,
    },
    artifacts: [],
    decision_request_id: decisionRequestId ?? null,
    run_id: runId,
    task_id: taskId ?? null,
    version_id: versionId,
    visited_routes: [],
  };

  await fs.mkdir(artifactDir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { height: 900, width: 1440 } });
  const page = await context.newPage();
  page.setDefaultTimeout(Math.min(timeoutMs, 30000));
  let monitorApplication = false;

  page.on('console', (message) => {
    if (monitorApplication && ['error', 'warning'].includes(message.type())) {
      consoleIssues.push({
        route: routeOnly(page.url()),
        text: redact(message.text(), secrets, origins).slice(0, 240),
        type: message.type(),
      });
    }
  });
  page.on('pageerror', (error) => {
    if (monitorApplication) {
      consoleIssues.push({
        route: routeOnly(page.url()),
        text: redact(error.message, secrets, origins).slice(0, 240),
        type: 'pageerror',
      });
    }
  });
  page.on('response', (response) => {
    if (monitorApplication && response.url().includes('/api/') && response.status() >= 400) {
      httpIssues.push({ route: routeOnly(response.url()), status: response.status() });
    }
  });

  const api = async (requestPath) => {
    const response = await page.evaluate(
      async ({ apiOrigin, pathName }) => {
        const token = window.localStorage.getItem('ai_brain_access_token');
        if (!token) {
          return { ok: false, status: 401 };
        }
        const response = await fetch(new URL(pathName, apiOrigin), {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) {
          return { ok: false, status: response.status };
        }
        const payload = await response.json();
        return { data: payload?.data ?? payload, ok: true, status: response.status };
      },
      { apiOrigin: apiUrl, pathName: requestPath },
    );
    if (!response.ok) {
      throw new Error(`API read failed (${response.status}) ${routeOnly(requestPath)}`);
    }
    return response.data;
  };

  const assertHealthyPage = async (label, expectedPath) => {
    await page.waitForLoadState('domcontentloaded');
    const health = await page.evaluate(() => {
      const visibleText = document.body?.innerText?.trim() ?? '';
      const fatalOverlay = document.querySelector(
        'vite-error-overlay, #webpack-dev-server-client-overlay, .ant-result-error',
      );
      return {
        fatalOverlay: Boolean(fatalOverlay),
        textLength: visibleText.length,
      };
    });
    const currentUrl = new URL(page.url());
    const title = (await page.title()).trim();
    if (
      health.fatalOverlay ||
      health.textLength < 20 ||
      currentUrl.pathname !== expectedPath ||
      !title.includes('Enterprise AI Brain')
    ) {
      throw new Error(`${label} is blank, unhealthy, or on the wrong route/title`);
    }
  };

  const capture = async (fileName) => {
    await page.evaluate(({ values, pageOrigins }) => {
      const masks = new Set(values.filter(Boolean));
      try {
        const currentUser = JSON.parse(
          window.localStorage.getItem('ai_brain_current_user') ?? '{}',
        );
        for (const field of ['display_name', 'email', 'mobile', 'username']) {
          if (currentUser?.[field]) {
            masks.add(String(currentUser[field]));
          }
        }
      } catch {
        // A malformed current-user cache should not expose input values in evidence.
      }
      const maskText = (text) => {
        let output = text;
        for (const value of [...masks, ...pageOrigins]) {
          if (value) {
            output = output.split(value).join('[masked]');
          }
        }
        return output;
      };
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      let node = walker.nextNode();
      while (node) {
        node.textContent = maskText(node.textContent ?? '');
        node = walker.nextNode();
      }
      for (const input of document.querySelectorAll('input, textarea')) {
        input.value = input.value ? '[masked]' : '';
      }
    }, { pageOrigins: origins, values: secrets });
    const target = path.join(artifactDir, fileName);
    await page.screenshot({ fullPage: true, path: target });
    evidence.artifacts.push(fileName);
  };

  try {
    await page.goto(`${webUrl}/login`, { waitUntil: 'domcontentloaded' });
    await page.getByLabel('账号').fill(username);
    await page.getByLabel('密码').fill(password);
    const challengeAnswer = page.getByPlaceholder('请输入计算结果');
    if (await challengeAnswer.count()) {
      const questionInput = page.locator('input[disabled]').last();
      await poll(
        'login safety challenge',
        () => questionInput.inputValue(),
        (question) => Boolean(question && !question.includes('正在生成')),
      );
      await challengeAnswer.fill(parseMathChallenge(await questionInput.inputValue()));
    }
    await page.getByRole('button', { name: '登录' }).click();
    await page.waitForURL((url) => url.pathname !== '/login', { timeout: Math.min(timeoutMs, 30000) });
    monitorApplication = true;

    await page.goto(
      `${webUrl}/delivery/versions?version_id=${encodeURIComponent(versionId)}&view=dashboard`,
      { waitUntil: 'domcontentloaded' },
    );
    evidence.visited_routes.push(routeOnly(page.url()));
    await assertHealthyPage('iteration version dashboard', '/delivery/versions');
    const dashboard = await api(`/api/product-versions/${encodeURIComponent(versionId)}/dashboard`);
    if (dashboard?.version?.id !== versionId || !JSON.stringify(dashboard).includes(runId)) {
      throw new Error('Iteration version dashboard does not reference the supplied version and run');
    }
    const dashboardDialog = page.getByRole('dialog').filter({ hasText: '研发协同' });
    await dashboardDialog.waitFor({ state: 'visible' });
    const continueButton = dashboardDialog.getByRole('button', { name: '继续研发协同' });
    await continueButton.waitFor({ state: 'visible' });
    if (await continueButton.isDisabled()) {
      throw new Error('Continue R&D collaboration control is disabled');
    }
    await capture('01-version-dashboard.png');
    await continueButton.click();
    await page.waitForURL((url) => (
      url.pathname === '/delivery/rd-collaboration' &&
      url.searchParams.get('run_id') === runId
    ));

    evidence.visited_routes.push(routeOnly(page.url()));
    await assertHealthyPage('R&D collaboration workbench', '/delivery/rd-collaboration');
    await page.getByRole('heading', { name: '研发协同运行' }).waitFor({ state: 'visible' });
    await page.getByText(runId, { exact: true }).waitFor({ state: 'visible' });
    await page.getByText(/工作项 DAG/).waitFor({ state: 'visible' });
    await page.getByText('策略快照', { exact: true }).waitFor({ state: 'visible' });
    await page.getByText(/此工作台不提供部署操作/).waitFor({ state: 'visible' });
    const run = await api(`/api/delivery/rd-collaboration-runs/${encodeURIComponent(runId)}`);
    const strategySnapshotId = run?.strategy_snapshot_id ?? run?.policy_snapshot_id;
    if (
      run?.id !== runId ||
      run?.product_version_id !== versionId ||
      run?.delivery_target !== 'ready_for_release' ||
      !strategySnapshotId
    ) {
      throw new Error('R&D collaboration run scope or no-deploy boundary is incorrect');
    }
    const workItemsResponse = await api(
      `/api/delivery/rd-collaboration-runs/${encodeURIComponent(runId)}/work-items`,
    );
    const workItems = workItemsResponse?.items ?? [];
    const completedWorkItemCount = workItems.filter((item) => item?.status === 'completed').length;
    if (!workItems.length) {
      throw new Error('R&D collaboration work-item DAG is empty');
    }
    await page.getByRole('tab', {
      name: `工作项 DAG（${completedWorkItemCount}/${workItems.length}）`,
      exact: true,
    }).waitFor({ state: 'visible' });
    await capture('02-rd-collaboration-workbench.png');

    if (decisionRequestId) {
      const decisionPath = `/api/delivery/decision-requests/${encodeURIComponent(decisionRequestId)}`;
      const beforeDecision = await api(decisionPath);
      const safeOptionCode = 'approve_dispatch';
      const safeOption = (beforeDecision?.options_json ?? []).find(
        (option) => option?.code === safeOptionCode,
      );
      if (
        beforeDecision?.decision_type !== 'high_risk_ai_dispatch' ||
        !safeOption ||
        !Number.isInteger(beforeDecision.version)
      ) {
        throw new Error('High-risk decision does not expose the exact safe option and version');
      }
      if (beforeDecision.status === 'pending') {
        const sourceWorkItem = workItems.find(
          (item) => item?.suspended_decision_request_id === decisionRequestId,
        );
        if (!sourceWorkItem?.title) {
          throw new Error('Supplied high-risk decision is not suspended on a work item');
        }
        await page.getByRole('tab', { name: '人工决策' }).click();
        const decisionSource = page.getByText(`来源工作项：${sourceWorkItem.title}`, { exact: true });
        await decisionSource.waitFor({ state: 'visible' });
        await decisionSource.locator('..').getByRole('button', {
          name: safeOption.label ?? safeOption.code,
          exact: true,
        }).click();
        evidence.actions.decision = true;
        await poll(
          'high-risk decision',
          () => api(decisionPath),
          (current) => (
            current?.status === 'approved' &&
            current?.selected_option_code === safeOptionCode &&
            Number(current?.version) > Number(beforeDecision.version)
          ),
          Math.min(timeoutMs, 60000),
        );
      } else if (
        beforeDecision.status !== 'approved' ||
        beforeDecision.selected_option_code !== safeOptionCode
      ) {
        throw new Error('Completed high-risk decision did not use the exact safe option');
      }
      await capture('03-high-risk-decision.png');
    }

    if (taskId) {
      const taskPath = `/api/ai-tasks/${encodeURIComponent(taskId)}`;
      const beforeTask = await api(taskPath);
      if (
        beforeTask?.id !== taskId ||
        beforeTask?.collaboration_run_id !== runId ||
        !beforeTask?.work_item_id
      ) {
        throw new Error('Supplied task does not belong to the supplied collaboration run');
      }
      const workItemId = String(beforeTask.work_item_id);
      const beforeWorkItems = await api(
        `/api/delivery/rd-collaboration-runs/${encodeURIComponent(runId)}/work-items`,
      );
      const beforeWorkItem = (beforeWorkItems?.items ?? []).find(
        (item) => item?.id === workItemId,
      );
      if (!beforeWorkItem || !Number.isInteger(beforeWorkItem.version)) {
        throw new Error('Task work item is missing or unversioned');
      }
      const pendingReview = beforeTask?.pending_review;
      let beforeReview;
      if (pendingReview?.id) {
        beforeReview = await api(`/api/reviews/${encodeURIComponent(pendingReview.id)}`);
        if (
          beforeReview?.id !== pendingReview.id ||
          beforeReview?.ai_task_id !== taskId ||
          beforeReview?.status !== 'pending' ||
          !Number.isInteger(beforeReview?.version)
        ) {
          throw new Error('Task pending Review is not exact, pending, and versioned');
        }
      }

      await page.goto(
        `${webUrl}/delivery/rd-tasks?task_id=${encodeURIComponent(taskId)}`,
        { waitUntil: 'domcontentloaded' },
      );
      evidence.visited_routes.push(routeOnly(page.url()));
      await assertHealthyPage('R&D task detail', '/delivery/rd-tasks');
      const detailDialog = page.getByRole('dialog').filter({ hasText: taskId });
      await detailDialog.waitFor({ state: 'visible' });
      for (const directAction of ['启动任务', '取消任务', '重试任务', '批量取消']) {
        if (await detailDialog.getByRole('button', { name: directAction, exact: true }).count()) {
          throw new Error(`V2 task detail exposes forbidden direct action: ${directAction}`);
        }
      }

      if (beforeReview) {
        await detailDialog.getByRole('button', { name: '处理待确认' }).click();
        const reviewDialog = page.getByRole('dialog').filter({ hasText: `确认输出` });
        await reviewDialog.waitFor({ state: 'visible' });
        await reviewDialog.getByText(beforeReview.id, { exact: true }).waitFor({ state: 'visible' });
        const approveButton = reviewDialog.getByRole('button', { name: '确认通过', exact: true });
        await approveButton.click();
        evidence.actions.review = true;
        await poll(
          'task Review approval',
          async () => {
            const [review, task, workItems] = await Promise.all([
              api(`/api/reviews/${encodeURIComponent(beforeReview.id)}`),
              api(taskPath),
              api(`/api/delivery/rd-collaboration-runs/${encodeURIComponent(runId)}/work-items`),
            ]);
            return {
              review,
              task,
              workItem: (workItems?.items ?? []).find((item) => item?.id === workItemId),
            };
          },
          (current) => (
            current.review?.status === 'approved' &&
            Number(current.review?.version) > Number(beforeReview.version) &&
            !current.task?.pending_review &&
            ['approved', 'completed'].includes(current.workItem?.status) &&
            Number(current.workItem?.version) > Number(beforeWorkItem.version)
          ),
          Math.min(timeoutMs, 60000),
        );
      } else {
        const currentWorkItem = beforeWorkItem;
        if (
          !['approved', 'completed'].includes(currentWorkItem.status) ||
          await detailDialog.getByRole('button', { name: '处理待确认' }).count()
        ) {
          throw new Error('Read-only replay is not durably completed');
        }
      }
      await capture('04-task-review.png');
    }

    if (consoleIssues.length || httpIssues.length) {
      throw new Error(
        `Browser diagnostics failed: console=${consoleIssues.length}, http=${httpIssues.length}`,
      );
    }
    evidence.console_issues = consoleIssues;
    evidence.http_issues = httpIssues;
    await fs.writeFile(
      path.join(artifactDir, 'browser-evidence.json'),
      `${JSON.stringify(evidence, null, 2)}\n`,
      { encoding: 'utf8', mode: 0o600 },
    );
    process.stdout.write('R&D collaboration browser smoke passed\n');
  } finally {
    await context.close();
    await browser.close();
  }
}

main().catch((error) => {
  const secrets = [
    String(process.env.RD_E2E_REVIEWER_USERNAME ?? ''),
    String(process.env.RD_E2E_REVIEWER_PASSWORD ?? ''),
  ];
  const origins = [
    String(process.env.AI_BRAIN_WEB_URL ?? ''),
    String(process.env.AI_BRAIN_API_URL ?? ''),
  ];
  console.error(`R&D collaboration browser smoke failed: ${redact(error?.message, secrets, origins)}`);
  process.exitCode = 1;
});
