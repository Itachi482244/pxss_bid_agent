import { useEffect, useMemo, useState } from "react";
import { Alert, Button, Checkbox, Input, Modal, Space, Tag, Tooltip, Typography } from "antd";
import {
  ArrowDownOutlined,
  ArrowUpOutlined,
  DeleteOutlined,
  PlusOutlined
} from "@ant-design/icons";

import type { OutlineChapterInput } from "../api/bid";

const { Text } = Typography;

export type OutlineSeedChapter = {
  section_type: string;
  title: string;
  custom?: boolean;
};

type OutlineRow = {
  key: string;
  section_type: string;
  title: string;
  custom: boolean;
  include: boolean;
};

type Props = {
  open: boolean;
  loading?: boolean;
  seed: OutlineSeedChapter[];
  onCancel: () => void;
  onApply: (outline: OutlineChapterInput[]) => void;
};

let customSeq = 0;

function buildRows(seed: OutlineSeedChapter[]): OutlineRow[] {
  return seed.map((chapter, index) => ({
    key: `${chapter.section_type}-${index}`,
    section_type: chapter.section_type,
    title: chapter.title,
    custom: Boolean(chapter.custom),
    include: true
  }));
}

export function OutlineEditorModal({ open, loading, seed, onCancel, onApply }: Props) {
  const [rows, setRows] = useState<OutlineRow[]>(() => buildRows(seed));

  useEffect(() => {
    if (open) {
      setRows(buildRows(seed));
    }
  }, [open, seed]);

  const includedCount = useMemo(() => rows.filter((row) => row.include).length, [rows]);

  const move = (index: number, delta: number) => {
    setRows((current) => {
      const next = [...current];
      const target = index + delta;
      if (target < 0 || target >= next.length) return current;
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  };

  const rename = (key: string, title: string) => {
    setRows((current) => current.map((row) => (row.key === key ? { ...row, title } : row)));
  };

  const toggleInclude = (key: string, include: boolean) => {
    setRows((current) => current.map((row) => (row.key === key ? { ...row, include } : row)));
  };

  const removeCustom = (key: string) => {
    setRows((current) => current.filter((row) => row.key !== key));
  };

  const addCustom = () => {
    customSeq += 1;
    setRows((current) => [
      ...current,
      {
        key: `custom-${Date.now()}-${customSeq}`,
        section_type: `custom_chapter_${customSeq}`,
        title: "",
        custom: true,
        include: true
      }
    ]);
  };

  const buildError = (): string | null => {
    const included = rows.filter((row) => row.include);
    if (included.length === 0) return "至少保留一个章节。";
    for (const row of included) {
      if (row.custom && !row.title.trim()) {
        return "自定义章节需填写标题。";
      }
    }
    const titles = included.map((row) => (row.title.trim() || row.section_type));
    if (new Set(titles).size !== titles.length) {
      return "存在重复的章节标题，请修改后再应用。";
    }
    return null;
  };

  const validationError = buildError();

  const handleApply = () => {
    if (validationError) return;
    const outline: OutlineChapterInput[] = rows
      .filter((row) => row.include)
      .map((row) => ({
        section_type: row.section_type,
        title: row.title.trim() || null,
        custom: row.custom
      }));
    onApply(outline);
  };

  return (
    <Modal
      open={open}
      title="编辑章节目录"
      width={680}
      onCancel={onCancel}
      onOk={handleApply}
      okText={`应用并预览（${includedCount} 章）`}
      okButtonProps={{ disabled: Boolean(validationError), loading }}
      cancelText="取消"
    >
      <Space direction="vertical" size="middle" style={{ width: "100%" }}>
        <Alert
          type="info"
          message="可重排、改名、移除模板章节或新增自定义章节。移除覆盖强制项的章节会在覆盖检查中如实标缺；自定义章节只生成占位，不编造正文。"
        />
        <div className="outline-editor-rows">
          {rows.map((row, index) => (
            <div
              key={row.key}
              className="outline-editor-row"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "8px 0",
                borderBottom: "1px solid #f0f0f0",
                opacity: row.include ? 1 : 0.45
              }}
            >
              <Text type="secondary" style={{ width: 24, textAlign: "right" }}>
                {index + 1}
              </Text>
              {!row.custom && (
                <Tooltip title={row.include ? "包含此章节" : "已移除（取消勾选即排除）"}>
                  <Checkbox
                    checked={row.include}
                    onChange={(event) => toggleInclude(row.key, event.target.checked)}
                  />
                </Tooltip>
              )}
              <Input
                size="small"
                value={row.title}
                placeholder={row.custom ? "自定义章节标题（必填）" : row.section_type}
                onChange={(event) => rename(row.key, event.target.value)}
                style={{ flex: 1 }}
                status={row.custom && !row.title.trim() ? "error" : undefined}
              />
              {row.custom ? (
                <Tag color="purple">自定义</Tag>
              ) : (
                <Tag color="blue">{row.section_type}</Tag>
              )}
              <Button
                size="small"
                type="text"
                icon={<ArrowUpOutlined />}
                disabled={index === 0}
                onClick={() => move(index, -1)}
              />
              <Button
                size="small"
                type="text"
                icon={<ArrowDownOutlined />}
                disabled={index === rows.length - 1}
                onClick={() => move(index, 1)}
              />
              {row.custom && (
                <Button
                  size="small"
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => removeCustom(row.key)}
                />
              )}
            </div>
          ))}
        </div>
        <Button icon={<PlusOutlined />} onClick={addCustom} block>
          新增自定义章节
        </Button>
        {validationError && <Text type="danger">{validationError}</Text>}
      </Space>
    </Modal>
  );
}
