/**
 * Seed a starter catalog.
 *
 * These are real, sellable 3D printing products with prices that reflect the
 * quote engine's own cost model, so the storefront is usable on day one and can
 * be edited from the admin console afterwards.
 */
import { closeDb, getDb } from './index.js';
import { products } from './repositories.js';
import { config } from '../config/env.js';
import { toPaise } from '../domain/money.js';
import { logger } from '../lib/logger.js';

interface SeedProduct {
  retailerId: string;
  name: string;
  description: string;
  category: string;
  /** Shelf price in rupees, GST inclusive. */
  price: number;
  materialKey: string;
  weightGrams: number;
  printHours: number;
  stockQuantity: number | null;
}

const CATALOG: SeedProduct[] = [
  {
    retailerId: 'nameplate-classic',
    name: 'Custom Name Plate — Classic',
    description:
      'Personalised door name plate in two-tone finish. Send us the name and we print it. ' +
      'Approx. 200 x 60 mm with keyhole mounting.',
    category: 'nameplates',
    price: 649,
    materialKey: 'pla',
    weightGrams: 85,
    printHours: 4.5,
    stockQuantity: null,
  },
  {
    retailerId: 'nameplate-led',
    name: 'LED Backlit Name Plate',
    description:
      'Warm-white LED backlit name plate with a frosted diffuser face. Includes adapter. ' +
      'Approx. 260 x 90 mm.',
    category: 'nameplates',
    price: 1899,
    materialKey: 'petg',
    weightGrams: 210,
    printHours: 11,
    stockQuantity: null,
  },
  {
    retailerId: 'phone-stand-adjustable',
    name: 'Adjustable Phone Stand',
    description: 'Folding desk stand with three viewing angles. Fits phones and small tablets.',
    category: 'desk',
    price: 349,
    materialKey: 'petg',
    weightGrams: 55,
    printHours: 3,
    stockQuantity: 25,
  },
  {
    retailerId: 'headphone-hook',
    name: 'Under-Desk Headphone Hook',
    description: 'Clamp-on headphone hanger with a cable channel. No screws needed.',
    category: 'desk',
    price: 299,
    materialKey: 'pla',
    weightGrams: 42,
    printHours: 2.2,
    stockQuantity: 40,
  },
  {
    retailerId: 'cable-organiser-set',
    name: 'Cable Organiser Set (6 pcs)',
    description: 'Adhesive-backed cable clips in three sizes. Set of six.',
    category: 'desk',
    price: 249,
    materialKey: 'tpu',
    weightGrams: 30,
    printHours: 2.5,
    stockQuantity: 60,
  },
  {
    retailerId: 'planter-hex-medium',
    name: 'Hexagonal Planter — Medium',
    description:
      'Self-watering hexagonal planter with a drainage tray. 120 mm across. ' +
      'Suits succulents and small herbs.',
    category: 'home',
    price: 599,
    materialKey: 'petg',
    weightGrams: 145,
    printHours: 7,
    stockQuantity: 15,
  },
  {
    retailerId: 'lithophane-frame',
    name: 'Photo Lithophane with Frame',
    description:
      'Your photograph rendered in translucent layers — glows when backlit. ' +
      'Includes a stand with an LED strip. Send the photo on WhatsApp.',
    category: 'gifts',
    price: 899,
    materialKey: 'pla',
    weightGrams: 95,
    printHours: 6.5,
    stockQuantity: null,
  },
  {
    retailerId: 'keychain-custom',
    name: 'Custom Keychain (Pack of 5)',
    description: 'Personalised keychains with names or logos. Pack of five, mixed colours.',
    category: 'gifts',
    price: 449,
    materialKey: 'pla_silk',
    weightGrams: 40,
    printHours: 3,
    stockQuantity: null,
  },
  {
    retailerId: 'desk-organiser-pro',
    name: 'Modular Desk Organiser',
    description: 'Three interlocking trays for pens, cards and stationery. Stackable.',
    category: 'desk',
    price: 799,
    materialKey: 'pla',
    weightGrams: 180,
    printHours: 9,
    stockQuantity: 12,
  },
  {
    retailerId: 'prototype-service',
    name: 'Rapid Prototype Service — per 100 g',
    description:
      'Functional prototyping from your CAD file, priced per 100 g of material. ' +
      'Includes support removal and a dimensional check.',
    category: 'services',
    price: 550,
    materialKey: 'petg',
    weightGrams: 100,
    printHours: 5,
    stockQuantity: null,
  },
  {
    retailerId: 'miniature-resin-32mm',
    name: 'Resin Miniature — 32 mm scale',
    description:
      'High-detail resin miniature printed at 32 mm scale, supports removed and cured. ' +
      'Supplied unpainted.',
    category: 'miniatures',
    price: 399,
    materialKey: 'resin_standard',
    weightGrams: 22,
    printHours: 3.5,
    stockQuantity: null,
  },
  {
    retailerId: 'jig-fixture-custom',
    name: 'Custom Jig / Fixture',
    description:
      'Workshop jigs and fixtures printed in carbon-fibre reinforced PLA. ' +
      'Send a drawing or sample and we will quote.',
    category: 'services',
    price: 1499,
    materialKey: 'pla_cf',
    weightGrams: 240,
    printHours: 12,
    stockQuantity: null,
  },
];

const db = getDb();

for (const item of CATALOG) {
  products.upsert(db, {
    retailerId: item.retailerId,
    name: item.name,
    description: item.description,
    category: item.category,
    price: toPaise(item.price),
    currency: config.CURRENCY,
    hsnCode: config.DEFAULT_HSN_CODE,
    gstRate: config.DEFAULT_GST_RATE,
    materialKey: item.materialKey,
    weightGrams: item.weightGrams,
    printHours: item.printHours,
    availability: item.stockQuantity === 0 ? 'out of stock' : 'in stock',
    stockQuantity: item.stockQuantity,
    isActive: true,
  });
}

logger.info('db.seeded', { products: CATALOG.length });
closeDb();
