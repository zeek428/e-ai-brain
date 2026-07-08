import type { KnowledgeRecord } from '../../data/management';

export type KnowledgeFormValues = {
  chunk_strategy?: string;
  content?: string;
  doc_type: string;
  folder_id?: string;
  index_status?: KnowledgeRecord['status'];
  knowledge_space_id?: string;
  permission_roles?: string[];
  parser_engine?: string;
  tags?: string;
  title: string;
};

export type KnowledgeSpaceFormValues = {
  code: string;
  description?: string;
  name: string;
};

export type KnowledgeFolderFormValues = {
  name: string;
};

export type KnowledgeFolderEditFormValues = {
  folder_id: string;
  name?: string;
  parent_folder_id?: string;
  sort_order?: number;
  status?: string;
};

export type KnowledgeBatchMoveFormValues = {
  folder_id?: string;
};

export type RejectDepositFormValues = {
  reason: string;
};

export type KnowledgeSearchFormValues = {
  knowledge_space_id?: string;
  query: string;
  top_k?: number;
};

export type KnowledgeQuickSearchFormValues = {
  quick_query: string;
  top_k?: number;
};

export type KnowledgeAdvancedFilterValues = {
  documentType?: string;
  folderId?: string;
  ownerRole?: string;
};

export type KnowledgeWorkbenchTab = 'deposits' | 'documents' | 'governance' | 'imports' | 'search';
