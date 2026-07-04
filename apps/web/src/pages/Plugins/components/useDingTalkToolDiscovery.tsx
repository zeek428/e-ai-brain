import { Modal, message } from 'antd';
import { useCallback, useState, type ReactNode } from 'react';

import {
  discoverPluginConnectionTools,
  type PluginConnectionRecord,
  type PluginConnectionToolDiscoveryResult,
} from '../../../services/aiBrain';
import { PluginConnectionToolDiscoveryContent } from './PluginDiagnostics';

type DingTalkToolDiscovery = {
  discoveringConnectionId?: string;
  discoverConnectionTools: (connection: PluginConnectionRecord) => Promise<void>;
  discoveryModal: ReactNode;
};

export function useDingTalkToolDiscovery(): DingTalkToolDiscovery {
  const [discoveryResult, setDiscoveryResult] = useState<
    PluginConnectionToolDiscoveryResult | undefined
  >();
  const [modalOpen, setModalOpen] = useState(false);
  const [discoveringConnectionId, setDiscoveringConnectionId] = useState<string | undefined>();

  const discoverConnectionTools = useCallback(
    async (connection: PluginConnectionRecord) => {
      if (discoveringConnectionId) {
        return;
      }
      setDiscoveringConnectionId(connection.id);
      try {
        const result = await discoverPluginConnectionTools(connection.id);
        setDiscoveryResult(result);
        setModalOpen(true);
        if (result.status === 'drift_detected') {
          message.warning('已发现钉钉 MCP 能力变化，请复核动作模板');
        } else {
          message.success('钉钉 MCP 能力发现完成');
        }
      } catch (error) {
        message.error(error instanceof Error ? error.message : '钉钉 MCP 能力发现失败');
      } finally {
        setDiscoveringConnectionId(undefined);
      }
    },
    [discoveringConnectionId],
  );

  return {
    discoveringConnectionId,
    discoverConnectionTools,
    discoveryModal: (
      <Modal
        footer={null}
        onCancel={() => setModalOpen(false)}
        open={modalOpen}
        title="钉钉动态能力发现"
        width={820}
      >
        {discoveryResult ? (
          <PluginConnectionToolDiscoveryContent result={discoveryResult} />
        ) : null}
      </Modal>
    ),
  };
}
