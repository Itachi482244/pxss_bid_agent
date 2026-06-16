import type { BidAppController, MatrixRow } from "../../../features/bid/useBidAppController";

type DraftBlockFilter = BidAppController["draftBlockFilter"];

export function ChapterTab({ app }: { app: BidAppController }) {
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
    exportingTenderFormatMode,
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
    handleExportTenderFormatDocx,
    handleExtractSemanticSection,
    handleGenerateMatrix,
    handleGenerateQualificationDecision,
    handleHistoryMaterialUpload,
    handleImportDirectoryFromTender,
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

  return (
                      <div className="workspace-panel editor-panel">
                        <div className="section-outline">
                          <div className="outline-title">
                            <Text strong>章节大纲</Text>
                            <Tag>{businessDraftChapters.length}</Tag>
                          </div>
                          {businessDraftChapters.map((chapter, index) => (
                            <button
                              key={chapter.id}
                              className={chapter.id === selectedDraftChapterId ? "outline-row active" : "outline-row"}
                              onClick={() => setSelectedDraftChapterId(chapter.id)}
                            >
                              {index + 1}. {chapter.title}
                            </button>
                          ))}
                          {!businessDraftChapters.length && (
                            <Empty
                              image={Empty.PRESENTED_IMAGE_SIMPLE}
                              description={
                                mvp13DraftWorkflowAvailable
                                  ? "尚未生成草稿"
                                  : "当前先确认投标素材包；章节草稿会基于已确认素材包生成"
                              }
                            />
                          )}
                        </div>
                        <div className="draft-editor">
                          <div className="context-pack-strip">
                            <div className="context-pack-main">
                              <Space wrap>
                                <Text strong>投标素材包</Text>
                                <Tag color={preflightColor(contextPackSource?.readiness_status ?? "warn")}>
                                  {contextPackSource ? preflightLabel(contextPackSource.readiness_status) : "未生成"}
                                </Tag>
                                <Tag color="blue">{contextPackOutlineSections.length} 章计划</Tag>
                                <Tag color={contextPackReadinessSummary.missingEvidence ? "red" : "green"}>
                                  缺证据项 {contextPackReadinessSummary.missingEvidence}
                                </Tag>
                                <Tag color={contextPackReadinessSummary.missingFacts ? "gold" : "green"}>
                                  待补事实 {contextPackReadinessSummary.missingFacts}
                                </Tag>
                                {coverageReview && (
                                  <Tag color={preflightColor(coverageReview.status)}>
                                    覆盖检查{preflightLabel(coverageReview.status)}
                                  </Tag>
                                )}
                                {coverageReview && (
                                  <Tag color={summaryNumber(coverageReview.summary_json, "quality_score") >= 85 ? "green" : "gold"}>
                                    质量分 {summaryNumber(coverageReview.summary_json, "quality_score")}
                                  </Tag>
                                )}
                                {contextPackQualificationGate.status !== "pass" && (
                                  <Tag color={preflightColor(contextPackQualificationGate.status)}>
                                    {contextPackQualificationGate.message}
                                  </Tag>
                                )}
                              </Space>
                              {contextPackChecks.length > 0 ? (
                                <div className="context-pack-checks">
                                  {contextPackChecks.slice(0, 3).map((check, index) => (
                                    <Tag
                                      key={`${String(check.code ?? index)}-${index}`}
                                      color={preflightColor(String(check.status ?? "warn"))}
                                    >
                                      {String(check.summary ?? check.code ?? "待处理")}
                                    </Tag>
                                  ))}
                                </div>
                              ) : (
                                <Text type="secondary">生成前会固定项目字段、矩阵项、证据、缺项和章节范围。</Text>
                              )}
                              {blockingContextPackChecks.length > 0 && (
                                <div className="context-pack-blockers">
                                  {blockingContextPackChecks.slice(0, 4).map((check, index) => {
                                    return (
                                      <div className="context-pack-blocker" key={`${String(check.code ?? index)}-blocker`}>
                                        <Tag color={preflightColor(String(check.status ?? "warn"))}>
                                          {String(check.summary ?? check.code ?? "待处理")}
                                        </Tag>
                                        <Text type="secondary">{String(check.action ?? "按提示处理后重新确认投标素材包。")}</Text>
                                        <Button size="small" onClick={() => handleContextPackCheckAction(check)}>
                                          {contextPackCheckActionText(check)}
                                        </Button>
                                      </div>
                                    );
                                  })}
                                </div>
                              )}
                              {businessDraftGenerationTaskId && (
                                <div className="context-pack-task-progress">
                                  <Space wrap>
                                    <Text strong>草稿生成任务</Text>
                                    <Tag color={businessDraftGenerationActive ? "blue" : businessDraftGenerationTask?.status === "succeeded" ? "green" : "red"}>
                                      {businessDraftGenerationStatusText}
                                    </Tag>
                                    {businessDraftGenerationActive && (
                                      <Text type="secondary">
                                        {[
                                          taskProgressMessage(businessDraftGenerationTask, "正在生成章节草稿…", "已生成"),
                                          asyncTaskEtaText(businessDraftGenerationTask, businessDraftGenerationTaskId)
                                        ]
                                          .filter(Boolean)
                                          .join(" · ")}
                                      </Text>
                                    )}
                                    {businessDraftGenerationTask?.error_message && (
                                      <Text type="danger">{businessDraftGenerationTask.error_message}</Text>
                                    )}
                                  </Space>
                                  <Progress percent={businessDraftGenerationProgress} size="small" />
                                </div>
                              )}
                            </div>
                            <Space wrap>
                              <Button loading={loadingContextPack} onClick={handlePreviewContextPack}>
                                预览
                              </Button>
                              <Button loading={loadingContextPack} onClick={handleOpenOutlineEditor}>
                                编辑目录
                              </Button>
                              <Tooltip title="解析招标文件的「投标文件格式 / 响应文件组成」章节，推导建议目录并打开编辑器供确认">
                                <Button
                                  loading={loadingContextPack}
                                  onClick={handleImportDirectoryFromTender}
                                >
                                  从招标文件导入目录
                                </Button>
                              </Tooltip>
                              {editedOutline && (
                                <Tag color="purple" closable onClose={handleResetOutline}>
                                  目录已编辑 {editedOutline.length} 章
                                </Tag>
                              )}
                              <Tooltip
                                title={
                                  activeContextPack
                                    ? "编辑生成指令将触发快速重新生成（沿用已核实的事实）"
                                    : "生成指令只影响表达与侧重，随预览/确认投标素材包应用"
                                }
                              >
                                <Button
                                  loading={loadingContextPack}
                                  onClick={() => setDirectiveEditorOpen(true)}
                                >
                                  编辑生成指令
                                </Button>
                              </Tooltip>
                              {editedDirectives && editedDirectives.length > 0 && (
                                <Tag color="geekblue" closable onClose={handleResetDirectives}>
                                  指令已暂存 {editedDirectives.length} 条
                                </Tag>
                              )}
                              {!editedDirectives && activePackDirectiveCount > 0 && (
                                <Tag color="geekblue">指令 {activePackDirectiveCount} 条</Tag>
                              )}
                              <Tooltip title={canConfirmContextPack ? "" : contextPackConfirmDisabledReason}>
                                <span>
                                  <Button
                                    loading={loadingContextPack}
                                    disabled={!canConfirmContextPack}
                                    onClick={handleCreateContextPack}
                                  >
                                    确认投标素材包
                                  </Button>
                                </span>
                              </Tooltip>
                              <Tooltip
                                title={
                                  canGenerateContextPackDraft
                                    ? ""
                                    : activeContextPack
                                      ? contextPackDraftGenerationTip
                                      : "先确认投标素材包。"
                                }
                              >
                                <span>
                                  <Button
                                    type="primary"
                                    icon={<RobotOutlined />}
                                    loading={loadingBusinessDraft || businessDraftGenerationActive}
                                    disabled={!canGenerateContextPackDraft || businessDraftGenerationActive}
                                    onClick={confirmContextPackDraftGeneration}
                                  >
                                    草稿生成
                                  </Button>
                                </span>
                              </Tooltip>
                              <Tooltip title="生成结构化草稿后执行覆盖检查。">
                                <span>
                                  <Button
                                    loading={loadingContextPack}
                                    disabled
                                    onClick={handleRunContextPackCoverageReview}
                                  >
                                    覆盖检查
                                  </Button>
                                </span>
                              </Tooltip>
                            </Space>
                          </div>
                          <div className="draft-toolbar">
                            <Space wrap>
                              <Button
                                type="primary"
                                icon={<RobotOutlined />}
                                loading={loadingBusinessDraft || businessDraftGenerationActive}
                                disabled={businessDraftGenerationActive || !mvp13DraftWorkflowAvailable || Boolean(activeContextPack)}
                                onClick={() =>
                                  activeContextPack
                                    ? confirmContextPackDraftGeneration()
                                    : qualificationDecisionConfirmed && qualificationDecisionIsNoGo && !businessDraftChapters.length
                                    ? confirmNoGoRiskAcceptance(confirmDraftGeneration)
                                    : confirmDraftGeneration()
                                }
                              >
                                {!mvp13DraftWorkflowAvailable
                                  ? "草稿生成"
                                  : activeContextPack
                                  ? "草稿生成"
                                  : qualificationDecisionConfirmed && qualificationDecisionIsNoGo && !businessDraftChapters.length
                                  ? "风险接受后生成草稿"
                                  : "生成商务标草稿"}
                              </Button>
                              <Button
                                icon={<SafetyCertificateOutlined />}
                                disabled={!mvp13DraftWorkflowAvailable || !selectedDraftChapter}
                                loading={savingBusinessDraft}
                                onClick={handleRunDraftFactCheck}
                              >
                                事实校验
                              </Button>
                              <Button
                                icon={<DownloadOutlined />}
                                disabled={!mvp13DraftWorkflowAvailable || !businessDraftChapters.length}
                                loading={exportingWord}
                                onClick={handleExportBusinessWord}
                              >
                                导出 Word
                              </Button>
                              <Button
                                icon={<DownloadOutlined />}
                                loading={exportingTenderFormatMode === "review"}
                                onClick={() => handleExportTenderFormatDocx("review")}
                              >
                                格式标审阅版
                              </Button>
                              <Button
                                type="primary"
                                icon={<DownloadOutlined />}
                                loading={exportingTenderFormatMode === "submission"}
                                onClick={() => handleExportTenderFormatDocx("submission")}
                              >
                                格式标正式版
                              </Button>
                            </Space>
                            {selectedDraftChapter && (
                              <Space wrap>
                                <Tag color={chapterStatusLabels[selectedDraftChapter.status] === "已确认" ? "green" : "gold"}>
                                  {chapterStatusLabels[selectedDraftChapter.status] ?? selectedDraftChapter.status}
                                </Tag>
                                <Tag color={selectedDraftChapter.fact_check_status === "verified" ? "green" : "red"}>
                                  {selectedDraftChapter.fact_check_status === "verified" ? "事实已核验" : "存在待核验事实"}
                                </Tag>
                                <Text type="secondary">v{selectedDraftChapter.version_no}</Text>
                              </Space>
                            )}
                          </div>
                          {selectedDraftChapter ? (
                            <>
                              <div className="draft-meta">
                                <Text strong>{selectedDraftChapter.title}</Text>
                                <Space wrap>
                                  <Tag color="blue">
                                    已绑定证据 {summaryNumber(selectedDraftChapter.evidence_summary_json, "bound_evidence_count")}
                                  </Tag>
                                  <Tag color={summaryNumber(selectedDraftChapter.evidence_summary_json, "unbound_item_count") ? "red" : "green"}>
                                    待补证 {summaryNumber(selectedDraftChapter.evidence_summary_json, "unbound_item_count")}
                                  </Tag>
                                </Space>
                              </div>
                              {selectedDraftChapter.fact_checks.some((check) => check.check_status !== "verified") && (
                                <Alert
                                  type="warning"
                                  showIcon
                                  className="draft-fact-alert"
                                  message="草稿存在待确认事实"
                                  description={`无法验证 ${selectedDraftChapter.fact_checks.filter((check) => check.check_status === "unverified").length} 项，风险提示 ${selectedDraftChapter.fact_checks.filter((check) => check.check_status === "warning").length} 项。导出前请人工复核。`}
                                />
                              )}
                              <TextArea
                                value={draftEditorValue}
                                readOnly={!mvp13DraftWorkflowAvailable}
                                onChange={(event) => {
                                  if (mvp13DraftWorkflowAvailable) setDraftEditorValue(event.target.value);
                                }}
                                autoSize={{ minRows: 12, maxRows: 18 }}
                              />
                              <div className="draft-action-row">
                                <Button
                                  type="primary"
                                  loading={savingBusinessDraft}
                                  disabled={!mvp13DraftWorkflowAvailable || draftEditorValue === selectedDraftChapter.content_text}
                                  onClick={handleSaveBusinessDraftChapter}
                                >
                                  {mvp13DraftWorkflowAvailable ? "保存修改" : "保存修改"}
                                </Button>
                                <Text type="secondary">
                                  {mvp13DraftWorkflowAvailable
                                    ? "保存会重新校验证书编号、金额、日期等事实，并替换无法验证内容。"
                                    : "当前先确认投标素材包；历史草稿内容仅供查看。"}
                                </Text>
                              </div>
                              {selectedDraftDiff && (
                                <div className="draft-diff-card">
                                  <div className="draft-diff-head">
                                    <Space wrap>
                                      <Text strong>最近修改对比</Text>
                                      <Tag color={selectedDraftDiff.action === "business_draft.block_updated" ? "blue" : "purple"}>
                                        {selectedDraftDiff.action === "business_draft.block_updated" ? "Block" : "章节"}
                                      </Tag>
                                      <Tag color={selectedDraftDiff.delta >= 0 ? "green" : "gold"}>
                                        {selectedDraftDiff.delta >= 0 ? "+" : ""}
                                        {selectedDraftDiff.delta} 字
                                      </Tag>
                                    </Space>
                                    <Text type="secondary">{formatDateTime(selectedDraftDiff.createdAt)}</Text>
                                  </div>
                                  <div className="draft-diff-grid">
                                    <div>
                                      <Text type="secondary">修改前</Text>
                                      <p>{truncateText(selectedDraftDiff.beforeText || "无旧内容", 180)}</p>
                                    </div>
                                    <div>
                                      <Text type="secondary">修改后</Text>
                                      <p>{truncateText(selectedDraftDiff.afterText || "无新内容", 180)}</p>
                                    </div>
                                  </div>
                                  {selectedDraftDiff.reason && (
                                    <Text type="secondary">原因：{selectedDraftDiff.reason}</Text>
                                  )}
                                </div>
                              )}
                              {selectedChapterBlocks.length > 0 && (
                                <div className="draft-block-list">
                                  <div className="draft-block-title">
                                    <Text strong>结构化草稿审阅</Text>
                                    <Tag>{selectedChapterBlocks.length}</Tag>
                                    {chapterMandatoryBlocks.length > 0 && (
                                      <Space wrap>
                                        <Button size="small" onClick={openMandatoryReview}>
                                          逐条查看指定内容（待看{" "}
                                          {chapterMandatoryBlocks.filter((b) => !viewedDraftBlockIds.has(b.id)).length}）
                                        </Button>
                                        <Button
                                          size="small"
                                          type="primary"
                                          loading={savingBusinessDraft}
                                          disabled={!mvp13DraftWorkflowAvailable}
                                          onClick={handleBatchConfirmMandatory}
                                        >
                                          批量确认指定内容
                                        </Button>
                                      </Space>
                                    )}
                                  </div>
                                  <Segmented
                                    size="small"
                                    value={draftBlockFilter}
                                    onChange={(value) => setDraftBlockFilter(value as DraftBlockFilter)}
                                    options={(Object.keys(draftBlockFilterLabels) as DraftBlockFilter[]).map((key) => ({
                                      value: key,
                                      label: `${draftBlockFilterLabels[key]}（${draftBlockFilterCounts[key]}）`
                                    }))}
                                  />
                                  {visibleChapterBlocks.length === 0 ? (
                                    <Empty
                                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                                      description={`「${draftBlockFilterLabels[draftBlockFilter]}」筛选下暂无草稿块`}
                                    />
                                  ) : (
                                    visibleChapterBlocks.map((block) => {
                                    const complianceItemIds = draftBlockLinkIds(block, "compliance_item_ids");
                                    const evidenceBindingIds = draftBlockLinkIds(block, "evidence_binding_ids");
                                    const linkedRows = complianceItemIds
                                      .map((itemId) => matrixRowsById.get(itemId))
                                      .filter((row): row is MatrixRow => Boolean(row));
                                    const isMandatory = block.review_status === "needs_confirm";
                                    const expanded = expandedDraftBlockIds.has(block.id);
                                    const viewed = viewedDraftBlockIds.has(block.id);
                                    return (
                                      <div
                                        className={`draft-block-item ${activeDraftBlockId === block.id ? "active" : ""}`}
                                        data-draft-block-id={block.id}
                                        key={block.id}
                                      >
                                        <div>
                                          <Space wrap>
                                            <Tag color={draftBlockStatusColors[block.review_status] ?? "default"}>
                                              {draftBlockStatusLabels[block.review_status] ?? block.review_status}
                                            </Tag>
                                            {isMandatory && (
                                              <Tag color={viewed ? "green" : "default"}>
                                                {viewed ? "已查看" : "未查看"}
                                              </Tag>
                                            )}
                                            <Button
                                              size="small"
                                              type="link"
                                              style={{ paddingLeft: 0 }}
                                              onClick={() => {
                                                toggleDraftBlockExpanded(block.id);
                                                if (isMandatory) markDraftBlockViewed(block.id);
                                              }}
                                            >
                                              {expanded
                                                ? "收起溯源"
                                                : `溯源（条款 ${complianceItemIds.length} · 证据 ${evidenceBindingIds.length}）`}
                                            </Button>
                                          </Space>
                                          <p>{block.content_text}</p>
                                          {expanded && linkedRows.length > 0 && (
                                            <div className="draft-block-trace">
                                              {linkedRows.slice(0, 4).map((row, index) => (
                                                <Tooltip title={row.requirement} key={`${block.id}-${row.key}`}>
                                                  <Button
                                                    size="small"
                                                    className="draft-block-trace-button"
                                                    onClick={() => locateMatrixRow(row.key)}
                                                  >
                                                    条款 {index + 1}
                                                  </Button>
                                                </Tooltip>
                                              ))}
                                              <Button
                                                size="small"
                                                onClick={() => {
                                                  setSourceDrawer(linkedRows[0]);
                                                }}
                                              >
                                                原文
                                              </Button>
                                              <Button
                                                size="small"
                                                onClick={() => {
                                                  setViewMode("workspace");
                                                  setActiveTab("review");
                                                  setWorkspaceNode("review");
                                                  window.setTimeout(() => focusReviewRow(linkedRows[0]), 100);
                                                }}
                                              >
                                                审阅台
                                              </Button>
                                            </div>
                                          )}
                                        </div>
                                        <Space wrap>
                                          <Button
                                            size="small"
                                            loading={savingBusinessDraft}
                                            disabled={!mvp13DraftWorkflowAvailable}
                                            onClick={() => openEditDraftBlock(block)}
                                          >
                                            {mvp13DraftWorkflowAvailable ? "编辑" : "编辑"}
                                          </Button>
                                          <Button
                                            size="small"
                                            disabled={!mvp13DraftWorkflowAvailable || block.review_status === "approved"}
                                            loading={savingBusinessDraft}
                                            onClick={() =>
                                              handleUpdateDraftBlockStatus(block, "approved", "人工审阅通过该结构化 block")
                                            }
                                          >
                                            通过
                                          </Button>
                                          <Button
                                            size="small"
                                            danger
                                            disabled={block.review_status === "needs_evidence"}
                                            loading={savingBusinessDraft}
                                            onClick={() =>
                                              handleUpdateDraftBlockStatus(block, "needs_evidence", "人工标记该 block 仍需补充证据")
                                            }
                                          >
                                            需补证
                                          </Button>
                                        </Space>
                                      </div>
                                    );
                                  })
                                  )}
                                </div>
                              )}
                              <div className="fact-check-list">
                                <Text strong>事实性校验</Text>
                                {selectedDraftChapter.fact_checks.map((check) => (
                                  <div className="fact-check-item" key={check.id}>
                                    <Tag color={check.check_status === "verified" ? "green" : "red"}>
                                      {factCheckLabels[check.check_status] ?? check.check_status}
                                    </Tag>
                                    <Text>{check.fact_text}</Text>
                                    <Text type="secondary">{check.detail}</Text>
                                  </div>
                                ))}
                              </div>
                            </>
                          ) : (
                            <Empty
                              image={Empty.PRESENTED_IMAGE_SIMPLE}
                              description={
                                mvp13DraftWorkflowAvailable
                                  ? "生成后可在这里编辑商务标章节草稿"
                                  : "将基于已确认投标素材包生成章节草稿"
                              }
                            />
                          )}
                        </div>
                      </div>
                    );
}
