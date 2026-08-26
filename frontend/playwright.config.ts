import { defineConfig } from '@playwright/test';

export default defineConfig({testDir: './e2e', webServer: {command: 'npm start', url: 'http://localhost:4200', reuseExistingServer: true, timeout: 120000}, use: {baseURL: 'http://localhost:4200'}});
