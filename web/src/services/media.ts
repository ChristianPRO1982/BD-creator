export function resolveMediaUrl(url: string): string {
  try {
    const parsed = new URL(url);
    const browserHost = window.location.hostname;
    if ((parsed.hostname === "minio" || parsed.hostname === "minio.local") && (browserHost === "localhost" || browserHost === "127.0.0.1")) {
      parsed.hostname = browserHost;
    }
    return parsed.toString();
  } catch {
    return url;
  }
}
