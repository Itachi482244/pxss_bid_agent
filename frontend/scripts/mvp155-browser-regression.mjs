import { chromium } from "playwright";

const DEFAULT_URLS = ["http://127.0.0.1:5174", "http://127.0.0.1:5173"];
const DEFAULT_BACKEND_URL = "http://127.0.0.1:8000";
const TIMEOUT_MS = 15000;

function normalizeBaseUrl(value) {
  return value.replace(/\/+$/, "");
}

async function request(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`${url} returned ${response.status}`);
  }
  return response;
}

async function detectBaseUrl() {
  const candidates = process.env.FRONTEND_BASE_URL
    ? [process.env.FRONTEND_BASE_URL]
    : DEFAULT_URLS;
  const backendBaseUrl = normalizeBaseUrl(process.env.BACKEND_BASE_URL ?? DEFAULT_BACKEND_URL);
  const errors = [];
  for (const candidate of candidates.map(normalizeBaseUrl)) {
    try {
      await request(candidate, { method: "GET" });
      // Health is checked against the backend directly; API assertions still go through
      // the frontend base URL so the Vite proxy path stays covered by the regression.
      await request(`${backendBaseUrl}/health`, { method: "GET" });
      return candidate;
    } catch (error) {
      errors.push(`${candidate}: ${error.message}`);
    }
  }
  throw new Error(
    [
      "Frontend/backend services are not ready for MVP1.5.5 browser regression.",
      "Start backend on 127.0.0.1:8000 and frontend on 5173/5174, or set FRONTEND_BASE_URL/BACKEND_BASE_URL.",
      ...errors
    ].join("\n")
  );
}

async function loadTargetProject(baseUrl) {
  const response = await request(`${baseUrl}/api/v1/projects?include_archived=false`);
  const projects = await response.json();
  if (!Array.isArray(projects) || !projects.length) {
    throw new Error("No projects returned by /api/v1/projects; run backend/scripts/seed_dev_data.py first.");
  }
  const requestedName = process.env.MVP155_PROJECT_NAME?.trim();
  if (requestedName) {
    const matched = projects.find((project) => project.name === requestedName);
    if (!matched) {
      throw new Error(`Project '${requestedName}' was not found in API results.`);
    }
    return matched;
  }
  return projects[0];
}

async function expectVisible(locator, label) {
  await locator.waitFor({ state: "visible", timeout: TIMEOUT_MS }).catch((error) => {
    throw new Error(`${label} was not visible: ${error.message}`);
  });
}

async function maybeClick(locator) {
  if ((await locator.count()) === 0) return false;
  if (!(await locator.first().isVisible().catch(() => false))) return false;
  await locator.first().click();
  return true;
}

async function selectProject(page, projectName) {
  await page.locator(".project-switcher").click();
  const option = page.locator(".ant-select-item-option-content", { hasText: projectName }).first();
  await expectVisible(option, `project option '${projectName}'`);
  await option.click();
}

async function assertTopTodoQueue(page) {
  const panel = page.locator(".preflight-panel").first();
  await expectVisible(panel, "project todo panel");
  const text = await panel.innerText();
  if (!text.includes("待办队列")) {
    throw new Error("Todo panel title is missing.");
  }
  if (!text.includes("默认突出最关键 3 项") && !text.includes("暂无阻断或需复核待办")) {
    throw new Error("Todo panel does not explain Top3 default behavior.");
  }

  const cards = panel.locator(".preflight-check");
  const initialCount = await cards.count();
  if (initialCount > 3) {
    throw new Error(`Todo panel should show at most 3 items by default, got ${initialCount}.`);
  }
  if (initialCount > 0 && !/(质量体检|提交前核验)/.test(text)) {
    throw new Error("Todo cards should show whether they come from quality check or preflight.");
  }

  const expand = panel.locator(".preflight-expand-button", { hasText: "展开全部" }).first();
  if (await maybeClick(expand)) {
    await page.waitForTimeout(150);
    const expandedCount = await cards.count();
    if (expandedCount <= initialCount) {
      throw new Error("Todo expand button did not reveal additional items.");
    }
    await panel.locator(".preflight-expand-button", { hasText: "收起待办" }).first().click();
    await page.waitForTimeout(150);
    const collapsedCount = await cards.count();
    if (collapsedCount > 3) {
      throw new Error(`Todo panel should collapse back to Top3, got ${collapsedCount}.`);
    }
  }
}

