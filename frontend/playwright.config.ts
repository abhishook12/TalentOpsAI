import { defineConfig, devices } from '@playwright/test';

const BASE_URL = process.env.PW_BASE_URL || 'http://127.0.0.1:5173';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.PW_WORKERS ? Number(process.env.PW_WORKERS) : 4,
  timeout: 45_000,
  expect: {
    timeout: 10_000,
  },
  reporter: [
    ['list'],
    ['json', { outputFile: '../reports/playwright-results.json' }],
  ],
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    actionTimeout: 15_000,
    navigationTimeout: 20_000,
  },
  projects: [
    {
      name: 'setup',
      testMatch: /auth\.setup\.ts/,
    },

    // ── Phones ───────────────────────────────────────────────────────────────
    {
      name: 'iPhone SE',
      use: { ...devices['iPhone SE'], storageState: 'playwright/.auth/admin.json' },
      dependencies: ['setup'],
    },
    {
      name: 'iPhone 13',
      use: { ...devices['iPhone 13'], storageState: 'playwright/.auth/admin.json' },
      dependencies: ['setup'],
    },
    {
      name: 'iPhone 15 Pro Max',
      use: { ...devices['iPhone 15 Pro Max'], storageState: 'playwright/.auth/admin.json' },
      dependencies: ['setup'],
    },
    {
      name: 'Pixel 7',
      use: { ...devices['Pixel 7'], channel: 'chromium', storageState: 'playwright/.auth/admin.json' },
      dependencies: ['setup'],
    },
    {
      name: 'Galaxy S9+',
      use: { ...devices['Galaxy S9+'], channel: 'chromium', storageState: 'playwright/.auth/admin.json' },
      dependencies: ['setup'],
    },
    {
      name: 'Small Android 320',
      use: {
        ...devices['Pixel 5'], channel: 'chromium',
        viewport: { width: 320, height: 568 },
        hasTouch: true,
        isMobile: true,
        storageState: 'playwright/.auth/admin.json',
      },
      dependencies: ['setup'],
    },

    // ── Tablets (Portrait & Landscape) ───────────────────────────────────────
    {
      name: 'iPad Mini',
      use: { ...devices['iPad Mini'], storageState: 'playwright/.auth/admin.json' },
      dependencies: ['setup'],
    },
    {
      name: 'iPad Mini landscape',
      use: { ...devices['iPad Mini landscape'], storageState: 'playwright/.auth/admin.json' },
      dependencies: ['setup'],
    },
    {
      name: 'iPad Pro 11',
      use: { ...devices['iPad Pro 11'], storageState: 'playwright/.auth/admin.json' },
      dependencies: ['setup'],
    },
    {
      name: 'iPad Pro 11 landscape',
      use: { ...devices['iPad Pro 11 landscape'], storageState: 'playwright/.auth/admin.json' },
      dependencies: ['setup'],
    },
    {
      name: 'Galaxy Tab S4',
      use: { ...devices['Galaxy Tab S4'], channel: 'chromium', storageState: 'playwright/.auth/admin.json' },
      dependencies: ['setup'],
    },
    {
      name: 'Galaxy Tab S4 landscape',
      use: { ...devices['Galaxy Tab S4 landscape'], channel: 'chromium', storageState: 'playwright/.auth/admin.json' },
      dependencies: ['setup'],
    },

    // ── Laptops & Desktops ───────────────────────────────────────────────────
    {
      name: 'Desktop 1280x720',
      use: {
        ...devices['Desktop Chrome'], channel: 'chromium',
        viewport: { width: 1280, height: 720 },
        storageState: 'playwright/.auth/admin.json',
      },
      dependencies: ['setup'],
    },
    {
      name: 'Desktop 1366x768',
      use: {
        ...devices['Desktop Chrome'], channel: 'chromium',
        viewport: { width: 1366, height: 768 },
        storageState: 'playwright/.auth/admin.json',
      },
      dependencies: ['setup'],
    },
    {
      name: 'Desktop 1440x900',
      use: {
        ...devices['Desktop Chrome'], channel: 'chromium',
        viewport: { width: 1440, height: 900 },
        storageState: 'playwright/.auth/admin.json',
      },
      dependencies: ['setup'],
    },
    {
      name: 'Desktop 1920x1080',
      use: {
        ...devices['Desktop Chrome'], channel: 'chromium',
        viewport: { width: 1920, height: 1080 },
        storageState: 'playwright/.auth/admin.json',
      },
      dependencies: ['setup'],
    },
    {
      name: 'Desktop 2560x1440',
      use: {
        ...devices['Desktop Chrome'], channel: 'chromium',
        viewport: { width: 2560, height: 1440 },
        storageState: 'playwright/.auth/admin.json',
      },
      dependencies: ['setup'],
    },
    {
      name: 'Desktop 3840x2160',
      use: {
        ...devices['Desktop Chrome'], channel: 'chromium',
        viewport: { width: 3840, height: 2160 },
        storageState: 'playwright/.auth/admin.json',
      },
      dependencies: ['setup'],
    },

    // ── Desktop Browsers ─────────────────────────────────────────────────────
    {
      name: 'Desktop Chrome',
      use: { ...devices['Desktop Chrome'], channel: 'chromium', storageState: 'playwright/.auth/admin.json' },
      dependencies: ['setup'],
    },
    {
      name: 'Desktop Firefox',
      use: { ...devices['Desktop Firefox'], storageState: 'playwright/.auth/admin.json' },
      dependencies: ['setup'],
    },
    {
      name: 'Desktop Safari',
      use: { ...devices['Desktop Safari'], storageState: 'playwright/.auth/admin.json' },
      dependencies: ['setup'],
    },
    {
      name: 'Desktop Edge',
      use: {
        ...devices['Desktop Chrome'], channel: 'chromium',
        userAgent: devices['Desktop Edge'].userAgent,
        viewport: devices['Desktop Edge'].viewport,
        storageState: 'playwright/.auth/admin.json',
      },
      dependencies: ['setup'],
    },
  ],
});
