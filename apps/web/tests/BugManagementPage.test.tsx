import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import BugsPage from '../src/pages/Bugs';
import { saveCurrentUser } from '../src/services/aiBrain';

const originalCreateObjectURL = URL.createObjectURL;
const originalRevokeObjectURL = URL.revokeObjectURL;

describe('bug management page', () => {
  afterEach(() => {
    Modal.destroyAll();
    message.destroy();
    notification.destroy();
    cleanup();
    window.localStorage.clear();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      value: originalCreateObjectURL,
    });
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      value: originalRevokeObjectURL,
    });
  });

  it('edits bug lifecycle evidence and duplicate merge fields from backend data', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? 'GET';
      if (path.startsWith('/api/products?') && path.includes('active_only=true')) {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'API-PRODUCT',
                id: 'product_api',
                name: '接口产品',
                owner_team: 'API Team',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (
        path === '/api/product-versions' ||
        (path.startsWith('/api/product-versions?') && !path.includes('active_only=true'))
      ) {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'v1',
                id: 'version_api',
                name: 'v1',
                product_id: 'product_api',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if ((path === '/api/bugs' || path.startsWith('/api/bugs?')) && method === 'GET') {
        const isVersionFiltered = path.includes('version=v1+MVP') || path.includes('version=v1%20MVP');
        const items = [
          {
            assignee: 'qa@example.com',
            created_at: '2026-06-04T08:00:00+00:00',
            description: '支付链路失败',
            duplicate_of_bug_id: 'bug_target',
            evidence: { log_id: 'log-1' },
            id: 'bug_main',
            module_code: 'checkout',
            product_id: 'product_api',
            reproduce_steps: ['打开支付页', '点击支付'],
            severity: 'major',
            source: 'manual_test',
            status: 'closed',
            title: '支付失败',
            version_id: 'version_api',
            version_name: 'v1 MVP',
          },
          {
            assignee: 'rd@example.com',
            created_at: '2026-06-04T08:10:00+00:00',
            description: '同类支付问题',
            id: 'bug_target',
            module_code: 'checkout',
            product_id: 'product_api',
            reproduce_steps: [],
            severity: 'minor',
            source: 'ai_auto_test',
            status: 'triaged',
            title: '支付重复问题',
            version_id: 'version_regression',
            version_name: 'v2 回归',
          },
        ];
        return jsonResponse({
          data: {
            items: isVersionFiltered ? items.slice(0, 1) : items,
            total: isVersionFiltered ? 1 : 2,
          },
        });
      }
      if (path === '/api/bugs/bug_main' && method === 'PATCH') {
        return jsonResponse({ data: { id: 'bug_main' } });
      }
      throw new Error(`Unexpected fetch call: ${path} ${method}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<BugsPage />);

    expect(await screen.findByText('支付失败')).toBeInTheDocument();
    expect(screen.getByText('创建时间')).toBeInTheDocument();
    expect(screen.getByText('2026-06-04 16:00')).toBeInTheDocument();
    expect(screen.getByText('2026-06-04 16:10')).toBeInTheDocument();
    expect(screen.getByText('v1 MVP')).toBeInTheDocument();
    expect(screen.getByText('v2 回归')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('迭代版本'), { target: { value: 'v1 MVP' } });
    fireEvent.submit(screen.getByRole('form', { name: '查询表格' }));

    await waitFor(() => expect(screen.queryByText('支付重复问题')).not.toBeInTheDocument());
    expect(screen.getByText('支付失败')).toBeInTheDocument();

    fireEvent.reset(screen.getByRole('form', { name: '查询表格' }));
    expect(await screen.findByText('支付重复问题')).toBeInTheDocument();

    const bugRow = screen.getByText('支付失败').closest('tr');
    expect(bugRow).not.toBeNull();
    fireEvent.click(within(bugRow as HTMLElement).getByRole('button', { name: /编辑/ }));

    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByLabelText('复现步骤')).toHaveValue('打开支付页\n点击支付');
    expect(within(dialog).getByLabelText('证据 JSON')).toHaveValue(
      JSON.stringify({ log_id: 'log-1' }, null, 2),
    );
    expect(within(dialog).getByLabelText('重复归并')).toBeInTheDocument();

    fireEvent.change(within(dialog).getByLabelText('复现步骤'), {
      target: { value: '打开支付页\n点击支付\n查看错误提示' },
    });
    fireEvent.change(within(dialog).getByLabelText('证据 JSON'), {
      target: { value: JSON.stringify({ log_id: 'log-2', screenshot: 'pay-fail.png' }, null, 2) },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: /保\s*存/ }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method, init?.body])).toContainEqual([
        '/api/bugs/bug_main',
        'PATCH',
        JSON.stringify({
          assignee: 'qa@example.com',
          description: '支付链路失败',
          duplicate_of_bug_id: 'bug_target',
          evidence: { log_id: 'log-2', screenshot: 'pay-fail.png' },
          reproduce_steps: ['打开支付页', '点击支付', '查看错误提示'],
          severity: 'major',
          status: 'closed',
          title: '支付失败',
        }),
      ]),
    );
  });

  it('batch updates selected bugs from the bug management page', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const bugRows = [
      {
        assignee: 'user_admin',
        created_at: '2026-06-04T09:00:00+00:00',
        description: '批量处理第一条',
        id: 'bug_batch_one',
        module_code: 'delivery',
        product_id: 'product_api',
        reproduce_steps: [],
        severity: 'minor',
        source: 'manual_test',
        status: 'open',
        title: '批量 Bug 一',
        version_id: 'version_api',
        version_name: 'v1 MVP',
      },
      {
        assignee: 'user_admin',
        created_at: '2026-06-04T09:10:00+00:00',
        description: '批量处理第二条',
        id: 'bug_batch_two',
        module_code: 'delivery',
        product_id: 'product_api',
        reproduce_steps: [],
        severity: 'major',
        source: 'manual_test',
        status: 'needs_info',
        title: '批量 Bug 二',
        version_id: 'version_api',
        version_name: 'v1 MVP',
      },
    ];
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? 'GET';
      if (path.startsWith('/api/products?') && path.includes('active_only=true')) {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'API-PRODUCT',
                id: 'product_api',
                name: '接口产品',
                owner_team: 'API Team',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (
        path === '/api/product-versions' ||
        (path.startsWith('/api/product-versions?') && !path.includes('active_only=true'))
      ) {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'v1',
                id: 'version_api',
                name: 'v1 MVP',
                product_id: 'product_api',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if ((path === '/api/bugs' || path.startsWith('/api/bugs?')) && method === 'GET') {
        return jsonResponse({
          data: {
            items: bugRows,
            page: 1,
            page_size: 10,
            total: bugRows.length,
          },
        });
      }
      if (path === '/api/bugs/batch-update' && method === 'POST') {
        return jsonResponse({
          data: {
            batch_id: 'bug_batch_001',
            skipped: [
              {
                code: 'BUG_STATE_INVALID',
                id: 'bug_closed',
                message: 'Bug cannot move to requested status',
              },
            ],
            skipped_count: 1,
            updated: bugRows.map((bug) => ({
              ...bug,
              assignee: 'qa@example.com',
              severity: 'major',
              status: 'triaged',
            })),
            updated_count: 2,
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${path} ${method}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<BugsPage />);

    expect(await screen.findByText('批量 Bug 一')).toBeInTheDocument();
    expect(screen.getByText('批量 Bug 二')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('checkbox', { name: '选择 bug_batch_one' }));
    fireEvent.click(screen.getByRole('checkbox', { name: '选择 bug_batch_two' }));
    fireEvent.click(screen.getByRole('button', { name: /批量处理/ }));

    const dialog = await screen.findByRole('dialog', { name: /批量处理 Bug/ });
    expect(within(dialog).getByLabelText('状态')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('严重级别')).toBeInTheDocument();
    fireEvent.change(within(dialog).getByLabelText('处理人'), {
      target: { value: 'qa@example.com' },
    });
    fireEvent.change(within(dialog).getByLabelText('处理说明'), {
      target: { value: '批量分诊给 QA' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: /批量处理/ }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toContainEqual([
        '/api/bugs/batch-update',
        'POST',
      ]),
    );
    const batchCall = fetchMock.mock.calls.find(
      ([path, init]) => path === '/api/bugs/batch-update' && init?.method === 'POST',
    );
    expect(JSON.parse(String(batchCall?.[1]?.body))).toEqual({
      assignee: 'qa@example.com',
      bug_ids: ['bug_batch_one', 'bug_batch_two'],
      reason: '批量分诊给 QA',
    });
    const resultDialog = await screen.findByRole('dialog', { name: /Bug 批量处理结果/ });
    expect(within(resultDialog).getByText('bug_batch_001')).toBeInTheDocument();
    expect(within(resultDialog).getByText('更新数')).toBeInTheDocument();
    expect(within(resultDialog).getByText('2')).toBeInTheDocument();
    expect(within(resultDialog).getByText('bug_closed')).toBeInTheDocument();
    expect(
      within(resultDialog).getByText('BUG_STATE_INVALID · Bug cannot move to requested status'),
    ).toBeInTheDocument();
  });

  it('renders bug management as read-only for viewer users', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? 'GET';
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-viewer' });
      if (path.startsWith('/api/products?') && path.includes('active_only=true')) {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'API-PRODUCT',
                id: 'product_api',
                name: '接口产品',
                owner_team: 'API Team',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/product-versions' || path.startsWith('/api/product-versions?')) {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'v1',
                id: 'version_api',
                name: 'v1 MVP',
                product_id: 'product_api',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if ((path === '/api/bugs' || path.startsWith('/api/bugs?')) && method === 'GET') {
        return jsonResponse({
          data: {
            items: [
              {
                assignee: 'qa@example.com',
                created_at: '2026-06-04T08:00:00+00:00',
                description: 'viewer 只能查看 Bug。',
                id: 'bug_viewer',
                module_code: 'checkout',
                product_id: 'product_api',
                reproduce_steps: [],
                severity: 'major',
                source: 'manual_test',
                status: 'open',
                title: '只读 Bug',
                version_id: 'version_api',
                version_name: 'v1 MVP',
              },
            ],
            page: 1,
            page_size: 10,
            total: 1,
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${path} ${method}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-viewer');
    saveCurrentUser({
      display_name: '查看者',
      id: 'user_viewer',
      permissions: ['bug.read'],
      roles: ['viewer'],
      username: 'viewer@example.com',
    });
    vi.stubGlobal('fetch', fetchMock);

    render(<BugsPage />);

    expect(await screen.findByText('只读 Bug')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /登记 Bug/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /批量处理/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('checkbox', { name: '选择 bug_viewer' })).not.toBeInTheDocument();

    const bugRow = screen.getByText('只读 Bug').closest('tr');
    expect(bugRow).not.toBeNull();
    expect(within(bugRow as HTMLElement).getByRole('link', { name: '全链路' })).toBeInTheDocument();
    expect(within(bugRow as HTMLElement).queryByRole('button', { name: /编辑/ })).not.toBeInTheDocument();
    expect(within(bugRow as HTMLElement).queryByRole('button', { name: /删除/ })).not.toBeInTheDocument();
  });

  it('allows selecting a testing iteration version when registering a bug', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? 'GET';
      if (path.startsWith('/api/products?') && path.includes('active_only=true')) {
        const fillerProducts = Array.from({ length: 11 }, (_, index) => ({
          code: `QA-${index + 1}`,
          id: `product_filler_${index + 1}`,
          name: `测试产品 ${index + 1}`,
          status: 'active',
        }));
        return jsonResponse({
          data: {
            items: [
              ...fillerProducts,
              {
                code: 'AI-BRAIN',
                id: 'product_ai_brain',
                name: 'AI Brain',
                status: 'active',
              },
            ],
            page: 1,
            page_size: 100,
            total: 12,
          },
        });
      }
      if (
        path === '/api/product-versions' ||
        (path.startsWith('/api/product-versions?') && !path.includes('active_only=true'))
      ) {
        return jsonResponse({
          data: {
            items: [
              {
                code: '2026-06',
                id: 'version_testing',
                name: '2026-06 测试迭代',
                product_id: 'product_ai_brain',
                status: 'testing',
              },
              {
                code: '2026-05',
                id: 'version_archived',
                name: '2026-05 历史归档',
                product_id: 'product_ai_brain',
                status: 'archived',
              },
            ],
            total: 2,
          },
        });
      }
      if (path === '/api/product-versions?active_only=true') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if ((path === '/api/bugs' || path.startsWith('/api/bugs?')) && method === 'GET') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (path === '/api/bugs' && method === 'POST') {
        return jsonResponse({ data: { id: 'bug_testing' } });
      }
      throw new Error(`Unexpected fetch call: ${path} ${method}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<BugsPage />);

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path]) => String(path))).toContain(
        '/api/products?active_only=true&page_size=100',
      ),
    );

    fireEvent.click(await screen.findByRole('button', { name: /登记 Bug/ }));
    const dialog = await screen.findByRole('dialog');
    fireEvent.change(within(dialog).getByLabelText('Bug 标题'), {
      target: { value: '测试版本 Bug' },
    });
    fireEvent.change(within(dialog).getByLabelText('描述'), {
      target: { value: '测试中版本登记 Bug 应能选择目标版本。' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: /保\s*存/ }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method, init?.body])).toContainEqual([
        '/api/bugs',
        'POST',
        JSON.stringify({
          description: '测试中版本登记 Bug 应能选择目标版本。',
          evidence: {},
          product_id: 'product_ai_brain',
          reproduce_steps: [],
          severity: 'major',
          source: 'manual_test',
          title: '测试版本 Bug',
          version_id: 'version_testing',
        }),
      ]),
    );
  });

  it('uploads multiple selected and pasted bug images before registering a bug', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
    });
    const uploadBodies: Array<Record<string, unknown>> = [];
    const previewRequests: string[] = [];
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? 'GET';
      if (path.startsWith('/api/products?') && path.includes('active_only=true')) {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'AI-BRAIN',
                id: 'product_ai_brain',
                name: 'AI Brain',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (
        path === '/api/product-versions' ||
        (path.startsWith('/api/product-versions?') && !path.includes('active_only=true'))
      ) {
        return jsonResponse({
          data: {
            items: [
              {
                code: '2026-07',
                id: 'version_testing',
                name: '2026-07 测试迭代',
                product_id: 'product_ai_brain',
                status: 'testing',
              },
            ],
            total: 1,
          },
        });
      }
      if (path === '/api/product-versions?active_only=true') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if ((path === '/api/bugs' || path.startsWith('/api/bugs?')) && method === 'GET') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (path === '/api/bugs/images/upload' && method === 'POST') {
        const body = JSON.parse(String(init?.body)) as {
          filename: string;
          mime_type: string;
          source: string;
        };
        uploadBodies.push(body);
        return jsonResponse({
          data: {
            bucket: 'ai-brain-knowledge',
            content_hash: `hash-${body.filename}`,
            filename: body.filename,
            id: `bug_image_${uploadBodies.length}`,
            mime_type: body.mime_type,
            object_key: `bugs/evidence/${body.filename}`,
            size_bytes: 128,
            source: body.source,
            storage_provider: 'minio',
            uploaded_at: '2026-07-03T08:00:00+00:00',
            uploaded_by: 'user_admin',
          },
        });
      }
      if (path.startsWith('/api/bugs/images/preview?') && method === 'GET') {
        previewRequests.push(path);
        return new Response(new Blob(['preview'], { type: 'image/png' }), {
          headers: { 'Content-Type': 'image/png' },
          status: 200,
        });
      }
      if (path === '/api/bugs' && method === 'POST') {
        return jsonResponse({ data: { id: 'bug_with_images' } });
      }
      throw new Error(`Unexpected fetch call: ${path} ${method}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);
    const createObjectURL = vi.fn(() => 'blob:bug-preview');
    const revokeObjectURL = vi.fn();
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      value: createObjectURL,
    });
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      value: revokeObjectURL,
    });

    render(<BugsPage />);

    fireEvent.click(await screen.findByRole('button', { name: /登记 Bug/ }));
    const dialog = await screen.findByRole('dialog');
    fireEvent.change(within(dialog).getByLabelText('Bug 标题'), {
      target: { value: '图片上传 Bug' },
    });
    fireEvent.change(within(dialog).getByLabelText('描述'), {
      target: { value: '登记 Bug 时需要上传多张截图。' },
    });

    const firstImage = new File(['first-image'], 'first.png', { type: 'image/png' });
    const secondImage = new File(['second-image'], 'second.jpg', { type: 'image/jpeg' });
    fireEvent.change(within(dialog).getByLabelText('选择图片文件'), {
      target: { files: [firstImage, secondImage] },
    });

    await waitFor(() => expect(uploadBodies).toHaveLength(2));
    expect(within(dialog).getByText('first.png')).toBeInTheDocument();
    expect(within(dialog).getByText('second.jpg')).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole('button', { name: '预览图片 first.png' }));
    const previewImage = await screen.findByRole('img', { name: 'first.png' });
    const previewDialog = previewImage.closest('[role="dialog"]');
    expect(previewDialog).not.toBeNull();
    expect(previewRequests).toHaveLength(1);
    expect(previewRequests[0]).toContain('/api/bugs/images/preview?');
    expect(previewRequests[0]).toContain('object_key=bugs%2Fevidence%2Ffirst.png');
    expect(createObjectURL).toHaveBeenCalled();
    expect(previewImage).toHaveAttribute('src', 'blob:bug-preview');
    fireEvent.click(within(previewDialog as HTMLElement).getByRole('button', { name: 'Close' }));
    await waitFor(() => expect(revokeObjectURL).toHaveBeenCalledWith('blob:bug-preview'));

    const pastedImage = new File(['pasted-image'], 'clipboard.png', { type: 'image/png' });
    fireEvent.paste(within(dialog).getByLabelText('粘贴图片区域'), {
      clipboardData: {
        files: [pastedImage],
        items: [
          {
            getAsFile: () => pastedImage,
            kind: 'file',
            type: 'image/png',
          },
        ],
      },
    });

    await waitFor(() => expect(uploadBodies).toHaveLength(3));
    expect(uploadBodies.map((body) => body.source)).toEqual([
      'file_picker',
      'file_picker',
      'clipboard',
    ]);
    expect(within(dialog).getByText('clipboard.png')).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole('button', { name: /保\s*存/ }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method, init?.body])).toContainEqual([
        '/api/bugs',
        'POST',
        JSON.stringify({
          description: '登记 Bug 时需要上传多张截图。',
          evidence: {
            images: [
              {
                bucket: 'ai-brain-knowledge',
                content_hash: 'hash-first.png',
                filename: 'first.png',
                id: 'bug_image_1',
                mime_type: 'image/png',
                object_key: 'bugs/evidence/first.png',
                size_bytes: 128,
                source: 'file_picker',
                storage_provider: 'minio',
                uploaded_at: '2026-07-03T08:00:00+00:00',
                uploaded_by: 'user_admin',
              },
              {
                bucket: 'ai-brain-knowledge',
                content_hash: 'hash-second.jpg',
                filename: 'second.jpg',
                id: 'bug_image_2',
                mime_type: 'image/jpeg',
                object_key: 'bugs/evidence/second.jpg',
                size_bytes: 128,
                source: 'file_picker',
                storage_provider: 'minio',
                uploaded_at: '2026-07-03T08:00:00+00:00',
                uploaded_by: 'user_admin',
              },
              {
                bucket: 'ai-brain-knowledge',
                content_hash: 'hash-clipboard.png',
                filename: 'clipboard.png',
                id: 'bug_image_3',
                mime_type: 'image/png',
                object_key: 'bugs/evidence/clipboard.png',
                size_bytes: 128,
                source: 'clipboard',
                storage_provider: 'minio',
                uploaded_at: '2026-07-03T08:00:00+00:00',
                uploaded_by: 'user_admin',
              },
            ],
          },
          product_id: 'product_ai_brain',
          reproduce_steps: [],
          severity: 'major',
          source: 'manual_test',
          title: '图片上传 Bug',
          version_id: 'version_testing',
        }),
      ]),
    );
  });
});
