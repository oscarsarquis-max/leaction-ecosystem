import { InstagramStrokeIcon, WhatsAppStrokeIcon } from "./HeaderIcons";

const WHATSAPP_HREF = "https://wa.me/5585999831861";
const INSTAGRAM_HREF = "https://www.instagram.com/loja.de.paes/";

export function HomeContact() {
  return (
    <section className="home-contact" aria-labelledby="home-contact-title">
      <h2 id="home-contact-title">Fale com A Loja</h2>
      <ul className="home-contact-list">
        <li>
          <a href={WHATSAPP_HREF} target="_blank" rel="noopener noreferrer">
            <WhatsAppStrokeIcon />
            <span>
              <strong>Converse pelo WhatsApp</strong>
              <span>(85) 99983-1861</span>
            </span>
          </a>
        </li>
        <li>
          <a href={INSTAGRAM_HREF} target="_blank" rel="noopener noreferrer">
            <InstagramStrokeIcon />
            <span>
              <strong>Acompanhe no Instagram</strong>
              <span>@loja.de.paes</span>
            </span>
          </a>
        </li>
      </ul>
    </section>
  );
}
