package br.com.actionfinance.domain;

public enum CategoryDirection {
    RECEIVABLE,
    PAYABLE,
    BOTH;

    public boolean supports(TitleDirection direction) {
        return this == BOTH || name().equals(direction.name());
    }
}
