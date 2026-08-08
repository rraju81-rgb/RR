import { config } from '../config/env.js';
import type { PaymentGateway } from './gateway.js';
import { MockGateway } from './mock.js';
import { RazorpayGateway } from './razorpay.js';

let gateway: PaymentGateway | null = null;

export function getGateway(): PaymentGateway {
  gateway ??= config.PAYMENT_PROVIDER === 'razorpay' ? new RazorpayGateway() : new MockGateway();
  return gateway;
}

/** Test seam. */
export function setGateway(next: PaymentGateway | null): void {
  gateway = next;
}

export * from './gateway.js';
export { MockGateway } from './mock.js';
export { RazorpayGateway } from './razorpay.js';
