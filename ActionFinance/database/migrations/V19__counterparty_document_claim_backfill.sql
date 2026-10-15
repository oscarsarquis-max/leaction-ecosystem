-- Incremental 013. Não edita V16 (já versionada; ausente no origin público em V13).
-- V16 preenchia claims com ON CONFLICT DO NOTHING e não registrava espelho
-- quando a pessoa já tinha o documento. Conflito entre pessoas distintas
-- não pode escolher dono em silêncio.

UPDATE actionfinance.counterparty_document_claim claim
   SET unit_id = unit.id,
       mirrored = TRUE
  FROM actionfinance.counterparty_unit unit
  JOIN actionfinance.counterparty person
    ON person.tenant_id = unit.tenant_id
   AND person.company_id = unit.company_id
   AND person.id = unit.counterparty_id
 WHERE claim.tenant_id = unit.tenant_id
   AND claim.company_id = unit.company_id
   AND claim.counterparty_id = unit.counterparty_id
   AND claim.document_country = unit.document_country
   AND claim.document_type = unit.document_type
   AND claim.document_number_normalized = unit.document_number_normalized
   AND claim.document_country = person.document_country
   AND claim.document_type = person.document_type
   AND claim.document_number_normalized = person.document_number_normalized
   AND unit.is_primary
   AND (
        SELECT count(*)
          FROM actionfinance.counterparty_unit other
         WHERE other.tenant_id = unit.tenant_id
           AND other.company_id = unit.company_id
           AND other.counterparty_id = unit.counterparty_id
           AND other.is_primary
       ) = 1;

DO $claim_conflict$
DECLARE
    diagnosis TEXT;
BEGIN
    SELECT string_agg(
               format(
                   '%s/%s %s %s %s donos=%s',
                   tenant_id,
                   company_id,
                   document_country,
                   document_type,
                   document_number_normalized,
                   owners),
               '; ')
      INTO diagnosis
      FROM (
            SELECT tenant_id,
                   company_id,
                   document_country,
                   document_type,
                   document_number_normalized,
                   string_agg(DISTINCT counterparty_id::text, ',') AS owners
              FROM (
                    SELECT tenant_id, company_id, document_country, document_type,
                           document_number_normalized, id AS counterparty_id
                      FROM actionfinance.counterparty
                     WHERE document_number_normalized IS NOT NULL
                    UNION ALL
                    SELECT tenant_id, company_id, document_country, document_type,
                           document_number_normalized, counterparty_id
                      FROM actionfinance.counterparty_unit
                     WHERE document_number_normalized IS NOT NULL
                   ) source
             GROUP BY tenant_id, company_id, document_country, document_type, document_number_normalized
            HAVING count(DISTINCT counterparty_id) > 1
           ) collisions;
    IF diagnosis IS NOT NULL THEN
        RAISE EXCEPTION 'counterparty_document_claim conflito pré-existente, sem escolha automática de dono: %', diagnosis;
    END IF;
END
$claim_conflict$;
