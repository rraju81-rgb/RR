/**
 * Render a sample invoice to disk without touching the database.
 *
 * Useful for checking the layout after editing the PDF renderer, and for
 * showing a customer what their invoice will look like.
 *
 *   npm run invoice:preview -- --inter-state
 */
import path from 'node:path';
import { computeTax } from '../domain/gst.js';
import { toPaise } from '../domain/money.js';
import { writeInvoicePdf } from '../pdf/invoice.js';
import { config, seller } from '../config/env.js';
import { logger } from '../lib/logger.js';

const interState = process.argv.includes('--inter-state');
const placeOfSupply = interState
  ? { code: '27', name: 'Maharashtra' }
  : { code: seller.stateCode, name: seller.state };

const tax = computeTax(
  [
    {
      id: '1',
      description: 'Custom Name Plate — Classic (PLA, two-tone, 200 x 60 mm)',
      hsnCode: '3926',
      quantity: 2,
      unitPrice: toPaise(550),
      gstRate: 18,
    },
    {
      id: '2',
      description: 'LED Backlit Name Plate with adapter',
      hsnCode: '3926',
      quantity: 1,
      unitPrice: toPaise(1609.32),
      gstRate: 18,
    },
    {
      id: '3',
      description: 'Rapid prototype service — PETG, 320 g, 14 h machine time',
      hsnCode: '998912',
      quantity: 1,
      unitPrice: toPaise(1760),
      discount: toPaise(160),
      gstRate: 18,
    },
  ],
  {
    sellerStateCode: seller.stateCode,
    placeOfSupplyStateCode: placeOfSupply.code,
    gstEnabled: true,
    shipping: toPaise(79),
    orderDiscount: toPaise(100),
  },
);

const { filePath } = await writeInvoicePdf(
  {
    invoiceNumber: 'INV/2026-27/0042',
    issuedAt: new Date(),
    orderNumber: 'ORD-20260808-0042',
    documentType: 'tax_invoice',
    buyer: {
      name: 'Ananya Sharma',
      legalName: 'Sharma Design Studio LLP',
      gstin: interState ? '27AAFCS1234R1ZY' : '',
      addressLine1: '402, Sunrise Residency',
      addressLine2: '14th Cross, HSR Layout',
      city: interState ? 'Mumbai' : 'Bengaluru',
      state: placeOfSupply.name,
      stateCode: placeOfSupply.code,
      pincode: interState ? '400052' : '560102',
      phone: '+919876543210',
      email: 'ananya@example.com',
    },
    placeOfSupply,
    tax,
    amountPaid: tax.grandTotal,
    paymentMethod: 'upi',
    notes: 'Thank you for your business!',
    itemNotes: {
      '1': 'PLA · White/Black · 85 g · 4.5 h print',
      '2': 'PETG · Frosted · 210 g · 11 h print',
      '3': 'PETG · Natural · 320 g · support removal + sanding',
    },
  },
  path.resolve(config.INVOICE_DIR, 'preview'),
);

logger.info('invoice.preview_written', {
  filePath,
  supply: tax.kind,
  total: tax.grandTotal,
});
