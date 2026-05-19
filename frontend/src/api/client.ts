import axios from "axios";

export const apiClient = axios.create({
  baseURL: "/api/v1",
  timeout: 30000,
  headers: {
    "X-Tenant-Code": "demo",
    "X-User-External-Id": "demo-admin"
  }
});
