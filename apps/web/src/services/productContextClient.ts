import type {
  ProductContextOption,
  ProductVersionOption,
} from '../data/management';
import { apiRequest } from './apiClient';
import type { ListResponse } from './apiClient';
import { requireAccessToken } from './authClient';

const PRODUCT_CONTEXT_PAGE_SIZE = 100;
const VERSION_CONTEXT_PAGE_SIZE = 100;
const CONTEXT_OPTION_MAX_PAGE_COUNT = 50;

export type ProductFilterOption = {
  code: string;
  id: string;
  name: string;
};

type ProductListItem = {
  code?: string;
  id: string;
  name: string;
};

type ProductVersionListItem = {
  code?: string;
  description?: string | null;
  id: string;
  name: string;
  product_id: string;
  status?: string;
};

function mapProductVersionOption(version: ProductVersionListItem): ProductVersionOption {
  return {
    code: version.code ?? version.id,
    description: version.description ?? undefined,
    id: version.id,
    name: version.name,
    status: version.status ?? '-',
  };
}

function isRequirementSchedulableVersion(version: ProductVersionListItem): boolean {
  return ['active', 'planning'].includes((version.status ?? '').toLowerCase());
}

function isBugAssignableVersion(version: ProductVersionListItem): boolean {
  return (version.status ?? '').toLowerCase() !== 'archived';
}

function isDeploymentEligibleVersion(version: ProductVersionListItem): boolean {
  return (version.status ?? '').toLowerCase() !== 'archived';
}

function mapProductContexts(
  products: ProductListItem[],
  versions: ProductVersionListItem[],
): ProductContextOption[] {
  const versionsByProductId = versions.reduce(
    (groupedVersions, version) => {
      const rows = groupedVersions.get(version.product_id) ?? [];
      rows.push(version);
      groupedVersions.set(version.product_id, rows);
      return groupedVersions;
    },
    new Map<string, ProductVersionListItem[]>(),
  );

  return products.map((product) => ({
    code: product.code ?? product.id,
    id: product.id,
    name: product.name,
    versions: (versionsByProductId.get(product.id) ?? []).map(mapProductVersionOption),
  }));
}

function paginatedListPath(path: string, page: number, pageSize: number) {
  const [basePath, queryString = ''] = path.split('?');
  const params = new URLSearchParams(queryString);
  params.set('page_size', String(pageSize));
  if (page > 1) {
    params.set('page', String(page));
  } else {
    params.delete('page');
  }
  return `${basePath}?${params.toString()}`;
}

async function fetchAllListItems<T>(
  path: string,
  {
    pageSize,
    token,
  }: {
    pageSize: number;
    token: string;
  },
): Promise<T[]> {
  const items: T[] = [];
  let currentPage = 1;
  let currentPageSize = pageSize;

  for (let pageCount = 0; pageCount < CONTEXT_OPTION_MAX_PAGE_COUNT; pageCount += 1) {
    const response = await apiRequest<ListResponse<T>>(
      paginatedListPath(path, currentPage, currentPageSize),
      { token },
    );
    items.push(...response.items);
    const total = response.total ?? items.length;
    if (items.length >= total || response.items.length === 0) {
      break;
    }
    currentPage = (response.page ?? currentPage) + 1;
    currentPageSize = response.page_size ?? currentPageSize;
  }

  return items;
}

export async function fetchProductContextOptions(): Promise<ProductContextOption[]> {
  const token = requireAccessToken();
  const [products, versions] = await Promise.all([
    fetchAllListItems<ProductListItem>('/api/products?active_only=true', {
      pageSize: PRODUCT_CONTEXT_PAGE_SIZE,
      token,
    }),
    fetchAllListItems<ProductVersionListItem>('/api/product-versions', {
      pageSize: VERSION_CONTEXT_PAGE_SIZE,
      token,
    }),
  ]);
  return mapProductContexts(products, versions.filter(isDeploymentEligibleVersion));
}

export async function fetchBugProductContextOptions(): Promise<ProductContextOption[]> {
  const token = requireAccessToken();
  const [products, versions] = await Promise.all([
    fetchAllListItems<ProductListItem>('/api/products?active_only=true', {
      pageSize: PRODUCT_CONTEXT_PAGE_SIZE,
      token,
    }),
    fetchAllListItems<ProductVersionListItem>('/api/product-versions', {
      pageSize: VERSION_CONTEXT_PAGE_SIZE,
      token,
    }),
  ]);
  return mapProductContexts(products, versions.filter(isBugAssignableVersion));
}

export async function fetchRequirementProductContextOptions(): Promise<ProductContextOption[]> {
  const token = requireAccessToken();
  const [products, versions] = await Promise.all([
    fetchAllListItems<ProductListItem>('/api/products?active_only=true', {
      pageSize: PRODUCT_CONTEXT_PAGE_SIZE,
      token,
    }),
    fetchAllListItems<ProductVersionListItem>('/api/product-versions', {
      pageSize: VERSION_CONTEXT_PAGE_SIZE,
      token,
    }),
  ]);
  return mapProductContexts(
    products,
    versions.filter(isRequirementSchedulableVersion),
  );
}

export async function fetchActiveProductOptions(): Promise<ProductFilterOption[]> {
  const token = requireAccessToken();
  const products = await fetchAllListItems<ProductListItem>('/api/products?active_only=true', {
    pageSize: PRODUCT_CONTEXT_PAGE_SIZE,
    token,
  });
  return products.map((product) => ({
    code: product.code ?? product.id,
    id: product.id,
    name: product.name,
  }));
}
