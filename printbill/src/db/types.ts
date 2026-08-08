/** Row shapes as stored in SQLite. Money fields are integer paise. */
import type { Paise } from '../domain/money.js';

export interface CustomerRow {
  id: number;
  wa_phone: string;
  name: string | null;
  email: string | null;
  gstin: string | null;
  legal_name: string | null;
  address_line1: string | null;
  address_line2: string | null;
  city: string | null;
  state: string | null;
  state_code: string | null;
  pincode: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductRow {
  id: number;
  retailer_id: string;
  name: string;
  description: string;
  category: string;
  price: Paise;
  currency: string;
  hsn_code: string;
  gst_rate: number;
  material_key: string | null;
  weight_grams: number | null;
  print_hours: number | null;
  image_url: string | null;
  availability: string;
  stock_quantity: number | null;
  is_active: number;
  catalog_synced_at: string | null;
  created_at: string;
  updated_at: string;
}

export type OrderStatus =
  | 'draft'
  | 'pending_payment'
  | 'paid'
  | 'in_production'
  | 'ready'
  | 'shipped'
  | 'delivered'
  | 'cancelled'
  | 'refunded';

export type OrderChannel = 'whatsapp_cart' | 'whatsapp_quote' | 'manual' | 'web';

export interface OrderRow {
  id: number;
  order_number: string;
  customer_id: number;
  quote_id: number | null;
  channel: OrderChannel;
  status: OrderStatus;
  place_of_supply_code: string;
  place_of_supply_name: string;
  tax_kind: 'intra_state' | 'inter_state';
  subtotal: Paise;
  discount: Paise;
  shipping: Paise;
  cgst: Paise;
  sgst: Paise;
  igst: Paise;
  round_off: Paise;
  total: Paise;
  amount_paid: Paise;
  currency: string;
  shipping_address: string | null;
  customer_note: string | null;
  internal_note: string | null;
  created_at: string;
  updated_at: string;
  paid_at: string | null;
}

export interface OrderItemRow {
  id: number;
  order_id: number;
  product_id: number | null;
  description: string;
  hsn_code: string;
  quantity: number;
  unit_price: Paise;
  discount: Paise;
  gst_rate: number;
  taxable_value: Paise;
  cgst: Paise;
  sgst: Paise;
  igst: Paise;
  line_total: Paise;
  meta_json: string | null;
}

export interface InvoiceRow {
  id: number;
  invoice_number: string;
  financial_year: string;
  sequence_number: number;
  order_id: number;
  document_type: 'tax_invoice' | 'bill_of_supply' | 'credit_note';
  issued_at: string;
  total: Paise;
  pdf_path: string | null;
  pdf_sha256: string | null;
  download_token: string;
  whatsapp_media_id: string | null;
  sent_at: string | null;
  cancelled_at: string | null;
  created_at: string;
}

export interface PaymentRow {
  id: number;
  order_id: number;
  provider: string;
  provider_payment_id: string;
  provider_link_id: string | null;
  amount: Paise;
  currency: string;
  status: 'created' | 'authorized' | 'captured' | 'failed' | 'refunded';
  method: string | null;
  raw_json: string | null;
  created_at: string;
}

export interface PaymentLinkRow {
  id: number;
  order_id: number;
  provider: string;
  provider_link_id: string;
  short_url: string;
  amount: Paise;
  status: string;
  expires_at: string | null;
  raw_json: string | null;
  created_at: string;
}

export interface QuoteRow {
  id: number;
  quote_number: string;
  customer_id: number;
  request_json: string;
  result_json: string;
  unit_price: Paise;
  total: Paise;
  status: 'draft' | 'sent' | 'accepted' | 'rejected' | 'expired';
  media_id: string | null;
  media_path: string | null;
  media_filename: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export type OutboxStatus = 'pending' | 'sent' | 'failed' | 'abandoned';

export interface OutboxRow {
  id: number;
  to_phone: string;
  kind: string;
  payload_json: string;
  status: OutboxStatus;
  attempts: number;
  next_attempt_at: string;
  last_error: string | null;
  provider_message_id: string | null;
  dedupe_key: string | null;
  order_id: number | null;
  created_at: string;
  sent_at: string | null;
}

export interface ConversationRow {
  wa_phone: string;
  state: string;
  context_json: string;
  last_inbound_at: string | null;
  updated_at: string;
}
