import type { BidAppController } from "../../../features/bid/useBidAppController";

export function QualificationTab({ app }: { app: BidAppController }) {
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
                      <div className="workspace-panel qualification-panel">
                        <div className="qualification-summary">
                          <div>
                            <Text strong>参标资格预评估</Text>
                            <p>基于资格类矩阵项和企业资料库执行轻量规则判断，结论需人工确认。</p>
                          </div>
                          <Space wrap>
                            <Tag color="green">
                              满足 {qualificationEvaluations.filter((item) => item.evaluation_status === "satisfied").length}
                            </Tag>
                            <Tag color="red">
                              阻断 {blockingQualificationEvaluations.length}
                            </Tag>
                            <Tag color="gold">
                              待确认 {qualificationEvaluations.filter((item) => item.evaluation_status === "pending_confirm").length}
                            </Tag>
                          </Space>
                        </div>
                        <div className="decision-card">
                          {qualificationDecision ? (
                            <>
                              <div className="decision-head">
                                <Space wrap>
                                  <Tag color={decisionColors[qualificationDecision.recommendation]}>
                                    {decisionLabels[qualificationDecision.recommendation] ??
                                      qualificationDecision.recommendation}
                                  </Tag>
                                  <Tag color={qualificationDecision.status === "confirmed" ? "green" : "gold"}>
                                    {qualificationDecision.status === "confirmed" ? "已确认" : "待确认"}
                                  </Tag>
                                  <Text type="secondary">
                                    满足 {qualificationDecision.satisfied_count} / 缺材料{" "}
                                    {qualificationDecision.missing_count} / 阻断 {qualificationDecision.blocking_count}
                                  </Text>
                                </Space>
                                <Button
                                  size="small"
                                  type="primary"
                                  disabled={qualificationDecision.status === "confirmed"}
                                  onClick={handleConfirmQualificationDecision}
                                >
                                  确认建议
                                </Button>
                              </div>
                              <p>{qualificationDecision.summary}</p>
                              {qualificationDecision.status === "confirmed" && qualificationDecision.recommendation === "no_go" && (
                                <Alert
                                  type="error"
                                  showIcon
                                  message="当前结论为不建议参标"
                                  description="如仍需生成商务草稿，请先在草稿入口填写风险接受说明；建议优先回到矩阵和证据项处理阻断。"
                                />
                              )}
                            </>
                          ) : (
                            <Alert
                              type="info"
                              showIcon
                              message="尚未生成参标建议"
                              description="点「生成参标建议」即可一步得出 Go/No-Go 结论，并创建确认审批任务。"
                            />
                          )}
                        </div>
                        {blockingQualificationEvaluations.length > 0 && (
                          <Alert
                            className="qualification-blocker-alert"
                            type="error"
                            showIcon
                            message={`当前存在 ${blockingQualificationEvaluations.length} 个资格阻断项`}
                            description={
                              <Space direction="vertical" size={8} style={{ width: "100%" }}>
                                <Text>
                                  {missingQualificationEvaluations.length
                                    ? `先处理 ${missingQualificationEvaluations.length} 项缺资料/未匹配企业资料；`
                                    : ""}
                                  {notSatisfiedQualificationEvaluations.length
                                    ? `再复核 ${notSatisfiedQualificationEvaluations.length} 项不满足规则；`
                                    : ""}
                                  处理后重新运行资格预评估，并重新生成/确认参标建议。
                                </Text>
                                <Space wrap>
                                  {missingQualificationEvaluations.length > 0 && (
                                    <Button size="small" type="primary" onClick={openQualificationEvidenceWork}>
                                      去补资料
                                    </Button>
                                  )}
                                  <Button size="small" onClick={() => activateWorkflowStep("review")}>
                                    回到矩阵审阅
                                  </Button>
                                  <Button size="small" loading={evaluatingQualification} onClick={handleRunQualificationEvaluation}>
                                    重新评估
                                  </Button>
                                </Space>
                              </Space>
                            }
                          />
                        )}
                        <div className="qualification-next-step">
                          {!qualificationEvaluations.length ? (
                            <>
                              <div>
                                <Text strong>下一步：生成参标建议</Text>
                                <p>直接汇总为 Go/No-Go 参标建议，并创建资格确认审批任务；系统会自动先做一次资格预评估。</p>
                              </div>
                              <Button
                                type="primary"
                                icon={<SafetyCertificateOutlined />}
                                loading={generatingDecision}
                                onClick={handleGenerateQualificationDecision}
                              >
                                生成参标建议
                              </Button>
                            </>
                          ) : !qualificationDecision ? (
                            <>
                              <div>
                                <Text strong>下一步：生成参标建议</Text>
                                <p>评估表已有结果，继续汇总为参标建议，并创建资格确认审批任务。</p>
                              </div>
                              <Button
                                type="primary"
                                icon={<SafetyCertificateOutlined />}
                                loading={generatingDecision}
                                onClick={handleGenerateQualificationDecision}
                              >
                                生成参标建议
                              </Button>
                            </>
                          ) : qualificationDecision.status !== "confirmed" ? (
                            <>
                              <div>
                                <Text strong>下一步：确认参标建议</Text>
                                <p>确认后即可把该结论作为商务标生成前的资格上下文。</p>
                              </div>
                              <Button type="primary" onClick={handleConfirmQualificationDecision}>
                                确认建议
                              </Button>
                            </>
                          ) : (
                            <>
                              <div>
                                <Text strong>下一步：生成商务标草稿</Text>
                                <p>资格结论已确认，可以进入商务草稿生成，把评估结果传给最终产出。</p>
                              </div>
                              <Button
                                type="primary"
                                icon={<SendOutlined />}
                                onClick={() => {
                                  setActiveTab("chapter");
                                  setWorkspaceNode("chapter");
                                }}
                              >
                                去商务草稿
                              </Button>
                            </>
                          )}
                        </div>
                        <div className="qualification-table-scroll">
                          <Table
                            size="middle"
                            rowKey="id"
                            pagination={LARGE_TABLE_PAGINATION}
                            loading={evaluatingQualification}
                            scroll={{ x: 1580 }}
                            dataSource={qualificationEvaluations}
                            locale={{
                              emptyText: (
                                <Empty
                                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                                  description="尚未运行资格预评估"
                                />
                              )
                            }}
                            columns={[
                              {
                                title: "资格要求",
                                dataIndex: "requirement_text",
                                width: 340,
                                render: (value) => (
                                  <Tooltip title={value}>
                                    <span className="clamped-cell">{value}</span>
                                  </Tooltip>
                                )
                              },
                              {
                                title: "类型",
                                dataIndex: "requirement_type",
                                width: 120,
                                render: (value) => <Tag>{qualificationTypeLabels[value] ?? value}</Tag>
                              },
                              {
                                title: "评估结果",
                                dataIndex: "evaluation_status",
                                width: 120,
                                render: (value) => (
                                  <Tag color={statusColor(value)}>{qualificationStatusLabels[value] ?? value}</Tag>
                                )
                              },
                              {
                                title: "风险",
                                dataIndex: "risk_level",
                                width: 90,
                                render: (value) => <Tag color={riskColor(value)}>{riskLabels[value] ?? value}</Tag>
                              },
                              {
                                title: "匹配资料",
                                dataIndex: "matched_material_name",
                                width: 220,
                                render: (value, record) => value || record.missing_materials?.join("、") || "需人工确认"
                              },
                              {
                                title: "规则",
                                dataIndex: "matched_rule_code",
                                width: 190,
                                render: (value, record) => (
                                  <Space direction="vertical" size={0}>
                                    <Text>{value}</Text>
                                    <Text type="secondary">v{record.rule_version}</Text>
                                  </Space>
                                )
                              },
                              {
                                title: "判断说明",
                                dataIndex: "reason",
                                width: 340,
                                render: (value) => (
                                  <Tooltip title={value}>
                                    <span className="clamped-cell">{value}</span>
                                  </Tooltip>
                                )
                              },
                              {
                                title: "确认",
                                dataIndex: "confirmed_at",
                                width: 160,
                                fixed: "right",
                                render: (value, record) =>
                                  value ? (
                                    <Tag color="green">已确认</Tag>
                                  ) : (
                                    <Button size="small" onClick={() => handleConfirmQualificationEvaluation(record)}>
                                      人工确认
                                    </Button>
                                  )
                              }
                            ]}
                          />
                        </div>
                      </div>
                    );
}
