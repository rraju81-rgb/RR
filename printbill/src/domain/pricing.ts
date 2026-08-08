/**
 * Quote engine for 3D printing jobs.
 *
 * A print is priced from what it actually consumes — grams of material, hours
 * on the machine, minutes of human attention — rather than from a guess. The
 * breakdown is kept in the result so the same numbers can be shown to the
 * customer on WhatsApp when they ask "why does it cost that much".
 */
import { type Paise, multiply, sum, toPaise } from './money.js';

export type MaterialCategory = 'filament' | 'resin' | 'powder';

export interface Material {
  readonly key: string;
  readonly name: string;
  readonly category: MaterialCategory;
  /** Purchase cost of stock, per kilogram, in paise. */
  readonly costPerKg: Paise;
  /** g/cm³ — lets us price from a slicer's volume estimate when weight is unknown. */
  readonly densityGramsPerCm3: number;
  /**
   * Difficulty multiplier on machine time. ABS warps, TPU prints slowly, resin
   * needs washing and curing — all of that is machine/operator time that a flat
   * hourly rate under-recovers.
   */
  readonly difficultyFactor: number;
  readonly notes?: string;
}

/** Stock catalogue. Costs are indicative — override them in the database. */
export const MATERIALS: readonly Material[] = Object.freeze([
  {
    key: 'pla',
    name: 'PLA',
    category: 'filament',
    costPerKg: toPaise(900),
    densityGramsPerCm3: 1.24,
    difficultyFactor: 1.0,
    notes: 'Best for display models, prototypes and indoor use.',
  },
  {
    key: 'pla_silk',
    name: 'Silk PLA',
    category: 'filament',
    costPerKg: toPaise(1250),
    densityGramsPerCm3: 1.24,
    difficultyFactor: 1.05,
    notes: 'Glossy finish, popular for gifts and nameplates.',
  },
  {
    key: 'petg',
    name: 'PETG',
    category: 'filament',
    costPerKg: toPaise(1100),
    densityGramsPerCm3: 1.27,
    difficultyFactor: 1.15,
    notes: 'Tougher and more heat resistant than PLA. Good for functional parts.',
  },
  {
    key: 'abs',
    name: 'ABS',
    category: 'filament',
    costPerKg: toPaise(1050),
    densityGramsPerCm3: 1.04,
    difficultyFactor: 1.3,
    notes: 'Heat resistant, machinable. Needs an enclosure.',
  },
  {
    key: 'asa',
    name: 'ASA',
    category: 'filament',
    costPerKg: toPaise(1500),
    densityGramsPerCm3: 1.07,
    difficultyFactor: 1.35,
    notes: 'UV stable — the right choice for outdoor parts.',
  },
  {
    key: 'tpu',
    name: 'TPU (Flexible)',
    category: 'filament',
    costPerKg: toPaise(1900),
    densityGramsPerCm3: 1.21,
    difficultyFactor: 1.5,
    notes: 'Rubber-like. Prints slowly, so machine time dominates.',
  },
  {
    key: 'pla_cf',
    name: 'PLA Carbon Fibre',
    category: 'filament',
    costPerKg: toPaise(2400),
    densityGramsPerCm3: 1.3,
    difficultyFactor: 1.25,
    notes: 'Stiff, matte finish. Requires a hardened nozzle.',
  },
  {
    key: 'nylon',
    name: 'Nylon (PA)',
    category: 'filament',
    costPerKg: toPaise(3200),
    densityGramsPerCm3: 1.14,
    difficultyFactor: 1.6,
    notes: 'High strength and wear resistance for gears and hinges.',
  },
  {
    key: 'resin_standard',
    name: 'Standard Resin',
    category: 'resin',
    costPerKg: toPaise(2200),
    densityGramsPerCm3: 1.1,
    difficultyFactor: 1.4,
    notes: 'High detail — miniatures, jewellery masters, dental models.',
  },
  {
    key: 'resin_tough',
    name: 'Tough / ABS-like Resin',
    category: 'resin',
    costPerKg: toPaise(3400),
    densityGramsPerCm3: 1.13,
    difficultyFactor: 1.5,
    notes: 'Detail of resin with impact resistance closer to ABS.',
  },
]);

export function findMaterial(key: string): Material | undefined {
  return MATERIALS.find((material) => material.key === key);
}

export type PostProcessing =
  | 'support_removal'
  | 'sanding'
  | 'priming'
  | 'painting'
  | 'polishing'
  | 'assembly'
  | 'uv_curing'
  | 'threaded_inserts';

/** Operator minutes each finishing step typically consumes, per unit. */
export const POST_PROCESSING_MINUTES: Readonly<Record<PostProcessing, number>> =
  Object.freeze({
    support_removal: 8,
    sanding: 25,
    priming: 12,
    painting: 45,
    polishing: 30,
    assembly: 15,
    uv_curing: 10,
    threaded_inserts: 12,
  });

