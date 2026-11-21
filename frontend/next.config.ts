import type { NextConfig } from "next";

const config: NextConfig = {
  output: "export", // static site: no server, no secrets at runtime
  trailingSlash: true,
  images: { unoptimized: true },
  poweredByHeader: false,
};

export default config;
