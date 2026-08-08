/**
 * Typed, validated configuration.
 *
 * Nothing in the app reads `process.env` directly — everything comes through
 * here so a missing credential fails loudly at boot instead of halfway through
 * a customer's checkout.
 */
import 'dotenv/config';
import { z } from 'zod';

/**
 * Env vars arrive as strings, so a boolean flag needs its own coercion with an
 * explicit default — `"false"` must read as false, and an unset var must fall
 * back to the flag's intended default rather than to false.
 */
const bool = (fallback: boolean) =>
  z
    .string()
    .optional()
    .transform((value) =>
      value === undefined || value === '' ? fallback : value === 'true' || value === '1',
    );

const schema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  PORT: z.coerce.number().int().positive().default(3000),

  /** Public base URL of this service. Used to build invoice + webhook links. */
  PUBLIC_BASE_URL: z.string().url().default('http://localhost:3000'),

  DATABASE_PATH: z.string().default('./data/printbill.db'),
  /** Where generated invoice PDFs are written. */
  INVOICE_DIR: z.string().default('./data/invoices'),

  /** Signs invoice download tokens and admin sessions. Must be set in production. */
  APP_SECRET: z.string().min(16).default('dev-secret-change-me-in-production'),
  ADMIN_API_KEY: z.string().min(8).default('dev-admin-key'),

  // ── Seller identity (printed on every invoice) ────────────────────────────
  SELLER_LEGAL_NAME: z.string().default('Your 3D Printing Studio'),
  SELLER_TRADE_NAME: z.string().default(''),
  SELLER_GSTIN: z.string().default(''),
  SELLER_PAN: z.string().default(''),
  SELLER_ADDRESS_LINE1: z.string().default(''),
  SELLER_ADDRESS_LINE2: z.string().default(''),
  SELLER_CITY: z.string().default(''),
  SELLER_STATE: z.string().default('Karnataka'),
  /** Two-digit GST state code of the seller. Drives CGST+SGST vs IGST. */
  SELLER_STATE_CODE: z.string().length(2).default('29'),
  SELLER_PINCODE: z.string().default(''),
  SELLER_PHONE: z.string().default(''),
  SELLER_EMAIL: z.string().default(''),
  SELLER_LOGO_PATH: z.string().default(''),

  /** Set false if you are below the GST registration threshold. */
  GST_ENABLED: bool(true),
  /** UPI id used to render the "scan to pay" QR on unpaid invoices. */
  SELLER_UPI_ID: z.string().default(''),

  BANK_NAME: z.string().default(''),
  BANK_ACCOUNT_NAME: z.string().default(''),
  BANK_ACCOUNT_NUMBER: z.string().default(''),
  BANK_IFSC: z.string().default(''),

  CURRENCY: z.string().length(3).default('INR'),

  // ── WhatsApp Cloud API (Meta) ─────────────────────────────────────────────
  WHATSAPP_API_VERSION: z.string().default('v21.0'),
  WHATSAPP_PHONE_NUMBER_ID: z.string().default(''),
  WHATSAPP_BUSINESS_ACCOUNT_ID: z.string().default(''),
  WHATSAPP_ACCESS_TOKEN: z.string().default(''),
  /** Echoed back to Meta during webhook subscription handshake. */
  WHATSAPP_VERIFY_TOKEN: z.string().default('printbill-verify'),
  /** Meta App Secret — validates the X-Hub-Signature-256 on every webhook. */
  WHATSAPP_APP_SECRET: z.string().default(''),
  /** Commerce Manager catalog that backs the in-chat storefront. */
  WHATSAPP_CATALOG_ID: z.string().default(''),

  // ── Payment gateway ───────────────────────────────────────────────────────
  PAYMENT_PROVIDER: z.enum(['razorpay', 'mock']).default('mock'),
  RAZORPAY_KEY_ID: z.string().default(''),
  RAZORPAY_KEY_SECRET: z.string().default(''),
  RAZORPAY_WEBHOOK_SECRET: z.string().default(''),

  // ── Pricing defaults for the quote engine ─────────────────────────────────
  /** Machine time charge per hour, in rupees. */
  PRICING_MACHINE_RATE_PER_HOUR: z.coerce.number().nonnegative().default(60),
  /** Flat setup/slicing fee added to every custom job. */
  PRICING_SETUP_FEE: z.coerce.number().nonnegative().default(50),
  /** Multiplier applied to (material + machine + labour) to cover overheads. */
  PRICING_MARGIN_MULTIPLIER: z.coerce.number().positive().default(1.35),
  /** Wastage/failed-print allowance as a fraction of material cost. */
  PRICING_WASTAGE_FACTOR: z.coerce.number().min(0).max(1).default(0.08),
  PRICING_LABOUR_RATE_PER_HOUR: z.coerce.number().nonnegative().default(150),
  /** Orders below this subtotal attract the delivery charge. */
  FREE_DELIVERY_THRESHOLD: z.coerce.number().nonnegative().default(999),
  DELIVERY_CHARGE: z.coerce.number().nonnegative().default(79),

  /** Default HSN for 3D printed plastic articles. */
  DEFAULT_HSN_CODE: z.string().default('3926'),
  /** SAC for job-work / printing services. */
  DEFAULT_SAC_CODE: z.string().default('998912'),
  DEFAULT_GST_RATE: z.coerce.number().min(0).max(28).default(18),
});

