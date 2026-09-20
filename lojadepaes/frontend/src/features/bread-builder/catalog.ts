import type {
  Article,
  CatalogPhoto,
  FormOption,
  IngredientOption,
  MassOption,
  Story,
} from "../../types/catalog";

export const OFFICIAL_LOGO = "/images/lojadepaeslogo.png";

/** Fotos de vitrine: só arquivos `internal*` em `frontend/images/`. A logo oficial não entra aqui. */
export function internalPhoto(file: string, alt: string): CatalogPhoto {
  return { src: `/images/${encodeURIComponent(file)}`, alt };
}

export const PHOTOS = {
  sourdough: internalPhoto("internal 1 bread.png", "Miolo alveolado e pão com espiga marcada na farinha"),
  levainProcess: internalPhoto("internal 2 bread.png", "Massa fermentando na tigela e levain no pote"),
  rusticCrust: internalPhoto("internal 3 bread.png", "Crosta caramelizada com cristais de sal"),
  morningLoaf: internalPhoto("internal 4 bread.png", "Pão recém-fatiado sobre tábua de madeira"),
  levainBanner: internalPhoto("internal 5 bread.png", "Potes de levain sobre a mesa da padaria"),
  boules: internalPhoto("internal 6 bread.png", "Fornada de pães rústicos de cesto"),
  multigrain: internalPhoto("internal 7 bread.png", "Pães de grãos com farinha e sementes"),
  doughHands: internalPhoto("internal 8 bread.png", "Mãos esticando a massa na bancada"),
  rosemary: internalPhoto("internal 9 bread.png", "Pão com alecrim partido sobre a tábua"),
  panelHero: internalPhoto("internal 10 bread.png", "Pães fatiados sobre tábua de madeira"),
  ingredients: internalPhoto("internal ingredients 1 bread.png", "Pão e conservas na despensa"),
  levain: internalPhoto("internal levain 1 bread.png", "Culturas de levain e massa levedada"),
  levainBowl: internalPhoto("internal levain 2 bread.png", "Massa levedada crescida no pote de vidro"),
  recipes: internalPhoto("internal recipes 1 bread.png", "Miolo escuro com inclusões ao corte"),
  textureDark: internalPhoto("internal texture 1 bread.png", "Crosta rachada em close"),
  textureFlour: internalPhoto("internal texture 2 bread.png", "Crosta clara com farinha e fendas"),
  workBench: internalPhoto("internal work 1 bread.png", "Padeiro trabalhando a massa na tigela"),
} as const;

export const STEP_LABELS = ["A essência", "Seu toque", "A forma", "O encontro"] as const;

export const STEP_HEADINGS = [
  "Comece pela essência.",
  "Um toque que é só seu.",
  "A forma também conta.",
  "O tempo de um bom encontro.",
] as const;

export const STEP_DESCRIPTIONS = [
  "Escolha a massa que vai dar vida ao seu pão.",
  "Escolha os sabores — ou deixe a massa brilhar sozinha.",
  "Cada formato traz um jeito diferente de partir e compartilhar.",
  "Imagine sua próxima fornada. Escolha uma data e um horário.",
] as const;

export const NEXT_LABELS = [
  "Escolher os sabores",
  "Escolher a forma",
  "Combinar o encontro",
  "Concluir minha criação",
] as const;

export const MASSES: MassOption[] = [
  {
    title: "Sourdough clássico",
    description: "Fermentação de 24h, miolo macio e acidez equilibrada.",
    tag: "A ESSÊNCIA DA CASA",
    photo: PHOTOS.sourdough,
  },
  {
    title: "Integral",
    description: "Sabor profundo de cereais, com miolo mais denso e acolhedor.",
    tag: "RÚSTICO E NUTRITIVO",
    photo: PHOTOS.rusticCrust,
  },
  {
    title: "Multigrãos",
    description: "Uma mistura de sementes para textura em cada fatia.",
    tag: "TEXTURA QUE SURPREENDE",
    photo: PHOTOS.multigrain,
  },
];

export const INGREDIENTS: IngredientOption[] = [
  { name: "Nozes", description: "Crocância delicada" },
  { name: "Damasco", description: "Doçura e maciez" },
  { name: "Azeitonas", description: "Sabor salgado" },
  { name: "Alecrim", description: "Aroma do jardim" },
];

