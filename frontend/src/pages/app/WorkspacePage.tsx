import { TasksTab } from "./workspace-tabs/TasksTab";
import { DocumentsTab } from "./workspace-tabs/DocumentsTab";
import { QualityTab } from "./workspace-tabs/QualityTab";
import { EvidenceTab } from "./workspace-tabs/EvidenceTab";
import { QualificationTab } from "./workspace-tabs/QualificationTab";
import { MatrixTab } from "./workspace-tabs/MatrixTab";
import { ReviewTab } from "./workspace-tabs/ReviewTab";
import { TechnicalTab } from "./workspace-tabs/TechnicalTab";
import { ChapterTab } from "./workspace-tabs/ChapterTab";
import { ApprovalTab } from "./workspace-tabs/ApprovalTab";
import type { BidAppController, WorkflowStepKey } from "../../features/bid/useBidAppController";

export function WorkspacePage({ app }: { app: BidAppController }) {
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
    loadingSectionQuality,
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
    reloadSectionQualitySummary,
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
    sectionQualityStatusColor,
    sectionQualityStatusLabel,
    sectionQualitySummary,
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

  return (
          <Layout className={projectNavCollapsed ? "workspace-layout project-nav-collapsed" : "workspace-layout"}>
            <aside className={projectNavCollapsed ? "project-nav collapsed" : "project-nav"}>
              <div className="pane-title-row">
                {!projectNavCollapsed && <Text strong>项目导航</Text>}
                <Space size={4}>
                  <Tooltip title={projectNavCollapsed ? "展开项目导航" : "收起项目导航"}>
                    <Button
                      type="text"
                      size="small"
                      aria-label={projectNavCollapsed ? "展开项目导航" : "收起项目导航"}
                      icon={projectNavCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                      onClick={() => setProjectNavCollapsed((value) => !value)}
                    />
                  </Tooltip>
                  {!projectNavCollapsed && (
                    <Tooltip title="新建项目">
                      <Button
                        type="text"
                        size="small"
                        aria-label="新建项目"
                        icon={<PlusOutlined />}
                        onClick={() => openCreateProjectModal("manual")}
                      />
                    </Tooltip>
                  )}
                </Space>
              </div>
              {projectNavCollapsed ? (
                <div className="project-nav-rail">
                  <Tooltip title="新建项目">
                    <Button
                      type="text"
                      size="small"
                      aria-label="新建项目"
                      icon={<PlusOutlined />}
                      onClick={() => openCreateProjectModal("manual")}
                    />
                  </Tooltip>
                  <Tooltip title="项目导航已收起">
                    <FolderOpenOutlined />
                  </Tooltip>
                </div>
              ) : (
                <>
                  <div className="todo-summary">
                    <div>
                      <Text strong>全局待办</Text>
                      <p>
                        {homeTodoRows.length
                          ? `${homeTodoRows.length} 项待办；${matrixRows.filter((row) => row.riskCode === "high").length} 条高风险缺项。`
                          : "当前项目暂无待办。"}
                      </p>
                    </div>
                    <Button size="small" onClick={() => locateMatrixRow(matrixRows[0]?.key)} disabled={!matrixRows.length}>
                      查看
                    </Button>
                  </div>
                  <Spin spinning={loadingWorkspace}>
                    <Tree
                      showIcon
                      defaultExpandAll
                      selectedKeys={[selectedSectionId ? `section:${selectedSectionId}` : selectedProjectId ? `project:${selectedProjectId}` : ""]}
                      treeData={projectTreeData}
                      onSelect={(keys) => {
                        const key = keys[0] ? String(keys[0]) : "";
                        const [scope, id] = key.split(":");
                        if (scope === "project" && id) {
                          openProjectWorkspace(id, recommendedStep?.key ?? "documents");
                          return;
                        }
                        if (scope === "section" && id) {
                          setSelectedSectionId(id);
                          setSelectedTreeKey(`section:${id}:${recommendedStep?.key ?? "documents"}`);
                          setActiveTab(recommendedStep?.key ?? "documents");
                        }
                      }}
                    />
                  </Spin>
                </>
              )}
            </aside>

            <Content className="work-area">
              <section className="context-bar">
                <div>
                  <Title level={3}>{contextTitle}</Title>
                  <Space size={8} wrap>
                    <Text type="secondary">{currentSection?.name ?? "请选择标段"}</Text>
                    <Tooltip title="冻结后仍允许人工修正解析结果；保存修正会生成新版本，原冻结版本将存档用于审计回溯。">
                      <Tag color="blue">解析结果已冻结 v0.1</Tag>
                    </Tooltip>
                  </Space>
                </div>
                <Space wrap>
                  <Tag icon={<ClockCircleOutlined />} color="processing">
                    截止 {formatDateTime(currentSection?.bid_deadline_at ?? currentProject?.bid_deadline_at ?? null)}
                  </Tag>
                  <Button onClick={openKeyInfoModal} disabled={!currentProject || !currentSection}>
                    项目信息
                  </Button>
                  <Button type="primary" onClick={confirmSubmit}>
                    提交确认
                  </Button>
                </Space>
              </section>

              {importProcessingVisible && importProcessing && (
                <section className="background-task-panel">
                  <Alert
                    showIcon
                    type={importProcessingFailed ? "error" : importProcessingDone ? "success" : "info"}
                    message={importProcessingStageTitle}
                    description={
                      importProcessingQualityBlocked
                        ? "系统已暂停本轮写入，上一版矩阵仍保留。请进入质量门禁页按建议处理阻断项。"
                        : importProcessingParseFailed
                        ? "文件解析失败，请在文件解析页重新解析；如果原文件异常，可重新上传后再生成矩阵。"
                        : importProcessingMatrixFailed
                        ? "矩阵生成失败，请查看矩阵任务错误后重新生成；如果被质量门禁拦截，先处理质检阻断。"
                        : importProcessingFailed
                        ? "解析或矩阵生成失败，请查看下方任务状态后重新解析或重新生成矩阵。"
                        : importProcessingDone
                          ? "文件解析和合规矩阵已刷新，可继续处理风险、证据和确认项。"
                          : "这是后台异步任务，可以切换页面继续查看项目；完成后会自动刷新。"
                    }
                  />
                  <div className="background-task-overview">
                    <div className="background-task-overview-header">
                      <div>
                        <Text strong>后台解析/生成进度</Text>
                        <Text type="secondary">{importProcessingStageMessage}</Text>
                      </div>
                      <Tag color={importProcessingFailed ? "red" : importProcessingDone ? "green" : "blue"}>
                        {importProcessingPercent}%
                      </Tag>
                    </div>
                    <Progress
                      percent={importProcessingPercent}
                      status={importProcessingFailed ? "exception" : importProcessingDone ? "success" : "active"}
                      showInfo={false}
                    />
                    {!importProcessingDone && !importProcessingFailed && (
                      <Text type="secondary" className="background-task-hint">
                        当前不需要人工操作；如果质量门禁拦截，系统会在完成后引导到专门处理页。
                      </Text>
                    )}
                    {(importProcessingInProgress || importProcessingQualityBlocked || importProcessingFailed) && (
                      <Space className="background-task-actions" wrap>
                        <Button onClick={() => openWorkspace("tasks")}>
                          进入任务中心
                        </Button>
                        {importProcessingQualityBlocked && (
                          <Button type="primary" onClick={() => openWorkspace("quality")}>
                            处理质量门禁
                          </Button>
                        )}
                      </Space>
                    )}
                  </div>
                  <div className="background-task-grid">
                    {importProcessing.parseTaskId && (
                      <div className="background-task-card">
                        <div className="background-task-title">
                          <Text strong>文件解析</Text>
                          <Tag color={asyncTaskStatusColors[importProcessing.parseTask?.status ?? "pending"]}>
                            {asyncTaskStatusLabels[importProcessing.parseTask?.status ?? "pending"] ?? "处理中"}
                          </Tag>
                        </div>
                        <Text type="secondary">
                          {taskProgressMessage(
                            importProcessing.parseTask,
                            "正在读取文件并切分条款...",
                            "解析版本已生成。"
                          )}
                        </Text>
                      </div>
                    )}
                    {importProcessing.matrixTaskId && (
                      <div className="background-task-card">
                        <div className="background-task-title">
                          <Text strong>合规矩阵</Text>
                          <Tag color={asyncTaskStatusColors[importProcessing.matrixTask?.status ?? "pending"]}>
                            {asyncTaskStatusLabels[importProcessing.matrixTask?.status ?? "pending"] ?? "处理中"}
                          </Tag>
                        </div>
                        <Text type="secondary">{matrixTaskStageTitle(importProcessing.matrixTask)}</Text>
                        <Text type="secondary">
                          {taskProgressMessage(
                            importProcessing.matrixTask,
                            "正在抽取资格项、强制响应项和风险点...",
                            "矩阵已生成并刷新。"
                          )}
                        </Text>
                      </div>
                    )}
                  </div>
                </section>
              )}

              <section className={preflightCheck ? "command-center" : "command-center command-center-single"}>
                <div className="workflow-guide">
                  {recommendedStep && (
                    <div className="next-action-card">
                      <div className="next-action-copy">
                        <Text type="secondary" className="next-action-eyebrow">
                          现在先做
                        </Text>
                        <Text strong>当前任务：{recommendedStep.title}</Text>
                        <Text type="secondary">
                          {recommendedPreflightCheck
                            ? recommendedPreflightCheck.message
                            : recommendedStep.reason}
                        </Text>
                        <div className="next-action-tags">
                          {extractionQualityReport?.status === "passed" && (
                            <Tag color="green">抽取质量门禁已通过</Tag>
                          )}
                          {preflightStatusForDisplay !== "pass" && (
                            <Tag color={preflightColor(preflightStatusForDisplay)}>
                              提交前核验·{preflightLabel(preflightStatusForDisplay)}
                            </Tag>
                          )}
                          {visiblePreflightChecks
                            .filter((item) => item.status !== "pass")
                            .slice(0, 3)
                            .map((item) => (
                              <Tag key={item.code} color={preflightColor(item.status)}>
                                {item.title} {item.count}
                              </Tag>
                            ))}
                        </div>
                      </div>
                      <Button type="primary" onClick={() => runWorkflowPrimaryAction(recommendedStep.key)}>
                        {recommendedStep.actionText}
                      </Button>
                    </div>
                  )}
                  {(sectionQualitySummary || loadingSectionQuality) && (
                    <section className={`section-quality-strip ${sectionQualitySummary?.status ?? "loading"}`}>
                      <div className="section-quality-main">
                        <Space wrap>
                          <Text strong>标书质量体检</Text>
                          <Tag color={sectionQualityStatusColor(sectionQualitySummary?.status ?? "pass")}>
                            {sectionQualitySummary
                              ? sectionQualitySummary.status_label || sectionQualityStatusLabel(sectionQualitySummary.status)
                              : "加载中"}
                          </Tag>
                          {sectionQualitySummary?.export_preview.submission_allowed === false && (
                            <Tag color="red">正式版不可导出</Tag>
                          )}
                        </Space>
                        <Text type="secondary">
                          {sectionQualitySummary?.summary ?? "正在汇总覆盖、报价、草稿事实和导出材料状态。"}
                        </Text>
                        {sectionQualitySummary && (
                          <div className="section-quality-tags">
                            <Tag color="red">
                              阻断 {sectionQualitySummary.checks.filter((check) => check.status === "block").length}
                            </Tag>
                            <Tag color="gold">
                              复核 {sectionQualitySummary.checks.filter((check) => check.status === "warn").length}
                            </Tag>
                            <Tag color="blue">
                              评分索引 {summaryNumber(sectionQualitySummary.export_preview, "scoring_index_count")}
                            </Tag>
                            <Tag color="blue">
                              占位 {summaryNumber(sectionQualitySummary.export_preview, "placeholder_count")}
                            </Tag>
                            <Tag color="green">
                              材料 {summaryNumber(sectionQualitySummary.material_summary, "embeddable_count")}/
                              {summaryNumber(sectionQualitySummary.material_summary, "selected_count")}
                            </Tag>
                          </div>
                        )}
                      </div>
                      <Space wrap>
                        <Button
                          size="small"
                          loading={loadingSectionQuality}
                          onClick={() => void reloadSectionQualitySummary()}
                        >
                          刷新体检
                        </Button>
                        <Button size="small" onClick={() => activateWorkflowStep("documents")}>
                          去导出
                        </Button>
                      </Space>
                    </section>
                  )}
                  <div className="workflow-steps" aria-label="项目简化流程">
                    {simpleWorkflowSteps.map((step, index) => (
                      <Tooltip
                        key={step.key}
                        title={
                          <div className="workflow-step-tooltip">
                            <div className="workflow-step-tooltip-head">
                              <strong>{step.title}</strong>
                              <Tag color={workflowStatusColor(step.status)}>{step.statusText}</Tag>
                            </div>
                            <p>{step.disabled ? step.disabledReason : step.reason}</p>
                          </div>
                        }
                      >
                        <span
                          className="workflow-step-hitbox"
                          title={`${step.title} · ${step.statusText}\n${step.disabled ? step.disabledReason ?? "" : step.reason}`}
                        >
                          <button
                            className={[
                              "workflow-step",
                              `status-${step.status === "not_started" ? "not-started" : step.status}`,
                              recommendedStep?.key &&
                              step.activeKeys.includes(recommendedStep.key) &&
                              step.status !== "done" &&
                              step.status !== "not_started"
                                ? "current-blocking"
                                : "",
                              step.activeKeys.includes(activeTab) ? "active" : "",
                              recommendedStep?.key && step.activeKeys.includes(recommendedStep.key) ? "recommended" : "",
                              step.disabled ? "disabled" : ""
                            ]
                              .filter(Boolean)
                              .join(" ")}
                            aria-label={`${index + 1}. ${step.title}，${step.statusText}`}
                            disabled={step.disabled}
                            onClick={() => activateWorkflowStep(step.targetKey)}
                          >
                            <span className="workflow-index">{index + 1}</span>
                            <strong>{step.title}</strong>
                          </button>
                        </span>
                      </Tooltip>
                    ))}
                  </div>

                  {currentProject && currentSection && missingKeyInfo.length > 0 && (
                    <section className="key-info-panel">
                      <div className="key-info-header">
                        <Space wrap>
                          <Text strong>项目关键信息</Text>
                          {missingKeyInfo.length ? (
                            <Tag color="orange">缺失 {missingKeyInfo.join("、")}</Tag>
                          ) : (
                            <Tag color="green">关键字段已填写</Tag>
                          )}
                        </Space>
                        <Button size="small" onClick={openKeyInfoModal}>
                          编辑/确认
                        </Button>
                      </div>
                      <div className="key-info-grid">
                        <div>
                          <Text type="secondary">招标人</Text>
                          <strong>{currentProject.purchaser || "未填写"}</strong>
                        </div>
                        <div>
                          <Text type="secondary">预算/限价</Text>
                          <strong>{currentSection.budget_amount || currentProject.budget_amount || "未填写"}</strong>
                        </div>
                        <div>
                          <Text type="secondary">投标截止</Text>
                          <strong>{formatDateTime(currentSection.bid_deadline_at ?? currentProject.bid_deadline_at)}</strong>
                        </div>
                        <div>
                          <Text type="secondary">地区/行业</Text>
                          <strong>{[currentProject.region_code, currentProject.industry_code].filter(Boolean).join(" / ") || "未填写"}</strong>
                        </div>
                      </div>
                    </section>
                  )}

                  <section className="status-grid">
                    <div className="metric-item">
                      <Text type="secondary">合规项</Text>
                      <strong>{currentSection?.compliance_item_count ?? matrixRows.length}</strong>
                      <Text type="secondary">{unresolvedMatrixRows.length ? `${unresolvedMatrixRows.length} 条待确认` : "已全部确认"}</Text>
                    </div>
                    <div className="metric-item">
                      <Text type="secondary">缺项</Text>
                      <strong>{matrixRows.filter((row) => row.statusCode === "needs_material").length}</strong>
                      <Text type="secondary">需要补资料或说明</Text>
                    </div>
	                    <div className="metric-item">
	                      <Text type="secondary">已确认</Text>
	                      <strong>{matrixRows.length ? matrixRows.filter((row) => row.statusCode === "confirmed").length : knownConfirmedMatrixCount}</strong>
	                      <Text type="secondary">人工核对完成</Text>
	                    </div>
                    <div className="metric-item">
                      <Text type="secondary">高风险</Text>
                      <strong>{currentSection?.high_risk_count ?? 0}</strong>
                      <Text type="secondary">{unresolvedHighRiskRows.length ? `${unresolvedHighRiskRows.length} 条待处理` : "暂无待处理"}</Text>
                    </div>
                    <div className="metric-item approval-metric">
                      <Text type="secondary">{mvp13DraftWorkflowAvailable ? "待审批" : "投标素材包"}</Text>
                      <strong>
                        {mvp13DraftWorkflowAvailable
                          ? approvalTasks.filter((task) => task.status === "pending").length
                          : activeContextPack
                            ? 1
                            : 0}
                      </strong>
                      <Button size="small" onClick={() => activateWorkflowStep(mvp13DraftWorkflowAvailable ? "tasks" : "chapter")}>
                        {mvp13DraftWorkflowAvailable ? "进入任务中心" : "查看投标素材包"}
                      </Button>
                    </div>
                  </section>
                </div>

                {preflightCheck && (
                  <div className="preflight-panel">
                    <div className="preflight-header">
                      <Space wrap>
                        <Text strong>待办队列</Text>
                        <Tag color={preflightColor(preflightStatusForDisplay)}>{preflightLabel(preflightStatusForDisplay)}</Tag>
                        {preflightCheck.matrix_outdated && <Tag color="red">矩阵已过期</Tag>}
                      </Space>
                      <Text type="secondary">
                        {visiblePreflightChecks.some((item) => item.status !== "pass")
                          ? "按卡片顺序处理；点击卡片会进入对应页面或执行对应操作。"
                          : preflightCheck.summary}
                      </Text>
                    </div>
                    <div className="preflight-checks">
                      {visiblePreflightChecks.map((item) => (
                        <button
                          key={item.code}
                          className={`preflight-check ${item.status}`}
                          onClick={() => handlePreflightCheckAction(item)}
                        >
                          <Tag color={preflightColor(item.status)}>{item.title}</Tag>
                          <strong>{item.status === "pass" ? "已通过" : item.count}</strong>
                          <span>{item.message}</span>
                          <span className="preflight-action-text">{preflightActionText(item)}</span>
                        </button>
                      ))}
                    </div>
                    {preflightChecksForDisplay.length > 4 && (
                      <Button
                        type="text"
                        size="small"
                        className="preflight-expand-button"
                        onClick={() => setPreflightExpanded((value) => !value)}
                      >
                        {preflightExpanded ? "收起待办" : `展开全部（还有 ${hiddenPreflightCheckCount} 项）`}
                      </Button>
                    )}
                  </div>
                )}
              </section>

              <Tabs
                className="workspace-tabs"
                activeKey={activeTab}
                renderTabBar={() => <></>}
                onChange={(key) => {
                  if (isWorkflowStepKey(key)) activateWorkflowStep(key);
                }}
                items={[
                  {
                    key: "tasks",
                    label: "任务中心",
                    children: <TasksTab app={app} />
                  },
                  {
                    key: "documents",
                    label: "文件解析",
                    children: <DocumentsTab app={app} />
                  },
                  {
                    key: "quality",
                    label: "质量门禁",
                    children: <QualityTab app={app} />
                  },
                  {
                    key: "evidence",
                    label: "证据处理",
                    children: <EvidenceTab app={app} />
                  },
                  {
                    key: "qualification",
                    label: "资格预评估",
                    children: <QualificationTab app={app} />
                  },
                  {
                    key: "matrix",
                    label: "合规矩阵",
                    children: <MatrixTab app={app} />
                  },
                  {
                    key: "review",
                    label: "矩阵审阅",
                    children: <ReviewTab app={app} />
                  },
                  {
                    key: "technical",
                    label: "技术响应",
                    children: <TechnicalTab app={app} />
                  },
                  {
                    key: "chapter",
                    label: "商务标章节",
                    children: <ChapterTab app={app} />
                  },
                  {
                    key: "approval",
                    label: "审批任务",
                    children: <ApprovalTab app={app} />
                  }
                ]}
              />
            </Content>

            <aside className={assistantCollapsed ? "assistant collapsed" : "assistant"}>
              <div className="assistant-header">
                {!assistantCollapsed && (
                  <Space>
                    <Avatar icon={<RobotOutlined />} className="assistant-avatar" />
                    <div>
                      <Text strong>流程助手</Text>
                      <div className="assistant-subtitle">按当前阻断项提示下一步</div>
                    </div>
                  </Space>
                )}
                <Tooltip title={assistantCollapsed ? "展开助手" : "折叠助手"}>
                  <Button
                    type="text"
                    icon={assistantCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                    onClick={() => setAssistantCollapsed((value) => !value)}
                  />
                </Tooltip>
              </div>

              {assistantCollapsed ? (
                <div className="assistant-rail">
                  <Tooltip title="流程助手">
                    <Button type="primary" icon={<RobotOutlined />} />
                  </Tooltip>
                  <Tooltip title="主动提醒">
                    <Badge dot>
                      <Button icon={<CommentOutlined />} />
                    </Badge>
                  </Tooltip>
                </div>
              ) : (
                <>
                  <div className="assistant-feed">
                    {recommendedStep && (
                      <div className="assistant-message primary-next">
                        <div className="message-title-row">
                          <Text strong>当前建议：{recommendedStep.title}</Text>
                          <Tag color={workflowStatusColor(recommendedStep.status)}>{recommendedStep.statusText}</Tag>
                        </div>
                        <p>{recommendedStep.reason}</p>
                        <Button type="primary" onClick={() => runWorkflowPrimaryAction(recommendedStep.key)}>
                          {recommendedStep.actionText}
                        </Button>
                      </div>
                    )}

                    {!focusQualityAssistant && (
                      <div className="quick-prompts compact">
                        {quickPrompts.map((prompt) => (
                          <Button size="small" key={prompt} onClick={() => handleQuickPrompt(prompt)}>
                            {prompt}
                          </Button>
                        ))}
                      </div>
                    )}

                    {!focusQualityAssistant &&
                      assistantMessages.map((item) => (
                        <div className="assistant-message" key={item.key}>
                          <div className="message-title-row">
                            <Text strong>{item.title}</Text>
                            <Button type="text" size="small" icon={<CloseOutlined />} />
                          </div>
                          <p>{item.content}</p>
                          <Space size={8}>
                            <Button
                              size="small"
                              type="primary"
                              onClick={() => handleAssistantMessageAction(item)}
                            >
                              {item.action}
                            </Button>
                            <Button size="small">转为任务</Button>
                          </Space>
                        </div>
                      ))}

                    <div className="operation-log">
                      <Text strong>操作日志</Text>
                      {displayedLogs.length ? (
                        displayedLogs.map((log, index) => (
                          <div className="log-line" key={`${log}-${index}`}>
                            {log}
                          </div>
                        ))
                      ) : (
                        <Text type="secondary">暂无操作日志</Text>
                      )}
                    </div>
                  </div>

                  <div className="assistant-input">
                    <TextArea
                      placeholder="可输入流程备注；当前可使用上方快捷入口处理流程。"
                      autoSize={{ minRows: 3, maxRows: 5 }}
                    />
                    <div className="assistant-actions">
                      <Text type="secondary">自然语言 Agent 问答当前仅记录备注，不触发自动执行。</Text>
                      <Button
                        type="primary"
                        icon={<SendOutlined />}
                        onClick={() => appendLog("记录自然语言请求；当前仅用于流程备注，不触发自动执行")}
                      >
                        发送
                      </Button>
                    </div>
                  </div>
                </>
              )}
            </aside>
          </Layout>
  );
}
