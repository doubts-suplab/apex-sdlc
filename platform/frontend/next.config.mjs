/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  experimental: {
    typedRoutes: true,
  },
  env: {
    NEXT_PUBLIC_LLM_PROVIDER: process.env.LLM_PROVIDER ?? "anthropic",
    NEXT_PUBLIC_LLM_MODEL: process.env.LLM_MODEL ?? "",
  },
};

export default nextConfig;
