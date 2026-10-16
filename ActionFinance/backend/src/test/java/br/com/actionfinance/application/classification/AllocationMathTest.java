package br.com.actionfinance.application.classification;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class AllocationMathTest {

    @Test
    void splitsTenReaisAndOneCentByStableCode() {
        List<AllocationMath.Portion> portions = AllocationMath.split(1001, List.of(
                new AllocationMath.Share("b", "BETA", 5000),
                new AllocationMath.Share("a", "ALFA", 5000)));
        assertThat(portions).extracting(AllocationMath.Portion::code).containsExactly("ALFA", "BETA");
        assertThat(portions).extracting(AllocationMath.Portion::amountMinor).containsExactly(501L, 500L);
        assertThat(portions.get(0).residue()).isTrue();
    }

    @Test
    void keepsAnExplicitUnassignedRemainder() {
        List<AllocationMath.Portion> portions = AllocationMath.split(1000, List.of(
                new AllocationMath.Share("a", "ALFA", 2500)));
        assertThat(portions).extracting(AllocationMath.Portion::amountMinor).containsExactly(250L, 750L);
        assertThat(portions.get(1).initiativeId()).isNull();
    }
}
