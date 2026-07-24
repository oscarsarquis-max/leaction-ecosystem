-- Destino CMS: painel logado ActionHub (coluna direita — insights/modais)

ALTER TABLE cms_posts DROP CONSTRAINT IF EXISTS chk_cms_posts_destino;

ALTER TABLE cms_posts ADD CONSTRAINT chk_cms_posts_destino CHECK (
    sistema_destino IN (
        'hub-publico',
        'actionhub',
        'inove4us',
        'paneldx',
        'todos'
    )
);
