// Copies the chosen snapshot into public/data before a build.
//   SNAPSHOT=real (default) -> snapshots/real   (the published portfolio site)
//   SNAPSHOT=demo           -> snapshots/demo   (synthetic data; used by CI)
import { cpSync, existsSync, rmSync } from "node:fs";

const name = process.env.SNAPSHOT ?? "real";
if (!["real", "demo"].includes(name)) {
  console.error(`Unknown SNAPSHOT "${name}" (expected "real" or "demo")`);
  process.exit(1);
}
const src = `snapshots/${name}`;
if (!existsSync(`${src}/meta.json`)) {
  console.error(`${src} is missing; export a snapshot first (see README).`);
  process.exit(1);
}
rmSync("public/data", { recursive: true, force: true });
cpSync(src, "public/data", { recursive: true });
console.log(`Using ${name} snapshot from ${src}`);
