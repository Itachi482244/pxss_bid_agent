import type { BidAppController, MatrixReviewFilter } from "../../../features/bid/useBidAppController";

export function ReviewTab({ app }: { app: BidAppController }) {
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
                      <div className="workspace-panel matrix-review-panel">
                        <div className="matrix-review-header">
                          <div>
                            <Text strong>原文 / 矩阵对照审阅</Text>
                            <p>按解析 chunk 定位来源，支持人工划选补漏、重复关联、级联确认和相似片段差异核对。</p>
                          </div>
                          <Space wrap>
                            <Tag color="green">
                              已确认 {reviewProgress.confirmed}/{reviewProgress.total}
                            </Tag>
                            <Tag color={reviewProgress.highTotal === reviewProgress.highConfirmed ? "green" : "red"}>
                              高风险 {reviewProgress.highConfirmed}/{reviewProgress.highTotal}
                            </Tag>
                            <Tag color={reviewUncoveredChunks.length ? "gold" : "green"}>
                              疑似未覆盖 {reviewUncoveredChunks.length}
                            </Tag>
                            <Tag color={reviewDuplicateGroups.length ? "blue" : "default"}>
                              关联组 {reviewDuplicateGroups.length}
                            </Tag>
                            <Select<MatrixReviewFilter>
                              value={matrixReviewFilter}
                              onChange={(value) => {
                                setMatrixReviewFilter(value);
                                setReviewQueuePage(1);
                              }}
                              className="toolbar-select"
                              options={[
                                { value: "all", label: "全部条目" },
                                { value: "unconfirmed", label: "仅未确认" },
                                { value: "high", label: "高风险" },
                                { value: "mandatory", label: "强制项" },
                                { value: "missing_evidence", label: "缺证据" }
                              ]}
                            />
                            <Button
                              icon={<HighlightOutlined />}
                              type={sourceCreateMode ? "primary" : "default"}
                              onClick={() => setSourceCreateMode((value) => !value)}
                            >
                              从原文新增
                            </Button>
                          </Space>
                        </div>
                        {sourceCreateMode && (
                          <Alert
                            type="info"
                            showIcon
                            message="请在左侧原文中划选需要补入矩阵的文字"
                            description="划选后会打开新增条目弹窗，系统保存 chunk 来源并提示其他相似片段。"
                          />
                        )}
                        <Progress
                          percent={reviewProgress.total ? Math.round((reviewProgress.confirmed / reviewProgress.total) * 100) : 0}
                          showInfo={false}
                          strokeColor="#16a34a"
                        />
                        {matrixRows.length === 0 ? (
                          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无矩阵项；请先生成合规矩阵" />
                        ) : (
                          <div className="matrix-review-layout">
                            <div className="review-source-pane" ref={reviewSourcePaneRef}>
                              <div className="review-pane-title">
                                <Text strong>招标文件原文</Text>
                                <Space size={6} wrap>
                                  <Tag
                                    color={
                                      reviewOpenXmlDocument?.mode === "word_xml"
                                        ? "blue"
                                        : reviewOpenXmlDocument?.mode === "pdf_layout"
                                          ? "cyan"
                                          : "gold"
                                    }
                                  >
                                    {reviewOpenXmlDocument?.mode === "word_xml"
                                      ? "Word 原文"
                                      : reviewOpenXmlDocument?.mode === "pdf_layout"
                                        ? "PDF 原文"
                                        : "解析文本"}
                                  </Tag>
                                  <Tag>
                                    {reviewOpenXmlDocument?.version_label ??
                                      reviewDocument?.current_version?.version_label ??
                                      "当前解析版本"}
                                  </Tag>
                                </Space>
                              </div>
                              <Spin spinning={loadingReviewChunks}>
                                {reviewOpenXmlDocument?.blocks.length ? (
                                  <div
                                    className={`word-review-document ${
                                      reviewOpenXmlDocument.mode === "word_xml"
                                        ? "word-mode"
                                        : reviewOpenXmlDocument.mode === "pdf_layout"
                                          ? "pdf-mode"
                                          : "fallback-mode"
                                    }`}
                                    style={{
                                      paddingTop: reviewOpenXmlDocument.page_margins?.top
                                        ? `${Math.min(reviewOpenXmlDocument.page_margins.top, 72)}pt`
                                        : undefined,
                                      paddingRight: reviewOpenXmlDocument.page_margins?.right
                                        ? `${Math.min(reviewOpenXmlDocument.page_margins.right, 72)}pt`
                                        : undefined,
                                      paddingBottom: reviewOpenXmlDocument.page_margins?.bottom
                                        ? `${Math.min(reviewOpenXmlDocument.page_margins.bottom, 72)}pt`
                                        : undefined,
                                      paddingLeft: reviewOpenXmlDocument.page_margins?.left
                                        ? `${Math.min(reviewOpenXmlDocument.page_margins.left, 72)}pt`
                                        : undefined
                                    }}
                                  >
                                    {reviewOpenXmlDocument.reason && (
                                      <Alert type="warning" showIcon message={reviewOpenXmlDocument.reason} className="review-fallback-alert" />
                                    )}
                                    {reviewOpenXmlDocument.headers.map((header, index) => (
                                      <div className="word-review-header-text" key={`header-${index}`}>
                                        {header}
                                      </div>
                                    ))}
                                    {(() => {
                                      let lastPdfPageNo: number | null = null;
                                      return reviewOpenXmlDocument.blocks.map((block) => {
                                      const highlights = block.chunk_id ? reviewHighlightByChunkId.get(block.chunk_id) ?? [] : [];
                                      const chunk = blockToReviewChunk(block);
                                      const uncovered = block.chunk_id ? uncoveredChunkMap.get(block.chunk_id) : undefined;
                                      const blockActive = highlights.some((highlight) => highlight.item_id === activeReviewItemId);
                                      const blockLocating = highlights.some((highlight) => highlight.item_id === locatingReviewItemId);
                                      const showPdfPage =
                                        reviewOpenXmlDocument.mode === "pdf_layout" &&
                                        block.page_no != null &&
                                        block.page_no !== lastPdfPageNo;
                                      if (block.page_no != null) lastPdfPageNo = block.page_no;
                                      const pageDivider = showPdfPage ? (
                                        <div className="pdf-review-page-break">第 {block.page_no} 页</div>
                                      ) : null;
                                      if (block.type === "table") {
                                        return (
                                          <Fragment key={block.id}>
                                            {pageDivider}
                                          <div
                                            id={block.chunk_id ? `review-block-${block.chunk_id}` : block.id}
                                            className={`word-review-block word-review-table-block ${blockActive ? "active" : ""} ${
                                              blockLocating ? "locating" : ""
                                            }`}
                                            style={reviewBlockCss(block)}
                                            onMouseUp={(event) => handleReviewBlockMouseUp(event, block)}
                                            onClick={() => block.chunk_id && focusReviewChunk(block.chunk_id)}
                                          >
                                            <table className="word-review-table">
                                              <tbody>
                                                {block.rows.map((row, rowIndex) => (
                                                  <tr key={`${block.id}-row-${rowIndex}`}>
                                                    {row.cells.map((cell, cellIndex) => (
                                                      <td key={`${block.id}-cell-${rowIndex}-${cellIndex}`}>
                                                        {cell.paragraphs.map((paragraph, paragraphIndex) => (
                                                          <p
                                                            key={`${block.id}-cell-p-${rowIndex}-${cellIndex}-${paragraphIndex}`}
                                                            style={paragraphCss(paragraph)}
                                                          >
                                                            {renderReviewParagraph(
                                                              paragraph,
                                                              highlights,
                                                              `${block.id}-cell-${rowIndex}-${cellIndex}-${paragraphIndex}`
                                                            )}
                                                          </p>
                                                        ))}
                                                      </td>
                                                    ))}
                                                  </tr>
                                                ))}
                                              </tbody>
                                            </table>
                                            {uncovered && chunk && (
                                              <div className="review-uncovered-hint">
                                                <WarningOutlined /> 疑似未覆盖：{uncovered.reason}
                                                <Button size="small" type="link" onClick={() => openSourceCreateDraft(chunk)}>
                                                  新增条目
                                                </Button>
                                              </div>
                                            )}
                                          </div>
                                          </Fragment>
                                        );
                                      }
                                      return (
                                        <Fragment key={block.id}>
                                          {pageDivider}
                                        <div
                                          id={block.chunk_id ? `review-block-${block.chunk_id}` : block.id}
                                          className={`word-review-block ${block.type === "heading" ? "word-review-heading" : ""} ${
                                            blockActive ? "active" : ""
                                          } ${blockLocating ? "locating" : ""}`}
                                          style={reviewBlockCss(block)}
                                          onMouseUp={(event) => handleReviewBlockMouseUp(event, block)}
                                          onClick={() => block.chunk_id && focusReviewChunk(block.chunk_id)}
                                        >
                                          <p style={paragraphCss(block.paragraph)}>
                                            {block.paragraph
                                              ? renderReviewParagraph(block.paragraph, highlights, block.id)
                                              : renderHighlightedText(block.text, highlights, block.id)}
                                          </p>
                                          {uncovered && chunk && (
                                            <div className="review-uncovered-hint">
                                              <WarningOutlined /> 疑似未覆盖：{uncovered.reason}
                                              <Button size="small" type="link" onClick={() => openSourceCreateDraft(chunk)}>
                                                新增条目
                                              </Button>
                                            </div>
                                          )}
                                        </div>
                                        </Fragment>
                                      );
                                      });
                                    })()}
                                    {reviewOpenXmlDocument.footers.map((footer, index) => (
                                      <div className="word-review-footer-text" key={`footer-${index}`}>
                                        {footer}
                                      </div>
                                    ))}
                                  </div>
                                ) : reviewDisplayChunks.length ? (
                                  <div className="word-review-document fallback-mode">
                                    <Alert
                                      type="warning"
                                      showIcon
                                      message="原文审阅结构暂未返回，已使用矩阵来源原文连续展示。"
                                      className="review-fallback-alert"
                                    />
                                    {reviewDisplayChunks.map((chunk) => {
                                      const highlights = reviewHighlightByChunkId.get(chunk.id) ?? [];
                                      const uncovered = uncoveredChunkMap.get(chunk.id);
                                      const blockActive = highlights.some((highlight) => highlight.item_id === activeReviewItemId);
                                      const blockLocating = highlights.some((highlight) => highlight.item_id === locatingReviewItemId);
                                      return (
                                        <div
                                          key={chunk.id}
                                          id={`review-block-${chunk.id}`}
                                          className={`word-review-block ${blockActive ? "active" : ""} ${blockLocating ? "locating" : ""}`}
                                          onMouseUp={(event) => handleReviewChunkMouseUp(event, chunk)}
                                          onClick={() => focusReviewChunk(chunk.id)}
                                        >
                                          {chunk.heading_path && <div className="word-review-fallback-heading">{chunk.heading_path}</div>}
                                          <p>{renderHighlightedText(chunk.content_text, highlights, `fallback-${chunk.id}`)}</p>
                                          {uncovered && (
                                            <div className="review-uncovered-hint">
                                              <WarningOutlined /> 疑似未覆盖：{uncovered.reason}
                                              <Button size="small" type="link" onClick={() => openSourceCreateDraft(chunk)}>
                                                新增条目
                                              </Button>
                                            </div>
                                          )}
                                        </div>
                                      );
                                    })}
                                  </div>
                                ) : (
                                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无可展示的原文内容" />
                                )}
                              </Spin>
                            </div>
                            <div className="review-item-pane" ref={reviewItemPaneRef}>
                              <div className="review-pane-title">
                                <Text strong>合规条目队列</Text>
                                <Space size={6}>
                                  <Badge count={matrixReviewRows.length} showZero color="#2563eb" />
                                  {matrixReviewFilter !== "all" && (
                                    <Text type="secondary">共 {matrixRows.length} 条</Text>
                                  )}
                                </Space>
                              </div>
                              {matrixReviewRows.length > reviewQueuePageSize && (
                                <Pagination
                                  className="review-queue-pagination"
                                  size="small"
                                  current={reviewQueuePage}
                                  pageSize={reviewQueuePageSize}
                                  total={matrixReviewRows.length}
                                  showSizeChanger
                                  pageSizeOptions={["25", "50", "100"]}
                                  showTotal={(total) => `共 ${total} 条`}
                                  onChange={(page, pageSize) => {
                                    setReviewQueuePage(page);
                                    setReviewQueuePageSize(pageSize);
                                  }}
                                />
                              )}
                              {matrixReviewRows.length ? (
                                pagedMatrixReviewRows.map((row) => {
                                  const isActive = row.key === activeReviewItemId;
                                  const duplicateGroups = duplicateGroupByItemId.get(row.key) ?? [];
                                  const reviewDetail = (
                                    <Space direction="vertical" size={8} className="review-popover">
                                      <Text strong>{row.requirement}</Text>
                                      {row.raw.source_quote && <Text type="secondary">来源摘录：{row.raw.source_quote}</Text>}
                                      {row.raw.classification_reason && <Text type="secondary">分类理由：{row.raw.classification_reason}</Text>}
                                      {row.raw.split_reason && <Text type="secondary">拆分理由：{row.raw.split_reason}</Text>}
                                      {row.raw.review_hint && <Alert type="warning" showIcon message={row.raw.review_hint} />}
                                      {duplicateGroups.length > 0 && (
                                        <Space wrap>
                                          {duplicateGroups.map((group) => (
                                            <Tag key={group.group_key} color={group.group_type === "confirmed" ? "green" : "blue"}>
                                              关联 x{group.item_count} · {group.group_type === "confirmed" ? "已确认" : "疑似"}
                                            </Tag>
                                          ))}
                                        </Space>
                                      )}
                                    </Space>
                                  );
                                  return (
                                    <div
                                      key={row.key}
                                      data-review-item-id={row.key}
                                      className={`review-item-card review-risk-${row.riskCode} ${row.statusCode === "confirmed" ? "confirmed" : ""} ${isActive ? "active" : ""}`}
                                      onClick={() => focusReviewRow(row)}
                                    >
                                      <div className="review-item-top">
                                        <Space size={6} wrap>
                                          <Tag color={riskColor(row.riskCode)}>{row.risk}</Tag>
                                          <Tag>{row.chapter}</Tag>
                                          {row.mandatory && <Tag color="red">强制</Tag>}
                                          {row.raw.needs_human_review && <Tag color="orange">需复核</Tag>}
                                          {row.enterpriseEvidenceCount === 0 && <Tag color="gold">缺证据</Tag>}
                                          {(row.raw.duplicate_group_count > 1 || duplicateGroups.length > 0) && (
                                            <Tag color={row.raw.duplicate_group_id ? "green" : "blue"} icon={<BranchesOutlined />}>
                                              关联 x{Math.max(row.raw.duplicate_group_count, duplicateGroups[0]?.item_count ?? 0)}
                                            </Tag>
                                          )}
                                        </Space>
                                        <Tag color={statusColor(row.statusCode)}>{row.status}</Tag>
                                      </div>
                                      <Popover content={reviewDetail} trigger="hover" mouseEnterDelay={0.15}>
                                        <Text strong className="review-item-summary">
                                          {truncateText(row.requirement, 44)}
                                        </Text>
                                      </Popover>
                                      <Text type="secondary" className="review-item-reason">
                                        {row.raw.review_hint ||
                                          row.raw.classification_reason ||
                                          explanationText(row.raw.rule_explanation, "risk_reason")}
                                      </Text>
                                      <Space size={6} wrap>
                                        <Button size="small" onClick={(event) => { event.stopPropagation(); focusReviewRow(row); }}>
                                          定位原文
                                        </Button>
                                        <Button size="small" onClick={(event) => { event.stopPropagation(); setSourceDrawer(row); }}>
                                          来源详情
                                        </Button>
                                        <Button
                                          size="small"
                                          onClick={(event) => {
                                            event.stopPropagation();
                                            openEditDraft(row);
                                          }}
                                        >
                                          编辑
                                        </Button>
                                        <Button
                                          size="small"
                                          onClick={(event) => {
                                            event.stopPropagation();
                                            void openSimilarCandidates(row);
                                          }}
                                        >
                                          查找相似
                                        </Button>
                                        <Button
                                          size="small"
                                          onClick={(event) => {
                                            event.stopPropagation();
                                            void handleConfirmDuplicateGroup(row);
                                          }}
                                        >
                                          确认关联
                                        </Button>
                                        {row.raw.duplicate_group_id && (
                                          <>
                                            <Button
                                              size="small"
                                              onClick={(event) => {
                                                event.stopPropagation();
                                                void handleUnlinkDuplicateGroup(row);
                                              }}
                                            >
                                              解除联动
                                            </Button>
                                            <Button
                                              size="small"
                                              onClick={(event) => {
                                                event.stopPropagation();
                                                void handleSplitDuplicateGroup(row);
                                              }}
                                            >
                                              拆分
                                            </Button>
                                          </>
                                        )}
                                        <Button
                                          size="small"
                                          type="primary"
                                          disabled={row.statusCode === "confirmed"}
                                          onClick={(event) => {
                                            event.stopPropagation();
                                            handleConfirmItem(row);
                                          }}
                                        >
                                          确认
                                        </Button>
                                      </Space>
                                    </div>
                                  );
                                })
                              ) : (
                                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前筛选条件下暂无条目" />
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    );
}
