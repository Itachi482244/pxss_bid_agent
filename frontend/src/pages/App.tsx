import { useBidAppController } from "../features/bid/useBidAppController";
import { AppOverlays } from "./app/AppOverlays";
import { DashboardPage } from "./app/DashboardPage";
import { EnterprisePage } from "./app/EnterprisePage";
import { HomePage } from "./app/HomePage";
import { SettingsPage } from "./app/SettingsPage";
import { WorkspacePage } from "./app/WorkspacePage";
import "./app.css";

export function App() {
  const app = useBidAppController();
  const {
    Alert,
    Avatar,
    Badge,
    BarChartOutlined,
    BellOutlined,
    Button,
    Header,
    Input,
    Layout,
    SafetyCertificateOutlined,
    SearchOutlined,
    Select,
    SettingOutlined,
    Tag,
    TeamOutlined,
    WarningOutlined,
    apiError,
    homeTodoRows,
    loadingProjects,
    openProjectWorkspace,
    projects,
    sections,
    selectedProjectId,
    setApiError,
    setViewMode,
    viewMode
  } = app;

  return (
    <>
      <Layout className="app-shell">
        <Header className="topbar">
          <div className="topbar-left">
            <button className="brand-mark" onClick={() => setViewMode("home")}>
              投标 Agent
            </button>
            <Button
              icon={<SafetyCertificateOutlined />}
              type={viewMode === "enterprise" ? "primary" : "default"}
              onClick={() => setViewMode("enterprise")}
            >
              企业资料库
            </Button>
            <Button
              icon={<BarChartOutlined />}
              type={viewMode === "dashboard" ? "primary" : "default"}
              onClick={() => setViewMode("dashboard")}
            >
              管理看板
            </Button>
            <Button
              icon={<SettingOutlined />}
              type={viewMode === "settings" ? "primary" : "default"}
              onClick={() => setViewMode("settings")}
            >
              模型设置
            </Button>
            <Select
              className="project-switcher"
              placeholder="选择项目"
              value={selectedProjectId}
              loading={loadingProjects}
              onChange={(value) => {
                openProjectWorkspace(value);
              }}
              options={projects.map((project) => ({ value: project.id, label: project.name }))}
            />
            <Input
              className="global-search"
              prefix={<SearchOutlined />}
              placeholder={viewMode === "home" ? "搜索项目、任务、审批、风险" : "搜索项目、条款、文件、证据"}
            />
            <Tag className="todo-tag" icon={<WarningOutlined />} color="orange">
              {sections.filter((section) => section.status !== "confirmed").length || 0} 个标段有未完成项
            </Tag>
          </div>
          <div className="topbar-actions">
            <Badge count={homeTodoRows.length} size="small">
              <Button icon={<BellOutlined />} />
            </Badge>
            <Avatar size={32} icon={<TeamOutlined />} />
          </div>
        </Header>

        {apiError && (
          <Alert
            className="api-alert"
            type="warning"
            showIcon
            closable
            message="数据加载提醒"
            description={apiError}
            onClose={() => setApiError("")}
          />
        )}

        {viewMode === "settings" ? (
          <SettingsPage app={app} />
        ) : viewMode === "enterprise" ? (
          <EnterprisePage app={app} />
        ) : viewMode === "dashboard" ? (
          <DashboardPage app={app} />
        ) : viewMode === "home" ? (
          <HomePage app={app} />
        ) : (
          <WorkspacePage app={app} />
        )}
      </Layout>
      <AppOverlays app={app} />
    </>
  );
}
