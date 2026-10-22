package br.com.actionfinance.application.finance;

public record AccountContactInput(
        String personName, String role, String email, String phone, boolean primaryContact, String association) {}
