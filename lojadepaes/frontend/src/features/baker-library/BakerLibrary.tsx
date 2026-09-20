import { useRef, useState, type MouseEvent } from "react";
import { ARTICLES, PHOTOS } from "../bread-builder/catalog";

export function BakerLibrary() {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const article = openIndex === null ? null : ARTICLES[openIndex];

  function openArticle(index: number) {
    setOpenIndex(index);
    dialogRef.current?.showModal();
  }

  function closeArticle() {
    dialogRef.current?.close();
    setOpenIndex(null);
  }

  function onBackdropClick(event: MouseEvent<HTMLDialogElement>) {
    const dialog = dialogRef.current;
    if (!dialog || event.target !== dialog) return;
    const rect = dialog.getBoundingClientRect();
    if (
      event.clientX < rect.left ||
      event.clientX > rect.right ||
      event.clientY < rect.top ||
      event.clientY > rect.bottom
    ) {
      closeArticle();
    }
  }

  return (
    <section id="biblioteca" className="library">
      <div className="library-heading">
        <p className="eyebrow">BIBLIOTECA DO PADEIRO</p>
        <h2>
          Um pouco de farinha.
          <br />
          <em>Um mundo para descobrir.</em>
        </h2>
        <p>Abra o caderno. Sempre há algo bom para aprender.</p>
        <img className="library-banner" src={PHOTOS.workBench.src} alt={PHOTOS.workBench.alt} />
      </div>
      <div className="articles">
        {ARTICLES.map((item, index) => (
          <button key={item.title} type="button" onClick={() => openArticle(index)}>
            <span>{item.kicker}</span>
            <h3>{item.title}</h3>
            <span className="article-bottom">
              {item.readingLabel} <b>↗</b>
            </span>
          </button>
        ))}
      </div>
      {/* Backdrop como no protótipo. Escape e o botão × cobrem o teclado. */}
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-noninteractive-element-interactions */}
      <dialog id="reading" ref={dialogRef} aria-labelledby="reading-title" onClick={onBackdropClick} onClose={() => setOpenIndex(null)}>
        <button className="close" type="button" aria-label="Fechar leitura" onClick={closeArticle}>
          ×
        </button>
        <div id="reading-body">
          {article ? (
            <>
              <p className="eyebrow">BIBLIOTECA DO PADEIRO</p>
              <h2 id="reading-title">{article.title}</h2>
              <img className="reading-photo" src={article.photo.src} alt={article.photo.alt} />
              {article.paragraphs.map((paragraph) => (
                <p key={paragraph}>{paragraph}</p>
              ))}
            </>
          ) : null}
        </div>
      </dialog>
    </section>
  );
}
