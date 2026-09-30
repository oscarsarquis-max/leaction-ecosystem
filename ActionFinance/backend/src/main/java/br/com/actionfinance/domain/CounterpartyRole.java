package br.com.actionfinance.domain;

public enum CounterpartyRole {
    CUSTOMER,
    SUPPLIER,
    BOTH;

    public boolean supports(TitleDirection direction) {
        return this == BOTH
                || (this == CUSTOMER && direction == TitleDirection.RECEIVABLE)
                || (this == SUPPLIER && direction == TitleDirection.PAYABLE);
    }
}
