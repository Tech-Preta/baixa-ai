export type MediaItem = {
  index: number;
  type: "video" | "image" | "audio";
  ext: string;
  label: string;
  filesize: number | null;
  download_path: string;
};

export type Extracted = {
  provider: "instagram" | "tiktok" | "x" | "youtube";
  title: string | null;
  author: string | null;
  thumbnail_path: string | null;
  items: MediaItem[];
};

const PROVIDER_LABEL: Record<Extracted["provider"], string> = {
  instagram: "Instagram",
  tiktok: "TikTok",
  x: "X",
  youtube: "YouTube",
};

export function apiBase(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  return (configured || "http://localhost:8000").replace(/\/$/, "");
}

export function absoluteApiPath(path: string): string {
  if (path.startsWith("https://") || path.startsWith("http://")) {
    return path;
  }
  return `${apiBase()}${path.startsWith("/") ? path : `/${path}`}`;
}

export function providerLabel(provider: Extracted["provider"]): string {
  return PROVIDER_LABEL[provider];
}

export function downloadLabel(label: string): string {
  if (label === "MP3" || label.startsWith("MP3 ")) {
    return `Baixar ${label}`;
  }
  const lower = label.charAt(0).toLocaleLowerCase("pt-BR") + label.slice(1);
  return `Baixar ${lower}`;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes.toLocaleString("pt-BR")} B`;
  }
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toLocaleString("pt-BR", {
    maximumFractionDigits: value >= 10 ? 0 : 1,
  })} ${units[unit]}`;
}

export async function extractMedia(url: string): Promise<Extracted> {
  let response: Response;
  try {
    response = await fetch(`${apiBase()}/api/extract`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ url }),
    });
  } catch {
    throw new Error("Não conseguimos falar com o servidor. Tente de novo em instantes.");
  }

  const payload = (await response.json().catch(() => null)) as { message?: string } | null;
  if (!response.ok) {
    throw new Error(payload?.message || "Não foi possível buscar a mídia.");
  }
  if (!payload || !("items" in payload)) {
    throw new Error("A resposta do servidor veio incompleta. Tente de novo.");
  }
  return payload as Extracted;
}
