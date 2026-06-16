import type { Dispatch, Key, SetStateAction } from "react";
import { useCallback, useEffect, useState } from "react";

import {
  getProject,
  listComplianceItems,
  listDocuments,
  listExportFiles,
  listSections,
  type ComplianceItem,
  type ExportFile,
  type ProjectDetail,
  type ProjectDocument,
  type SectionSummary
} from "../../../api/bid";

type UseWorkspaceDataOptions = {
  formatError: (error: unknown, fallback: string) => string;
  matrixFetchLimit: number;
  onError: (message: string) => void;
  selectedProjectId?: string;
  selectedSectionId?: string;
  setSelectedRowKeys: Dispatch<SetStateAction<Key[]>>;
  setSelectedSectionId: Dispatch<SetStateAction<string | undefined>>;
};

export function useWorkspaceData({
  formatError,
  matrixFetchLimit,
  onError,
  selectedProjectId,
  selectedSectionId,
  setSelectedRowKeys,
  setSelectedSectionId
}: UseWorkspaceDataOptions) {
  const [projectDetail, setProjectDetail] = useState<ProjectDetail | null>(null);
  const [sections, setSections] = useState<SectionSummary[]>([]);
  const [documents, setDocuments] = useState<ProjectDocument[]>([]);
  const [exportFiles, setExportFiles] = useState<ExportFile[]>([]);
  const [complianceItems, setComplianceItems] = useState<ComplianceItem[]>([]);
  const [loadingWorkspace, setLoadingWorkspace] = useState(false);
  const [loadingMatrix, setLoadingMatrix] = useState(false);

  useEffect(() => {
    if (!selectedProjectId) return;
    let active = true;
    setLoadingWorkspace(true);
    setProjectDetail(null);
    setSections([]);
    setSelectedSectionId(undefined);
    setComplianceItems([]);
    setDocuments([]);
    setExportFiles([]);
    Promise.all([getProject(selectedProjectId), listSections(selectedProjectId)])
      .then(([detail, sectionData]) => {
        if (!active) return;
        setProjectDetail(detail);
        setSections(sectionData);
        setSelectedSectionId((current) => {
          if (current && sectionData.some((section) => section.id === current)) return current;
          return sectionData[0]?.id;
        });
      })
      .catch((error: unknown) => {
        if (active) onError(formatError(error, "项目工作台加载失败"));
      })
      .finally(() => {
        if (active) setLoadingWorkspace(false);
      });
    return () => {
      active = false;
    };
  }, [formatError, onError, selectedProjectId, setSelectedSectionId]);

  useEffect(() => {
    if (!selectedProjectId || !selectedSectionId) return;
    let active = true;
    setLoadingMatrix(true);
    listComplianceItems(selectedProjectId, selectedSectionId, { limit: matrixFetchLimit })
      .then((data) => {
        if (!active) return;
        setComplianceItems(data);
        setSelectedRowKeys([]);
      })
      .catch((error: unknown) => {
        if (active) onError(formatError(error, "合规矩阵加载失败"));
      })
      .finally(() => {
        if (active) setLoadingMatrix(false);
      });
    return () => {
      active = false;
    };
  }, [formatError, matrixFetchLimit, onError, selectedProjectId, selectedSectionId, setSelectedRowKeys]);

  useEffect(() => {
    if (!selectedProjectId || !selectedSectionId) return;
    let active = true;
    Promise.all([listDocuments(selectedProjectId, selectedSectionId), listExportFiles(selectedProjectId, selectedSectionId)])
      .then(([documentData, exportData]) => {
        if (!active) return;
        setDocuments(documentData);
        setExportFiles(exportData);
      })
      .catch(() => {
        if (!active) return;
        setDocuments([]);
        setExportFiles([]);
      });
    return () => {
      active = false;
    };
  }, [selectedProjectId, selectedSectionId]);

  const reloadMatrix = useCallback(async () => {
    if (!selectedProjectId || !selectedSectionId) return [];
    setLoadingMatrix(true);
    try {
      const data = await listComplianceItems(selectedProjectId, selectedSectionId, { limit: matrixFetchLimit });
      setComplianceItems(data);
      setSelectedRowKeys([]);
      return data;
    } finally {
      setLoadingMatrix(false);
    }
  }, [matrixFetchLimit, selectedProjectId, selectedSectionId, setSelectedRowKeys]);

  const reloadWorkspaceSummary = useCallback(async () => {
    if (!selectedProjectId) return;
    const [detail, sectionData] = await Promise.all([
      getProject(selectedProjectId),
      listSections(selectedProjectId)
    ]);
    setProjectDetail(detail);
    setSections(sectionData);
  }, [selectedProjectId]);

  const reloadDocumentsAndExports = useCallback(async () => {
    if (!selectedProjectId || !selectedSectionId) return;
    const [documentData, exportData] = await Promise.all([
      listDocuments(selectedProjectId, selectedSectionId),
      listExportFiles(selectedProjectId, selectedSectionId)
    ]);
    setDocuments(documentData);
    setExportFiles(exportData);
  }, [selectedProjectId, selectedSectionId]);

  return {
    complianceItems,
    documents,
    exportFiles,
    loadingMatrix,
    loadingWorkspace,
    projectDetail,
    reloadDocumentsAndExports,
    reloadMatrix,
    reloadWorkspaceSummary,
    sections,
    setComplianceItems,
    setDocuments,
    setExportFiles,
    setLoadingMatrix,
    setLoadingWorkspace,
    setProjectDetail,
    setSections
  };
}