export type AppConfig = z.infer<typeof schema> & {
  isProduction: boolean;
  isTest: boolean;
};

function load(): AppConfig {
  const parsed = schema.safeParse(process.env);
  if (!parsed.success) {
    const issues = parsed.error.issues
      .map((i) => `  - ${i.path.join('.')}: ${i.message}`)
      .join('\n');
    throw new Error(`Invalid environment configuration:\n${issues}`);
  }
  const value = parsed.data;

  if (value.NODE_ENV === 'production') {
    const required: Array<[string, string]> = [
      ['APP_SECRET', value.APP_SECRET],
      ['WHATSAPP_ACCESS_TOKEN', value.WHATSAPP_ACCESS_TOKEN],
      ['WHATSAPP_PHONE_NUMBER_ID', value.WHATSAPP_PHONE_NUMBER_ID],
      ['WHATSAPP_APP_SECRET', value.WHATSAPP_APP_SECRET],
    ];
    const missing = required.filter(([, v]) => !v || v.startsWith('dev-'));
    if (missing.length > 0) {
      throw new Error(
        `Refusing to start in production without: ${missing.map(([k]) => k).join(', ')}`,
      );
    }
    if (value.PAYMENT_PROVIDER === 'razorpay' && !value.RAZORPAY_WEBHOOK_SECRET) {
      throw new Error('RAZORPAY_WEBHOOK_SECRET is required when PAYMENT_PROVIDER=razorpay');
    }
  }

  return {
    ...value,
    isProduction: value.NODE_ENV === 'production',
    isTest: value.NODE_ENV === 'test',
  };
}

export const config: AppConfig = load();

/** Seller block, assembled once for the invoice renderer. */
export const seller = {
  legalName: config.SELLER_LEGAL_NAME,
  tradeName: config.SELLER_TRADE_NAME || config.SELLER_LEGAL_NAME,
  gstin: config.SELLER_GSTIN,
  pan: config.SELLER_PAN,
  addressLine1: config.SELLER_ADDRESS_LINE1,
  addressLine2: config.SELLER_ADDRESS_LINE2,
  city: config.SELLER_CITY,
  state: config.SELLER_STATE,
  stateCode: config.SELLER_STATE_CODE,
  pincode: config.SELLER_PINCODE,
  phone: config.SELLER_PHONE,
  email: config.SELLER_EMAIL,
  logoPath: config.SELLER_LOGO_PATH,
  upiId: config.SELLER_UPI_ID,
  bank: {
    name: config.BANK_NAME,
    accountName: config.BANK_ACCOUNT_NAME,
    accountNumber: config.BANK_ACCOUNT_NUMBER,
    ifsc: config.BANK_IFSC,
  },
} as const;
