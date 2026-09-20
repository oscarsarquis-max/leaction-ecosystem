# Corpus controlado SEGSENSE_PRM_020_COR_001

Fixture de teste (não é prova da Wikipedia ao vivo): `backend/src/test/resources/urlcapture/SEGSENSE_PRM_020_COR_001_wikipedia_fixture.html`. Hashes dessa fixture só identificam o arquivo de teste.

| Caso | Resultado esperado | Teste |
|---|---|---|
| Evento e cultura na mesma sentença | Associação permitida (`crop=milho`) | `sameSentenceAllowsCropAssociation` |
| Evento num parágrafo; cultura só no índice | Cultura omitida | `cropOnlyInIndexIsOmitted` |
| Evento numa seção; região em história institucional | Região omitida | `distantInstitutionalHistoryDoesNotBecomeRegion` |
| Vários eventos/culturas sem relação inequívoca | Sem combinação cartesiana; cultura omitida | `multipleUnrelatedCropsStayAmbiguous` |
| `nav`/`aside`/sumário/rodapé/oculto | Fora do conteúdo principal | `chromeNavAsideTocFooterAndHiddenAreExcluded` |
| Sem `main`/`article`, fallback | `STRIP_CHROME_BODY_FALLBACK` utilizável | `bodyWithoutMainUsesDocumentedFallback` |
| Sem conteúdo principal confiável | `usable=false` → `NO_MEANINGFUL_TEXT` | `chromeOnlyPageFailsHonestly` |
| HTML hostil e excessivo | Sem script; texto limitado a 32 KiB | `hostileAndOversizedStayLimited` |
| Fixture representativa da auditoria | Tema/evento; sem milho nem Rio Grande do Sul | `auditedWikipediaFixtureOmitsDistantMilhoAndRioGrandeDoSul` |
| Payload Spider | `URL_EXTRACTED` sem atributo não sustentado | `UrlExtractedEnvelopeTest` + `ConfirmUrlCaptureUseCaseTest` |
