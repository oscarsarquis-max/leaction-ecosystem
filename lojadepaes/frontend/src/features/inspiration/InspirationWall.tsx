import { STORIES } from "../bread-builder/catalog";

export function InspirationWall() {
  return (
    <section id="mural" className="community">
      <div className="section-head">
        <div>
          <p className="eyebrow">À NOSSA MESA</p>
          <h2>O pão aproxima.</h2>
        </div>
        <p>
          Fornadas, descobertas e pequenos rituais.
          <br />
          Inspiração para a próxima fatia.
        </p>
      </div>
      <div className="gallery" id="gallery">
        {STORIES.map((story) => (
          <article className="story" key={story.title}>
            <div className={story.mediaPosition === "left" ? "story-media is-left" : "story-media"}>
              <img src={story.photo.src} alt={story.photo.alt} loading="lazy" />
            </div>
            <small>{story.kicker}</small>
            <h3>{story.title}</h3>
            <p>{story.text}</p>
          </article>
        ))}
      </div>
      <p className="sample-note">
        Mural editorial de inspiração. O envio de fornadas pela comunidade fará parte de uma próxima etapa.
      </p>
    </section>
  );
}
