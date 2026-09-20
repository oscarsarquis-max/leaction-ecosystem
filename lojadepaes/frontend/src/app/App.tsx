import { BakerLibrary } from "../features/baker-library/BakerLibrary";
import { BreadBuilder } from "../features/bread-builder/BreadBuilder";
import { PHOTOS } from "../features/bread-builder/catalog";
import { InspirationWall } from "../features/inspiration/InspirationWall";
import { StorefrontLayout } from "../components/StorefrontLayout";
import { ProductShelf } from "../shop/ProductShelf";

export function App() {
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
            <img className="intro-photo" src={PHOTOS.levainBowl.src} alt={PHOTOS.levainBowl.alt} />
            <div className="seal">
              FERMENTAÇÃO
              <br />
              <strong>natural</strong>
              <span>✦</span>
              SEM PRESSA, SEM ATALHOS
            </div>
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
      </main>
    </StorefrontLayout>
  );
}
