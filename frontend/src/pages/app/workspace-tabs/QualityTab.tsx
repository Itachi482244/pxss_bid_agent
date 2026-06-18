import type { BidAppController } from "../../../features/bid/useBidAppController";

export function QualityTab({ app }: { app: BidAppController }) {
  const {
    actionLogs,
    activateProjectWorkspace,
    activateReviewHighlight,
    activateWorkflowStep,
    activeContextPack,
    activeDraftBlockId,
    activePackDirectiveCount,
    activeReviewItemId,
    activeTab,
    Alert,
    allMatrixReviewRows,
    apiError,
    appendLog,
    applyChatModelConfig,
    applyImportDraft,
    applyProjectList,
    applySimilarCandidates,
    approvalBusyId,
    approvalStatusLabels,
    approvalTasks,
    approvalTaskTypeLabels,
    assignComplianceItem,
    assistantCollapsed,
    assistantMessages,
    ASYNC_TASK_STALE_AFTER_MS,
    asyncTaskEtaText,
    asyncTaskProgress,
    asyncTaskStatusColors,
    asyncTaskStatusLabels,
    asyncTaskStatusText,
    auditActionText,
    auditContentText,
    auditLogs,
    AuditOutlined,
    autoResolveActive,
    autoResolveResult,
    Avatar,
    Badge,
    BarChartOutlined,
    BellOutlined,
    bindComplianceEvidence,
    bindingMaterialId,
    blockingContextPackChecks,
    blockingQualificationEvaluations,
    blockingSummary,
    blockToReviewChunk,
    BranchesOutlined,
    buildCurrentConfirmationQueue,
    buildMatrixReviewRows,
    buildMatrixTableRows,
    bulkAssignComplianceItems,
    bulkConfirmComplianceItems,
    businessDraftChapters,
    businessDraftContextPacks,
    businessDraftGenerationActive,
    businessDraftGenerationProgress,
    businessDraftGenerationStatusText,
    businessDraftGenerationTask,
    businessDraftGenerationTaskId,
    businessDraftTerminalTaskRef,
    Button,
    canConfirmContextPack,
    candidateIncludeRestricted,
    candidateIncludeUnconfirmed,
    canGenerateContextPackDraft,
    chapterMandatoryBlocks,
    chapterStatusLabels,
    chatModelConfig,
    Checkbox,
    CheckCircleOutlined,
    classifyProjectGroup,
    ClockCircleOutlined,
    CloseOutlined,
    CloudUploadOutlined,
    CommentOutlined,
    COMPLIANCE_ITEM_FETCH_LIMIT,
    complianceItems,
    computeDashboardStats,
    computeDraftBlockFilterCounts,
    confirmComplianceItem,
    confirmContextPackDraftGeneration,
    confirmDeleteProjects,
    confirmDraftGeneration,
    confirmDuplicateGroup,
    confirmExport,
    confirmingMaterialId,
    confirmNoGoRiskAcceptance,
    confirmProjectImportDraft,
    confirmQualificationDecision,
    confirmQualificationEvaluation,
    confirmSubmit,
    Content,
    contextPackCheckActionText,
    contextPackChecks,
    contextPackConfirmDisabledReason,
    contextPackDraftGenerationAvailable,
    contextPackDraftGenerationTip,
    contextPackHardBlockers,
    contextPackOutlineSections,
    contextPackPreview,
    contextPackPreviewChecks,
    ContextPackPreviewDrawer,
    contextPackPreviewOpen,
    contextPackProjectFields,
    contextPackQualificationGate,
    contextPackReadinessSummary,
    contextPackSource,
    contextTitle,
    coverageReview,
    createApprovalTask,
    createBusinessDraftContextPack,
    createComplianceItemFromSource,
    createEnterpriseMaterial,
    createEnterpriseMaterialsHistoryExtractTask,
    createParseTask,
    createProject,
    createProjectImportDraftFromFile,
    createProjectImportDraftFromUrl,
    currentImportProcessing,
    currentProject,
    currentSection,
    dashboardStats,
    dataLevelLabels,
    DatePicker,
    dayjs,
    decideApprovalTask,
    decisionColors,
    decisionLabels,
    DeleteOutlined,
    deleteProject,
    deletingProjects,
    deriveProjectNextStep,
    DirectiveEditorModal,
    directiveEditorOpen,
    directiveScopeOptions,
    directiveSeed,
    displayedLogs,
    displayedMatrixRows,
    documentBusy,
    documents,
    DownloadOutlined,
    draftBlockFilter,
    draftBlockFilterCounts,
    draftBlockFilterLabels,
    draftBlockLinkIds,
    draftBlocks,
    draftBlocksByComplianceItemId,
    draftBlockStatusColors,
    draftBlockStatusLabels,
    draftEditorValue,
    Drawer,
    duplicateGroupByItemId,
    editDraft,
    editedDirectives,
    editedOutline,
    effectiveReviewHighlights,
    Empty,
    enterpriseMaterials,
    enterpriseProfile,
    errorMessage,
    evaluatingQualification,
    evidenceBindings,
    EvidenceCandidatePanel,
    evidenceCandidates,
    evidenceDrawer,
    evidenceRows,
    executeProjectDeletion,
    expandedDraftBlockIds,
    explanationKeywords,
    explanationText,
    exportBusinessDraftWord,
    exportComplianceMatrixExcel,
    exportFiles,
    exportingExcel,
    exportingWord,
    extractDocumentSemanticSectionCompliance,
    extractingHistoryMaterial,
    extractionBlocked,
    extractionBlockReason,
    extractionQualityIssueCount,
    extractionQualityIssues,
    extractionQualityReport,
    factCheckLabels,
    fetchEvidenceCandidates,
    FileDoneOutlined,
    FileSearchOutlined,
    FileTextOutlined,
    filteredHomeProjects,
    filteredRevisionChunks,
    filterHomeProjects,
    findNextUnresolvedMatrixRow,
    focusAutoConfirmationRow,
    focusDraftBlock,
    focusQualityAssistant,
    focusReviewChunk,
    focusReviewRow,
    FolderOpenOutlined,
    formatDateTime,
    formatShortTime,
    Fragment,
    generateBusinessDraftChapters,
    generateBusinessDraftFromContextPackAsync,
    generateComplianceMatrix,
    generateQualificationDecision,
    generatingDecision,
    getChatModelConfig,
    getDocumentExtractionQualityReport,
    getEnterpriseMaterialIndexHealth,
    getEnterpriseProfile,
    getMatrixReview,
    getPreflightCheck,
    getProject,
    getQualificationDecision,
    getTask,
    handleApplyDirectives,
    handleApplyOutline,
    handleApplySimilarCandidates,
    handleAutoResolveMatrix,
    handleAssignItem,
    handleAssistantMessageAction,
    handleBatchAssign,
    handleBatchConfirm,
    handleBatchConfirmMandatory,
    handleBindEvidence,
    handleConfirmDuplicateGroup,
    handleConfirmExtractedMaterial,
    handleConfirmItem,
    handleConfirmProjectDeletion,
    handleConfirmQualificationDecision,
    handleConfirmQualificationEvaluation,
    handleContextPackCheckAction,
    handleCreateContextPack,
    handleCreateEnterpriseMaterial,
    handleCreateProject,
    handleCreateSourceItem,
    handleDecideApprovalTask,
    handleExportBusinessWord,
    handleExportBusinessWordConfirmed,
    handleExportExcel,
    handleExtractSemanticSection,
    handleGenerateMatrix,
    handleGenerateQualificationDecision,
    handleHistoryMaterialUpload,
    handleImportDraftFile,
    handleImportDraftUrl,
    handleOpenOutlineEditor,
    handleOpenRevisionDrawer,
    handlePreflightCheckAction,
    handlePreviewContextPack,
    handlePublicUrlAcquisition,
    handlePublishManualRevision,
    handleQuickPrompt,
    handleRebuildMaterialIndex,
    handleReparseDocument,
    handleReplanSemanticSections,
    handleResetDirectives,
    handleResetOutline,
    handleReviewBlockMouseUp,
    handleReviewChunkMouseUp,
    handleRunContextPackCoverageReview,
    handleRunDraftFactCheck,
    handleRunQualificationEvaluation,
    handleSaveBusinessDraftChapter,
    handleSaveEditDraft,
    handleSaveEnterpriseProfile,
    handleSaveKeyInfo,
    handleSaveModelConfig,
    handleSplitDuplicateGroup,
    handleTestModelConfig,
    handleToggleCandidateRestricted,
    handleToggleCandidateUnconfirmed,
    handleUnbindEvidence,
    handleUnlinkDuplicateGroup,
    handleUpdateDraftBlockStatus,
    handleUploadDocument,
    handleWaiveEvidenceRequirement,
    Header,
    hiddenPreflightCheckCount,
    highlightedRowKey,
    HighlightOutlined,
    historyExtractActive,
    historyExtractProgress,
    historyExtractResult,
    historyExtractResultFromTask,
    historyExtractStatusText,
    historyExtractTask,
    historyExtractTaskId,
    historyExtractTaskStageTitle,
    historyExtractTerminalTaskRef,
    homeProjectGroup,
    homeProjectPage,
    homeProjectPageSize,
    homeProjectSearch,
    homeTodoRows,
    IMPORT_PROCESSING_STORAGE_KEY,
    importingProjectDraft,
    importProcessing,
    importProcessingDone,
    importProcessingFailed,
    importProcessingHasActiveTask,
    importProcessingInProgress,
    importProcessingMatrixFailed,
    importProcessingOpenTask,
    importProcessingParseFailed,
    importProcessingPercent,
    importProcessingProgress,
    importProcessingQualityBlocked,
    importProcessingStageMessage,
    importProcessingStageTitle,
    importProcessingVisible,
    importUrl,
    importUrlSite,
    Input,
    isAsyncTaskActive,
    isAsyncTaskStale,
    isAsyncTaskTerminal,
    isAsyncTaskTerminalStatus,
    isHttpNotFound,
    isHttpNotFoundError,
    isMatrixComplete,
    isMatrixItemResolved,
    isQualityGateTaskError,
    isUsableParseStatus,
    isWorkflowStepKey,
    itemTypeLabels,
    keyInfoDraft,
    keyInfoModalOpen,
    knownConfirmedMatrixCount,
    knownHighRiskCount,
    knownMatrixCount,
    knownPendingMatrixCount,
    knownUnresolvedHighRiskCount,
    LARGE_TABLE_PAGINATION,
    Layout,
    LinkOutlined,
    listApprovalTasks,
    listAuditLogs,
    listBusinessDraftBlocks,
    listBusinessDraftChapters,
    listBusinessDraftContextPacks,
    listComplianceEvidenceBindings,
    listComplianceEvidenceCandidates,
    listComplianceItems,
    listDocumentChunks,
    listDocuments,
    listDocumentSemanticSections,
    listEnterpriseMaterials,
    listExportFiles,
    listProjects,
    listQualificationEvaluations,
    listSections,
    listSimilarCandidates,
    listTasks,
    loadImportProcessingState,
    loadingBusinessDraft,
    loadingContextPack,
    loadingEnterprise,
    loadingEvidenceCandidates,
    loadingMaterialIndexHealth,
    loadingMaterialSearch,
    loadingMatrix,
    loadingModelConfig,
    loadingProjects,
    loadingQualityChunks,
    loadingReviewChunks,
    loadingRevisionChunks,
    loadingSimilarCandidates,
    loadingWorkspace,
    locateDraftBlockForRow,
    locateMatrixRow,
    locateReviewTimerRef,
    locatingReviewItemId,
    makeMaterialFileUploadRequest,
    mandatoryFilter,
    mandatoryReviewIndex,
    mandatoryReviewOpen,
    mapMatrixRow,
    markDraftBlockViewed,
    matchesDraftBlockFilter,
    materialExtractionMeta,
    materialIndexHealth,
    materialModalOpen,
    materialSearchQuery,
    materialSearchResults,
    materialTypeLabels,
    matrixForkJoinCompleted,
    matrixForkJoinPending,
    matrixForkJoinPendingSections,
    matrixForkJoinTotal,
    matrixForkJoinWorkers,
    matrixReviewFilter,
    matrixReviewRows,
    matrixRows,
    matrixRowsById,
    matrixTaskActive,
    matrixTaskOutput,
    matrixTaskStageTitle,
    MenuFoldOutlined,
    MenuUnfoldOutlined,
    missingKeyInfo,
    missingQualificationEvaluations,
    Modal,
    modelConfigDraft,
    modelConfigPayload,
    modelConfigTestResult,
    MVP13_DRAFT_WORKFLOW_AVAILABLE,
    mvp13DraftWorkflowAvailable,
    mvp13PreflightCodes,
    newMaterialDraft,
    newProjectDraft,
    newProjectOpen,
    notification,
    notSatisfiedQualificationEvaluations,
    openContextPackDraftGenerationConfirm,
    openCreateProjectModal,
    openEditDraft,
    openEditDraftBlock,
    openEvidenceBindingDrawer,
    openingEvidenceItemId,
    openKeyInfoModal,
    openMandatoryReview,
    openProjectWorkspace,
    openQualificationEvidenceWork,
    openSimilarCandidates,
    openSourceCreateDraft,
    openWorkspace,
    OutlineEditorModal,
    outlineEditorOpen,
    outlineSectionsFromPreview,
    outlineSeed,
    outputRecord,
    ownerFilter,
    ownerOptions,
    pagedMatrixReviewRows,
    Pagination,
    paragraphCss,
    parseTaskActive,
    plainTerm,
    PlusOutlined,
    Popover,
    preflightActionText,
    preflightCheck,
    preflightChecksForDisplay,
    preflightColor,
    preflightExpanded,
    preflightLabel,
    preflightStatusForDisplay,
    preflightWorkflowTargets,
    previewBusinessDraftContextPack,
    primaryBlockingPreflightCheck,
    primaryBlockingPreflightTarget,
    prioritySortEnabled,
    profileDraft,
    Progress,
    projectCreateMode,
    projectDeleteTargets,
    projectDetail,
    projectGroupCounts,
    projectGroupLabels,
    projectGroupOrder,
    projectImportDraft,
    projectImportError,
    projectNavCollapsed,
    projects,
    projectStatusLabels,
    projectTreeData,
    publicUrl,
    publicUrlSite,
    publishDocumentManualRevision,
    publishingRevision,
    qualificationDecision,
    qualificationDecisionConfirmed,
    qualificationDecisionIsNoGo,
    qualificationDecisionNeedsConfirmation,
    qualificationEvaluations,
    qualificationNeedsMaterialByItemId,
    qualificationStatusLabels,
    qualificationTypeLabels,
    qualityChunks,
    qualityDisplayChunks,
    qualityGateTaskErrorCodes,
    qualityIssueActionText,
    qualityIssueSearchTerms,
    qualityIssueSeverityColor,
    qualityIssueSourceChunk,
    qualityIssueSourceExcerpt,
    quickPrompts,
    rawMatrixTaskActive,
    rawParseTaskActive,
    rebuildEnterpriseMaterialIndex,
    rebuildingMaterialIndex,
    recommendedPreflightCheck,
    recommendedStep,
    refreshAfterMatrixMutation,
    refreshMatrixRelatedPanels,
    reloadApprovalTasks,
    reloadAuditLogs,
    reloadBusinessDraftChapters,
    reloadBusinessDraftContext,
    reloadChatModelConfig,
    reloadDocumentsAndExports,
    reloadEnterprise,
    reloadEvidenceBindings,
    reloadEvidenceCandidates,
    reloadExtractionQuality,
    reloadMaterialIndexHealth,
    reloadMatrix,
    reloadMatrixReview,
    reloadPreflightCheck,
    reloadProjects,
    reloadQualificationDecision,
    reloadQualificationEvaluations,
    reloadWorkspaceSummary,
    renderDiffSegments,
    renderHighlightedText,
    renderReviewParagraph,
    replanDocumentSemanticSections,
    requestPublicUrlAcquisition,
    resetNewMaterialDraft,
    resetNewProjectDraft,
    reviewBlockCss,
    reviewChunkById,
    reviewChunks,
    reviewDisplayChunks,
    reviewDocument,
    reviewDuplicateGroups,
    reviewFallbackChunks,
    reviewHighlightByChunkId,
    reviewHighlights,
    reviewItemPaneRef,
    reviewOpenXmlDocument,
    reviewProgress,
    reviewQueuePage,
    reviewQueuePageSize,
    reviewSourcePaneRef,
    reviewUncoveredChunks,
    revisionChunks,
    revisionDocument,
    revisionDrawerOpen,
    revisionReason,
    revisionSearch,
    riskColor,
    riskFilter,
    riskLabels,
    RobotOutlined,
    runBusinessDraftContextPackCoverageReview,
    runBusinessDraftFactChecks,
    runCss,
    runMaterialSearch,
    runQualificationEvaluation,
    runWorkflowPrimaryAction,
    SafetyCertificateOutlined,
    saveChatModelConfig,
    saveImportProcessingState,
    savingBusinessDraft,
    savingEnterprise,
    savingMatrixAction,
    savingModelConfig,
    savingProject,
    savingSourceItem,
    scrollElementIntoContainer,
    searchEnterpriseMaterials,
    SearchOutlined,
    sectionExtractingId,
    sectionPlanLoading,
    sections,
    Segmented,
    Select,
    selectedChapterBlocks,
    selectedDraftChapter,
    selectedDraftChapterId,
    selectedDraftDiff,
    selectedProjectId,
    selectedProjectRowKeys,
    selectedRowKeys,
    selectedSectionId,
    selectedTreeKey,
    semanticSections,
    SendOutlined,
    setActionLogs,
    setActiveDraftBlockId,
    setActiveReviewItemId,
    setActiveTab,
    setApiError,
    setApprovalBusyId,
    setApprovalTasks,
    setAssistantCollapsed,
    setAuditLogs,
    setBindingMaterialId,
    setBusinessDraftChapters,
    setBusinessDraftContextPacks,
    setBusinessDraftGenerationTask,
    setBusinessDraftGenerationTaskId,
    setCandidateIncludeRestricted,
    setCandidateIncludeUnconfirmed,
    setChatModelConfig,
    setComplianceItems,
    setConfirmingMaterialId,
    setContextPackPreview,
    setContextPackPreviewOpen,
    setCoverageReview,
    setDeletingProjects,
    setDirectiveEditorOpen,
    setDocumentBusy,
    setDocuments,
    setDraftBlockFilter,
    setDraftBlocks,
    setDraftEditorValue,
    setEditDraft,
    setEditedDirectives,
    setEditedOutline,
    setEnterpriseMaterials,
    setEnterpriseProfile,
    setEvaluatingQualification,
    setEvidenceBindings,
    setEvidenceCandidates,
    setEvidenceDrawer,
    setExpandedDraftBlockIds,
    setExportFiles,
    setExportingExcel,
    setExportingWord,
    setExtractingHistoryMaterial,
    setExtractionQualityReport,
    setGeneratingDecision,
    setHighlightedRowKey,
    setHistoryExtractResult,
    setHistoryExtractTask,
    setHistoryExtractTaskId,
    setHomeProjectGroup,
    setHomeProjectPage,
    setHomeProjectPageSize,
    setHomeProjectSearch,
    setImportingProjectDraft,
    setImportProcessing,
    setImportUrl,
    setImportUrlSite,
    setKeyInfoDraft,
    setKeyInfoModalOpen,
    setLoadingBusinessDraft,
    setLoadingContextPack,
    setLoadingEnterprise,
    setLoadingEvidenceCandidates,
    setLoadingMaterialIndexHealth,
    setLoadingMaterialSearch,
    setLoadingMatrix,
    setLoadingModelConfig,
    setLoadingProjects,
    setLoadingQualityChunks,
    setLoadingReviewChunks,
    setLoadingRevisionChunks,
    setLoadingSimilarCandidates,
    setLoadingWorkspace,
    setLocatingReviewItemId,
    setMandatoryFilter,
    setMandatoryReviewIndex,
    setMandatoryReviewOpen,
    setMaterialIndexHealth,
    setMaterialModalOpen,
    setMaterialSearchQuery,
    setMaterialSearchResults,
    setMatrixReviewFilter,
    setModelConfigDraft,
    setModelConfigTestResult,
    setNewMaterialDraft,
    setNewProjectDraft,
    setNewProjectOpen,
    setOpeningEvidenceItemId,
    setOutlineEditorOpen,
    setOutlineSeed,
    setOwnerFilter,
    setPreflightCheck,
    setPreflightExpanded,
    setPrioritySortEnabled,
    setProfileDraft,
    setProjectCreateMode,
    setProjectDeleteTargets,
    setProjectDetail,
    setProjectImportDraft,
    setProjectImportError,
    setProjectNavCollapsed,
    setProjects,
    setPublicUrl,
    setPublicUrlSite,
    setPublishingRevision,
    setQualificationDecision,
    setQualificationEvaluations,
    setQualityChunks,
    setRebuildingMaterialIndex,
    setReviewChunks,
    setReviewDuplicateGroups,
    setReviewHighlights,
    setReviewOpenXmlDocument,
    setReviewQueuePage,
    setReviewQueuePageSize,
    setReviewUncoveredChunks,
    setRevisionChunks,
    setRevisionDocument,
    setRevisionDrawerOpen,
    setRevisionReason,
    setRevisionSearch,
    setRiskFilter,
    setSavingBusinessDraft,
    setSavingEnterprise,
    setSavingMatrixAction,
    setSavingModelConfig,
    setSavingProject,
    setSavingSourceItem,
    setSectionExtractingId,
    setSectionPlanLoading,
    setSections,
    setSelectedDraftChapterId,
    setSelectedProjectId,
    setSelectedProjectRowKeys,
    setSelectedRowKeys,
    setSelectedSectionId,
    setSelectedTreeKey,
    setSemanticSections,
    setSimilarActions,
    setSimilarBaseRow,
    setSimilarCandidates,
    setSimilarDrawerOpen,
    setSourceCreateMode,
    setSourceDrawer,
    setSourceSelectionDraft,
    setStatusFilter,
    setTestingModelConfig,
    SettingOutlined,
    setUnbindingId,
    setViewedDraftBlockIds,
    setViewMode,
    setWaivingEvidenceItemId,
    setWorkspaceNode,
    similarActions,
    similarBaseRow,
    similarCandidates,
    similarDrawerOpen,
    simpleWorkflowSteps,
    sourceCreateMode,
    sourceDrawer,
    sourceMetaText,
    sourceSelectionDraft,
    Space,
    Spin,
    splitDuplicateGroupItem,
    Statistic,
    statusColor,
    statusFilter,
    statusLabels,
    summaryNumber,
    Switch,
    Table,
    Tabs,
    Tag,
    taskOutputText,
    taskProgressMessage,
    taskShortId,
    taskTimeRange,
    TeamOutlined,
    technicalRows,
    terminalTaskRefreshKeysRef,
    testChatModelConfig,
    testingModelConfig,
    Text,
    TextArea,
    Title,
    toggleDraftBlockExpanded,
    Tooltip,
    Tree,
    truncateText,
    Typography,
    unapprovedDraftBlockCount,
    unbindComplianceEvidence,
    unbindingId,
    uncoveredChunkMap,
    unlinkDuplicateGroupItem,
    unresolvedHighRiskRows,
    unresolvedMatrixRows,
    updateBusinessDraftBlock,
    updateBusinessDraftChapter,
    updateBusinessDraftContextPackDirectives,
    updateComplianceItem,
    updateEnterpriseMaterial,
    updateProject,
    updateRevisionChunk,
    updateSection,
    Upload,
    uploadDocument,
    uploadEnterpriseMaterialFile,
    upsertEnterpriseProfile,
    useCallback,
    useEffect,
    useMemo,
    useRef,
    useState,
    verificationStatusLabels,
    viewedDraftBlockIds,
    viewMode,
    visibleChapterBlocks,
    visiblePreflightChecks,
    waiveComplianceEvidenceRequirement,
    waivingEvidenceItemId,
    WarningOutlined,
    workflowStatusColor,
    workflowStepForContextPackCheck,
    workflowStepForPreflightCheck,
    workflowStepKeys,
    workflowSteps
  } = app;

  // Agent 自动复检后仍未解决 → 进入“转人工”状态，展示手动处理入口。
  const autoHandedToManual = Boolean(autoResolveResult && !autoResolveResult.resolved);

  // 质量报告里后端落下的自动处理痕迹（刷新/重进后仍可见，作为本会话 autoResolveResult 的兜底）。
  const reportSummary = (extractionQualityReport?.summary_json ?? {}) as Record<string, unknown>;
  const reportAutoResolved =
    reportSummary.auto_resolve === true && extractionQualityReport?.status === "passed";
  const reportRound = typeof reportSummary.round === "number" ? reportSummary.round : null;
  const reportReextractedSections = Array.isArray(reportSummary.reextracted_sections)
    ? (reportSummary.reextracted_sections as unknown[]).filter((value): value is string => typeof value === "string")
    : [];

  // Agent 处理日志（含每一轮策略/涉及章节/结果），通过与未通过都展示，保留可追溯的处理过程。
  const autoResolveReport = autoResolveResult ? (
    <div
      className={`auto-resolve-report ${
        autoResolveResult.resolved ? "auto-resolve-report-ok" : "auto-resolve-report-warn"
      }`}
    >
      <div className="auto-resolve-report-head">
        <Tag color={autoResolveResult.resolved ? "green" : "orange"}>
          {autoResolveResult.resolved ? "已解决" : "仍有阻断"}
        </Tag>
        <Text strong>Agent 自动处理报告 · 共 {autoResolveResult.round_count} 轮</Text>
      </div>
      <ol className="auto-resolve-rounds">
        {autoResolveResult.rounds.map((round) => (
          <li key={round.round}>
            <Tag color={round.strategy === "replan_regen" ? "purple" : "blue"}>
              {round.strategy === "replan_regen" ? "重排重抽" : "定向重抽"}
            </Tag>
            <span className="auto-resolve-round-reason">{round.reason}</span>
            {round.reextracted_sections && round.reextracted_sections.length > 0 && (
              <span className="auto-resolve-round-sections">涉及：{round.reextracted_sections.join("、")}</span>
            )}
            <Tag color={round.resolved ? "green" : "default"}>{round.resolved ? "本轮通过" : "未通过"}</Tag>
          </li>
        ))}
      </ol>
      {!autoResolveResult.resolved && autoResolveResult.remaining_issues.length > 0 && (
        <div className="auto-resolve-remaining">
          <Text type="secondary">
            仍剩 {autoResolveResult.remaining_count} 处需人工确认，详见下方“原文定位与逐条明细”：
          </Text>
          <ul>
            {autoResolveResult.remaining_issues.slice(0, 5).map((issue, index) => (
              <li key={`${issue.code}-${issue.section_id ?? "unknown"}-${index}`}>
                <Tag color={qualityIssueSeverityColor(issue.severity)}>{issue.severity}</Tag>
                <span className="quality-recommendation-issue-where">{issue.section_title ?? "未定位章节"}</span>
                <span className="quality-recommendation-issue-msg">{issue.message}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  ) : reportAutoResolved ? (
    <div className="auto-resolve-report auto-resolve-report-ok">
      <div className="auto-resolve-report-head">
        <Tag color="green">已解决</Tag>
        <Text strong>本次质量门禁由 Agent 自动处理通过{reportRound ? ` · 第 ${reportRound} 轮` : ""}</Text>
      </div>
      {reportReextractedSections.length > 0 && (
        <div className="auto-resolve-round-sections">定向重抽章节：{reportReextractedSections.join("、")}</div>
      )}
    </div>
  ) : null;

  return (
                      <div className="workspace-panel quality-gate-panel">
                        <div className="tab-intro">
                          <div>
                            <Text strong>{extractionBlocked ? "处理质量门禁" : "抽取质量门禁"}</Text>
                            <p>
                              {extractionBlocked
                                ? autoHandedToManual
                                  ? "Agent 自动处理已达上限，仍有阻断项，请人工处理。"
                                  : "已检测到阻断项，Agent 正在自动处理，无需手动操作。"
                                : "生成矩阵时自动检查章节规划、来源回链和关键条款覆盖。"}
                            </p>
                          </div>
                          <Tag color={extractionBlocked ? "red" : extractionQualityReport ? "green" : "default"}>
                            {extractionBlocked ? `${extractionQualityIssueCount} 个阻断` : extractionQualityReport ? "质量通过" : "待生成"}
                          </Tag>
                        </div>

                        {!reviewDocument?.current_version_id ? (
                          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="请先上传并解析招标文件" />
                        ) : !extractionQualityReport ? (
                          <Alert
                            type="info"
                            showIcon
                            message="尚未形成质量报告"
                            description={
                              <Space direction="vertical" size={8}>
                                <Text>先生成合规矩阵；系统会自动检查是否漏抽关键条款。</Text>
                                <Button type="primary" icon={<RobotOutlined />} onClick={() => handleGenerateMatrix(reviewDocument)}>
                                  生成合规矩阵
                                </Button>
                              </Space>
                            }
                          />
                        ) : extractionQualityReport.status === "passed" ? (
                          <>
                            <Alert
                              type="success"
                              showIcon
                              message="质量门禁已通过"
                              description={
                                <Space direction="vertical" size={8}>
                                  <Text>
                                    {autoResolveReport
                                      ? "Agent 已自动处理并复检通过，处理过程见下方日志，可继续处理合规矩阵。"
                                      : "最近一次抽取未发现阻断项，可以继续处理合规矩阵。"}
                                  </Text>
                                  <Button type="primary" icon={<FileSearchOutlined />} onClick={() => activateWorkflowStep("matrix")}>
                                    进入合规矩阵
                                  </Button>
                                </Space>
                              }
                            />
                            {autoResolveReport}
                          </>
                        ) : (
                          <>
                            <div className="quality-recommendation-card">
                              <div className="quality-recommendation-main">
                                <span className="quality-recommendation-icon">
                                  {autoHandedToManual ? <WarningOutlined /> : <RobotOutlined />}
                                </span>
                                <div>
                                  <Text strong>
                                    {autoHandedToManual ? "Agent 已尽力，仍需人工处理" : "Agent 正在自动处理阻断项"}
                                  </Text>
                                  <p>
                                    {autoHandedToManual
                                      ? `Agent 自动复检 ${autoResolveResult?.round_count ?? 0} 轮后仍有 ${
                                          autoResolveResult?.remaining_count ?? extractionQualityIssueCount
                                        } 处无法自动消除，请用下面的方式人工处理；人工已确认/编辑过的条目全程受保护。`
                                      : "已检测到阻断项，Agent 自动接手：漏抽集中在个别章节就只定向重抽这几段，存在结构性问题则重排章节后整体重抽，并自动复检收敛（最多 2 轮）。无需手动操作，完成后会在下方给出明细报告；仍有阻断时再交还你处理。"}
                                  </p>
                                </div>
                              </div>
                              {extractionQualityIssues.length > 0 && (
                                <div className="quality-recommendation-issues">
                                  <div className="quality-recommendation-issues-label">
                                    {autoHandedToManual
                                      ? `仍需人工处理以下 ${extractionQualityIssueCount} 处：`
                                      : `Agent 正在重点补抽以下 ${extractionQualityIssueCount} 处：`}
                                  </div>
                                  <ul>
                                    {extractionQualityIssues.slice(0, 3).map((issue, index) => (
                                      <li key={`${issue.code}-${issue.section_id ?? "unknown"}-${index}`}>
                                        <Tag color={qualityIssueSeverityColor(issue.severity)}>{issue.severity}</Tag>
                                        <span className="quality-recommendation-issue-where">
                                          {issue.section_title ??
                                            semanticSections.find((section) => section.id === issue.section_id)?.title ??
                                            "未定位章节"}
                                        </span>
                                        <span className="quality-recommendation-issue-msg">{issue.message}</span>
                                      </li>
                                    ))}
                                  </ul>
                                  {extractionQualityIssues.length > 3 && (
                                    <Text type="secondary" className="quality-recommendation-issues-more">
                                      还有 {extractionQualityIssues.length - 3} 处，展开下方“原文定位与逐条明细”查看。
                                    </Text>
                                  )}
                                </div>
                              )}
                              {autoHandedToManual ? (
                                <div className="quality-recommendation-actions">
                                  <Button
                                    type="primary"
                                    icon={<RobotOutlined />}
                                    loading={loadingMatrix || matrixTaskActive}
                                    disabled={autoResolveActive || matrixTaskActive}
                                    onClick={() => handleGenerateMatrix(reviewDocument)}
                                  >
                                    {matrixTaskActive ? "正在整体重抽" : "整体重抽（手动）"}
                                  </Button>
                                  <Button
                                    icon={<RobotOutlined />}
                                    loading={autoResolveActive}
                                    disabled={autoResolveActive || matrixTaskActive}
                                    onClick={() => handleAutoResolveMatrix(reviewDocument)}
                                  >
                                    {autoResolveActive ? "Agent 处理中…" : "让 Agent 再试一次"}
                                  </Button>
                                  <Button
                                    icon={<FileSearchOutlined />}
                                    disabled={!matrixRows.length}
                                    onClick={() => activateWorkflowStep("matrix")}
                                  >
                                    查看上一版矩阵
                                  </Button>
                                </div>
                              ) : (
                                <div className="quality-auto-running">
                                  <Spin />
                                  <Text type="secondary">
                                    {autoResolveActive
                                      ? "Agent 正在自动处理中，可切换页面继续其它工作，完成后这里会自动更新…"
                                      : "正在唤起 Agent 自动处理…"}
                                  </Text>
                                </div>
                              )}
                              <div className="quality-safety-notes">
                                <span>人工确认项受保护</span>
                                <span>失败结果未写入</span>
                                <span>上一版矩阵保留</span>
                                <span>{extractionQualityIssueCount} 个阻断会重新校验</span>
                              </div>
                            </div>
                            {autoResolveReport}
                            <details className="quality-details">
                              <summary>原文定位与逐条明细：{extractionQualityIssueCount} 处漏抽</summary>
                              <div className="quality-detail-intro">
                                <Text strong>系统定位到的漏抽位置</Text>
                                <p>
                                  下面是每处漏抽的原文定位与原因，便于你核对。Agent 会自动整体/定向重抽；若已转人工，也可对单处点“只重抽这一段”。
                                </p>
                              </div>
                              <Spin spinning={loadingQualityChunks}>
                                <div className="quality-issue-list quality-issue-list-standalone">
                                  {extractionQualityIssues.length ? (
                                    extractionQualityIssues.map((issue, index) => {
                                      const semanticSection = semanticSections.find((section) => section.id === issue.section_id);
                                      const terms = qualityIssueSearchTerms(issue);
                                      const sourceChunk = qualityIssueSourceChunk(issue, semanticSection, qualityDisplayChunks);
                                      const sourceExcerpt = qualityIssueSourceExcerpt(sourceChunk, terms);
                                      return (
                                        <div className="quality-issue-item" key={`${issue.code}-${issue.section_id ?? "unknown"}-${index}`}>
                                          <div className="quality-issue-title">
                                            <Space size={6} wrap>
                                              <Tag color={qualityIssueSeverityColor(issue.severity)}>{issue.severity}</Tag>
                                              <Text strong>{issue.section_title ?? semanticSection?.title ?? "未定位章节"}</Text>
                                              {semanticSection && <Tag>{semanticSection.start_page}-{semanticSection.end_page} 页</Tag>}
                                              {issue.page_no && <Tag>第 {issue.page_no} 页</Tag>}
                                              {issue.source_chunk_index && <Tag>chunk {issue.source_chunk_index}</Tag>}
                                            </Space>
                                          </div>
                                          <Text>{issue.message}</Text>
                                          <Text type="secondary">{qualityIssueActionText(issue)}</Text>
                                          {sourceExcerpt && (
                                            <div className="quality-source-snippet">
                                              <Text type="secondary">
                                                原文定位：第 {sourceChunk?.page_no ?? "-"} 页
                                                {sourceChunk?.chunk_index ? ` · chunk ${sourceChunk.chunk_index}` : ""}
                                              </Text>
                                              <p>{sourceExcerpt}</p>
                                            </div>
                                          )}
                                          <Button
                                            size="small"
                                            disabled={!semanticSection}
                                            loading={Boolean(semanticSection && sectionExtractingId === semanticSection.id)}
                                            onClick={() => semanticSection && handleExtractSemanticSection(semanticSection)}
                                          >
                                            只重抽这一段
                                          </Button>
                                        </div>
                                      );
                                    })
                                  ) : (
                                    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无可展示的阻断明细" />
                                  )}
                                </div>
                              </Spin>
                              <div className="quality-gate-toolbar">
                                <Text type="secondary">高级操作</Text>
                                <Button size="small" loading={sectionPlanLoading} onClick={handleReplanSemanticSections}>
                                  重新规划章节
                                </Button>
                                <Button size="small" disabled={!matrixRows.length} onClick={() => activateWorkflowStep("review")}>
                                  打开审阅台
                                </Button>
                              </div>
                            </details>
                          </>
                        )}
                      </div>
                    );
}
