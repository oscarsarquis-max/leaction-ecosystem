import { useEffect } from "react";
import { BakerLibrary } from "../features/baker-library/BakerLibrary";
import { BreadBuilder } from "../features/bread-builder/BreadBuilder";
import { HOME_VITRINE } from "../features/bread-builder/catalog";
import { InspirationWall } from "../features/inspiration/InspirationWall";
import { HomeContact } from "../components/HomeContact";
import { StorefrontLayout } from "../components/StorefrontLayout";
import { ProductShelf } from "../shop/ProductShelf";
import { scrollToLocationHash } from "./homeHash";

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