export const POST_PROCESSING_LABELS: Readonly<Record<PostProcessing, string>> =
  Object.freeze({
    support_removal: 'Support removal',
    sanding: 'Sanding',
    priming: 'Priming',
    painting: 'Painting',
    polishing: 'Polishing',
    assembly: 'Assembly',
    uv_curing: 'UV curing',
    threaded_inserts: 'Threaded inserts',
  });

export type RushLevel = 'standard' | 'priority' | 'same_day';

/** Surcharge for jumping the print queue. */
export const RUSH_MULTIPLIER: Readonly<Record<RushLevel, number>> = Object.freeze({
  standard: 1.0,
  priority: 1.25,
  same_day: 1.6,
});

/**
 * Volume discount on the per-unit price. Repeat units of the same model reuse
 * the slicing setup and print unattended, so the marginal cost genuinely falls.
 */
export const QUANTITY_BREAKS: readonly { readonly minQuantity: number; readonly discount: number }[] =
  Object.freeze([
    { minQuantity: 50, discount: 0.2 },
    { minQuantity: 20, discount: 0.15 },
    { minQuantity: 10, discount: 0.1 },
    { minQuantity: 5, discount: 0.05 },
    { minQuantity: 1, discount: 0 },
  ]);

export function quantityDiscountFor(quantity: number): number {
  return QUANTITY_BREAKS.find((tier) => quantity >= tier.minQuantity)?.discount ?? 0;
}

export interface PricingRates {
  readonly machineRatePerHour: Paise;
  readonly labourRatePerHour: Paise;
  readonly setupFee: Paise;
  readonly marginMultiplier: number;
  readonly wastageFactor: number;
}

export interface QuoteRequest {
  readonly materialKey: string;
  /** Material consumed per unit. Supply this or `volumeCm3`. */
  readonly weightGrams?: number;
  /** Slicer volume per unit; converted to weight via material density. */
  readonly volumeCm3?: number;
  /** Machine hours per unit, from the slicer's estimate. */
  readonly printHours: number;
  readonly quantity: number;
  readonly postProcessing?: readonly PostProcessing[];
  readonly rush?: RushLevel;
  /** Extra operator minutes per unit beyond the standard finishing steps. */
  readonly extraLabourMinutes?: number;
  /** Cost of bought-in parts (magnets, inserts, LEDs) per unit. */
  readonly hardwareCost?: Paise;
  /** Override the computed unit price entirely, e.g. for a negotiated rate. */
  readonly manualUnitPrice?: Paise;
}

export interface QuoteBreakdown {
  readonly materialCost: Paise;
  readonly wastageCost: Paise;
  readonly machineCost: Paise;
  readonly labourCost: Paise;
  readonly hardwareCost: Paise;
  /** Sum of the above — what the job costs before margin. */
  readonly directCost: Paise;
  /** Uplift applied by the margin multiplier. */
  readonly margin: Paise;
  readonly setupFee: Paise;
  readonly rushSurcharge: Paise;
  readonly quantityDiscount: Paise;
}

export interface Quote {
  readonly material: Material;
  readonly quantity: number;
  readonly weightGramsPerUnit: number;
  readonly printHoursPerUnit: number;
  readonly rush: RushLevel;
  readonly postProcessing: readonly PostProcessing[];
  readonly breakdown: QuoteBreakdown;
  /** Price of one unit, exclusive of GST. */
  readonly unitPrice: Paise;
  /** unitPrice x quantity, exclusive of GST. */
  readonly total: Paise;
  /** Estimated machine hours for the whole job — drives the delivery promise. */
  readonly totalPrintHours: number;
  readonly estimatedReadyInDays: number;
}

export class PricingError extends Error {
  override readonly name = 'PricingError';
}

/**
 * Price a print job.
 *
 * Costs that scale with each unit (material, machine time, finishing) are
 * computed per unit and discounted for volume; costs incurred once for the job
 * (slicing, bed setup) are added afterwards and spread across the quantity.
 */
