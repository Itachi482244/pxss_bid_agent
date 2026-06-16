import type { Key } from "react";
import { useCallback, useEffect, useState } from "react";

import { listProjects, type ProjectSummary } from "../../../api/bid";

type UseProjectsOptions = {
  formatError: (error: unknown, fallback: string) => string;
  onError: (message: string) => void;
};

export function useProjects({ formatError, onError }: UseProjectsOptions) {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>();
  const [selectedProjectRowKeys, setSelectedProjectRowKeys] = useState<Key[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(false);

  const applyProjectList = useCallback((data: ProjectSummary[]) => {
    setProjects(data);
    setSelectedProjectRowKeys((keys) => keys.filter((key) => data.some((project) => project.id === key)));
    setSelectedProjectId((current) => (current && data.some((project) => project.id === current) ? current : data[0]?.id));
  }, []);

  const reloadProjects = useCallback(async () => {
    setLoadingProjects(true);
    try {
      const data = await listProjects();
      applyProjectList(data);
      return data;
    } catch (error) {
      onError(formatError(error, "项目列表加载失败"));
      return [];
    } finally {
      setLoadingProjects(false);
    }
  }, [applyProjectList, formatError, onError]);

  useEffect(() => {
    let active = true;
    setLoadingProjects(true);
    listProjects()
      .then((data) => {
        if (active) applyProjectList(data);
      })
      .catch((error: unknown) => {
        if (active) onError(formatError(error, "项目列表加载失败"));
      })
      .finally(() => {
        if (active) setLoadingProjects(false);
      });
    return () => {
      active = false;
    };
  }, [applyProjectList, formatError, onError]);

  return {
    applyProjectList,
    loadingProjects,
    projects,
    reloadProjects,
    selectedProjectId,
    selectedProjectRowKeys,
    setLoadingProjects,
    setProjects,
    setSelectedProjectId,
    setSelectedProjectRowKeys
  };
}
