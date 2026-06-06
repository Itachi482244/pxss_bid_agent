import { useEffect, useMemo, useState } from "react";
import { Alert, Button, Input, Modal, Select, Space, Tag, Tooltip, Typography } from "antd";
import { DeleteOutlined, PlusOutlined } from "@ant-design/icons";

import type { AuthorDirectiveInput, AuthorDirectiveType } from "../api/bid";

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

export type DirectiveScopeOption = {
  value: string;
  label: string;
};

type DirectiveRow = {
  key: string;
  scope: string;
  directive_type: AuthorDirectiveType;
  text: string;
};

type Props = {
  open: boolean;
  loading?: boolean;
  seed: AuthorDirectiveInput[];
  scopeOptions: DirectiveScopeOption[];
  /** When true the modal is editing a confirmed pack (triggers lightweight rebuild). */
  rebuildMode?: boolean;
  onCancel: () => void;
  onApply: (directives: AuthorDirectiveInput[]) => void;
};

const directiveTypeLabels: Record<AuthorDirectiveType, string> = {
  style: "纯风格",
  emphasis: "内容侧重",
  mandatory_text: "必须原样写入的内容"
};

const directiveTypeHints: Record<AuthorDirectiveType, string> = {
  style: "只调整语气、措辞风格，不新增事实。",
  emphasis: "提示模型在已有证据范围内侧重某些内容。",
  mandatory_text: "原样写入草稿，标记为「待确认的指定内容」，仍需通过事实核查与逐条人工确认后方可导出。"
};

let directiveSeq = 0;

function buildRows(seed: AuthorDirectiveInput[]): DirectiveRow[] {
  return seed.map((directive, index) => ({
    key: `seed-${index}`,
    scope: directive.scope,
    directive_type: directive.directive_type,
    text: directive.text
  }));
}

export function DirectiveEditorModal({
  open,
  loading,
  seed,
  scopeOptions,
  rebuildMode,
  onCancel,
  onApply
}: Props) {
  const [rows, setRows] = useState<DirectiveRow[]>(() => buildRows(seed));

  useEffect(() => {
    if (open) {
      setRows(buildRows(seed));
    }
  }, [open, seed]);

  const allScopeOptions = useMemo<DirectiveScopeOption[]>(
    () => [{ value: "pack", label: "整体（pack）" }, ...scopeOptions],
    [scopeOptions]
  );

  const update = (key: string, patch: Partial<DirectiveRow>) => {
    setRows((current) => current.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  };

  const remove = (key: string) => {
    setRows((current) => current.filter((row) => row.key !== key));
  };

  const add = () => {
    directiveSeq += 1;
    setRows((current) => [
      ...current,
      {
        key: `new-${Date.now()}-${directiveSeq}`,
        scope: "pack",
        directive_type: "style",
        text: ""
      }
    ]);
  };

  const validationError = useMemo<string | null>(() => {
    for (const row of rows) {
      if (!row.text.trim()) return "每条指令都需填写内容。";
    }
    return null;
  }, [rows]);

  const mandatoryCount = useMemo(
    () => rows.filter((row) => row.directive_type === "mandatory_text").length,
    [rows]
  );

  const handleApply = () => {
    if (validationError) return;
    const directives: AuthorDirectiveInput[] = rows.map((row) => ({
      scope: row.scope,
      directive_type: row.directive_type,
      text: row.text.trim()
    }));
    onApply(directives);
  };

  return (
    <Modal
      open={open}
      title="编辑生成指令"
      width={720}
      onCancel={onCancel}
      onOk={handleApply}
      okText={rebuildMode ? `应用并快速重新生成（${rows.length} 条）` : `应用（${rows.length} 条）`}
      okButtonProps={{ disabled: Boolean(validationError), loading }}
      cancelText="取消"
    >
      <Space direction="vertical" size="middle" style={{ width: "100%" }}>
        <Alert
          type="info"
          message="指令层只影响表达与侧重，不能新增事实。"
          description={
            <Paragraph style={{ marginBottom: 0 }}>
              事实层保持不可变。“必须原样写入的内容”会原样写入草稿，但仍受事实核查兜底（夹带的硬数据若无法回链证据将拦截导出），且默认「待确认的指定内容」，需逐条人工确认。
              {rebuildMode
                ? "应用后将触发快速重新生成：沿用现有已核实的事实，生成新版本投标素材包，旧版本置为已废弃，需重新生成草稿以应用新指令。"
                : "这些指令会随「确认投标素材包」一起写入。"}
            </Paragraph>
          }
        />
        <div className="directive-editor-rows">
          {rows.length === 0 && (
            <Text type="secondary">暂无指令，点击下方按钮新增。</Text>
          )}
          {rows.map((row) => (
            <div
              key={row.key}
              className="directive-editor-row"
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 8,
                padding: "10px 0",
                borderBottom: "1px solid #f0f0f0"
              }}
            >
              <Space wrap>
                <Select<string>
                  size="small"
                  value={row.scope}
                  style={{ minWidth: 180 }}
                  options={allScopeOptions}
                  onChange={(value) => update(row.key, { scope: value })}
                />
                <Select<AuthorDirectiveType>
                  size="small"
                  value={row.directive_type}
                  style={{ minWidth: 140 }}
                  onChange={(value) => update(row.key, { directive_type: value })}
                  options={(["style", "emphasis", "mandatory_text"] as AuthorDirectiveType[]).map(
                    (value) => ({ value, label: directiveTypeLabels[value] })
                  )}
                />
                {row.directive_type === "mandatory_text" && <Tag color="purple">需逐条确认</Tag>}
                <Button
                  size="small"
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => remove(row.key)}
                />
              </Space>
              <Tooltip title={directiveTypeHints[row.directive_type]} placement="topLeft">
                <TextArea
                  rows={row.directive_type === "mandatory_text" ? 3 : 2}
                  value={row.text}
                  placeholder={directiveTypeHints[row.directive_type]}
                  onChange={(event) => update(row.key, { text: event.target.value })}
                  status={!row.text.trim() ? "error" : undefined}
                />
              </Tooltip>
            </div>
          ))}
        </div>
        <Button icon={<PlusOutlined />} onClick={add} block>
          新增指令
        </Button>
        {mandatoryCount > 0 && (
          <Text type="warning">
            含 {mandatoryCount} 条必须原样写入的内容，导出前需逐条人工确认并通过事实核查。
          </Text>
        )}
        {validationError && <Text type="danger">{validationError}</Text>}
      </Space>
    </Modal>
  );
}
