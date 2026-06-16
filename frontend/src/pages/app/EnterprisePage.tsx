import type { BidAppController } from "../../features/bid/useBidAppController";

export function EnterprisePage({ app }: { app: BidAppController }) {
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
          <Content className="enterprise-page">
            <section className="home-heading">
              <div>
                <Text type="secondary">企业资料库</Text>
                <Title level={2}>投标能力底座</Title>
                <Text type="secondary">维护企业画像、资质证照、人员材料、业绩案例和商务模板；历史文件可先自动抽取为待确认草稿。</Text>
              </div>
              <Space wrap>
                <Button onClick={reloadEnterprise} loading={loadingEnterprise}>
                  刷新
                </Button>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => {
                    resetNewMaterialDraft();
                    setMaterialModalOpen(true);
                  }}
                >
                  新增资料
                </Button>
              </Space>
            </section>

            <section className="enterprise-grid">
              <div className="home-panel profile-panel">
                <div className="panel-title-row">
                  <div>
                    <Text strong>企业画像</Text>
                    <p>资格预评估会优先读取这些基础字段</p>
                  </div>
                  {enterpriseProfile && <Tag color="green">已建档</Tag>}
                </div>
                <Space direction="vertical" size={12} style={{ width: "100%" }}>
                  <Input
                    placeholder="企业名称"
                    value={profileDraft.companyName}
                    onChange={(event) => setProfileDraft((draft) => ({ ...draft, companyName: event.target.value }))}
                  />
                  <Space.Compact style={{ width: "100%" }}>
                    <Input
                      placeholder="统一社会信用代码"
                      value={profileDraft.unifiedSocialCreditCode}
                      onChange={(event) =>
                        setProfileDraft((draft) => ({ ...draft, unifiedSocialCreditCode: event.target.value }))
                      }
                    />
                    <Input
                      placeholder="法定代表人"
                      value={profileDraft.legalRepresentative}
                      onChange={(event) =>
                        setProfileDraft((draft) => ({ ...draft, legalRepresentative: event.target.value }))
                      }
                    />
                  </Space.Compact>
                  <Input
                    placeholder="注册地址"
                    value={profileDraft.registeredAddress}
                    onChange={(event) =>
                      setProfileDraft((draft) => ({ ...draft, registeredAddress: event.target.value }))
                    }
                  />
                  <TextArea
                    placeholder="经营范围"
                    value={profileDraft.businessScope}
                    autoSize={{ minRows: 3, maxRows: 5 }}
                    onChange={(event) => setProfileDraft((draft) => ({ ...draft, businessScope: event.target.value }))}
                  />
                  <Select
                    mode="tags"
                    placeholder="地域偏好，例如：湖南省、岳阳市、CN-4306"
                    value={profileDraft.regionPreferences}
                    onChange={(value) => setProfileDraft((draft) => ({ ...draft, regionPreferences: value }))}
                    tokenSeparators={[",", "，", " "]}
                  />
                  <Select
                    mode="tags"
                    placeholder="行业偏好，例如：市政、燃气、municipal-gas"
                    value={profileDraft.industryPreferences}
                    onChange={(value) => setProfileDraft((draft) => ({ ...draft, industryPreferences: value }))}
                    tokenSeparators={[",", "，", " "]}
                  />
                  <TextArea
                    placeholder="禁投规则，每行一条；命中项目上下文时会进入参标阻断（不建议参标）"
                    value={profileDraft.forbiddenRulesText}
                    autoSize={{ minRows: 3, maxRows: 5 }}
                    onChange={(event) =>
                      setProfileDraft((draft) => ({ ...draft, forbiddenRulesText: event.target.value }))
                    }
                  />
                  <Button type="primary" loading={savingEnterprise} onClick={handleSaveEnterpriseProfile}>
                    保存企业画像
                  </Button>
                </Space>
              </div>

              <div className="home-panel materials-panel">
                <div className="panel-title-row">
                  <div>
                    <Text strong>企业资料</Text>
                    <p>历史 Word 直接解析文本，PDF 自动识别文本型/扫描件；抽取结果必须人工确认后才进入检索语料。</p>
                  </div>
                  <Space wrap>
                    <Tag color="blue">{enterpriseMaterials.length} 条资料</Tag>
                    <Tag color="green">{enterpriseMaterials.filter((item) => item.verification_status === "confirmed").length} 条已确认</Tag>
                  </Space>
                </div>
                <div className="material-index-card">
                  <div>
                    <Space size={8} wrap>
                      <Text strong>检索索引</Text>
                      <Tag color={materialIndexHealth?.status === "healthy" ? "green" : materialIndexHealth?.status === "empty" ? "default" : "orange"}>
                        {materialIndexHealth?.status === "healthy"
                          ? "健康"
                          : materialIndexHealth?.status === "empty"
                            ? "暂无索引"
                            : "需重建"}
                      </Tag>
                      <Tag color="blue">
                        {materialIndexHealth
                          ? `${materialIndexHealth.embedding_model} · ${materialIndexHealth.embedding_dimensions} 维`
                          : "embedding"}
                      </Tag>
                      <Tag color="purple">
                        {materialIndexHealth ? `Rerank · ${materialIndexHealth.rerank_model}` : "rerank"}
                      </Tag>
                      {materialIndexHealth?.fallback_chunk_count ? (
                        <Tag color="orange">{materialIndexHealth.fallback_chunk_count} 个兜底切片</Tag>
                      ) : null}
                    </Space>
                    <p>
                      {materialIndexHealth
                        ? `已索引 ${materialIndexHealth.indexed_material_count}/${materialIndexHealth.confirmed_material_count} 条已确认资料，${materialIndexHealth.chunk_count} 个切片。`
                        : "加载企业资料索引状态。"}
                    </p>
                    <Progress
                      percent={Math.round((materialIndexHealth?.coverage_rate ?? 0) * 100)}
                      size="small"
                      status={materialIndexHealth?.status === "needs_rebuild" ? "exception" : "normal"}
                    />
                  </div>
                  <Space wrap>
                    <Button onClick={reloadMaterialIndexHealth} loading={loadingMaterialIndexHealth}>
                      刷新索引状态
                    </Button>
                    <Button type="primary" onClick={handleRebuildMaterialIndex} loading={rebuildingMaterialIndex}>
                      重建索引
                    </Button>
                  </Space>
                </div>
                <div className="history-extract-card">
                  <div>
                    <Text strong>从历史投标文件抽取</Text>
                    <p>
                      上传历史 Word、PDF 或图片，系统自动识别文本层/OCR，并整理为待确认企业资料草稿。
                    </p>
                    <Space wrap>
                      <Upload
                        showUploadList={false}
                        disabled={extractingHistoryMaterial || historyExtractActive}
                        accept=".docx,.pdf,.jpg,.jpeg,.png,.bmp,.tif,.tiff"
                        customRequest={handleHistoryMaterialUpload}
                      >
                        <Button
                          icon={<CloudUploadOutlined />}
                          loading={extractingHistoryMaterial || historyExtractActive}
                          disabled={extractingHistoryMaterial || historyExtractActive}
                        >
                          {historyExtractActive ? "正在抽取" : "上传历史投标文件"}
                        </Button>
                      </Upload>
                    </Space>
                    {historyExtractTaskId && (
                      <div className="history-extract-task">
                        <Space wrap size={8}>
                          <Tag color={asyncTaskStatusColors[historyExtractTask?.status ?? "pending"]}>
                            {historyExtractStatusText}
                          </Tag>
                          <Text type="secondary">{historyExtractTaskStageTitle(historyExtractTask)}</Text>
                          {asyncTaskEtaText(historyExtractTask, historyExtractTaskId) && (
                            <Text type="secondary">{asyncTaskEtaText(historyExtractTask, historyExtractTaskId)}</Text>
                          )}
                        </Space>
                        <Progress
                          percent={historyExtractProgress}
                          size="small"
                          status={
                            historyExtractTask?.status === "failed"
                              ? "exception"
                              : historyExtractTask?.status === "succeeded"
                                ? "success"
                                : "active"
                          }
                        />
                      </div>
                    )}
                  </div>
                  <Alert
                    type={historyExtractResult?.warning_messages.length ? "warning" : "info"}
                    showIcon
                    message={
                      historyExtractResult
                        ? `最近抽取：${historyExtractResult.draft_count} 条草稿 · ${historyExtractResult.text_block_count} 个文本块`
                        : "抽取结果会先标记为待确认"
                    }
                    description={
                      historyExtractResult
                        ? `${historyExtractResult.source_file_name} · ${
                            historyExtractResult.extraction_method === "llm" ? "LLM 整理" : "本地规则兜底"
                          }${historyExtractResult.warning_messages.length ? ` · ${historyExtractResult.warning_messages.join("；")}` : ""}`
                        : "请逐条核对名称、证书号、来源片段和有效期；确认后才会进入候选证据检索。"
                    }
                  />
                </div>
                <Table
                  size="middle"
                  rowKey="id"
                  loading={loadingEnterprise}
                  dataSource={enterpriseMaterials}
                  pagination={{ pageSize: 8 }}
                  scroll={{ x: 1180 }}
                  locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无企业资料" /> }}
                  columns={[
                    {
                      title: "资料名称",
                      dataIndex: "name",
                      width: 300,
                      render: (value, record) => {
                        const meta = materialExtractionMeta(record);
                        return (
                          <Space direction="vertical" size={0}>
                            <Space wrap size={4}>
                              <Text strong>{value}</Text>
                              {meta.isHistoryExtracted && <Tag color="purple">历史抽取</Tag>}
                              {meta.sourceFileCount > 1 && <Tag color="blue">已合并来源</Tag>}
                            </Space>
                            <Text type="secondary">
                              {record.certificate_no || record.project_name || record.holder_name || "待补充结构化字段"}
                            </Text>
                            {meta.isHistoryExtracted && (
                              <Text type="secondary" className="material-source-line">
                                来源：{meta.sourceFileSummary || "历史文件"}
                                {meta.sourceFileCount > 1 && meta.sourceFileName ? ` · 最近 ${meta.sourceFileName}` : ""}
                                {meta.sourceLocationText ? ` · ${meta.sourceLocationText}` : ""}
                                {meta.sourceImageCount ? ` · 原页图片 ${meta.sourceImageCount} 张` : ""}
                                {meta.confidence !== null ? ` · 置信度 ${Math.round((meta.confidence ?? 0) * 100)}%` : ""}
                              </Text>
                            )}
                          </Space>
                        );
                      }
                    },
                    {
                      title: "类型",
                      dataIndex: "material_type",
                      width: 120,
                      render: (value) => <Tag>{materialTypeLabels[value] ?? value}</Tag>
                    },
                    {
                      title: "数据等级",
                      dataIndex: "data_level",
                      width: 110,
                      render: (value) => <Tag color={value === "confidential" ? "red" : value === "restricted" ? "orange" : "blue"}>{dataLevelLabels[value] ?? value}</Tag>
                    },
                    {
                      title: "状态",
                      dataIndex: "verification_status",
                      width: 110,
                      render: (value) => <Tag color={statusColor(value)}>{verificationStatusLabels[value] ?? value}</Tag>
                    },
                    {
                      title: "有效期",
                      dataIndex: "valid_until",
                      width: 130,
                      render: (value) => value ?? "未设置"
                    },
                    {
                      title: "证据",
                      dataIndex: "evidence_text",
                      width: 260,
                      render: (value, record) => value || record.file_name || "待补充"
                    },
                    {
                      title: "原始文件",
                      dataIndex: "file_name",
                      width: 170,
                      render: (value, record) => (
                        <Space direction="vertical" size={4}>
                          <Text type={value ? undefined : "secondary"}>{value || "未上传"}</Text>
                          <Upload
                            showUploadList={false}
                            customRequest={makeMaterialFileUploadRequest(record)}
                          >
                            <Button size="small" icon={<CloudUploadOutlined />} loading={savingEnterprise}>
                              上传
                            </Button>
                          </Upload>
                        </Space>
                      )
                    },
                    {
                      title: "操作",
                      key: "action",
                      fixed: "right",
                      width: 130,
                      render: (_, record) => {
                        const meta = materialExtractionMeta(record);
                        const canConfirm = record.verification_status === "pending_confirm";
                        return (
                          <Space direction="vertical" size={4}>
                            <Button
                              size="small"
                              type={canConfirm ? "primary" : "default"}
                              icon={<CheckCircleOutlined />}
                              disabled={!canConfirm}
                              loading={confirmingMaterialId === record.id}
                              onClick={() => void handleConfirmExtractedMaterial(record)}
                            >
                              {canConfirm ? "确认入库" : "已处理"}
                            </Button>
                            {meta.needsHumanConfirm && canConfirm && (
                              <Text type="secondary">核对来源后确认</Text>
                            )}
                          </Space>
                        );
                      }
                    }
                  ]}
                />
              </div>
            </section>
          </Content>
  );
}
