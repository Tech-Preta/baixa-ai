"use client";

import { useState, type FormEvent } from "react";
import {
  absoluteApiPath,
  downloadLabel,
  extractMedia,
  formatBytes,
  providerLabel,
  type Extracted,
} from "@/lib/api";

type Status = "idle" | "loading" | "ready" | "error";

export function Downloader() {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [media, setMedia] = useState<Extracted | null>(null);
  const [hiddenThumb, setHiddenThumb] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) {
      setMedia(null);
      setStatus("error");
      setError("Cole um link do Instagram, do TikTok, do X ou do YouTube.");
      return;
    }

    setStatus("loading");
    setError(null);
    try {
      const result = await extractMedia(trimmed);
      setMedia(result);
      setStatus("ready");
    } catch (caught) {
      setMedia(null);
      setStatus("error");
      setError(caught instanceof Error ? caught.message : "Não foi possível buscar a mídia.");
    }
  }

  const thumb = media?.thumbnail_path ?? null;
  const showThumb = Boolean(thumb) && hiddenThumb !== thumb;

  return (
    <div className="flex flex-col gap-8">
      <form onSubmit={onSubmit} aria-busy={status === "loading"} className="flex flex-col gap-3">
        <label
          htmlFor="media-url"
          className="font-mono text-[11px] tracking-[0.16em] text-muted uppercase"
        >
          Link da publicação
        </label>
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            id="media-url"
            name="url"
            data-testid="url-input"
            type="url"
            inputMode="url"
            autoComplete="off"
            spellCheck={false}
            required
            placeholder="https://www.youtube.com/watch?v=…"
            value={url}
            aria-invalid={status === "error"}
            onChange={(event) => setUrl(event.target.value)}
            className="h-12 w-full flex-1 rounded-md border border-border bg-background px-3 text-base text-foreground placeholder:text-muted"
          />
          <button
            type="submit"
            data-testid="submit"
            disabled={status === "loading"}
            className="h-12 rounded-md bg-foreground px-5 text-sm font-medium text-background hover:opacity-80 disabled:cursor-wait disabled:opacity-50"
          >
            {status === "loading" ? "Buscando…" : "Buscar"}
          </button>
        </div>
        <p className="text-sm leading-6 text-muted">
          Post, Reel ou Story público, vídeo do TikTok, post do X, ou um vídeo único do YouTube.
          Vídeos também podem ser baixados em MP3.
        </p>
      </form>

      <div aria-live="polite">
        {status === "loading" ? <p className="text-sm text-muted">Buscando a mídia…</p> : null}
        {status === "error" && error ? (
          <p
            role="alert"
            data-testid="error"
            className="rounded-md border border-danger/40 px-3 py-3 text-sm leading-6 text-danger"
          >
            {error}
          </p>
        ) : null}
        {status === "ready" && media ? (
          <article data-testid="preview" className="overflow-hidden rounded-md border border-border bg-background">
            {showThumb && thumb ? (
              // The API already proxies the preview. Skipping the image optimizer avoids a second hop.
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={absoluteApiPath(thumb)}
                alt={media.title ? `Prévia de ${media.title}` : "Prévia da mídia"}
                className="aspect-video w-full bg-hover object-cover"
                onError={() => setHiddenThumb(thumb)}
              />
            ) : null}
            <div className="flex flex-col gap-5 p-5">
              <div className="flex flex-col gap-2">
                <p className="font-mono text-[11px] tracking-[0.16em] text-muted uppercase">
                  {providerLabel(media.provider)}
                </p>
                <h2 className="text-2xl font-semibold tracking-tight">
                  {media.title || "Mídia pública"}
                </h2>
                {media.author ? <p className="text-sm text-muted">{media.author}</p> : null}
              </div>
              <ul className="flex flex-col gap-2">
                {media.items.map((item) => (
                  <li key={item.download_path}>
                    <a
                      data-testid={item.ext === "mp3" ? "download-mp3" : "download-link"}
                      href={absoluteApiPath(item.download_path)}
                      className="flex min-h-12 items-center justify-between gap-3 rounded-md border border-border px-3 py-3 text-sm font-medium hover:bg-hover"
                    >
                      <span>{downloadLabel(item.label)}</span>
                      {item.filesize ? (
                        <span className="font-mono text-xs font-normal text-muted">
                          {formatBytes(item.filesize)}
                        </span>
                      ) : null}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </article>
        ) : null}
      </div>
    </div>
  );
}
