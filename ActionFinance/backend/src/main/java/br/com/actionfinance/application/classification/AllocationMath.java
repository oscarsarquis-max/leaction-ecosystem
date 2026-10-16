package br.com.actionfinance.application.classification;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

public final class AllocationMath {

    public static final String CRITERION =
            "Fração inteira em centavos; o resíduo vai para a maior parcela e, no empate, para o menor código.";

    private AllocationMath() {}

    public record Share(String initiativeId, String code, int basisPoints) {}

    public record Portion(String initiativeId, String code, int basisPoints, long amountMinor, boolean residue) {}

    public static List<Portion> split(long basisMinor, List<Share> shares) {
        if (basisMinor < 0) {
            throw new IllegalArgumentException("base negativa");
        }
        int points = 0;
        for (Share share : shares) {
            if (share.basisPoints() <= 0) {
                throw new IllegalArgumentException("parcela inválida");
            }
            points += share.basisPoints();
        }
        if (points <= 0 || points > 10000) {
            throw new IllegalArgumentException("percentual fora de 0 a 100");
        }
        List<Share> ordered = new ArrayList<>(shares);
        ordered.sort(Comparator.comparingInt(Share::basisPoints).reversed().thenComparing(Share::code));
        long[] amounts = new long[ordered.size()];
        long used = 0;
        for (int index = 0; index < ordered.size(); index++) {
            amounts[index] = basisMinor * ordered.get(index).basisPoints() / 10000L;
            used += amounts[index];
        }
        long residue = basisMinor - used;
        if (points == 10000 && residue != 0 && amounts.length > 0) {
            amounts[0] += residue;
        }
        long unassigned = points == 10000 ? 0 : basisMinor - used;
        List<Portion> portions = new ArrayList<>();
        for (int index = 0; index < ordered.size(); index++) {
            Share share = ordered.get(index);
            boolean gotResidue = points == 10000 && index == 0 && residue != 0;
            portions.add(new Portion(share.initiativeId(), share.code(), share.basisPoints(), amounts[index], gotResidue));
        }
        if (unassigned > 0) {
            portions.add(new Portion(null, "", 10000 - points, unassigned, false));
        }
        long total = portions.stream().mapToLong(Portion::amountMinor).sum();
        if (total != basisMinor) {
            throw new IllegalStateException("A soma das parcelas não fecha a base.");
        }
        return List.copyOf(portions);
    }
}
