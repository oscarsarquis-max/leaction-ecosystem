import { useEffect } from "react";
import { BakerLibrary } from "../features/baker-library/BakerLibrary";
import { BreadBuilder } from "../features/bread-builder/BreadBuilder";
import { HOME_VITRINE } from "../features/bread-builder/catalog";
import { InspirationWall } from "../features/inspiration/InspirationWall";
import { HomeContact } from "../components/HomeContact";
import { StorefrontLayout } from "../components/StorefrontLayout";
import lepainLogo from "../../images/lepain-logo.png";
import { ProductShelf } from "../shop/ProductShelf";
import { trackEvent } from "../shop/tracking";
import { scrollToLocationHash } from "./homeHash";

const LEPAIN_HERO_HREF =
  "https://lepain.lojadepaes.com.br/pt?utm_source=lojadepaes&utm_medium=hero&utm_campaign=lancamento-lepain";

export function App() {
  useEffect(() => {
    let stop = scrollToLocationHash();
    const refresh = () => {
      stop();
      stop = scrollToLocationHash();
    };
    window.addEventListener("hashchange", refresh);
    window.addEventListener("popstate", refresh);
    return () => {
      stop();
      window.removeEventListener("hashchange", refresh);
      window.removeEventListener("popstate", refresh);
    };
  }, []);

  return (
    <StorefrontLayout>
      <main id="inicio">
        <section className="intro">
          <div className="intro-copy">
            <p className="eyebrow">O DESPERTAR DO LEVAIN</p>
            <h1>
              Todo pão tem uma história.
              <br /> <em>Vamos criar a sua?</em>
            </h1>
            <p>
              Uma boa massa, os seus sabores e o tempo que a natureza pede.
              <br /> Um pão feito à mão, do seu jeito.
            </p>
            <a
              className="lepain-seal"
              href={LEPAIN_HERO_HREF}
              aria-label="Conheça o LePain, o blog da Loja de Pães"
              onClick={() => trackEvent("lepain_hero_click")}
            >
              <span className="lepain-seal-brand">
                <img className="lepain-seal-mark" src={lepainLogo} alt="" />
                <span className="lepain-seal-kicker">NOVO</span>
              </span>
              <span className="lepain-seal-line">
                Histórias, viagens e memórias do pão
                <span className="lepain-seal-arrow" aria-hidden="true">
                  →
                </span>
              </span>
            </a>
          </div>
          <div className="intro-aside">
            <img
              className="intro-photo"
              src={HOME_VITRINE.src}
              alt={HOME_VITRINE.alt}
              width={1237}
              height={646}
            />
          </div>
        </section>
        <ProductShelf />
        <BreadBuilder />
        <div className="craft-notes">
          <span>✦ &nbsp; Fermentação longa, sabor de verdade</span>
          <span>✦ &nbsp; Ingredientes que você reconhece</span>
          <span>✦ &nbsp; Cada pão, um gesto de cuidado</span>
        </div>
        <InspirationWall />
        <BakerLibrary />
        <HomeContact />
      </main>
    </StorefrontLayout>
  );
}
