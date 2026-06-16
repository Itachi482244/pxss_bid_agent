import { useEffect, useState } from "react";
import { Alert, Button, Checkbox, Empty, Space, Table, Tag, Tooltip, Typography } from "antd";

import type { EnterpriseMaterialSearchResult } from "../api/bid";
import { formatEvidenceSnippet, stripGeneratedIdSuffix } from "../features/bid/evidenceText";

const { Text, Title } = Typography;

// 弱相关阈值：重排分（或匹配度）低于此值的候选会被标注并降级展示。
const LOW_RELEVANCE_THRESHOLD = 0.3;

type Props = {
  candidates: EnterpriseMaterialSearchResult[];
  loading: boolean;
  boundMaterialIds: string[];
  bindingMaterialId: string;
  rejectingCandidateId: string;
  includeUnconfirmed: boolean;
  includeRestricted: boolean;
  materialTypeLabels: Record<string, string>;
  verificationStatusLabels: Record<string, string>;
  onToggleUnconfirmed: (checked: boolean) => void;
  onToggleRestricted: (checked: boolean) => void;
  onRefresh: () => void;
  onBind: (material: EnterpriseMaterialSearchResult) => void;
  onReject: (material: EnterpriseMaterialSearchResult) => void;
};

/**
 * RAG 智能推荐证据面板。嵌在合规项证据抽屉内：按条款语义检索 + 重排返回候选材料，
 * 附推荐理由、来源片段、重排分数与降级提示。采纳即复用既有绑定流程。
 */
