import React from "react";
import ReactDOM from "react-dom/client";
import { ConfigProvider, type ThemeConfig } from "antd";
import zhCN from "antd/locale/zh_CN";

import { App } from "./pages/App";
import "./styles/global.css";

const theme: ThemeConfig = {
  token: {
    colorPrimary: "#4f46e5",
    colorInfo: "#4f46e5",
    colorSuccess: "#15a34a",
    colorWarning: "#d97706",
    colorError: "#e11d48",
    colorTextBase: "#141925",
    colorBgLayout: "#eceef3",
    borderRadius: 12,
    borderRadiusLG: 16,
    borderRadiusSM: 9,
    controlHeight: 36,
    fontFamily:
      "Inter, 'PingFang SC', 'Microsoft YaHei', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    fontSize: 14,
    colorBorder: "#e5e7ee",
    colorBorderSecondary: "#eef0f4",
    boxShadow: "0 6px 20px rgba(15, 20, 34, 0.09), 0 2px 6px rgba(15, 20, 34, 0.05)",
    boxShadowSecondary: "0 8px 24px rgba(15, 20, 34, 0.12)"
  },
  components: {
    Button: {
      fontWeight: 500,
      primaryShadow: "0 2px 8px rgba(79, 70, 229, 0.28)",
      defaultShadow: "none",
      controlHeight: 36
    },
    Card: {
      borderRadiusLG: 16,
      boxShadowTertiary: "0 1px 3px rgba(15, 20, 34, 0.06), 0 4px 12px rgba(15, 20, 34, 0.05)"
    },
    Table: {
      headerBg: "#f6f7fb",
      headerColor: "#586074",
      headerSplitColor: "#eef0f4",
      borderColor: "#eef0f4",
      rowHoverBg: "#f5f4ff",
      cellPaddingBlock: 13
    },
    Tabs: {
      itemSelectedColor: "#4f46e5",
      itemHoverColor: "#4338ca",
      inkBarColor: "#4f46e5",
      titleFontSize: 14
    },
    Tag: {
      borderRadiusSM: 7
    },
    Input: {
      borderRadius: 9,
      activeShadow: "0 0 0 3px rgba(79, 70, 229, 0.14)"
    },
    Select: {
      borderRadius: 9
    },
    Segmented: {
      borderRadius: 9,
      itemSelectedColor: "#4f46e5"
    },
    Modal: {
      borderRadiusLG: 18
    },
    Drawer: {
      colorBgElevated: "#ffffff"
    },
    Alert: {
      borderRadiusLG: 12
    },
    Progress: {
      defaultColor: "#4f46e5"
    }
  }
};

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <ConfigProvider locale={zhCN} theme={theme}>
      <App />
    </ConfigProvider>
  </React.StrictMode>
);
