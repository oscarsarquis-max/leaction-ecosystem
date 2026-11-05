# Processo da Gestão

Cada ciclo da Loja de Pães – Gestão segue estas regras.

1. **O ciclo sai da branch em produção.** A branch nova nasce do commit que está no ar, não de uma `main` local desatualizada.
2. **O retorno e as capturas entram no mesmo commit do ciclo.** `docs/retornos/` e `docs/evidence/` acompanham o código. Não ficam só na pasta de trabalho.
3. **A pasta de trabalho termina na branch publicada.** `C:\Projetos\lojadepaes-gestao` fica nessa branch, com `git status` limpo.
4. **Depois do aceite do Oscar, o merge vai para a `main` por PR.** Quem aprova é o Oscar. O PR não é mergeado no meio do ciclo.