export function quotePrintJob(request: QuoteRequest, rates: PricingRates): Quote {
  const material = findMaterial(request.materialKey);
  if (!material) {
    throw new PricingError(`Unknown material "${request.materialKey}"`);
  }
  if (!Number.isInteger(request.quantity) || request.quantity < 1) {
    throw new PricingError(`Quantity must be a positive integer, got ${request.quantity}`);
  }
  if (!Number.isFinite(request.printHours) || request.printHours <= 0) {
    throw new PricingError(`Print hours must be positive, got ${request.printHours}`);
  }

  const weightGrams = resolveWeight(request, material);
  if (weightGrams <= 0) {
    throw new PricingError('Weight must be greater than zero');
  }

  const rush = request.rush ?? 'standard';
  const postProcessing = request.postProcessing ?? [];
  const quantity = request.quantity;

  // ── Per-unit direct costs ────────────────────────────────────────────────
  const materialCost = multiply(material.costPerKg, weightGrams / 1000);
  const wastageCost = multiply(materialCost, rates.wastageFactor);

  // Difficult materials occupy the machine and the operator disproportionately.
  const machineCost = multiply(
    rates.machineRatePerHour,
    request.printHours * material.difficultyFactor,
  );

  const finishingMinutes = postProcessing.reduce(
    (total, step) => total + (POST_PROCESSING_MINUTES[step] ?? 0),
    0,
  );
  const labourMinutes = finishingMinutes + (request.extraLabourMinutes ?? 0);
  const labourCost = multiply(rates.labourRatePerHour, labourMinutes / 60);

  const hardwareCost = request.hardwareCost ?? 0;

  const directCost = sum([materialCost, wastageCost, machineCost, labourCost, hardwareCost]);

  // ── Margin, rush, volume ─────────────────────────────────────────────────
  const withMargin = multiply(directCost, rates.marginMultiplier);
  const margin = withMargin - directCost;

  const rushMultiplier = RUSH_MULTIPLIER[rush];
  const withRush = multiply(withMargin, rushMultiplier);
  const rushSurcharge = withRush - withMargin;

  const discountRate = quantityDiscountFor(quantity);
  const discountPerUnit = multiply(withRush, discountRate);
  const discountedUnit = withRush - discountPerUnit;

  // Setup is charged once for the job, then spread so the per-unit price stays
  // meaningful when it is shown on WhatsApp.
  const setupPerUnit = Math.round(rates.setupFee / quantity);

  const computedUnitPrice = discountedUnit + setupPerUnit;
  const unitPrice = request.manualUnitPrice ?? computedUnitPrice;

  return {
    material,
    quantity,
    weightGramsPerUnit: weightGrams,
    printHoursPerUnit: request.printHours,
    rush,
    postProcessing,
    breakdown: {
      materialCost: materialCost * quantity,
      wastageCost: wastageCost * quantity,
      machineCost: machineCost * quantity,
      labourCost: labourCost * quantity,
      hardwareCost: hardwareCost * quantity,
      directCost: directCost * quantity,
      margin: margin * quantity,
      setupFee: rates.setupFee,
      rushSurcharge: rushSurcharge * quantity,
      quantityDiscount: discountPerUnit * quantity,
    },
    unitPrice,
    total: unitPrice * quantity,
    totalPrintHours: round2(request.printHours * quantity),
    estimatedReadyInDays: estimateLeadDays(
      request.printHours * quantity,
      finishingMinutes * quantity,
      rush,
    ),
  };
}

function resolveWeight(request: QuoteRequest, material: Material): number {
  if (typeof request.weightGrams === 'number') return request.weightGrams;
  if (typeof request.volumeCm3 === 'number') {
    return round2(request.volumeCm3 * material.densityGramsPerCm3);
  }
  throw new PricingError('Provide either weightGrams or volumeCm3');
}

/**
 * Turn machine + finishing time into a promise date.
 *
 * Assumes ~10 usable print hours a day across the farm, one working day for
 * finishing, and a one-day dispatch buffer. Rush levels compress the queue
 * rather than the physics, so the floor is never below a day.
 */
function estimateLeadDays(
  totalPrintHours: number,
  totalFinishingMinutes: number,
  rush: RushLevel,
): number {
  const printDays = totalPrintHours / 10;
  const finishingDays = totalFinishingMinutes / (60 * 6);
  const raw = printDays + finishingDays + 1;
  const compressed = rush === 'same_day' ? raw * 0.4 : rush === 'priority' ? raw * 0.7 : raw;
  return Math.max(1, Math.ceil(compressed));
}

function round2(value: number): number {
  return Math.round(value * 100) / 100;
}

/**
 * A human-readable explanation of the quote, formatted for a WhatsApp message.
 * Customers who understand the breakdown haggle less.
 */
export function explainQuote(quote: Quote, formatMoney: (paise: Paise) => string): string {
  const lines = [
    `*Material:* ${quote.material.name} — ${quote.weightGramsPerUnit} g/unit`,
    `*Print time:* ${quote.printHoursPerUnit} h/unit (${quote.totalPrintHours} h total)`,
    `*Quantity:* ${quote.quantity}`,
  ];

  if (quote.postProcessing.length > 0) {
    const steps = quote.postProcessing
      .map((step) => POST_PROCESSING_LABELS[step] ?? step)
      .join(', ');
    lines.push(`*Finishing:* ${steps}`);
  }
  if (quote.rush !== 'standard') {
    lines.push(`*Priority:* ${quote.rush === 'same_day' ? 'Same day' : 'Priority'}`);
  }
  if (quote.breakdown.quantityDiscount > 0) {
    lines.push(`*Bulk discount:* −${formatMoney(quote.breakdown.quantityDiscount)}`);
  }

  lines.push(
    '',
    `*Unit price:* ${formatMoney(quote.unitPrice)}`,
    `*Total (before GST):* ${formatMoney(quote.total)}`,
    `*Ready in:* ~${quote.estimatedReadyInDays} day(s)`,
  );
  return lines.join('\n');
}
