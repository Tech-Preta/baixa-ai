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
      setError("Cole um link do Instagram, do TikTok ou do X.");
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
    <div className="flex flex-col gap-6">
      <form onSubmit={onSubmit} aria-busy={status === "loading"} className="flex flex-col gap-3">
        <label htmlFor="media-url" className="text-sm font-medium text-ink">
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
            placeholder="https://www.instagram.com/reel/…"
            value={url}
            aria-invalid={status === "error"}
            onChange={(event) => setUrl(event.target.value)}
            className="min-h-12 w-full flex-1 rounded-2xl border border-line bg-card px-4 text-base text-ink shadow-[3px_3px_0_#1c1915] outline-none placeholder:text-muted/80"
          />
          <button
            type="submit"
            data-testid="submit"
            disabled={status === "loading"}
            className="min-h-12 rounded-2xl bg-pine px-6 text-base font-semibold text-white shadow-[3px_3px_0_#1c1915] transition-transform enabled:hover:-translate-y-0.5 enabled:active:translate-y-0 disabled:cursor-wait disabled:opacity-70"
          >
            {status === "loading" ? "Buscando…" : "Buscar"}
          </button>
        </div>
        <p className="text-sm leading-6 text-muted">
          Post e Reel do Instagram, Story público, vídeo do TikTok ou post com mídia no X.
        </p>
      </form>

      <div aria-live="polite" className="min-h-16">
        {status === "loading" ? <p className="text-sm text-muted">Buscando a mídia…</p> : null}
        {status === "error" && error ? (
          <p
            role="alert"
            data-testid="error"
            className="rounded-2xl border border-danger/30 bg-white px-4 py-3 text-sm leading-6 text-danger"
          >
            {error}
          </p>
        ) : null}
        {status === "ready" && media ? (
          <article
            data-testid="preview"
            className="overflow-hidden rounded-3xl border border-line bg-card shadow-[6px_6px_0_#1c1915]"
          >
            {showThumb && thumb ? (
              // The API already proxies the preview. Skipping the image optimizer avoids a second hop.
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={absoluteApiPath(thumb)}
                alt={media.title ? `Prévia de ${media.title}` : "Prévia da mídia"}
                className="aspect-video w-full bg-paper object-cover"
                onError={() => setHiddenThumb(thumb)}
              />
            ) : null}
            <div className="flex flex-col gap-4 p-5">
              <div className="flex flex-col gap-1">
                <p className="text-xs font-semibold tracking-[0.14em] text-pine uppercase">
                  {providerLabel(media.provider)}
                </p>
                <h2 className="font-display text-2xl leading-tight text-ink">
                  {media.title || "Mídia pública"}
                </h2>
                {media.author ? <p className="text-sm text-muted">{media.author}</p> : null}
              </div>
              <ul className="flex flex-col gap-2">
                {media.items.map((item) => (
                  <li key={`${item.index}-${item.label}-${item.ext}`}>
                    <a
                      data-testid="download-link"
                      href={absoluteApiPath(item.download_path)}
                      className="flex min-h-12 items-center justify-between gap-3 rounded-2xl border border-ink/15 bg-white px-4 py-3 text-sm font-semibold text-ink hover:border-pine hover:text-pine"
                    >
                      <span>{downloadLabel(item.label)}</span>
                      {item.filesize ? (
                        <span className="font-normal text-muted">{formatBytes(item.filesize)}</span>
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
