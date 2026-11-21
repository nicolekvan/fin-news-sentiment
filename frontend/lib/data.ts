// Build-time data access. The site is a static snapshot: pages read the JSON exported by the
// backend (`python -m marketlens.jobs.export`) when `next build` runs. No API keys are involved.
import "server-only";
import { readFileSync } from "node:fs";
import path from "node:path";
import type { CompanyFile, CompanyRow, Meta, Overview, Performance } from "./types";

const DATA_DIR = path.join(process.cwd(), "public", "data");

function read<T>(rel: string): T {
  try {
    return JSON.parse(readFileSync(path.join(DATA_DIR, rel), "utf8")) as T;
  } catch {
    throw new Error(`Snapshot file missing: public/data/${rel}. Run the backend export job.`);
  }
}

export const getMeta = () => read<Meta>("meta.json");
export const getCompanies = () => read<CompanyRow[]>("companies.json");
export const getOverview = () => read<Overview>("overview.json");
export const getCompanyFile = (ticker: string) => read<CompanyFile>(`company/${ticker}.json`);

/** Optional: older snapshots have no evaluation yet. */
export function getPerformance(): Performance | null {
  try {
    return read<Performance>("performance.json");
  } catch {
    return null;
  }
}