export const FORMS: FormOption[] = [
  {
    title: "Rústico de cesto",
    description: "Crosta marcante, desenho de farinha e fatias generosas.",
    photo: PHOTOS.textureFlour,
  },
  {
    title: "Pão de forma",
    description: "Topo abaulado e fatias regulares para os seus rituais.",
    photo: PHOTOS.rosemary,
  },
];

export function previewPhoto(
  step: number,
  massIndex: number,
  shapeIndex: number,
  finished: boolean,
): CatalogPhoto {
  if (finished) {
    return MASSES[massIndex].photo;
  }
  if (step === 0) {
    return PHOTOS.levain;
  }
  if (step === 1) {
    return PHOTOS.ingredients;
  }
  if (step === 2) {
    return FORMS[shapeIndex].photo;
  }
  return PHOTOS.boules;
}

export const TIME_SLOTS = ["8h–10h", "10h–12h", "14h–16h"] as const;

export const WEEKDAYS = ["D", "S", "T", "Q", "Q", "S", "S"] as const;

export const STORIES: Story[] = [
  {
    kicker: "O RITUAL DA MANHÃ",
    title: "Uma fatia. Um café. Uma pausa.",
    text: "Pão de fermentação natural, manteiga e um começo sem pressa.",
    photo: PHOTOS.morningLoaf,
  },
  {
    kicker: "DA CROSTA AO MIOLO",
    title: "O encanto dos pequenos detalhes.",
    text: "Sementes, texturas e sabores que transformam uma fatia.",
    photo: PHOTOS.textureDark,
  },
  {
    kicker: "FEITO COM AS MÃOS",
    title: "Cada corte, uma assinatura.",
    text: "A beleza de uma fornada que nunca sai igual à outra.",
    photo: PHOTOS.doughHands,
    mediaPosition: "left",
  },
];

export const ARTICLES: Article[] = [
  {
    kicker: "01 / O COMEÇO",
    title: "Levain: um ingrediente vivo",
    readingLabel: "Guia de leitura · 3 min",
    photo: PHOTOS.levain,
    paragraphs: [
      "O levain é uma cultura de farinha e água que abriga leveduras e bactérias. Com alimento e tempo, ele fermenta a massa e participa da construção de aroma, sabor e textura.",
      "Alimentar o levain significa renovar parte da cultura com farinha e água. O ritmo muda com a temperatura, o tipo de farinha e a proporção usada. Observe o crescimento, as bolhas e o aroma para conhecer o seu.",
      "Para começar, siga uma receita com quantidades e horários definidos, usando um recipiente limpo. Aprender a ler os sinais da cultura é mais útil do que correr contra o relógio.",
    ],
  },
  {
    kicker: "02 / AS MÃOS NA MASSA",
    title: "A delicadeza de uma boa dobra",
    readingLabel: "Técnica · 2 min",
    photo: PHOTOS.levainProcess,
    paragraphs: [
      "As dobras ajudam a organizar a estrutura da massa durante a fermentação. O gesto é simples: levantar uma lateral com delicadeza e dobrá-la sobre o centro.",
      "Com as mãos levemente úmidas, repita o gesto nas outras laterais. Evite rasgar a massa. Depois, cubra e deixe descansar conforme a receita, para que ela relaxe antes da próxima série.",
      "A massa muda a cada descanso. Mais coesão e elasticidade são sinais para observar; o número de dobras depende da farinha, da hidratação e do processo escolhido.",
    ],
  },
  {
    kicker: "03 / À MESA",
    title: "Como guardar seu pão",
    readingLabel: "Cuidado cotidiano · 2 min",
    photo: PHOTOS.recipes,
    paragraphs: [
      "Espere o pão esfriar antes de guardá-lo. O vapor preso em uma embalagem pode deixar a crosta úmida. No dia a dia, um local seco e protegido ajuda a preservar a qualidade.",
      "Para guardar por mais tempo, corte em fatias e congele em uma embalagem bem fechada. Assim, você retira apenas o que vai comer e aquece direto na torradeira ou no forno.",
      "A geladeira costuma acelerar o ressecamento do miolo. Se aparecer mofo, descarte o pão inteiro: retirar apenas a parte visível não é suficiente.",
    ],
  },
];
