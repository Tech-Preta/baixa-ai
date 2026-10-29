import { Downloader } from "./components/downloader";

const sources = ["Instagram", "TikTok", "X", "YouTube"];

export default function Home() {
  return (
    <>
      <header className="border-b border-border bg-background/80">
        <div className="mx-auto flex h-14 w-full max-w-3xl items-center justify-between px-6">
          <p className="text-sm font-semibold tracking-tight">baixa.ai</p>
          <p className="font-mono text-[11px] tracking-[0.16em] text-muted uppercase">Sem anúncios</p>
        </div>
      </header>
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-6 py-16 sm:py-24">
        <p className="font-mono text-[11px] tracking-[0.18em] text-muted uppercase">Uso pessoal</p>
        <h1 className="mt-4 max-w-2xl text-4xl font-semibold tracking-tight text-balance sm:text-6xl sm:leading-[1.05]">
          Baixe a mídia pública. Sem conta.
        </h1>
        <p className="mt-6 max-w-xl text-base leading-7 text-muted sm:text-lg">
          Cole um link do Instagram, do TikTok, do X ou do YouTube. O arquivo chega na hora — sem
          cadastro, sem anúncio e sem ficar guardado nos nossos servidores.
        </p>
        <ul aria-label="Fontes aceitas" className="mt-8 flex flex-wrap gap-2">
          {sources.map((source) => (
            <li
              key={source}
              className="rounded-md border border-border bg-background px-2.5 py-1 font-mono text-[11px] tracking-[0.14em] text-muted uppercase"
            >
              {source}
            </li>
          ))}
        </ul>
        <div className="mt-10">
          <Downloader />
        </div>
      </main>
      <footer className="border-t border-border">
        <div className="mx-auto w-full max-w-3xl px-6 py-8 text-sm leading-6 text-muted">
          <p>
            Uso pessoal. Respeite os direitos autorais e os termos do Instagram, do TikTok, do X e
            do YouTube. O Baixa.ai não pede a sua senha e não armazena os arquivos: o download passa
            pelo servidor e segue direto para o seu aparelho.
          </p>
        </div>
      </footer>
    </>
  );
}
