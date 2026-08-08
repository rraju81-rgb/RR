/**
 * Copy non-TypeScript sources into the build output.
 *
 * `tsc` emits only .js, but the runtime reads schema.sql from beside its module,
 * so without this step a compiled deployment starts and immediately fails to
 * open the database.
 */
import { copyFileSync, mkdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

const assets = [['src/db/schema.sql', 'dist/db/schema.sql']];

for (const [from, to] of assets) {
  const target = path.join(root, to);
  mkdirSync(path.dirname(target), { recursive: true });
  copyFileSync(path.join(root, from), target);
  console.log(`copied ${from} → ${to}`);
}
