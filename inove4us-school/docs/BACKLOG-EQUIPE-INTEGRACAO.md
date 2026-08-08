# Backlog — Equipe / ponte School ↔ Inove (B2C)

Pendências formalizadas a partir da revisão do módulo Equipe.  
**Não implementar neste ciclo** (reformulação Extrato Acadêmico). Viram prompts próprios depois do descritivo do Editor Pedagógico.

## Itens

1. **`professor_b2c_id` — id real no aceite de convite**  
   Etapa 13 (**feita**, migration `030`): coluna é `INTEGER` (= `ctdi_clie.id_clie`). Convite ainda grava placeholder **negativo** até existir fluxo de aceite que escreva o `id_clie` real.

2. **Transição `pendente → ativo`**  
   Não há endpoint na Equipe nem webhook B2C óbvio que promova o vínculo. Decisão de produto: o que dispara o aceite?

3. **`TEACHER_INVITE` no B2C só loga**  
   Convite não materializa conta no Inove. Depende de trabalho B2C (mesmo padrão do mural: `inove4us-20-mural-comunicacoes-escola.md`).

4. **Revogar não avisa o B2C**  
   Professor revogado no School continua “existindo” do ponto de vista do B2C.

## Próxima etapa de produto (fora deste backlog)

Descritivo + reformulação do Editor Pedagógico (Metodologias/PEI), depois prompts próprios para os gaps acima.
