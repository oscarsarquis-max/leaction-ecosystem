package br.com.segsense.domain.opportunity;

public record GovernanceEffect(
    LifecycleEvent event, OpportunitySubmission submission, OpportunityDecision decision) {}
