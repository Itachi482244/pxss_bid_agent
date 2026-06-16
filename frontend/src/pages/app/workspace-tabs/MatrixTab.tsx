import type { BidAppController } from "../../../features/bid/useBidAppController";

export function MatrixTab({ app }: { app: BidAppController }) {
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
                      <div className="workspace-panel">
                        <div className="matrix-toolbar">
                          <Space wrap>
                            <Select
                              allowClear
                              placeholder="状态"
                              value={statusFilter}
                              onChange={setStatusFilter}
                              options={Object.entries(statusLabels).map(([value, label]) => ({
                                value,
                                label
                              }))}
                              className="toolbar-select"
                            />
                            <Select
                              allowClear
                              placeholder="责任人"
                              value={ownerFilter}
                              onChange={setOwnerFilter}
                              options={ownerOptions}
                              className="toolbar-select"
                            />
                            <Select
                              allowClear
                              placeholder="风险"
                              value={riskFilter}
                              onChange={setRiskFilter}
                              options={Object.entries(riskLabels).map(([value, label]) => ({ value, label }))}
                              className="toolbar-select"
                            />
                            <Select
                              allowClear
                              placeholder="强制项"
                              value={mandatoryFilter}
                              onChange={setMandatoryFilter}
                              options={[
                                { value: "mandatory", label: "仅强制项" },
                                { value: "normal", label: "非强制项" }
                              ]}
                              className="toolbar-select"
                            />
                            <Switch
                              checked={prioritySortEnabled}
                              onChange={setPrioritySortEnabled}
                              checkedChildren="推荐处理"
                              unCheckedChildren="原顺序"
                            />
                          </Space>
                          <Space wrap>
                            <Button icon={<RobotOutlined />} loading={loadingMatrix} onClick={() => handleGenerateMatrix()}>
                              生成矩阵
                            </Button>
                            <Button icon={<FileSearchOutlined />} disabled={!matrixRows.length} onClick={() => activateWorkflowStep("review")}>
                              矩阵审阅
                            </Button>
                            <Button disabled={!selectedRowKeys.length} onClick={handleBatchConfirm}>
                              批量确认
                            </Button>
                            <Button
                              disabled={!selectedRowKeys.length}
                              onClick={handleBatchAssign}
                            >
                              批量指派
                            </Button>
                            <Tooltip title="导出当前筛选结果的只读快照，用于归档、会议或外部协作；最新状态以平台为准。">
                              <Button icon={<DownloadOutlined />} onClick={confirmExport} loading={exportingExcel}>
                                导出快照
                              </Button>
                            </Tooltip>
                          </Space>
                        </div>
                        {preflightCheck?.matrix_outdated && (
                          <Alert
                            className="matrix-completion-alert"
                            type="error"
                            showIcon
                            message="矩阵已过期，建议基于最新解析版本重新生成"
                            description={`当前最新解析版本：${preflightCheck.latest_document_version_label ?? "未识别"}；矩阵使用版本：${preflightCheck.matrix_version_labels.join("、") || "未生成"}`}
                            action={
                              <Button size="small" type="primary" onClick={() => handleGenerateMatrix()}>
                                重新生成矩阵
                              </Button>
                            }
                          />
                        )}
                        {isMatrixComplete && (
                          <Alert
                            className="matrix-completion-alert"
                            type="success"
                            showIcon
                            message="合规矩阵已完成"
                            description={
                              evidenceRows.length
                                ? `已确认 ${matrixRows.length} 条矩阵项。下一步建议处理 ${evidenceRows.length} 条证据绑定，再运行资格预评估。`
                                : "所有矩阵项已确认且证据已齐备，可以运行资格预评估并生成参标建议。"
                            }
                            action={
                              <Button
                                size="small"
                                type="primary"
                                onClick={() => runWorkflowPrimaryAction(recommendedStep?.key ?? "evidence")}
                              >
                                进入下一步
                              </Button>
                            }
                          />
                        )}
                        <Table
                          size="middle"
                          pagination={LARGE_TABLE_PAGINATION}
                          loading={loadingMatrix}
                          rowSelection={{
                            selectedRowKeys,
                            onChange: setSelectedRowKeys
                          }}
                          rowClassName={(record) => (record.key === highlightedRowKey ? "highlighted-row" : "")}
                          scroll={{ x: 1840 }}
                          dataSource={displayedMatrixRows}
                          locale={{
                            emptyText: (
                              <Empty
                                image={Empty.PRESENTED_IMAGE_SIMPLE}
                                description={
                                  documents.some((document) => isUsableParseStatus(document.current_version?.parse_status))
                                    ? "暂无合规矩阵项；请先点击生成合规矩阵"
                                    : "暂无合规矩阵项；请先完成文件解析"
                                }
                              />
                            )
                          }}
                          columns={[
                            {
                              title: "招标要求",
                              dataIndex: "requirement",
                              width: 360,
                              render: (value: string) => (
                                <Tooltip title={value}>
                                  <span className="clamped-cell">{value}</span>
                                </Tooltip>
                              )
                            },
                            {
                              title: "证据来源",
                              dataIndex: "source",
                              width: 240,
                              render: (value: string, record) => (
                                <Tooltip title={value}>
                                  <Button
                                    type="link"
                                    className="table-link-text"
                                    onClick={(event) => {
                                      event.stopPropagation();
                                      setSourceDrawer(record);
                                    }}
                                  >
                                    {value}
                                  </Button>
                                </Tooltip>
                              )
                            },
                            {
                              title: "章节",
                              dataIndex: "chapter",
                              width: 120,
                              sorter: (a, b) => a.chapter.localeCompare(b.chapter)
                            },
                            {
                              title: "推荐处理",
                              dataIndex: ["raw", "priority_label"],
                              width: 150,
                              sorter: (a, b) => a.raw.priority_rank - b.raw.priority_rank,
                              render: (_: unknown, record) => (
                                <Tooltip title={record.raw.priority_reason}>
                                  <Tag color={record.raw.priority_rank <= 1 ? "red" : record.raw.priority_rank === 2 ? "blue" : "default"}>
                                    {record.raw.priority_label}
                                  </Tag>
                                </Tooltip>
                              )
                            },
                            {
                              title: "强制项",
                              dataIndex: "mandatory",
                              width: 100,
                              render: (value: boolean, record) => (
                                <Tooltip title={explanationText(record.raw.rule_explanation, "batch_confirm_reason")}>
                                  {value ? <Tag color="red">是</Tag> : <Tag>否</Tag>}
                                </Tooltip>
                              )
                            },
                            {
                              title: "责任人",
                              dataIndex: "owner",
                              width: 120,
                              sorter: (a, b) => a.owner.localeCompare(b.owner)
                            },
                            {
                              title: "状态",
                              dataIndex: "status",
                              width: 110,
                              sorter: (a, b) => a.status.localeCompare(b.status),
                              render: (value: string) => <Tag color={statusColor(value)}>{value}</Tag>
                            },
                            {
                              title: "风险",
                              dataIndex: "risk",
                              width: 90,
                              sorter: (a, b) => {
                                const order: Record<string, number> = { 高: 3, 中: 2, 低: 1 };
                                return order[a.risk] - order[b.risk];
                              },
                              render: (value: string, record) => (
                                <Tooltip title={explanationText(record.raw.rule_explanation, "risk_reason")}>
                                  <Tag color={riskColor(value)}>{value}</Tag>
                                </Tooltip>
                              )
                            },
                            {
                              title: "响应证据",
                              dataIndex: "evidence",
                              width: 360,
                              fixed: "right",
                              render: (value: string, record) => (
                                <Space direction="vertical" size={6} className="evidence-cell">
                                  <Tooltip title={value}>
                                    <Text className="evidence-text">{value}</Text>
                                  </Tooltip>
                                  <Space size={6} wrap>
                                    {record.enterpriseEvidenceCount > 0 && (
                                      <Tag color="blue">已绑定 {record.enterpriseEvidenceCount} 项</Tag>
                                    )}
                                    {record.enterpriseEvidenceNotRequired && (
                                      <Tooltip title={record.enterpriseEvidenceNotRequiredReason ?? "人工判定无需绑定企业资料证据"}>
                                        <Tag color="green">无需绑定证据</Tag>
                                      </Tooltip>
                                    )}
                                    <Button
                                      size="small"
                                      type={record.statusCode === "needs_material" && !record.enterpriseEvidenceNotRequired ? "primary" : "default"}
                                      icon={<FileSearchOutlined />}
                                      loading={openingEvidenceItemId === record.key}
                                      disabled={Boolean(openingEvidenceItemId) && openingEvidenceItemId !== record.key}
                                      onClick={() => openEvidenceBindingDrawer(record)}
                                    >
                                      {record.enterpriseEvidenceCount ? "管理资料" : "绑定资料"}
                                    </Button>
                                    {!record.enterpriseEvidenceNotRequired && record.enterpriseEvidenceCount === 0 && (
                                      <Button
                                        size="small"
                                        loading={waivingEvidenceItemId === record.key}
                                        disabled={Boolean(waivingEvidenceItemId) && waivingEvidenceItemId !== record.key}
                                        onClick={() => handleWaiveEvidenceRequirement(record)}
                                      >
                                        无需绑定证据
                                      </Button>
                                    )}
                                  </Space>
                                </Space>
                              )
                            },
                            {
                              title: "操作",
                              dataIndex: "actions",
                              width: 340,
                              fixed: "right",
                              render: (_: unknown, record) => (
                                <Space size={6}>
                                  <Button size="small" icon={<FileTextOutlined />} onClick={() => setSourceDrawer(record)}>
                                    原文
                                  </Button>
                                  <Tooltip
                                    title={
                                      draftBlocksByComplianceItemId.has(record.key)
                                        ? "定位覆盖该条款的结构化草稿 block"
                                        : "该条款尚未覆盖到结构化草稿 block"
                                    }
                                  >
                                    <span>
                                      <Button
                                        size="small"
                                        disabled={!draftBlocksByComplianceItemId.has(record.key)}
                                        onClick={() => locateDraftBlockForRow(record.key)}
                                      >
                                        草稿
                                      </Button>
                                    </span>
                                  </Tooltip>
                                  <Button
                                    size="small"
                                    type="primary"
                                    disabled={record.statusCode === "confirmed"}
                                    onClick={() => handleConfirmItem(record)}
                                  >
                                    确认
                                  </Button>
                                  <Button size="small" onClick={() => openEditDraft(record)}>
                                    编辑
                                  </Button>
                                  <Button size="small" onClick={() => handleAssignItem(record)}>
                                    指派
                                  </Button>
                                </Space>
                              )
                            }
                          ]}
                        />
                      </div>
                    );
}
