-- PRM_016: demo journey statuses for insufficient/ambiguous context. V1–V13 unchanged.

ALTER TABLE segsense.demo_protection_journey
    DROP CONSTRAINT demo_protection_journey_status_chk;

ALTER TABLE segsense.demo_protection_journey
    ADD CONSTRAINT demo_protection_journey_status_chk CHECK (
        status IN (
            'SUBMITTED',
            'SPIDER_DECISION',
            'PRE_PROPOSAL_AVAILABLE',
            'REJECTED',
            'SPIDER_UNAVAILABLE',
            'MOCK_UNAVAILABLE',
            'INCOMPLETE_CANONICAL',
            'MISSING_CONTEXT',
            'AMBIGUOUS'
        )
    );
