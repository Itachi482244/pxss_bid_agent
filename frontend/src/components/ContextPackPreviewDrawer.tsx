import { Alert, Button, Drawer, Empty, Space, Table, Tag, Typography } from "antd";

import type {
  BusinessDraftContextPack,
  BusinessDraftContextPackPreview
} from "../api/bid";

const { Text, Title } = Typography;

type ContextPackSource = BusinessDraftContextPackPreview | BusinessDraftContextPack;
type ContextPackCheck = Record<string, unknown>;

type Props = {
  open: boolean;
  source: ContextPackSource | null;
  loading: boolean;
  onClose: () => void;
  onAction: (check: ContextPackCheck) => void;
  actionLabel: (check: ContextPackCheck) => string;
};

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function asRecords(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value)
    ? value.filter((item): item is Record<string, unknown> => Boolean(item && typeof item === "object"))
    : [];
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "待补";
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}

function readinessColor(status: string): string {
  if (status === "pass") return "green";
  if (status === "block") return "red";
  return "gold";
}

function readinessLabel(status: string): string {
  if (status === "pass") return "可确认";
  if (status === "block") return "存在阻断";
  return "需复核";
}

export function ContextPackPreviewDrawer({
  open,
  source,
  loading,
  onClose,
  onAction,
  actionLabel
}: Props) {
  const context = asRecord(source?.context_json);
  const readiness = asRecord(source?.readiness_json);
  const outline = asRecord(source?.outline_plan_json);
  const sourceDocument = asRecord(context.source_document);
  const qualification = asRecord(context.qualification_decision);
  const matrixSummary = asRecord(context.matrix_summary);
  const projectFacts = asRecord(context.project_facts);
  const checks = asRecords(readiness.checks);
  const matrixItems = asRecords(context.matrix_items);
  const evidence = asRecords(context.bound_evidence);
  const missingFacts = asRecords(context.missing_facts);
  const sections = asRecords(outline.sections);
  const readinessStatus = String(source?.readiness_status ?? "warn");

  return (
    <Drawer
      title="ContextPack 完整预览"
      open={open}
      width={980}
      loading={loading}
      onClose={onClose}
      extra={
        source ? (
          <Space wrap>
            <Tag color={readinessColor(readinessStatus)}>{readinessLabel(readinessStatus)}</Tag>
            <Tag color="blue">Schema {source.schema_version}</Tag>
            <Tag>{sections.length} 个章节</Tag>
          </Space>
        ) : null
      }
    >
      {!source ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="尚未生成 ContextPack 预览" />
      ) : (
        <div className="context-pack-preview">
          <Alert
            showIcon
            type={readinessStatus === "block" ? "error" : readinessStatus === "warn" ? "warning" : "success"}
            message={readinessLabel(readinessStatus)}
            description={
              readinessStatus === "block"
                ? "必须先处理下列硬阻断；已确认 No-Go 仅作为风险快照保存。"
                : "当前快照可用于确认，待补事实会保留为明确缺项。"
            }
          />

          <section className="context-pack-preview-section">
            <Title level={5}>来源与资格结论</Title>
            <div className="context-pack-preview-meta">
              <div>
                <Text type="secondary">招标文件</Text>
                <strong>{displayValue(sourceDocument.title)}</strong>
              </div>
              <div>
                <Text type="secondary">来源版本</Text>
                <strong>{displayValue(sourceDocument.current_version_label)}</strong>
              </div>
              <div>
                <Text type="secondary">解析状态</Text>
                <strong>{displayValue(sourceDocument.version_status)}</strong>
              </div>
              <div>
                <Text type="secondary">参标建议</Text>
                <strong>{displayValue(qualification.recommendation)}</strong>
              </div>
              <div>
                <Text type="secondary">建议状态</Text>
                <strong>{displayValue(qualification.status)}</strong>
              </div>
              <div>
                <Text type="secondary">确认说明</Text>
                <strong>{displayValue(qualification.confirm_reason)}</strong>
              </div>
            </div>
          </section>

          <section className="context-pack-preview-section">
            <Title level={5}>准备度检查</Title>
            <div className="context-pack-preview-checks">
              {checks.map((check, index) => {
                const status = String(check.status ?? "warn");
                return (
                  <div className="context-pack-preview-check" key={`${String(check.code ?? index)}-${index}`}>
                    <Tag color={readinessColor(status)}>{readinessLabel(status)}</Tag>
                    <div>
                      <Text strong>{displayValue(check.summary ?? check.code)}</Text>
                      <Text type="secondary">{displayValue(check.action)}</Text>
                    </div>
                    {status !== "pass" && (
                      <Button size="small" onClick={() => onAction(check)}>
                        {actionLabel(check)}
                      </Button>
                    )}
                  </div>
                );
              })}
              {!checks.length && <Text type="secondary">当前没有待处理检查项。</Text>}
            </div>
          </section>

          <section className="context-pack-preview-section">
            <Title level={5}>项目与企业事实</Title>
            <Table
              size="small"
              rowKey="field"
              pagination={{ pageSize: 12, hideOnSinglePage: true }}
              dataSource={Object.entries(projectFacts).map(([field, value]) => ({ field, value }))}
              columns={[
                { title: "字段", dataIndex: "field", width: 260 },
                {
                  title: "当前值",
                  dataIndex: "value",
                  render: (value: unknown) => (
                    <Text type={value === null || value === undefined || value === "" ? "warning" : undefined}>
                      {displayValue(value)}
                    </Text>
                  )
                }
              ]}
            />
          </section>

          <section className="context-pack-preview-section">
            <Title level={5}>合规矩阵与证据</Title>
            <Space wrap className="context-pack-preview-summary">
              {Object.entries(matrixSummary).map(([key, value]) => (
                <Tag key={key} color={key === "missing_evidence" && Number(value) > 0 ? "red" : "blue"}>
                  {key} {displayValue(value)}
                </Tag>
              ))}
            </Space>
            <Table
              size="small"
              rowKey={(row) => String(row.compliance_item_id)}
              pagination={{ pageSize: 10, showSizeChanger: false }}
              dataSource={matrixItems}
              columns={[
                {
                  title: "条款",
                  dataIndex: "requirement_text",
                  render: (value: unknown) => <Text>{displayValue(value)}</Text>
                },
                {
                  title: "类型",
                  dataIndex: "item_type",
                  width: 130,
                  render: (value: unknown) => <Tag>{displayValue(value)}</Tag>
                },
                {
                  title: "状态",
                  dataIndex: "status",
                  width: 120,
                  render: (value: unknown) => <Tag>{displayValue(value)}</Tag>
                },
                {
                  title: "证据",
                  dataIndex: "bound_evidence_count",
                  width: 90,
                  render: (value: unknown) => displayValue(value)
                }
              ]}
            />
            <Table
              size="small"
              rowKey={(row) => String(row.binding_id)}
              pagination={{ pageSize: 8, hideOnSinglePage: true }}
              dataSource={evidence}
              locale={{ emptyText: "暂无已绑定企业资料证据" }}
              columns={[
                { title: "资料", dataIndex: "material_name", width: 240 },
                { title: "类型", dataIndex: "material_type", width: 130 },
                { title: "证据摘录", dataIndex: "evidence_text" }
              ]}
            />
          </section>

          <section className="context-pack-preview-section">
            <Title level={5}>待补事实</Title>
            <Table
              size="small"
              rowKey={(row, index) => `${String(row.field ?? row.compliance_item_id ?? "missing")}-${index}`}
              pagination={false}
              dataSource={missingFacts}
              locale={{ emptyText: "没有待补事实" }}
              columns={[
                {
                  title: "字段/条款",
                  render: (_: unknown, row) => displayValue(row.field ?? row.compliance_item_id)
                },
                { title: "原因", dataIndex: "reason" }
              ]}
            />
          </section>

          <section className="context-pack-preview-section">
            <Title level={5}>章节 ContextPack 计划</Title>
            <Table
              size="small"
              rowKey={(row) => String(row.section_type)}
              pagination={{ pageSize: 10, hideOnSinglePage: true }}
              dataSource={sections}
              columns={[
                { title: "顺序", dataIndex: "order_index", width: 80 },
                { title: "章节", dataIndex: "title" },
                { title: "类型", dataIndex: "section_type", width: 220 },
                {
                  title: "关联条款",
                  dataIndex: "compliance_item_ids",
                  width: 110,
                  render: (value: unknown) => (Array.isArray(value) ? value.length : 0)
                }
              ]}
            />
          </section>

          <details className="context-pack-preview-raw">
            <summary>原始 ContextPack 快照</summary>
            <pre>{JSON.stringify({ context, readiness, outline }, null, 2)}</pre>
          </details>
        </div>
      )}
    </Drawer>
  );
}