export function EvidenceCandidatePanel({
  candidates,
  loading,
  boundMaterialIds,
  bindingMaterialId,
  rejectingCandidateId,
  includeUnconfirmed,
  includeRestricted,
  materialTypeLabels,
  verificationStatusLabels,
  onToggleUnconfirmed,
  onToggleRestricted,
  onRefresh,
  onBind,
  onReject
}: Props) {
  // 语义检索 + 重排首次可能需要数秒，用计时让等待可感知：进入加载即显示提示，
  // 超过 4s 升级文案，避免用户误以为卡死。加载结束自动归零。
  const [loadingElapsedMs, setLoadingElapsedMs] = useState(0);
  useEffect(() => {
    if (!loading) {
      setLoadingElapsedMs(0);
      return;
    }
    const startedAt = Date.now();
    const timer = window.setInterval(() => {
      setLoadingElapsedMs(Date.now() - startedAt);
    }, 500);
    return () => window.clearInterval(timer);
  }, [loading]);

  const boundSet = new Set(boundMaterialIds);
  const degraded = candidates.some(
    (item) => item.rerank_fallback_used || Boolean(item.rerank_error)
  );
  const degradeMessage =
    candidates.find((item) => item.rerank_error)?.rerank_error ??
    "Rerank 服务已降级，当前按召回顺序展示候选，建议人工核验排序。";
  const isRestricted = (item: EnterpriseMaterialSearchResult) =>
    item.data_level === "restricted" || item.data_level === "confidential";
  // 语义相关度判定：rerank 真正跑过（非降级）时以重排分为准，否则退回匹配度。
  // 低于阈值视为弱相关，仅做视觉弱化与提示，不隐藏、不禁用采纳，最终由人工判断。
  const relevanceScore = (item: EnterpriseMaterialSearchResult) =>
    item.rerank_used && !item.rerank_fallback_used && item.rerank_score != null
      ? item.rerank_score
      : item.confidence_score;
  const isLowRelevance = (item: EnterpriseMaterialSearchResult) =>
    relevanceScore(item) < LOW_RELEVANCE_THRESHOLD;

  return (
    <div className="evidence-candidate-panel">
      <div className="evidence-section-title">
        <Space direction="vertical" size={0}>
          <Title level={5} style={{ marginBottom: 0 }}>
            智能推荐证据
          </Title>
          <Text type="secondary">
            按条款语义检索 + 重排，自动排除已绑定资料；候选需人工采纳后才会进入可引用证据。
          </Text>
        </Space>
        <Button size="small" loading={loading} onClick={onRefresh}>
          刷新推荐
        </Button>
      </div>
      <Space size={16} wrap style={{ marginBottom: 8 }}>
        <Checkbox
          checked={includeUnconfirmed}
          onChange={(event) => onToggleUnconfirmed(event.target.checked)}
        >
          含待确认/风险资料
        </Checkbox>
        <Checkbox
          checked={includeRestricted}
          onChange={(event) => onToggleRestricted(event.target.checked)}
        >
          含受限/机密资料
        </Checkbox>
      </Space>
      {degraded && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 8 }}
          message="重排能力降级"
          description={degradeMessage}
        />
      )}
      {loading && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 8 }}
          message={
            loadingElapsedMs > 4000
              ? `仍在检索候选证据（已等待 ${Math.round(loadingElapsedMs / 1000)}s）…语义检索 + 重排首次较慢，请稍候`
              : "正在按条款语义检索并重排候选证据…"
          }
        />
      )}
      <Table<EnterpriseMaterialSearchResult>
        size="small"
        rowKey="id"
        pagination={false}
        loading={loading}
        dataSource={candidates}
        locale={{
          emptyText: (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="暂无智能推荐；可放宽筛选或在下方手动检索企业资料"
            />
          )
        }}
        columns={[
          {
            title: "候选资料",
            dataIndex: "name",
            width: 200,
            render: (value: string, record) => (
              <Space direction="vertical" size={2}>
                <Text strong>{stripGeneratedIdSuffix(value)}</Text>
                <Space size={4} wrap>
                  <Tag>{materialTypeLabels[record.material_type] ?? record.material_type}</Tag>
                  <Tag color={record.verification_status === "confirmed" ? "green" : "orange"}>
                    {verificationStatusLabels[record.verification_status] ?? record.verification_status}
                  </Tag>
                  {isRestricted(record) && <Tag color="red">需脱敏</Tag>}
                  {isLowRelevance(record) && (
                    <Tooltip title="语义相关度较低，绑定前请人工确认是否切合本条款要求">
                      <Tag>相关度较低</Tag>
                    </Tooltip>
                  )}
                </Space>
              </Space>
            )
          },
          {
            title: "推荐理由与来源",
            dataIndex: "recommend_reason",
            render: (_: string | null, record) => (
              <Space direction="vertical" size={4}>
                {record.recommend_reason && (
                  <Text type="secondary" className="recommend-reason">
                    推荐原因：{record.recommend_reason}
                  </Text>
                )}
                <Text className="evidence-snippet">{formatEvidenceSnippet(record)}</Text>
                <Space size={6} wrap>
                  <Text type="secondary">匹配度 {Math.round(record.confidence_score * 100)}%</Text>
                  {record.rerank_score != null && (
                    <Tag color={record.rerank_fallback_used ? "gold" : "purple"}>
                      重排 {Math.round(record.rerank_score * 100)}%
                    </Tag>
                  )}
                  {record.base_score != null && (
                    <Tag color="blue">召回 {Math.round(record.base_score * 100)}%</Tag>
                  )}
                </Space>
                {record.material_status_hint && <Tag color="gold">{record.material_status_hint}</Tag>}
                {record.matched_terms?.length ? (
                  <Space size={4} wrap>
                    {record.matched_terms.slice(0, 4).map((term) => (
                      <Tag key={term} color="blue">
                        {term}
                      </Tag>
                    ))}
                  </Space>
                ) : null}
              </Space>
            )
          },
          {
            title: "操作",
            dataIndex: "action",
            width: 112,
            render: (_: unknown, record) => {
              const bound = boundSet.has(record.id);
              const blocked =
                record.verification_status === "conflict" ||
                record.verification_status === "expired" ||
                isRestricted(record);
              const busy = Boolean(bindingMaterialId || rejectingCandidateId);
              const lowRelevance = isLowRelevance(record);
              const disabledReason = bound
                ? "该资料已绑定到当前条款"
                : isRestricted(record)
                  ? "受限或机密资料需先脱敏，不能直接绑定为响应证据"
                  : blocked
                  ? "冲突或过期资料不能绑定"
                  : busy
                    ? "正在绑定其他资料"
                    : null;
              return (
                <Space direction="vertical" size={6}>
                  <Tooltip title={disabledReason}>
                    <span>
                      <Button
                        size="small"
                        type={lowRelevance && !bound && !blocked ? "default" : "primary"}
                        disabled={bound || blocked || (busy && bindingMaterialId !== record.id)}
                        loading={bindingMaterialId === record.id}
                        onClick={() => onBind(record)}
                      >
                        {bound ? "已绑定" : blocked ? "不可绑定" : "采纳绑定"}
                      </Button>
                    </span>
                  </Tooltip>
                  <Button
                    size="small"
                    disabled={bound || (busy && rejectingCandidateId !== record.id)}
                    loading={rejectingCandidateId === record.id}
                    onClick={() => onReject(record)}
                  >
                    不采用
                  </Button>
                </Space>
              );
            }
          }
        ]}
        scroll={{ x: 672 }}
        tableLayout="fixed"
      />
    </div>
  );
}
