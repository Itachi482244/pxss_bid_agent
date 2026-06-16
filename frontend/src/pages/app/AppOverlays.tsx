import type {
  BidAppController,
  MatrixRow,
  ProjectCreateMode
} from "../../features/bid/useBidAppController";
import { formatEvidenceSnippet, stripGeneratedIdSuffix } from "../../features/bid/evidenceText";

type ComplianceEvidenceBinding = BidAppController["evidenceBindings"][number];
type EnterpriseMaterialSearchResult = BidAppController["materialSearchResults"][number];

export function AppOverlays({ app }: { app: BidAppController }) {
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
    handleRejectEvidenceCandidate,
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
    rejectingCandidateId,
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
    <>
      <Modal
        title={projectDeleteTargets.length === 1 ? "删除项目" : `批量删除 ${projectDeleteTargets.length} 个项目`}
        open={projectDeleteTargets.length > 0}
        okText="删除项目"
        okButtonProps={{ danger: true }}
        cancelText="取消"
        confirmLoading={deletingProjects}
        destroyOnHidden
        maskClosable={!deletingProjects}
        maskTransitionName=""
        transitionName=""
        onOk={handleConfirmProjectDeletion}
        onCancel={() => {
          if (!deletingProjects) setProjectDeleteTargets([]);
        }}
      >
        <Space direction="vertical" size={8} style={{ width: "100%" }}>
          <Text>
            删除后项目会归档隐藏，默认项目列表不再显示；项目文件、矩阵、审批和审计记录会保留在系统中。
          </Text>
          <Text type="secondary">
            {projectDeleteTargets
              .slice(0, 5)
              .map((project) => project.name)
              .join("、")}
            {projectDeleteTargets.length > 5 ? ` 等 ${projectDeleteTargets.length} 个项目` : ""}
          </Text>
        </Space>
      </Modal>
      <Modal
        title="新建投标项目"
        open={newProjectOpen}
        width={760}
        okText={savingProject ? "创建中..." : projectCreateMode === "manual" ? "创建项目" : "确认导入并创建"}
        cancelText="取消"
        confirmLoading={savingProject}
        okButtonProps={{ disabled: savingProject || importingProjectDraft || (projectCreateMode !== "manual" && !projectImportDraft) }}
        onOk={handleCreateProject}
        onCancel={() => {
          if (!savingProject) setNewProjectOpen(false);
        }}
      >
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          {savingProject && projectCreateMode !== "manual" && (
            <Alert
              type="info"
              showIcon
              message="正在创建项目"
              description="请勿重复点击。项目创建成功后会自动进入工作台，文件解析和矩阵生成将在后台继续处理。"
            />
          )}
          <Tabs
            activeKey={projectCreateMode}
            tabBarExtraContent={savingProject ? <Tag color="processing">创建中</Tag> : null}
            onChange={(key) => {
              if (savingProject) return;
              setProjectCreateMode(key as ProjectCreateMode);
              setProjectImportDraft(null);
              setProjectImportError("");
            }}
            items={[
              {
                key: "manual",
                label: "手工新建",
                children: <Text type="secondary">录入项目基础信息后创建空项目。</Text>
              },
              {
                key: "file",
                label: "从文件导入",
                children: (
                  <Space direction="vertical" size={10} className="import-upload-panel">
                    <Upload
                      maxCount={1}
                      showUploadList={false}
                      accept=".doc,.docx,.pdf,.html,.htm"
                      disabled={savingProject}
                      beforeUpload={handleImportDraftFile}
                    >
                      <Button type="primary" icon={<CloudUploadOutlined />} loading={importingProjectDraft} disabled={savingProject}>
                        导入招标文件
                      </Button>
                    </Upload>
                    <Text type="secondary">
                      支持 Word、可复制 PDF 和网页 HTML。外部文件按非可信输入处理，识别结果必须人工确认。
                    </Text>
                  </Space>
                )
              },
              {
                key: "url",
                label: "从网页导入",
                children: (
                  <Space direction="vertical" size={10} style={{ width: "100%" }}>
                    <Space.Compact style={{ width: "100%" }}>
                      <Input
                        placeholder="公告网页或附件 URL（按非可信输入处理）"
                        value={importUrl}
                        disabled={savingProject}
                        onChange={(event) => setImportUrl(event.target.value)}
                      />
                      <Input
                        placeholder="资源站点"
                        value={importUrlSite}
                        disabled={savingProject}
                        onChange={(event) => setImportUrlSite(event.target.value)}
                        style={{ width: 160 }}
                      />
                      <Button
                        type="primary"
                        icon={<LinkOutlined />}
                        loading={importingProjectDraft}
                        disabled={savingProject}
                        onClick={handleImportDraftUrl}
                      >
                        识别
                      </Button>
                    </Space.Compact>
                  </Space>
                )
              }
            ]}
          />

          {projectImportError && projectCreateMode !== "manual" && (
            <Alert
              type="error"
              showIcon
              closable
              message={projectCreateMode === "file" ? "招标文件识别失败" : "导入识别失败"}
              description={projectImportError}
              onClose={() => setProjectImportError("")}
            />
          )}

          {projectImportDraft && (
            <div className="import-draft-panel">
              <div className="import-draft-title">
                <Text strong>导入识别结果</Text>
                <Tag color="blue">{projectImportDraft.source.original_filename}</Tag>
              </div>
              {projectImportDraft.warnings.length > 0 && (
                <Alert
                  type="warning"
                  showIcon
                  message={projectImportDraft.warnings.join("；")}
                />
              )}
              <div className="import-draft-summary">
                <div>
                  <Text type="secondary">项目名称</Text>
                  <strong>{projectImportDraft.project.name}</strong>
                </div>
                <div>
                  <Text type="secondary">采购人</Text>
                  <strong>{projectImportDraft.project.purchaser || "未识别"}</strong>
                </div>
                <div>
                  <Text type="secondary">代理机构</Text>
                  <strong>{projectImportDraft.project.agency || "未识别"}</strong>
                </div>
                <div>
                  <Text type="secondary">预算金额</Text>
                  <strong>{projectImportDraft.project.budget_amount || "未识别"}</strong>
                </div>
                <div>
                  <Text type="secondary">标段</Text>
                  <strong>{projectImportDraft.sections.map((section) => section.name).join("、")}</strong>
                </div>
                <div>
                  <Text type="secondary">投标截止时间</Text>
                  <strong>{formatDateTime(projectImportDraft.project.bid_deadline_at)}</strong>
                </div>
              </div>
              <div className="import-confidence">
                {Object.entries(projectImportDraft.confidence).map(([key, rawValue]) => {
                  const value = Number(rawValue) || 0;
                  return (
                  <Tag key={key} color={value >= 0.7 ? "green" : value > 0 ? "gold" : "default"}>
                    {key} {Math.round(value * 100)}%
                  </Tag>
                  );
                })}
              </div>
              <div className="import-preview-text">{projectImportDraft.preview_text}</div>
            </div>
          )}

          {projectCreateMode === "manual" && (
            <>
              <Input
                placeholder="项目名称"
                value={newProjectDraft.name}
                onChange={(event) =>
                  setNewProjectDraft((draft) => ({ ...draft, name: event.target.value }))
                }
              />
              <Input
                placeholder="采购人"
                value={newProjectDraft.purchaser}
                onChange={(event) =>
                  setNewProjectDraft((draft) => ({ ...draft, purchaser: event.target.value }))
                }
              />
              <Input
                placeholder="代理机构"
                value={newProjectDraft.agency}
                onChange={(event) =>
                  setNewProjectDraft((draft) => ({ ...draft, agency: event.target.value }))
                }
              />
              <Space.Compact style={{ width: "100%" }}>
                <Input
                  placeholder="预算金额"
                  value={newProjectDraft.budgetAmount}
                  onChange={(event) =>
                    setNewProjectDraft((draft) => ({ ...draft, budgetAmount: event.target.value }))
                  }
                />
                <Input
                  placeholder="标段名称"
                  value={newProjectDraft.sectionName}
                  onChange={(event) =>
                    setNewProjectDraft((draft) => ({ ...draft, sectionName: event.target.value }))
                  }
                />
              </Space.Compact>
              <Space.Compact style={{ width: "100%" }}>
                <Input
                  placeholder="地区编码"
                  value={newProjectDraft.regionCode}
                  onChange={(event) =>
                    setNewProjectDraft((draft) => ({ ...draft, regionCode: event.target.value }))
                  }
                />
                <Input
                  placeholder="行业编码"
                  value={newProjectDraft.industryCode}
                  onChange={(event) =>
                    setNewProjectDraft((draft) => ({ ...draft, industryCode: event.target.value }))
                  }
                />
              </Space.Compact>
              <Input
                placeholder="公告链接"
                value={newProjectDraft.noticeUrl}
                onChange={(event) =>
                  setNewProjectDraft((draft) => ({ ...draft, noticeUrl: event.target.value }))
                }
              />
              <DatePicker
                showTime
                style={{ width: "100%" }}
                placeholder="投标截止时间"
                value={newProjectDraft.bidDeadlineAt ? dayjs(newProjectDraft.bidDeadlineAt) : null}
                onChange={(value) =>
                  setNewProjectDraft((draft) => ({
                    ...draft,
                    bidDeadlineAt: value ? value.toISOString() : null
                  }))
                }
              />
            </>
          )}
        </Space>
      </Modal>
      <Modal
        title="项目关键信息"
        open={keyInfoModalOpen}
        width={760}
        okText="保存并确认"
        cancelText="取消"
        confirmLoading={savingProject}
        onOk={handleSaveKeyInfo}
        onCancel={() => setKeyInfoModalOpen(false)}
      >
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Alert
            type={missingKeyInfo.length ? "warning" : "info"}
            showIcon
            message={missingKeyInfo.length ? `仍缺少：${missingKeyInfo.join("、")}` : "关键字段已填写"}
            description="这些字段会进入提交前核验、审批说明和导出复盘。复杂的保证金、工期、质量标准等字段暂由合规矩阵承载。"
          />
          <Space.Compact style={{ width: "100%" }}>
            <Input
              placeholder="项目名称"
              value={keyInfoDraft.projectName}
              onChange={(event) => setKeyInfoDraft((draft) => ({ ...draft, projectName: event.target.value }))}
            />
            <Input
              placeholder="标段名称"
              value={keyInfoDraft.sectionName}
              onChange={(event) => setKeyInfoDraft((draft) => ({ ...draft, sectionName: event.target.value }))}
            />
          </Space.Compact>
          <Space.Compact style={{ width: "100%" }}>
            <Input
              placeholder="招标人/采购人"
              value={keyInfoDraft.purchaser}
              onChange={(event) => setKeyInfoDraft((draft) => ({ ...draft, purchaser: event.target.value }))}
            />
            <Input
              placeholder="代理机构"
              value={keyInfoDraft.agency}
              onChange={(event) => setKeyInfoDraft((draft) => ({ ...draft, agency: event.target.value }))}
            />
          </Space.Compact>
          <Space.Compact style={{ width: "100%" }}>
            <Input
              placeholder="项目预算/限价"
              value={keyInfoDraft.budgetAmount}
              onChange={(event) => setKeyInfoDraft((draft) => ({ ...draft, budgetAmount: event.target.value }))}
            />
            <Input
              placeholder="标段预算/限价"
              value={keyInfoDraft.sectionBudgetAmount}
              onChange={(event) =>
                setKeyInfoDraft((draft) => ({ ...draft, sectionBudgetAmount: event.target.value }))
              }
            />
          </Space.Compact>
          <Space.Compact style={{ width: "100%" }}>
            <Input
              placeholder="地区编码"
              value={keyInfoDraft.regionCode}
              onChange={(event) => setKeyInfoDraft((draft) => ({ ...draft, regionCode: event.target.value }))}
            />
            <Input
              placeholder="行业编码"
              value={keyInfoDraft.industryCode}
              onChange={(event) => setKeyInfoDraft((draft) => ({ ...draft, industryCode: event.target.value }))}
            />
            <Input
              placeholder="标段编号"
              value={keyInfoDraft.sectionCode}
              onChange={(event) => setKeyInfoDraft((draft) => ({ ...draft, sectionCode: event.target.value }))}
            />
          </Space.Compact>
          <Input
            placeholder="公告链接"
            value={keyInfoDraft.noticeUrl}
            onChange={(event) => setKeyInfoDraft((draft) => ({ ...draft, noticeUrl: event.target.value }))}
          />
          <Space.Compact style={{ width: "100%" }}>
            <DatePicker
              showTime
              style={{ width: "50%" }}
              placeholder="项目投标截止时间"
              value={keyInfoDraft.bidDeadlineAt ? dayjs(keyInfoDraft.bidDeadlineAt) : null}
              onChange={(value) =>
                setKeyInfoDraft((draft) => ({ ...draft, bidDeadlineAt: value ? value.toISOString() : null }))
              }
            />
            <DatePicker
              showTime
              style={{ width: "50%" }}
              placeholder="标段投标截止时间"
              value={keyInfoDraft.sectionBidDeadlineAt ? dayjs(keyInfoDraft.sectionBidDeadlineAt) : null}
              onChange={(value) =>
                setKeyInfoDraft((draft) => ({
                  ...draft,
                  sectionBidDeadlineAt: value ? value.toISOString() : null
                }))
              }
            />
          </Space.Compact>
          <TextArea
            placeholder="修改/确认原因"
            value={keyInfoDraft.reason}
            autoSize={{ minRows: 2, maxRows: 4 }}
            onChange={(event) => setKeyInfoDraft((draft) => ({ ...draft, reason: event.target.value }))}
          />
        </Space>
      </Modal>
      <Modal
        title="从原文新增合规条目"
        open={Boolean(sourceSelectionDraft)}
        width={760}
        okText="保存并查找相似片段"
        cancelText="取消"
        confirmLoading={savingSourceItem}
        onOk={handleCreateSourceItem}
        onCancel={() => setSourceSelectionDraft(null)}
      >
        {sourceSelectionDraft && (
          <Space direction="vertical" size={12} style={{ width: "100%" }}>
            <Alert
              type="info"
              showIcon
              message={`来源：#${sourceSelectionDraft.chunk.chunk_index}${sourceSelectionDraft.chunk.page_no ? ` · P${sourceSelectionDraft.chunk.page_no}` : ""}`}
              description={sourceSelectionDraft.chunk.heading_path ?? "未识别章节路径"}
            />
            <TextArea
              value={sourceSelectionDraft.selectedText}
              autoSize={{ minRows: 4, maxRows: 8 }}
              onChange={(event) =>
                setSourceSelectionDraft((draft) => draft ? { ...draft, selectedText: event.target.value } : draft)
              }
            />
            <Space.Compact style={{ width: "100%" }}>
              <Select
                value={sourceSelectionDraft.itemType}
                style={{ width: "34%" }}
                options={Object.entries(itemTypeLabels).map(([value, label]) => ({ value, label }))}
                onChange={(value) =>
                  setSourceSelectionDraft((draft) => draft ? { ...draft, itemType: value } : draft)
                }
              />
              <Select
                value={sourceSelectionDraft.riskLevel}
                style={{ width: "33%" }}
                options={Object.entries(riskLabels).map(([value, label]) => ({ value, label: `风险：${label}` }))}
                onChange={(value) =>
                  setSourceSelectionDraft((draft) => draft ? { ...draft, riskLevel: value } : draft)
                }
              />
              <Select
                value={sourceSelectionDraft.isMandatory ? "mandatory" : "normal"}
                style={{ width: "33%" }}
                options={[
                  { value: "mandatory", label: "强制处理" },
                  { value: "normal", label: "普通响应" }
                ]}
                onChange={(value) =>
                  setSourceSelectionDraft((draft) => draft ? { ...draft, isMandatory: value === "mandatory" } : draft)
                }
              />
            </Space.Compact>
            <TextArea
              placeholder="处理建议"
              value={sourceSelectionDraft.responseSuggestion}
              autoSize={{ minRows: 2, maxRows: 4 }}
              onChange={(event) =>
                setSourceSelectionDraft((draft) => draft ? { ...draft, responseSuggestion: event.target.value } : draft)
              }
            />
            <TextArea
              placeholder="新增原因"
              value={sourceSelectionDraft.reason}
              autoSize={{ minRows: 2, maxRows: 4 }}
              onChange={(event) =>
                setSourceSelectionDraft((draft) => draft ? { ...draft, reason: event.target.value } : draft)
              }
            />
          </Space>
        )}
      </Modal>
      <Modal
        title="新增企业资料"
        open={materialModalOpen}
        width={720}
        okText="新增资料"
        cancelText="取消"
        confirmLoading={savingEnterprise}
        onOk={handleCreateEnterpriseMaterial}
        onCancel={() => setMaterialModalOpen(false)}
      >
        <Space direction="vertical" size={12} style={{ width: "100%" }}>
          <Space.Compact style={{ width: "100%" }}>
            <Select
              value={newMaterialDraft.materialType}
              onChange={(value) => setNewMaterialDraft((draft) => ({ ...draft, materialType: value }))}
              options={Object.entries(materialTypeLabels).map(([value, label]) => ({ value, label }))}
              style={{ width: 180 }}
            />
            <Input
              placeholder="资料名称，例如：市政公用工程施工总承包二级资质"
              value={newMaterialDraft.name}
              onChange={(event) => setNewMaterialDraft((draft) => ({ ...draft, name: event.target.value }))}
            />
          </Space.Compact>
          <Space.Compact style={{ width: "100%" }}>
            <Input
              placeholder="发证机关/建设单位"
              value={newMaterialDraft.issuingAuthority}
              onChange={(event) =>
                setNewMaterialDraft((draft) => ({ ...draft, issuingAuthority: event.target.value }))
              }
            />
            <Input
              placeholder="证书编号"
              value={newMaterialDraft.certificateNo}
              onChange={(event) =>
                setNewMaterialDraft((draft) => ({ ...draft, certificateNo: event.target.value }))
              }
            />
          </Space.Compact>
          <Space.Compact style={{ width: "100%" }}>
            <Input
              placeholder="人员姓名"
              value={newMaterialDraft.holderName}
              onChange={(event) => setNewMaterialDraft((draft) => ({ ...draft, holderName: event.target.value }))}
            />
            <Input
              placeholder="业绩项目名称"
              value={newMaterialDraft.projectName}
              onChange={(event) => setNewMaterialDraft((draft) => ({ ...draft, projectName: event.target.value }))}
            />
            <Input
              placeholder="金额"
              value={newMaterialDraft.amount}
              onChange={(event) => setNewMaterialDraft((draft) => ({ ...draft, amount: event.target.value }))}
            />
          </Space.Compact>
          <Space wrap>
            <DatePicker
              placeholder="有效期至"
              value={newMaterialDraft.validUntil ? dayjs(newMaterialDraft.validUntil) : null}
              onChange={(value) =>
                setNewMaterialDraft((draft) => ({ ...draft, validUntil: value ? value.format("YYYY-MM-DD") : null }))
              }
            />
            <Select
              value={newMaterialDraft.dataLevel}
              onChange={(value) => setNewMaterialDraft((draft) => ({ ...draft, dataLevel: value }))}
              options={Object.entries(dataLevelLabels).map(([value, label]) => ({ value, label }))}
              style={{ width: 140 }}
            />
            <Select
              value={newMaterialDraft.verificationStatus}
              onChange={(value) => setNewMaterialDraft((draft) => ({ ...draft, verificationStatus: value }))}
              options={Object.entries(verificationStatusLabels).map(([value, label]) => ({ value, label }))}
              style={{ width: 140 }}
            />
          </Space>
          <TextArea
            placeholder="证据摘录，例如：证书载明资质类别、等级和有效期"
            value={newMaterialDraft.evidenceText}
            autoSize={{ minRows: 3, maxRows: 5 }}
            onChange={(event) => setNewMaterialDraft((draft) => ({ ...draft, evidenceText: event.target.value }))}
          />
          <Alert
            type="info"
            showIcon
            message="本窗口用于快速录入结构化资料；如需从历史文件抽取，请使用企业资料库的历史文件抽取入口。"
          />
        </Space>
      </Modal>
      <Modal
        title="编辑合规矩阵项"
        open={Boolean(editDraft)}
        okText="保存修改"
        cancelText="取消"
        confirmLoading={savingMatrixAction}
        onOk={handleSaveEditDraft}
        onCancel={() => setEditDraft(null)}
      >
        {editDraft && (
          <Space direction="vertical" size={14} style={{ width: "100%" }}>
            <Text>{truncateText(editDraft.row.requirement, 72)}</Text>
            <Space wrap>
              <div className="modal-field">
                <Text type="secondary">状态</Text>
                <Select
                  value={editDraft.status}
                  onChange={(value) => setEditDraft((draft) => (draft ? { ...draft, status: value } : draft))}
                  options={Object.entries(statusLabels)
                    .filter(([value]) => value !== "confirmed")
                    .map(([value, label]) => ({ value, label }))}
                  style={{ width: 160 }}
                />
              </div>
              <div className="modal-field">
                <Text type="secondary">风险</Text>
                <Select
                  value={editDraft.riskLevel}
                  onChange={(value) => setEditDraft((draft) => (draft ? { ...draft, riskLevel: value } : draft))}
                  options={Object.entries(riskLabels).map(([value, label]) => ({ value, label }))}
                  style={{ width: 120 }}
                />
              </div>
              <div className="modal-field compact">
                <Text type="secondary">强制项</Text>
                <Switch
                  checked={editDraft.isMandatory}
                  onChange={(checked) =>
                    setEditDraft((draft) => (draft ? { ...draft, isMandatory: checked } : draft))
                  }
                />
              </div>
            </Space>
            <div className="modal-field full">
              <Text type="secondary">响应建议</Text>
              <TextArea
                value={editDraft.responseSuggestion}
                autoSize={{ minRows: 3, maxRows: 6 }}
                onChange={(event) =>
                  setEditDraft((draft) =>
                    draft ? { ...draft, responseSuggestion: event.target.value } : draft
                  )
                }
              />
            </div>
            <div className="modal-field full">
              <Text type="secondary">修改原因</Text>
              <TextArea
                value={editDraft.reason}
                placeholder="必填，例如：根据公告原文补充风险等级或材料状态"
                autoSize={{ minRows: 2, maxRows: 4 }}
                onChange={(event) =>
                  setEditDraft((draft) => (draft ? { ...draft, reason: event.target.value } : draft))
                }
              />
            </div>
          </Space>
        )}
      </Modal>
      <ContextPackPreviewDrawer
        open={contextPackPreviewOpen}
        source={contextPackSource}
        loading={loadingContextPack}
        onClose={() => setContextPackPreviewOpen(false)}
        onAction={handleContextPackCheckAction}
        actionLabel={contextPackCheckActionText}
      />
      <OutlineEditorModal
        open={outlineEditorOpen}
        loading={loadingContextPack}
        seed={outlineSeed}
        onCancel={() => setOutlineEditorOpen(false)}
        onApply={handleApplyOutline}
      />
      <DirectiveEditorModal
        open={directiveEditorOpen}
        loading={loadingContextPack}
        seed={directiveSeed}
        scopeOptions={directiveScopeOptions}
        rebuildMode={Boolean(activeContextPack)}
        onCancel={() => setDirectiveEditorOpen(false)}
        onApply={handleApplyDirectives}
      />
      {(() => {
        const total = chapterMandatoryBlocks.length;
        const current = chapterMandatoryBlocks[mandatoryReviewIndex] ?? null;
        const currentRows = current
          ? draftBlockLinkIds(current, "compliance_item_ids")
              .map((itemId) => matrixRowsById.get(itemId))
              .filter((row): row is MatrixRow => Boolean(row))
          : [];
        const remaining = chapterMandatoryBlocks.filter((b) => !viewedDraftBlockIds.has(b.id)).length;
        return (
          <Modal
            title="逐条查看：必须原样写入的内容"
            open={mandatoryReviewOpen && total > 0}
            width={720}
            onCancel={() => setMandatoryReviewOpen(false)}
            footer={
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <Text type="secondary">
                  第 {Math.min(mandatoryReviewIndex + 1, total)} / {total} 条 · 待看 {remaining}
                </Text>
                <Space wrap>
                  <Button
                    disabled={mandatoryReviewIndex <= 0}
                    onClick={() => setMandatoryReviewIndex((i) => Math.max(0, i - 1))}
                  >
                    上一条
                  </Button>
                  {current && (
                    <Button
                      danger
                      loading={savingBusinessDraft}
                      disabled={!mvp13DraftWorkflowAvailable}
                      onClick={() => {
                        const target = current;
                        let reason = "逐条审阅驳回指定内容";
                        Modal.confirm({
                          title: "驳回该指定内容",
                          content: (
                            <Space direction="vertical" style={{ width: "100%" }}>
                              <Text type="secondary">驳回需填写原因，将回到待补证据状态。</Text>
                              <Input.TextArea
                                defaultValue={reason}
                                autoSize={{ minRows: 2, maxRows: 4 }}
                                aria-label="驳回原因"
                                onChange={(event) => {
                                  reason = event.target.value;
                                }}
                              />
                            </Space>
                          ),
                          okText: "确认驳回",
                          cancelText: "取消",
                          onOk: async () => {
                            if (!reason.trim()) {
                              Modal.warning({ title: "需要填写驳回原因" });
                              throw new Error("reject reason required");
                            }
                            await handleUpdateDraftBlockStatus(target, "needs_evidence", reason.trim());
                          }
                        });
                      }}
                    >
                      驳回
                    </Button>
                  )}
                  {current && (
                    <Button
                      type="primary"
                      loading={savingBusinessDraft}
                      disabled={!mvp13DraftWorkflowAvailable}
                      onClick={async () => {
                        await handleUpdateDraftBlockStatus(current, "approved", "逐条审阅确认指定内容");
                        if (mandatoryReviewIndex < total - 1) {
                          setMandatoryReviewIndex((i) => i + 1);
                        }
                      }}
                    >
                      确认本条
                    </Button>
                  )}
                  <Button
                    disabled={mandatoryReviewIndex >= total - 1}
                    onClick={() => setMandatoryReviewIndex((i) => Math.min(total - 1, i + 1))}
                  >
                    下一条
                  </Button>
                </Space>
              </div>
            }
          >
            {current ? (
              <Space direction="vertical" size={12} style={{ width: "100%" }}>
                <Alert
                  type="warning"
                  showIcon
                  message="该内容将原样写入标书"
                  description="请核对措辞与其中的事实是否准确；无法回链证据的事实会在导出前被拦截。"
                />
                <div className="draft-block-mandatory-text">
                  <Text strong>指定内容</Text>
                  <p style={{ whiteSpace: "pre-wrap" }}>{current.content_text}</p>
                </div>
                {currentRows.length > 0 && (
                  <div>
                    <Text strong>关联条款</Text>
                    <Space direction="vertical" style={{ width: "100%" }}>
                      {currentRows.slice(0, 6).map((row) => (
                        <Text key={`mandatory-${current.id}-${row.key}`} type="secondary">
                          · {truncateText(row.requirement, 60)}
                        </Text>
                      ))}
                    </Space>
                  </div>
                )}
              </Space>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="没有待确认的指定内容" />
            )}
          </Modal>
        );
      })()}
      <Drawer
        title="查看/修正解析分块"
        open={revisionDrawerOpen}
        width={860}
        onClose={() => {
          setRevisionDrawerOpen(false);
          setRevisionDocument(null);
          setRevisionChunks([]);
          setRevisionReason("");
          setRevisionSearch("");
        }}
        extra={
          <Space>
            {revisionDocument?.current_version && (
              <Tag color={revisionDocument.current_version.parser_name === "manual-editor" ? "gold" : "blue"}>
                {revisionDocument.current_version.version_label}
              </Tag>
            )}
            <Button
              type="primary"
              loading={publishingRevision}
              disabled={!revisionChunks.length}
              onClick={handlePublishManualRevision}
            >
              发布修正版
            </Button>
          </Space>
        }
      >
        <Spin spinning={loadingRevisionChunks}>
          <Space direction="vertical" size={14} style={{ width: "100%" }}>
            <Alert
              type="info"
              showIcon
              message="发布后会生成新的解析版本，不会自动覆盖合规矩阵；需要在文件列表中手动重新生成矩阵。"
            />
            <Input
              prefix={<SearchOutlined />}
              placeholder="搜索解析分块、章节路径或页码，例如：资格、检测报告、P12"
              value={revisionSearch}
              onChange={(event) => setRevisionSearch(event.target.value)}
            />
            <TextArea
              placeholder="修正原因，例如：人工补正 OCR 漏字和章节识别"
              value={revisionReason}
              autoSize={{ minRows: 2, maxRows: 4 }}
              onChange={(event) => setRevisionReason(event.target.value)}
            />
            {filteredRevisionChunks.map((chunk) => (
              <div className="revision-chunk" key={chunk.id}>
                <Space.Compact style={{ width: "100%" }}>
                  <Input
                    type="number"
                    min={1}
                    placeholder="页码"
                    value={chunk.page_no ?? ""}
                    onChange={(event) =>
                      updateRevisionChunk(chunk.id, {
                        page_no: event.target.value ? Number(event.target.value) : null
                      })
                    }
                    style={{ width: 110 }}
                  />
                  <Input
                    placeholder="章节路径"
                    value={chunk.heading_path ?? ""}
                    onChange={(event) => updateRevisionChunk(chunk.id, { heading_path: event.target.value || null })}
                  />
                </Space.Compact>
                <TextArea
                  value={chunk.content_text}
                  autoSize={{ minRows: 4, maxRows: 10 }}
                  onChange={(event) => updateRevisionChunk(chunk.id, { content_text: event.target.value })}
                />
                {chunk.table_json && (
                  <pre className="revision-table-json">{JSON.stringify(chunk.table_json, null, 2)}</pre>
                )}
              </div>
            ))}
            {!!revisionChunks.length && !filteredRevisionChunks.length && !loadingRevisionChunks && (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="没有匹配的解析分块" />
            )}
            {!revisionChunks.length && !loadingRevisionChunks && (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前版本暂无解析分块" />
            )}
          </Space>
        </Spin>
      </Drawer>
      <Drawer
        title="绑定企业资料证据"
        open={Boolean(evidenceDrawer)}
        width={720}
        onClose={() => {
          setEvidenceDrawer(null);
          setEvidenceBindings([]);
          setMaterialSearchResults([]);
          setEvidenceCandidates([]);
        }}
      >
        {evidenceDrawer && (
          <div className="evidence-drawer">
            <Alert
              type="info"
              showIcon
              message="绑定不会自动确认矩阵项；资格项会自动重跑预评估，并使旧参标建议失效。"
            />
            <div className="evidence-requirement">
              <Text type="secondary">当前条款</Text>
              <p>{stripGeneratedIdSuffix(evidenceDrawer.requirement)}</p>
            </div>
            <div className="evidence-section-title">
              <Title level={5}>已绑定资料</Title>
              <Space size={6} wrap>
                <Tag color={evidenceBindings.length ? "blue" : "default"}>
                  {evidenceBindings.length} 项
                </Tag>
                {evidenceDrawer.enterpriseEvidenceNotRequired && (
                  <Tag color="green">无需绑定证据</Tag>
                )}
                {!evidenceDrawer.enterpriseEvidenceNotRequired && !evidenceBindings.length && (
                  <Button
                    size="small"
                    loading={waivingEvidenceItemId === evidenceDrawer.key}
                    onClick={() => handleWaiveEvidenceRequirement(evidenceDrawer)}
                  >
                    无需绑定证据
                  </Button>
                )}
              </Space>
            </div>
            <Table<ComplianceEvidenceBinding>
              size="small"
              rowKey="id"
              pagination={LARGE_TABLE_PAGINATION}
              dataSource={evidenceBindings}
              scroll={{ x: 620 }}
              tableLayout="fixed"
              locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="尚未绑定企业资料" /> }}
              columns={[
                {
                  title: "资料",
                  dataIndex: "material_name",
                  width: 210,
                  render: (value: string | null, record) => (
                    <Space direction="vertical" size={2}>
                      <Text strong>{value ?? "未命名资料"}</Text>
                      <Space size={4} wrap>
                        <Tag>{materialTypeLabels[record.material_type ?? "other"] ?? record.material_type}</Tag>
                        <Tag color={record.material_verification_status === "confirmed" ? "green" : "orange"}>
                          {verificationStatusLabels[record.material_verification_status ?? "draft"] ??
                            record.material_verification_status}
                        </Tag>
                      </Space>
                    </Space>
                  )
                },
                {
                  title: "证据摘录",
                  dataIndex: "evidence_text",
                  render: (value: string) => <Text className="evidence-snippet">{value}</Text>
                },
                {
                  title: "操作",
                  dataIndex: "action",
                  width: 90,
                  render: (_: unknown, record) => (
                    <Button
                      size="small"
                      danger
                      loading={unbindingId === record.id}
                      onClick={() => handleUnbindEvidence(record)}
                    >
                      解除
                    </Button>
                  )
                }
              ]}
            />
            <EvidenceCandidatePanel
              candidates={evidenceCandidates}
              loading={loadingEvidenceCandidates}
              boundMaterialIds={evidenceBindings.map((binding) => binding.enterprise_material_id)}
              bindingMaterialId={bindingMaterialId}
              rejectingCandidateId={rejectingCandidateId}
              includeUnconfirmed={candidateIncludeUnconfirmed}
              includeRestricted={candidateIncludeRestricted}
              materialTypeLabels={materialTypeLabels}
              verificationStatusLabels={verificationStatusLabels}
              onToggleUnconfirmed={handleToggleCandidateUnconfirmed}
              onToggleRestricted={handleToggleCandidateRestricted}
              onRefresh={() => void reloadEvidenceCandidates()}
              onBind={(material) => void handleBindEvidence(material)}
              onReject={(material) => handleRejectEvidenceCandidate(material)}
            />
            <div className="evidence-section-title">
              <Title level={5}>手动检索企业资料</Title>
              <Text type="secondary">推荐之外按关键词全库检索</Text>
            </div>
            <Input.Search
              value={materialSearchQuery}
              placeholder="输入条款关键词、证书名称、人员或业绩名称"
              enterButton="检索"
              loading={loadingMaterialSearch}
              onChange={(event) => setMaterialSearchQuery(event.target.value)}
              onSearch={(value) => runMaterialSearch(value.trim() || evidenceDrawer.requirement)}
            />
            <Table<EnterpriseMaterialSearchResult>
              size="small"
              rowKey="id"
              pagination={LARGE_TABLE_PAGINATION}
              loading={loadingMaterialSearch}
              dataSource={materialSearchResults}
              scroll={{ x: 760 }}
              tableLayout="fixed"
              locale={{
                emptyText: (
                  <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description="暂无匹配资料；请更换关键词或先到企业资料库补充资料"
                  />
                )
              }}
              columns={[
                {
                  title: "候选资料",
                  dataIndex: "name",
                  width: 230,
                  render: (value: string, record) => (
                    <Space direction="vertical" size={2}>
                      <Text strong>{stripGeneratedIdSuffix(value)}</Text>
                      <Space size={4} wrap>
                        <Tag>{materialTypeLabels[record.material_type] ?? record.material_type}</Tag>
                        <Tag color={record.verification_status === "confirmed" ? "green" : "orange"}>
                          {verificationStatusLabels[record.verification_status] ?? record.verification_status}
                        </Tag>
                        {(record.data_level === "restricted" || record.data_level === "confidential") && (
                          <Tag color="red">需脱敏</Tag>
                        )}
                      </Space>
                    </Space>
                  )
                },
                {
                  title: "匹配证据",
                  dataIndex: "snippet",
                  render: (_value: string | null, record) => (
                    <Space direction="vertical" size={4}>
                      <Text className="evidence-snippet">{formatEvidenceSnippet(record)}</Text>
                      <Space size={6} wrap>
                        <Text type="secondary">匹配度 {Math.round(record.confidence_score * 100)}%</Text>
                        {record.rerank_score != null && (
                          <Tag color={record.rerank_fallback_used ? "gold" : "purple"}>
                            Rerank {Math.round(record.rerank_score * 100)}%
                          </Tag>
                        )}
                        {record.base_score != null && (
                          <Tag color="blue">召回 {Math.round(record.base_score * 100)}%</Tag>
                        )}
                      </Space>
                      {record.rerank_model && (
                        <Text type="secondary" className="recommend-reason">
                          重排模型：{record.rerank_model}
                        </Text>
                      )}
                      {record.recommend_reason && (
                        <Text type="secondary" className="recommend-reason">
                          推荐原因：{record.recommend_reason}
                        </Text>
                      )}
                      {record.material_status_hint && <Tag>{record.material_status_hint}</Tag>}
                      {record.matched_terms?.length ? (
                        <Space size={4} wrap>
                          {record.matched_terms.slice(0, 4).map((term) => (
                            <Tag key={term} color="blue">
                              {term}
                            </Tag>
                          ))}
                        </Space>
                      ) : null}
                    </Space>
                  )
                },
                {
                  title: "操作",
                  dataIndex: "action",
                  width: 110,
                  render: (_: unknown, record) => {
                    const bound = evidenceBindings.some(
                      (binding) => binding.enterprise_material_id === record.id
                    );
                    const restricted =
                      record.data_level === "restricted" || record.data_level === "confidential";
                    const blocked =
                      record.verification_status === "conflict" || record.verification_status === "expired" || restricted;
                    const busy = Boolean(bindingMaterialId);
                    const disabledReason = bound
                      ? "该资料已绑定到当前条款"
                      : restricted
                        ? "受限或机密资料需先脱敏，不能直接绑定为响应证据"
                        : blocked
                        ? "冲突或过期资料不能绑定"
                        : busy
                          ? "正在绑定其他资料"
                          : null;
                    return (
                      <Tooltip title={disabledReason}>
                        <span>
                          <Button
                            size="small"
                            type="primary"
                            disabled={bound || blocked || (busy && bindingMaterialId !== record.id)}
                            loading={bindingMaterialId === record.id}
                            onClick={() => handleBindEvidence(record)}
                          >
                            {bound ? "已绑定" : blocked ? "不可绑定" : "绑定"}
                          </Button>
                        </span>
                      </Tooltip>
                    );
                  }
                }
              ]}
            />
          </div>
        )}
      </Drawer>
      <Drawer title="证据来源原文" open={Boolean(sourceDrawer)} width={560} onClose={() => setSourceDrawer(null)}>
        {sourceDrawer && (
          <div className="source-drawer">
            <Space size={8} wrap>
              <Tag color={riskColor(sourceDrawer.risk)}>风险：{sourceDrawer.risk}</Tag>
              <Tag color={sourceDrawer.mandatory ? "red" : "default"}>
                {sourceDrawer.mandatory ? "强制项" : "非强制项"}
              </Tag>
              <Tag color={sourceDrawer.raw.source_content_text ? "blue" : "default"}>
                {sourceDrawer.raw.source_content_text ? "已回链原文" : "无原文片段"}
              </Tag>
            </Space>
            <Title level={5}>{sourceDrawer.source}</Title>
            <div className="source-meta-grid">
              <div>
                <Text type="secondary">来源文件</Text>
                <strong>{sourceDrawer.raw.source_document_title ?? "招标文件"}</strong>
              </div>
              <div>
                <Text type="secondary">解析版本</Text>
                <strong>{sourceDrawer.raw.source_version_label ?? "未记录"}</strong>
              </div>
              <div>
                <Text type="secondary">页码</Text>
                <strong>{sourceDrawer.raw.source_page_no ? `P${sourceDrawer.raw.source_page_no}` : "未记录"}</strong>
              </div>
              <div>
                <Text type="secondary">分块</Text>
                <strong>{sourceDrawer.raw.source_chunk_index ?? "未记录"}</strong>
              </div>
            </div>
            <div className="source-section">
              <Text type="secondary">章节路径</Text>
              <p>{sourceDrawer.raw.source_heading_path ?? "未识别章节路径"}</p>
            </div>
            <div className="source-section">
              <Text type="secondary">原文摘录</Text>
              <p>{sourceDrawer.raw.source_quote ?? sourceDrawer.raw.source_content_text ?? sourceDrawer.raw.evidence_text ?? sourceDrawer.requirement}</p>
            </div>
            {(sourceDrawer.raw.classification_reason || sourceDrawer.raw.split_reason || sourceDrawer.raw.review_hint) && (
              <div className="source-section">
                <Text type="secondary">AI/规则复核提示</Text>
                <p>{sourceDrawer.raw.review_hint ?? sourceDrawer.raw.classification_reason ?? "暂无复核提示"}</p>
                {sourceDrawer.raw.split_reason && <p>{sourceDrawer.raw.split_reason}</p>}
              </div>
            )}
            <div className="source-section">
              <Text type="secondary">规则命中解释</Text>
              <p>
                {explanationText(sourceDrawer.raw.rule_explanation, "rule_name")}：
                {explanationText(sourceDrawer.raw.rule_explanation, "rule_reason")}
              </p>
              <Space size={6} wrap>
                <Tag>{explanationText(sourceDrawer.raw.rule_explanation, "rule_code")}</Tag>
                {explanationKeywords(sourceDrawer.raw.rule_explanation).map((keyword) => (
                  <Tag color="blue" key={keyword}>
                    {keyword}
                  </Tag>
                ))}
              </Space>
            </div>
            <div className="source-section">
              <Text type="secondary">风险解释</Text>
              <p>{explanationText(sourceDrawer.raw.rule_explanation, "risk_reason")}</p>
            </div>
            <div className="source-section">
              <Text type="secondary">批量确认限制</Text>
              <p>{explanationText(sourceDrawer.raw.rule_explanation, "batch_confirm_reason")}</p>
            </div>
            <div className="source-meta-box">
              <Text type="secondary">定位元数据</Text>
              <p>BBox：{sourceMetaText(sourceDrawer.raw.source_bbox_json)}</p>
              <p>表格：{sourceMetaText(sourceDrawer.raw.source_table_json)}</p>
            </div>
            <Button type="primary" onClick={() => appendLog(`查看证据来源：${sourceDrawer.source}`)}>
              确认已核验
            </Button>
          </div>
        )}
      </Drawer>
    </>
  );
}
