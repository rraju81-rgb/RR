import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/**/*.test.ts'],
    // Config is read once at import time, so the test environment is pinned here.
    env: {
      NODE_ENV: 'test',
      DATABASE_PATH: ':memory:',
      INVOICE_DIR: './data/test-invoices',
      APP_SECRET: 'test-secret-key-0123456789',
      PAYMENT_PROVIDER: 'mock',
      SELLER_STATE_CODE: '29',
      SELLER_STATE: 'Karnataka',
      SELLER_LEGAL_NAME: 'Test 3D Studio',
      GST_ENABLED: 'true',
    },
  },
});
