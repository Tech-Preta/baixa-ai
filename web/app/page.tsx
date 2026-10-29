import { Downloader } from "./components/downloader";

const sources = ["Instagram", "TikTok", "X"];

export default function Home() {
  return (
    <>
      <header className="mx-auto flex w-full max-w-3xl items-center justify-between gap-4 px-5 pt-6 sm:pt-8">
        <p className="font-display text-3xl tracking-tight text-ink">
          baixa<span className="text-ember">.ai</span>
        </p>
        <p className="text-sm text-muted">Grátis · sem anúncios</p>
      </header>
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-5 pt-10 pb-12 sm:pt-16">
        <p className="text-sm font-semibold tracking-[0.16em] text-pine uppercase">Uso pessoal</p>
        <h1 className="mt-3 max-w-xl font-display text-4xl leading-[1.05] text-ink sm:text-6xl">
          Baixe a mídia pública. Sem conta.
        </h1>
        <p className="mt-5 max-w-xl text-lg leading-8 text-muted">
          Cole um link do Instagram, do TikTok ou do X. O arquivo chega na hora — sem cadastro,
          sem anúncio e sem ficar guardado nos nossos servidores.
        </p>
        <ul aria-label="Fontes aceitas" className="mt-6 flex flex-wrap gap-2">
          {sources.map((source) => (
            <li
              key={source}
              className="rounded-full border border-line bg-card px-3 py-1 text-sm text-ink"
            >
              {source}
            </li>
          ))}
        </ul>
        <div className="mt-8">
          <Downloader />
        </div>
      </main>
      <footer className="mx-auto w-full max-w-3xl px-5 pb-10 text-sm leading-6 text-muted">
        <p>
          Uso pessoal. Respeite os direitos autorais e os termos do Instagram, do TikTok e do X. O
          Baixa.ai não pede a sua senha e não armazena os arquivos: o download passa pelo servidor
          e segue direto para o seu aparelho.
        </p>
      </footer>
    </>
  );
}
