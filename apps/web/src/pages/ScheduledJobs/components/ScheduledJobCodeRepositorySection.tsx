import { PlusOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { Alert, Button, Col, Form, Input, InputNumber, Row, Select, Switch } from 'antd';

import type { ProductGitRepositoryOption } from '../../../services/aiBrain';
import { ScheduledJobFormSection as FormSection } from './ScheduledJobFormSection';

type SelectOption = {
  label: string;
  value: string;
};

type ScheduledJobCodeRepositorySectionProps = {
  advancedInitiallyVisible?: boolean;
  builtinRuleOptions: SelectOption[];
  ignoreRuleOptions: SelectOption[];
  loadingRepositories: boolean;
  onRepositoryChange: (repositoryId?: string) => void;
  onScanModeChange: (scanMode?: string) => void;
  repositories: ProductGitRepositoryOption[];
  scanModeOptions: SelectOption[];
  scannerEngineOptions: SelectOption[];
  selectedProductId?: string;
  selectedRepositoryDefaultBranch?: string | null;
  severityThresholdOptions: SelectOption[];
};

export function ScheduledJobCodeRepositorySection({
  advancedInitiallyVisible = false,
  builtinRuleOptions,
  ignoreRuleOptions,
  loadingRepositories,
  onRepositoryChange,
  onScanModeChange,
  repositories,
  scanModeOptions,
  scannerEngineOptions,
  selectedProductId,
  selectedRepositoryDefaultBranch,
  severityThresholdOptions,
}: ScheduledJobCodeRepositorySectionProps) {
  const repositoryOptions = repositories.map((repository) => ({
    label: repository.label,
    value: repository.id,
  }));
  const productRepositoryConfigHref = selectedProductId
    ? `/assets/products?product_id=${encodeURIComponent(selectedProductId)}&resource=repository&action=create`
    : '/assets/products';
  const repositorySelectDisabled = !selectedProductId || (!loadingRepositories && repositories.length === 0);
  const [advancedVisible, setAdvancedVisible] = useState(advancedInitiallyVisible);
  useEffect(() => {
    setAdvancedVisible(advancedInitiallyVisible);
  }, [advancedInitiallyVisible]);

  return (
    <FormSection label="代码仓库配置" marker="仓库">
      <Row gutter={12}>
        {!selectedProductId ? (
          <Col span={24}>
            <Alert
              showIcon
              title="请先选择产品，系统会加载该产品下维护的代码仓库。"
              type="info"
            />
          </Col>
        ) : null}
        {selectedProductId && !loadingRepositories && repositories.length === 0 ? (
          <Col span={24}>
            <Alert
              action={(
                <Button
                  href={productRepositoryConfigHref}
                  icon={<PlusOutlined />}
                  size="small"
                  type="primary"
                >
                  新增 Git 资源
                </Button>
              )}
              showIcon
              title="当前产品还没有维护代码仓库。请先在产品管理的产品配置里新增 Git 资源，再创建代码巡检作业。"
              type="warning"
            />
          </Col>
        ) : null}
        {selectedProductId && !loadingRepositories && repositories.length > 0 ? (
          <Col span={24}>
            <Alert
              showIcon
              title={`默认扫描该产品下 ${repositories.length} 个 active 代码仓库`}
              type="info"
            />
          </Col>
        ) : null}
        <Col span={24}>
          <Form.Item label="扫描方式" name={['config_json', 'scan_mode']}>
            <Select options={scanModeOptions} onChange={onScanModeChange} />
          </Form.Item>
        </Col>
        <Col span={24}>
          <Button onClick={() => setAdvancedVisible((visible) => !visible)}>
            高级仓库配置
          </Button>
        </Col>
        {advancedVisible ? (
          <>
            <Col span={14}>
              <Form.Item
                label="代码仓库"
                name={['config_json', 'repository_id']}
              >
                <Select
                  allowClear
                  disabled={repositorySelectDisabled}
                  loading={loadingRepositories}
                  onChange={onRepositoryChange}
                  optionFilterProp="label"
                  options={repositoryOptions}
                  placeholder={selectedProductId ? '默认全部仓库，可指定单仓库' : '请先选择产品'}
                  showSearch
                />
              </Form.Item>
            </Col>
            <Col span={10}>
              <Form.Item label="扫描分支" name={['config_json', 'branch']}>
                <Input placeholder={selectedRepositoryDefaultBranch ?? '使用仓库默认分支'} />
              </Form.Item>
            </Col>
            <Col span={24}>
              <Form.Item
                extra="留空时扫描当前产品全部 active 代码仓库"
                label="批量代码仓库"
                name={['config_json', 'repository_ids']}
              >
                <Select
                  allowClear
                  disabled={repositorySelectDisabled}
                  loading={loadingRepositories}
                  mode="multiple"
                  optionFilterProp="label"
                  options={repositoryOptions}
                  placeholder="默认全部仓库，可指定多个仓库"
                  showSearch
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                initialValue={['builtin']}
                label="扫描引擎"
                name={['config_json', 'scanner_engines']}
              >
                <Select
                  mode="multiple"
                  optionFilterProp="label"
                  options={scannerEngineOptions}
                  placeholder="请选择扫描引擎"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                initialValue={['secrets', 'internal_addresses']}
                label="内置规则"
                name={['config_json', 'scan_rules']}
              >
                <Select
                  mode="multiple"
                  optionFilterProp="label"
                  options={builtinRuleOptions}
                  placeholder="请选择内置规则"
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="严重级别阈值" name={['config_json', 'severity_threshold']}>
                <Select
                  allowClear
                  options={severityThresholdOptions}
                  placeholder="默认 high"
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                initialValue={true}
                label="异步执行"
                name={['config_json', 'async_execution']}
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="忽略目录" name={['config_json', 'ignore_dirs']}>
                <Select mode="tags" placeholder="如 node_modules、dist、coverage" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="忽略规则" name={['config_json', 'ignore_rules']}>
                <Select
                  mode="multiple"
                  optionFilterProp="label"
                  options={ignoreRuleOptions}
                  placeholder="请选择要忽略的规则"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="Baseline Fingerprints" name={['config_json', 'baseline_fingerprints']}>
                <Select mode="tags" placeholder="粘贴历史问题 fingerprint，回车分隔" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="已接受风险 Fingerprints" name={['config_json', 'accepted_risk_fingerprints']}>
                <Select mode="tags" placeholder="粘贴已接受风险 fingerprint，回车分隔" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                label="启用质量门禁"
                name={['config_json', 'quality_gate', 'enabled']}
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
            <Col span={5}>
              <Form.Item label="Critical 上限" name={['config_json', 'quality_gate', 'critical_max']}>
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={5}>
              <Form.Item label="High 上限" name={['config_json', 'quality_gate', 'high_max']}>
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="Medium 上限" name={['config_json', 'quality_gate', 'medium_max']}>
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="增量基线 Commit" name={['config_json', 'incremental_from_commit']}>
                <Input placeholder="留空表示全量扫描" />
              </Form.Item>
            </Col>
          </>
        ) : null}
      </Row>
    </FormSection>
  );
}