async function openDocumentsTab(page) {
  const shortcut = page.locator(".section-quality-strip").getByRole("button", { name: "去导出" });
  if (await maybeClick(shortcut)) return;
  await page.getByRole("button", { name: /文件解析/ }).first().click();
}

async function assertEvidenceCandidateExplanation(page) {
  const evidenceStep = page.locator(".workflow-steps").getByRole("button", { name: /绑定资料/ }).first();
  await expectVisible(evidenceStep, "evidence workflow step");
  await evidenceStep.click();
  const panel = page.locator(".evidence-work-panel").first();
  await expectVisible(panel, "evidence work panel");

  const bindButtons = panel.getByRole("button", { name: "绑定资料" });
  const bindButtonCount = await bindButtons.count();
  if (!bindButtonCount) {
    throw new Error("Evidence work panel has no bind buttons; seed data should expose candidate evidence work.");
  }
  await bindButtons.first().click();

  const drawer = page.locator(".ant-drawer").filter({ hasText: "绑定企业资料证据" }).first();
  await expectVisible(drawer, "evidence binding drawer");
  await expectVisible(drawer.getByText("智能推荐证据"), "smart evidence candidate section");
  await expectVisible(drawer.getByText("为什么推荐").first(), "candidate recommendation reason");
  await expectVisible(drawer.getByText("来源在哪里").first(), "candidate source reference");
  await expectVisible(drawer.getByText("风险是什么").first(), "candidate risk note");
  await expectVisible(drawer.getByText("采纳后覆盖").first(), "candidate coverage target");
  await drawer.locator(".ant-drawer-close").click();
  await drawer.waitFor({ state: "hidden", timeout: TIMEOUT_MS }).catch(() => undefined);
}

async function assertExportDialog(page, mode) {
  const isSubmission = mode === "submission";
  const titlePattern = isSubmission ? /正式版导出被阻断|导出前确认：正式版/ : /导出前确认：审阅版/;
  const dialog = page.locator(".ant-modal").filter({ hasText: titlePattern }).first();
  await expectVisible(dialog, `${mode} export confirmation dialog`);
  const text = await dialog.innerText();
  for (const requiredText of ["标书质量体检", "导出模式", "嵌入材料", "评分索引", "剩余占位", "阻断项", "可接受风险", "PAGEREF"]) {
    if (!text.includes(requiredText)) {
      throw new Error(`${mode} export dialog is missing '${requiredText}'.`);
    }
  }

  if (isSubmission && text.includes("正式版导出被阻断")) {
    const blockedOk = dialog.locator("button").filter({ hasText: /处理阻断后再导出/ }).first();
    if (!(await blockedOk.isDisabled())) {
      throw new Error("Blocked submission export should disable the primary confirmation button.");
    }
  }
  await dialog.locator("button").filter({ hasText: /取\s*消|取消/ }).first().click();
  await dialog.waitFor({ state: "hidden", timeout: TIMEOUT_MS }).catch(() => undefined);
}

async function run() {
  const baseUrl = await detectBaseUrl();
  const project = await loadTargetProject(baseUrl);
  const browser = await chromium.launch({ headless: process.env.HEADLESS !== "false" });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
  try {
    // domcontentloaded（不是 networkidle）：工作台加载会触发证据检索评估等真实推理请求，
    // 接入 Infinity 后这些后台请求耗时可能 >30s，networkidle 永不空闲；后续步骤均有显式
    // expectVisible 等待，不依赖网络空闲。
    await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
    await expectVisible(page.getByText("投标 Agent").first(), "app shell");
    await selectProject(page, project.name);
    await expectVisible(page.getByText("标书质量体检").first(), "section quality strip");
    await assertTopTodoQueue(page);
    await assertEvidenceCandidateExplanation(page);

    await openDocumentsTab(page);
    await expectVisible(page.locator(".format-export-bar").first(), "format export bar");
    await page.locator(".format-export-bar").getByRole("button", { name: "审阅版" }).click();
    await assertExportDialog(page, "review");
    await page.locator(".format-export-bar").getByRole("button", { name: "正式版" }).click();
    await assertExportDialog(page, "submission");

    console.log(`MVP1.5.5 browser regression passed at ${baseUrl} for project '${project.name}'.`);
  } finally {
    await browser.close();
  }
}

run().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
