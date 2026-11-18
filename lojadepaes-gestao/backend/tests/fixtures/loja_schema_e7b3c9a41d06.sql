-- Esquema da Loja de Paes (somente DDL, sem dados) na versao Alembic e7b3c9a41d06.
-- Referencia de contrato para os testes do Gestao. Gerado por pg_dump --schema-only de uma copia
-- local da Loja; nunca aplicado na Loja. Regenerar quando a Loja mudar de cabeca do Alembic.

--
-- PostgreSQL database dump
--


-- Dumped from database version 16.14 (Debian 16.14-1.pgdg13+1)
-- Dumped by pg_dump version 16.14 (Debian 16.14-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: set_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.set_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: accompaniment_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.accompaniment_items (
    id uuid NOT NULL,
    hub_offer_id character varying(80) NOT NULL,
    hub_source character varying(40) DEFAULT 'mercadolivre'::character varying NOT NULL,
    snapshot_title character varying(240) DEFAULT ''::character varying NOT NULL,
    snapshot_description text DEFAULT ''::text NOT NULL,
    snapshot_image_url character varying(500),
    snapshot_price_amount numeric(12,2),
    snapshot_price_currency character varying(8) DEFAULT 'BRL'::character varying NOT NULL,
    snapshot_link text,
    snapshot_fetched_at timestamp with time zone,
    occasion character varying(80) DEFAULT ''::character varying NOT NULL,
    story_title character varying(160) DEFAULT ''::character varying NOT NULL,
    story_lead text DEFAULT ''::text NOT NULL,
    why_pairs text DEFAULT ''::text NOT NULL,
    serving_tip text DEFAULT ''::text NOT NULL,
    related_product_slugs json DEFAULT '[]'::json NOT NULL,
    related_recipe_slugs json DEFAULT '[]'::json NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    published boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_accompaniment_hub_id CHECK (((char_length((hub_offer_id)::text) >= 1) AND (char_length((hub_offer_id)::text) <= 80))),
    CONSTRAINT ck_accompaniment_sort CHECK ((sort_order >= 0))
);


--
-- Name: admin_accounts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admin_accounts (
    id uuid NOT NULL,
    username character varying(80) NOT NULL,
    password_hash text,
    password_set_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: admin_activation_dispatches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admin_activation_dispatches (
    id uuid NOT NULL,
    username character varying(80) NOT NULL,
    recipient character varying(254) NOT NULL,
    provider_message_id character varying(200),
    status character varying(32) NOT NULL,
    sent_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: admin_activation_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admin_activation_tokens (
    id uuid NOT NULL,
    username character varying(80) NOT NULL,
    token_hash character varying(64) NOT NULL,
    purpose character varying(40) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    consumed_at timestamp with time zone,
    invalidated_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: admin_login_attempts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admin_login_attempts (
    username character varying(80) NOT NULL,
    client_host character varying(80) NOT NULL,
    succeeded boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    id uuid NOT NULL
);


--
-- Name: admin_push_subscriptions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admin_push_subscriptions (
    id uuid NOT NULL,
    actor_ref character varying(120) NOT NULL,
    endpoint text NOT NULL,
    endpoint_hash character varying(64) NOT NULL,
    p256dh character varying(200) NOT NULL,
    auth_secret character varying(200) NOT NULL,
    label character varying(40) NOT NULL,
    active boolean NOT NULL,
    failure_count integer NOT NULL,
    last_error character varying(280),
    revoked_at timestamp with time zone,
    revoked_reason character varying(120),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: admin_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.admin_sessions (
    token_hash character varying(64) NOT NULL,
    csrf_token_hash character varying(64) NOT NULL,
    username character varying(80) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    last_seen_at timestamp with time zone NOT NULL,
    revoked_at timestamp with time zone,
    client_host character varying(80),
    id uuid NOT NULL
);


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: allergens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.allergens (
    name character varying(120) NOT NULL,
    slug character varying(80) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: articles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.articles (
    title character varying(160) NOT NULL,
    slug character varying(80) NOT NULL,
    summary character varying(400) NOT NULL,
    body_markdown text NOT NULL,
    category character varying(40) NOT NULL,
    cover_image_ref character varying(500),
    editorial_status character varying(20) NOT NULL,
    published_at timestamp with time zone,
    estimated_reading_minutes integer,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_articles_editorial_status CHECK (((editorial_status)::text = ANY ((ARRAY['draft'::character varying, 'published'::character varying, 'archived'::character varying])::text[]))),
    CONSTRAINT ck_articles_reading_minutes CHECK (((estimated_reading_minutes IS NULL) OR (estimated_reading_minutes > 0)))
);


--
-- Name: bread_shapes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bread_shapes (
    name character varying(120) NOT NULL,
    slug character varying(80) NOT NULL,
    description character varying(280) NOT NULL,
    crust_crumb_notes text NOT NULL,
    image_ref character varying(500),
    sort_order integer NOT NULL,
    is_active boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: customer_accounts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customer_accounts (
    id uuid NOT NULL,
    name character varying(160) NOT NULL,
    email character varying(254) NOT NULL,
    email_verified_at timestamp with time zone,
    cpf_hmac character varying(64) NOT NULL,
    cpf_last2 character varying(2) NOT NULL,
    marketing_opt_in boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: customer_challenges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customer_challenges (
    id uuid NOT NULL,
    account_id uuid,
    email character varying(254) NOT NULL,
    purpose character varying(20) NOT NULL,
    code_hash character varying(64) NOT NULL,
    token_hash character varying(64) NOT NULL,
    attempts integer DEFAULT 0 NOT NULL,
    max_attempts integer DEFAULT 5 NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    consumed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: customer_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customer_sessions (
    id uuid NOT NULL,
    account_id uuid NOT NULL,
    token_hash character varying(64) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    revoked_at timestamp with time zone
);


--
-- Name: date_request_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.date_request_events (
    id uuid NOT NULL,
    request_id uuid NOT NULL,
    action character varying(40) NOT NULL,
    actor_ref character varying(80),
    detail text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: date_requests; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.date_requests (
    id uuid NOT NULL,
    desired_date date NOT NULL,
    customer_name character varying(160) NOT NULL,
    customer_email character varying(254) NOT NULL,
    intended_quantity integer,
    message text,
    status character varying(32) NOT NULL,
    proposed_date date,
    admin_note text,
    cart_context jsonb,
    idempotency_key character varying(120) NOT NULL,
    client_host character varying(80) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    closed_at timestamp with time zone,
    converted_order_id uuid,
    accept_authorized_at timestamp with time zone,
    complement json,
    CONSTRAINT ck_date_requests_quantity CHECK (((intended_quantity IS NULL) OR (intended_quantity >= 1))),
    CONSTRAINT ck_date_requests_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'alternative_proposed'::character varying, 'awaiting_details'::character varying, 'converted'::character varying, 'closed'::character varying])::text[])))
);


--
-- Name: dough_allergens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dough_allergens (
    dough_type_id uuid NOT NULL,
    allergen_id uuid NOT NULL,
    presence character varying(20) NOT NULL,
    is_reviewed boolean NOT NULL,
    id uuid NOT NULL,
    CONSTRAINT ck_dough_allergens_presence CHECK (((presence)::text = ANY ((ARRAY['contains'::character varying, 'may_contain'::character varying])::text[])))
);


--
-- Name: dough_ingredient_compatibilities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dough_ingredient_compatibilities (
    dough_type_id uuid NOT NULL,
    ingredient_id uuid NOT NULL,
    id uuid NOT NULL
);


--
-- Name: dough_shape_compatibilities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dough_shape_compatibilities (
    dough_type_id uuid NOT NULL,
    bread_shape_id uuid NOT NULL,
    id uuid NOT NULL
);


--
-- Name: dough_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dough_types (
    name character varying(120) NOT NULL,
    slug character varying(80) NOT NULL,
    short_description character varying(280) NOT NULL,
    story text,
    fermentation_hours integer,
    image_ref character varying(500),
    sort_order integer NOT NULL,
    is_active boolean NOT NULL,
    base_price_cents integer,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    recipe_base_id uuid,
    creator_kind character varying(20),
    CONSTRAINT ck_dough_types_base_price_cents CHECK (((base_price_cents IS NULL) OR (base_price_cents >= 0))),
    CONSTRAINT ck_dough_types_creator_kind CHECK (((creator_kind IS NULL) OR ((creator_kind)::text = ANY ((ARRAY['preparation'::character varying, 'retired_mass'::character varying])::text[])))),
    CONSTRAINT ck_dough_types_fermentation_hours CHECK (((fermentation_hours IS NULL) OR (fermentation_hours > 0)))
);


--
-- Name: email_outbox; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.email_outbox (
    id uuid NOT NULL,
    order_id uuid,
    kind character varying(40) NOT NULL,
    to_address character varying(254) NOT NULL,
    subject character varying(180) NOT NULL,
    body text NOT NULL,
    status character varying(20) NOT NULL,
    attempts integer NOT NULL,
    last_error text,
    dedupe_key character varying(160) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    sent_at timestamp with time zone,
    provider_message_id character varying(200),
    date_request_id uuid,
    CONSTRAINT ck_email_outbox_attempts CHECK ((attempts >= 0)),
    CONSTRAINT ck_email_outbox_kind CHECK (((kind)::text = ANY ((ARRAY['order_submitted'::character varying, 'payment_approved'::character varying, 'order_accepted'::character varying, 'date_request_received'::character varying, 'date_request_proposed'::character varying, 'adaptation_proposed'::character varying, 'customer_verify'::character varying, 'customer_resume'::character varying, 'order_submitted_admin'::character varying, 'date_request_received_admin'::character varying, 'date_request_available'::character varying, 'date_request_declined'::character varying, 'adaptation_customer_replied_admin'::character varying, 'ops_attendance_summary'::character varying, 'order_auto_accepted_admin'::character varying, 'date_request_complete'::character varying, 'acceptance_update_admin'::character varying, 'payment_sync_alert'::character varying, 'order_date_changed'::character varying])::text[]))),
    CONSTRAINT ck_email_outbox_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'skipped'::character varying, 'sent'::character varying, 'failed'::character varying])::text[])))
);


--
-- Name: fulfillment_slots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fulfillment_slots (
    production_batch_id uuid NOT NULL,
    starts_at timestamp with time zone NOT NULL,
    ends_at timestamp with time zone NOT NULL,
    capacity_units integer NOT NULL,
    is_active boolean NOT NULL,
    modality character varying(20) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_fulfillment_slots_capacity CHECK ((capacity_units > 0)),
    CONSTRAINT ck_fulfillment_slots_modality CHECK (((modality)::text = ANY ((ARRAY['pickup'::character varying, 'delivery'::character varying])::text[]))),
    CONSTRAINT ck_fulfillment_slots_window CHECK ((starts_at < ends_at))
);


--
-- Name: gigio_credit_operations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gigio_credit_operations (
    operation_id character varying(80) NOT NULL,
    subject_hmac character varying(64),
    status character varying(20) NOT NULL,
    reply_json text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: gigio_editorial_notes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gigio_editorial_notes (
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    topic_key character varying(80) NOT NULL,
    title character varying(160) NOT NULL,
    body text NOT NULL,
    editorial_status character varying(16) DEFAULT 'draft'::character varying NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    CONSTRAINT ck_gigio_editorial_status CHECK (((editorial_status)::text = ANY ((ARRAY['draft'::character varying, 'published'::character varying])::text[]))),
    CONSTRAINT ck_gigio_editorial_title CHECK (((char_length((title)::text) >= 1) AND (char_length((title)::text) <= 160))),
    CONSTRAINT ck_gigio_editorial_topic CHECK (((char_length((topic_key)::text) >= 1) AND (char_length((topic_key)::text) <= 80)))
);


--
-- Name: gigio_pairing_references; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gigio_pairing_references (
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    profile_key character varying(80) NOT NULL,
    category character varying(16) NOT NULL,
    scope character varying(16) NOT NULL,
    title character varying(160) NOT NULL,
    synthesis text NOT NULL,
    editorial_note text DEFAULT ''::text NOT NULL,
    characteristics jsonb DEFAULT '{}'::jsonb NOT NULL,
    culinary_contexts jsonb DEFAULT '{}'::jsonb NOT NULL,
    match_hints jsonb DEFAULT '[]'::jsonb NOT NULL,
    identity jsonb DEFAULT '{}'::jsonb NOT NULL,
    source_url character varying(500) NOT NULL,
    source_title character varying(240) NOT NULL,
    source_author character varying(160) DEFAULT ''::character varying NOT NULL,
    source_date character varying(32) DEFAULT ''::character varying NOT NULL,
    consulted_at character varying(32) NOT NULL,
    source_kind character varying(32) NOT NULL,
    commercial_relation character varying(40) DEFAULT 'unknown'::character varying NOT NULL,
    editorial_status character varying(16) DEFAULT 'draft'::character varying NOT NULL,
    reviewed_by character varying(80) DEFAULT ''::character varying NOT NULL,
    reviewed_at character varying(32) DEFAULT ''::character varying NOT NULL,
    loja_choice boolean DEFAULT false NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    evidence_type character varying(32) DEFAULT 'style_unverified'::character varying NOT NULL,
    retrieval_role character varying(16) DEFAULT 'excluded'::character varying NOT NULL,
    verification_status character varying(16) DEFAULT 'pending'::character varying NOT NULL,
    support_locator text DEFAULT ''::text NOT NULL,
    claim_layers jsonb DEFAULT '{}'::jsonb NOT NULL,
    CONSTRAINT ck_gigio_pairing_category CHECK (((category)::text = ANY ((ARRAY['vinhos'::character varying, 'queijos'::character varying, 'azeites'::character varying, 'frios'::character varying])::text[]))),
    CONSTRAINT ck_gigio_pairing_evidence CHECK (((evidence_type)::text = ANY ((ARRAY['pairing_recommendation'::character varying, 'official_register'::character varying, 'research_project'::character varying, 'method_help'::character varying, 'style_unverified'::character varying, 'guide_evaluation'::character varying])::text[]))),
    CONSTRAINT ck_gigio_pairing_profile CHECK (((char_length((profile_key)::text) >= 1) AND (char_length((profile_key)::text) <= 80))),
    CONSTRAINT ck_gigio_pairing_retrieval CHECK (((retrieval_role)::text = ANY ((ARRAY['pairing'::character varying, 'informational'::character varying, 'excluded'::character varying, 'evaluation'::character varying])::text[]))),
    CONSTRAINT ck_gigio_pairing_scope CHECK (((scope)::text = ANY ((ARRAY['general'::character varying, 'style'::character varying, 'product'::character varying])::text[]))),
    CONSTRAINT ck_gigio_pairing_source_kind CHECK (((source_kind)::text = ANY ((ARRAY['commercial'::character varying, 'independent'::character varying, 'producer'::character varying, 'commercial_editorial'::character varying, 'official_register'::character varying, 'research_institution'::character varying])::text[]))),
    CONSTRAINT ck_gigio_pairing_status CHECK (((editorial_status)::text = ANY ((ARRAY['draft'::character varying, 'reviewed'::character varying, 'published'::character varying, 'archived'::character varying])::text[]))),
    CONSTRAINT ck_gigio_pairing_title CHECK (((char_length((title)::text) >= 1) AND (char_length((title)::text) <= 160))),
    CONSTRAINT ck_gigio_pairing_verification CHECK (((verification_status)::text = ANY ((ARRAY['verified'::character varying, 'pending'::character varying, 'inaccessible'::character varying])::text[])))
);


--
-- Name: gigio_usage_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gigio_usage_events (
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    origin character varying(20) NOT NULL,
    function character varying(32) NOT NULL,
    ok boolean NOT NULL,
    duration_ms integer NOT NULL,
    tokens_in integer,
    tokens_out integer,
    fail_kind character varying(40),
    subject_hmac character varying(64),
    article_id character varying(80),
    provider character varying(20)
);


--
-- Name: house_fidelity_adjustments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.house_fidelity_adjustments (
    id uuid NOT NULL,
    campaign_id uuid NOT NULL,
    account_id uuid NOT NULL,
    kind character varying(24) NOT NULL,
    reason character varying(280) NOT NULL,
    actor_ref character varying(80) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: house_fidelity_campaigns; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.house_fidelity_campaigns (
    id uuid NOT NULL,
    slug character varying(80) NOT NULL,
    version integer NOT NULL,
    status character varying(20) NOT NULL,
    rules_version character varying(20) NOT NULL,
    title character varying(160) NOT NULL,
    starts_at timestamp with time zone,
    rules_json text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    rules_effective_at timestamp with time zone,
    CONSTRAINT ck_house_fidelity_campaigns_status CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'paused'::character varying, 'active'::character varying])::text[])))
);


--
-- Name: house_fidelity_credits; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.house_fidelity_credits (
    id uuid NOT NULL,
    campaign_id uuid NOT NULL,
    account_id uuid NOT NULL,
    source_event_id uuid NOT NULL,
    cycle_year integer NOT NULL,
    cycle_month integer NOT NULL,
    group_index integer NOT NULL,
    status character varying(16) NOT NULL,
    reserved_order_id uuid,
    used_order_id uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_house_fidelity_credits_status CHECK (((status)::text = ANY ((ARRAY['available'::character varying, 'reserved'::character varying, 'used'::character varying, 'returned'::character varying])::text[])))
);


--
-- Name: house_fidelity_enrollments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.house_fidelity_enrollments (
    id uuid NOT NULL,
    account_id uuid NOT NULL,
    campaign_id uuid NOT NULL,
    rules_version character varying(20) NOT NULL,
    enrolled_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: house_fidelity_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.house_fidelity_events (
    id uuid NOT NULL,
    campaign_id uuid NOT NULL,
    account_id uuid NOT NULL,
    order_id uuid,
    kind character varying(24) NOT NULL,
    status character varying(16) NOT NULL,
    cycle_year integer NOT NULL,
    cycle_month integer NOT NULL,
    eligible_at timestamp with time zone NOT NULL,
    reason character varying(280) DEFAULT ''::character varying NOT NULL,
    actor_ref character varying(80),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_house_fidelity_events_kind CHECK (((kind)::text = ANY ((ARRAY['qualify'::character varying, 'reverse'::character varying, 'manual_grant'::character varying, 'manual_reverse'::character varying, 'partial_review'::character varying])::text[]))),
    CONSTRAINT ck_house_fidelity_events_status CHECK (((status)::text = ANY ((ARRAY['applied'::character varying, 'reversed'::character varying, 'pending'::character varying])::text[])))
);


--
-- Name: house_fidelity_rule_changes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.house_fidelity_rule_changes (
    id uuid NOT NULL,
    campaign_id uuid NOT NULL,
    previous_rules_version character varying(20) NOT NULL,
    new_rules_version character varying(20) NOT NULL,
    previous_rules_json text NOT NULL,
    new_rules_json text NOT NULL,
    starts_at_preserved timestamp with time zone,
    effective_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: hub_authorization_cache; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.hub_authorization_cache (
    subject_hmac character varying(64) NOT NULL,
    app_id character varying(40) NOT NULL,
    active boolean NOT NULL,
    plan_sku character varying(80),
    valid_until timestamp with time zone,
    checked_at timestamp with time zone NOT NULL,
    source character varying(20) NOT NULL
);


--
-- Name: hub_plans_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.hub_plans_events (
    event_id character varying(120) NOT NULL,
    event_type character varying(80) NOT NULL,
    subject_hmac character varying(64),
    business_status character varying(40),
    issued_at timestamp with time zone,
    received_at timestamp with time zone NOT NULL,
    process_status character varying(20) NOT NULL,
    payload_json text
);


--
-- Name: ingredient_allergens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ingredient_allergens (
    ingredient_id uuid NOT NULL,
    allergen_id uuid NOT NULL,
    presence character varying(20) NOT NULL,
    is_reviewed boolean NOT NULL,
    id uuid NOT NULL,
    CONSTRAINT ck_ingredient_allergens_presence CHECK (((presence)::text = ANY ((ARRAY['contains'::character varying, 'may_contain'::character varying])::text[])))
);


--
-- Name: ingredients; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ingredients (
    name character varying(120) NOT NULL,
    slug character varying(80) NOT NULL,
    description character varying(280) NOT NULL,
    image_ref character varying(500),
    sort_order integer NOT NULL,
    is_active boolean NOT NULL,
    surcharge_cents integer,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    assistant_role character varying(20) DEFAULT 'inclusion'::character varying NOT NULL,
    CONSTRAINT ck_ingredients_assistant_role CHECK (((assistant_role)::text = ANY ((ARRAY['flour'::character varying, 'inclusion'::character varying])::text[]))),
    CONSTRAINT ck_ingredients_surcharge_cents CHECK (((surcharge_cents IS NULL) OR (surcharge_cents >= 0)))
);


--
-- Name: inspiration_posts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inspiration_posts (
    title character varying(160) NOT NULL,
    slug character varying(80) NOT NULL,
    caption text NOT NULL,
    image_ref character varying(500),
    credit character varying(160),
    source_url character varying(500),
    source_kind character varying(20) NOT NULL,
    editorial_status character varying(20) NOT NULL,
    published_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_inspiration_editorial_status CHECK (((editorial_status)::text = ANY ((ARRAY['draft'::character varying, 'published'::character varying, 'archived'::character varying])::text[]))),
    CONSTRAINT ck_inspiration_source_kind CHECK (((source_kind)::text = ANY ((ARRAY['editorial'::character varying, 'community'::character varying])::text[])))
);


--
-- Name: managerial_exclusions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.managerial_exclusions (
    id uuid NOT NULL,
    subject_type character varying(20) NOT NULL,
    subject_id uuid NOT NULL,
    reason character varying(280) NOT NULL,
    author_ref character varying(120) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    reversed_at timestamp with time zone,
    reversed_by character varying(120),
    reverse_reason character varying(280),
    kind character varying(20) DEFAULT 'test'::character varying NOT NULL,
    original_order_id uuid,
    CONSTRAINT ck_managerial_exclusions_kind CHECK (((kind)::text = ANY ((ARRAY['test'::character varying, 'duplicate'::character varying])::text[]))),
    CONSTRAINT ck_managerial_exclusions_subject CHECK (((subject_type)::text = ANY ((ARRAY['order'::character varying, 'date_request'::character varying])::text[])))
);


--
-- Name: media_assets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.media_assets (
    stored_name character varying(80) NOT NULL,
    content_type character varying(32) NOT NULL,
    byte_size integer NOT NULL,
    width integer NOT NULL,
    height integer NOT NULL,
    created_by_ref character varying(80),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    id uuid NOT NULL,
    object_key character varying(240) NOT NULL,
    storage_backend character varying(16) DEFAULT 'local'::character varying NOT NULL,
    CONSTRAINT ck_media_assets_backend CHECK (((storage_backend)::text = ANY ((ARRAY['local'::character varying, 's3'::character varying])::text[]))),
    CONSTRAINT ck_media_assets_content_type CHECK (((content_type)::text = ANY ((ARRAY['image/jpeg'::character varying, 'image/png'::character varying, 'image/webp'::character varying])::text[]))),
    CONSTRAINT ck_media_assets_dimensions CHECK (((width > 0) AND (height > 0))),
    CONSTRAINT ck_media_assets_size CHECK ((byte_size > 0))
);


--
-- Name: ops_channel_settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ops_channel_settings (
    channel character varying(20) NOT NULL,
    destination character varying(40) DEFAULT ''::character varying NOT NULL,
    enabled boolean DEFAULT false NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_by character varying(120) DEFAULT ''::character varying NOT NULL,
    CONSTRAINT ck_ops_channel_settings_channel CHECK (((channel)::text = 'whatsapp'::text))
);


--
-- Name: ops_owner_alerts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ops_owner_alerts (
    id uuid NOT NULL,
    channel character varying(20) NOT NULL,
    event_key character varying(160) NOT NULL,
    kind character varying(40) NOT NULL,
    order_id uuid,
    date_request_id uuid,
    status character varying(20) NOT NULL,
    summary character varying(500) NOT NULL,
    last_error character varying(280),
    attempts integer DEFAULT 0 NOT NULL,
    provider_reference character varying(120),
    email_outbox_id uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_ops_owner_alerts_channel CHECK (((channel)::text = ANY ((ARRAY['email'::character varying, 'whatsapp'::character varying])::text[]))),
    CONSTRAINT ck_ops_owner_alerts_status CHECK (((status)::text = ANY ((ARRAY['awaiting'::character varying, 'accepted'::character varying, 'delivered'::character varying, 'failed'::character varying, 'disabled'::character varying])::text[])))
);


--
-- Name: ops_push_deliveries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ops_push_deliveries (
    id uuid NOT NULL,
    event_key character varying(160) NOT NULL,
    subscription_id uuid NOT NULL,
    kind character varying(40) NOT NULL,
    status character varying(20) NOT NULL,
    title character varying(120) NOT NULL,
    body character varying(180) NOT NULL,
    path character varying(200) NOT NULL,
    attempts integer NOT NULL,
    last_error character varying(280),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_ops_push_deliveries_status CHECK (((status)::text = ANY ((ARRAY['awaiting'::character varying, 'accepted'::character varying, 'failed'::character varying, 'inactive'::character varying])::text[])))
);


--
-- Name: order_internal_notes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.order_internal_notes (
    order_id uuid NOT NULL,
    body text NOT NULL,
    author_ref character varying(80),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    id uuid NOT NULL,
    CONSTRAINT ck_order_internal_notes_body CHECK (((char_length(body) >= 1) AND (char_length(body) <= 2000)))
);


--
-- Name: order_item_adaptation_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.order_item_adaptation_events (
    id uuid NOT NULL,
    adaptation_id uuid NOT NULL,
    from_status character varying(40),
    to_status character varying(40) NOT NULL,
    actor_kind character varying(20) NOT NULL,
    actor_ref character varying(80),
    note character varying(2000),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_item_adaptation_events_actor CHECK (((actor_kind)::text = ANY ((ARRAY['customer'::character varying, 'bakery'::character varying])::text[])))
);


--
-- Name: order_item_adaptations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.order_item_adaptations (
    id uuid NOT NULL,
    order_item_id uuid NOT NULL,
    customer_text character varying(500) NOT NULL,
    reason character varying(40),
    status character varying(40) DEFAULT 'pending'::character varying NOT NULL,
    bakery_response character varying(2000) DEFAULT ''::character varying NOT NULL,
    client_decision character varying(40),
    client_decided_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_item_adaptations_client_decision CHECK (((client_decision IS NULL) OR ((client_decision)::text = ANY ((ARRAY['accepted_alternative'::character varying, 'declined'::character varying])::text[])))),
    CONSTRAINT ck_item_adaptations_customer_text CHECK (((char_length((customer_text)::text) >= 1) AND (char_length((customer_text)::text) <= 500))),
    CONSTRAINT ck_item_adaptations_reason CHECK (((reason IS NULL) OR ((reason)::text = ANY ((ARRAY['preference'::character varying, 'dietary_restriction'::character varying])::text[])))),
    CONSTRAINT ck_item_adaptations_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'accepted'::character varying, 'alternative_proposed'::character varying, 'declined'::character varying, 'alternative_accepted'::character varying])::text[])))
);


--
-- Name: order_item_ingredients; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.order_item_ingredients (
    order_item_id uuid NOT NULL,
    ingredient_id uuid NOT NULL,
    name_snapshot character varying(120),
    surcharge_cents integer,
    id uuid NOT NULL,
    CONSTRAINT ck_order_item_ingredients_surcharge CHECK (((surcharge_cents IS NULL) OR (surcharge_cents >= 0)))
);


--
-- Name: order_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.order_items (
    order_id uuid NOT NULL,
    dough_type_id uuid,
    bread_shape_id uuid,
    quantity integer NOT NULL,
    dough_name_snapshot character varying(120),
    shape_name_snapshot character varying(120),
    unit_price_cents integer,
    line_total_cents integer,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    product_id uuid,
    product_variant_id uuid,
    recipe_base_id uuid,
    physical_units integer,
    net_weight_grams integer,
    CONSTRAINT ck_order_items_line_total CHECK (((line_total_cents IS NULL) OR (line_total_cents >= 0))),
    CONSTRAINT ck_order_items_origin CHECK ((((dough_type_id IS NOT NULL) AND (bread_shape_id IS NOT NULL) AND (product_variant_id IS NULL)) OR ((product_id IS NOT NULL) AND (product_variant_id IS NOT NULL)))),
    CONSTRAINT ck_order_items_physical_units CHECK (((physical_units IS NULL) OR (physical_units > 0))),
    CONSTRAINT ck_order_items_quantity CHECK ((quantity > 0)),
    CONSTRAINT ck_order_items_unit_price CHECK (((unit_price_cents IS NULL) OR (unit_price_cents >= 0)))
);


--
-- Name: order_status_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.order_status_history (
    order_id uuid NOT NULL,
    from_status character varying(20),
    to_status character varying(20) NOT NULL,
    reason character varying(280),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    id uuid NOT NULL,
    actor_ref character varying(80),
    CONSTRAINT ck_order_status_history_from CHECK (((from_status IS NULL) OR ((from_status)::text = ANY ((ARRAY['draft'::character varying, 'submitted'::character varying, 'confirmed'::character varying, 'in_production'::character varying, 'ready'::character varying, 'completed'::character varying, 'cancelled'::character varying])::text[])))),
    CONSTRAINT ck_order_status_history_to CHECK (((to_status)::text = ANY ((ARRAY['draft'::character varying, 'submitted'::character varying, 'confirmed'::character varying, 'in_production'::character varying, 'ready'::character varying, 'completed'::character varying, 'cancelled'::character varying])::text[])))
);


--
-- Name: orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.orders (
    public_reference character varying(20) NOT NULL,
    status character varying(20) NOT NULL,
    fulfillment_modality character varying(20),
    fulfillment_slot_id uuid,
    production_batch_id uuid,
    identity_subject_id uuid,
    customer_name character varying(160),
    customer_email character varying(254),
    customer_phone character varying(40),
    delivery_street character varying(160),
    delivery_number character varying(20),
    delivery_complement character varying(80),
    delivery_district character varying(80),
    delivery_city character varying(80),
    delivery_state character varying(2),
    delivery_postal_code character varying(12),
    customer_note character varying(2000) NOT NULL,
    currency character varying(3) NOT NULL,
    subtotal_cents integer,
    delivery_fee_cents integer,
    discount_cents integer,
    total_cents integer,
    confirmed_at timestamp with time zone,
    cancelled_at timestamp with time zone,
    production_started_at timestamp with time zone,
    ready_at timestamp with time zone,
    completed_at timestamp with time zone,
    cancellation_reason character varying(280),
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    holds_capacity boolean DEFAULT false NOT NULL,
    production_local_date date,
    access_token_hash character varying(64),
    submit_idempotency_key character varying(120),
    proposed_production_date date,
    crm_id_sessao character varying(36),
    preferred_time time without time zone,
    order_kind character varying(20) DEFAULT 'standard'::character varying NOT NULL,
    fulfilled_at timestamp with time zone,
    fidelity_account_id uuid,
    fidelity_campaign_id uuid,
    fidelity_rules_version character varying(20),
    fidelity_opt_in boolean DEFAULT false NOT NULL,
    fidelity_credit_id uuid,
    fidelity_qualifies boolean,
    source_date_request_id uuid,
    delivery_confirmed_at timestamp with time zone,
    requested_date date,
    date_change_origin character varying(20),
    date_change_reason character varying(280),
    date_change_actor character varying(120),
    CONSTRAINT ck_orders_currency CHECK (((currency)::text = 'BRL'::text)),
    CONSTRAINT ck_orders_customer_note CHECK ((char_length((customer_note)::text) <= 2000)),
    CONSTRAINT ck_orders_date_change_origin CHECK (((date_change_origin IS NULL) OR ((date_change_origin)::text = ANY ((ARRAY['customer'::character varying, 'store'::character varying])::text[])))),
    CONSTRAINT ck_orders_delivery_fee CHECK (((delivery_fee_cents IS NULL) OR (delivery_fee_cents >= 0))),
    CONSTRAINT ck_orders_discount CHECK (((discount_cents IS NULL) OR (discount_cents >= 0))),
    CONSTRAINT ck_orders_kind CHECK (((order_kind)::text = ANY ((ARRAY['standard'::character varying, 'redemption'::character varying])::text[]))),
    CONSTRAINT ck_orders_modality CHECK (((fulfillment_modality IS NULL) OR ((fulfillment_modality)::text = ANY ((ARRAY['pickup'::character varying, 'delivery'::character varying])::text[])))),
    CONSTRAINT ck_orders_status CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'submitted'::character varying, 'confirmed'::character varying, 'in_production'::character varying, 'ready'::character varying, 'completed'::character varying, 'cancelled'::character varying])::text[]))),
    CONSTRAINT ck_orders_subtotal CHECK (((subtotal_cents IS NULL) OR (subtotal_cents >= 0))),
    CONSTRAINT ck_orders_total CHECK (((total_cents IS NULL) OR (total_cents >= 0)))
);


--
-- Name: pairing_tips; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pairing_tips (
    ingredient_id uuid NOT NULL,
    paired_ingredient_id uuid,
    message text NOT NULL,
    priority integer NOT NULL,
    is_active boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_pairing_tips_canonical_order CHECK (((paired_ingredient_id IS NULL) OR (ingredient_id < paired_ingredient_id))),
    CONSTRAINT ck_pairing_tips_not_self CHECK (((paired_ingredient_id IS NULL) OR (ingredient_id <> paired_ingredient_id)))
);


--
-- Name: payment_integration_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payment_integration_events (
    provider character varying(40) NOT NULL,
    external_event_id character varying(160) NOT NULL,
    payment_record_id uuid,
    external_type character varying(80),
    received_at timestamp with time zone NOT NULL,
    provider_occurred_at timestamp with time zone,
    process_status character varying(20) NOT NULL,
    sanitized_error text,
    id uuid NOT NULL,
    CONSTRAINT ck_payment_events_process_status CHECK (((process_status)::text = ANY ((ARRAY['received'::character varying, 'ignored'::character varying, 'applied'::character varying, 'failed'::character varying])::text[]))),
    CONSTRAINT ck_payment_events_provider CHECK (((provider)::text = 'actionhub'::text))
);


--
-- Name: payment_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payment_records (
    order_id uuid NOT NULL,
    provider character varying(40) NOT NULL,
    external_reference character varying(120),
    idempotency_key character varying(120),
    expected_cents integer NOT NULL,
    currency character varying(3) NOT NULL,
    financial_status character varying(32) NOT NULL,
    external_status_raw character varying(80),
    amount_paid_cents integer,
    amount_refunded_cents integer,
    confirmed_at timestamp with time zone,
    last_synced_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    sanitized_error text,
    method character varying(20),
    mp_payment_id character varying(80),
    pix_qr_code text,
    pix_qr_code_base64 text,
    pix_ticket_url text,
    pix_expires_at timestamp with time zone,
    CONSTRAINT ck_payment_records_currency CHECK (((currency)::text = 'BRL'::text)),
    CONSTRAINT ck_payment_records_expected CHECK ((expected_cents >= 0)),
    CONSTRAINT ck_payment_records_method CHECK (((method IS NULL) OR ((method)::text = ANY ((ARRAY['pix'::character varying, 'card'::character varying])::text[])))),
    CONSTRAINT ck_payment_records_paid CHECK (((amount_paid_cents IS NULL) OR (amount_paid_cents >= 0))),
    CONSTRAINT ck_payment_records_provider CHECK (((provider)::text = 'actionhub'::text)),
    CONSTRAINT ck_payment_records_refund_lte_paid CHECK (((amount_paid_cents IS NULL) OR (amount_refunded_cents IS NULL) OR (amount_refunded_cents <= amount_paid_cents))),
    CONSTRAINT ck_payment_records_refunded CHECK (((amount_refunded_cents IS NULL) OR (amount_refunded_cents >= 0))),
    CONSTRAINT ck_payment_records_status CHECK (((financial_status)::text = ANY ((ARRAY['pending'::character varying, 'paid'::character varying, 'failed'::character varying, 'cancelled'::character varying, 'partially_refunded'::character varying, 'refunded'::character varying, 'unknown'::character varying])::text[])))
);


--
-- Name: product_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.product_events (
    product_id uuid NOT NULL,
    action character varying(32) NOT NULL,
    actor_ref character varying(80),
    detail character varying(280),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    id uuid NOT NULL,
    CONSTRAINT ck_product_events_action CHECK (((action)::text = ANY ((ARRAY['created'::character varying, 'updated'::character varying, 'published'::character varying, 'unpublished'::character varying, 'archived'::character varying, 'availability'::character varying, 'image'::character varying])::text[])))
);


--
-- Name: product_ingredients; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.product_ingredients (
    product_id uuid NOT NULL,
    name character varying(120) NOT NULL,
    sort_order integer NOT NULL,
    catalog_ingredient_id uuid,
    id uuid NOT NULL,
    CONSTRAINT ck_product_ingredients_name CHECK (((char_length((name)::text) >= 1) AND (char_length((name)::text) <= 120)))
);


--
-- Name: product_variants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.product_variants (
    product_id uuid NOT NULL,
    display_name character varying(80) NOT NULL,
    presentation_type character varying(20) NOT NULL,
    net_weight_grams integer,
    units_per_pack integer,
    price_cents integer,
    currency character varying(3) DEFAULT 'BRL'::character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    physical_units integer,
    CONSTRAINT ck_product_variants_currency CHECK (((currency)::text = 'BRL'::text)),
    CONSTRAINT ck_product_variants_measures CHECK (((((presentation_type)::text = 'weight'::text) AND (net_weight_grams IS NOT NULL) AND (net_weight_grams > 0) AND (units_per_pack IS NULL)) OR (((presentation_type)::text = 'pack'::text) AND (units_per_pack IS NOT NULL) AND (units_per_pack > 0) AND (net_weight_grams IS NULL)))),
    CONSTRAINT ck_product_variants_physical_units CHECK (((physical_units IS NULL) OR (physical_units > 0))),
    CONSTRAINT ck_product_variants_presentation CHECK (((presentation_type)::text = ANY ((ARRAY['weight'::character varying, 'pack'::character varying])::text[]))),
    CONSTRAINT ck_product_variants_price CHECK (((price_cents IS NULL) OR (price_cents > 0)))
);


--
-- Name: production_batch_dough_limits; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.production_batch_dough_limits (
    production_batch_id uuid NOT NULL,
    dough_type_id uuid NOT NULL,
    capacity_units integer NOT NULL,
    id uuid NOT NULL,
    CONSTRAINT ck_batch_dough_limit_capacity CHECK ((capacity_units > 0))
);


--
-- Name: production_batches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.production_batches (
    code character varying(40) NOT NULL,
    planned_start_at timestamp with time zone NOT NULL,
    breads_available_at timestamp with time zone NOT NULL,
    order_deadline_at timestamp with time zone NOT NULL,
    capacity_units integer NOT NULL,
    status character varying(20) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_production_batches_capacity CHECK ((capacity_units > 0)),
    CONSTRAINT ck_production_batches_deadline CHECK ((order_deadline_at <= breads_available_at)),
    CONSTRAINT ck_production_batches_start_before_available CHECK ((planned_start_at < breads_available_at)),
    CONSTRAINT ck_production_batches_status CHECK (((status)::text = ANY ((ARRAY['planned'::character varying, 'open'::character varying, 'closed'::character varying, 'cancelled'::character varying])::text[])))
);


--
-- Name: products; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.products (
    name character varying(120) NOT NULL,
    slug character varying(80) NOT NULL,
    short_description character varying(280) DEFAULT ''::character varying NOT NULL,
    long_description text,
    featured_image_id uuid,
    featured_image_alt character varying(160) DEFAULT ''::character varying NOT NULL,
    editorial_status character varying(20) DEFAULT 'draft'::character varying NOT NULL,
    is_available boolean DEFAULT true NOT NULL,
    sort_order integer DEFAULT 0 NOT NULL,
    published_at timestamp with time zone,
    archived_at timestamp with time zone,
    updated_by_ref character varying(80),
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    recipe_base_id uuid,
    featured_image_caption character varying(200) NOT NULL,
    fidelity_eligible boolean NOT NULL,
    CONSTRAINT ck_products_editorial_status CHECK (((editorial_status)::text = ANY ((ARRAY['draft'::character varying, 'published'::character varying, 'archived'::character varying])::text[]))),
    CONSTRAINT ck_products_name CHECK (((char_length((name)::text) >= 1) AND (char_length((name)::text) <= 120))),
    CONSTRAINT ck_products_slug CHECK (((char_length((slug)::text) >= 1) AND (char_length((slug)::text) <= 80)))
);


--
-- Name: recipe_bases; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.recipe_bases (
    code character varying(40) NOT NULL,
    name character varying(120) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    id uuid NOT NULL,
    CONSTRAINT ck_recipe_bases_code CHECK (((char_length((code)::text) >= 1) AND (char_length((code)::text) <= 40))),
    CONSTRAINT ck_recipe_bases_name CHECK (((char_length((name)::text) >= 1) AND (char_length((name)::text) <= 120)))
);


--
-- Name: schedule_closure_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schedule_closure_events (
    id uuid NOT NULL,
    closure_id uuid NOT NULL,
    action character varying(32) NOT NULL,
    actor_ref character varying(120) NOT NULL,
    detail jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: schedule_closures; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schedule_closures (
    id uuid NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    first_eligible_date date NOT NULL,
    pause_intake boolean DEFAULT false NOT NULL,
    internal_reason character varying(120) NOT NULL,
    public_notice text,
    created_by character varying(120) NOT NULL,
    updated_by character varying(120) NOT NULL,
    cancelled_at timestamp with time zone,
    cancelled_by character varying(120),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_schedule_closures_first_eligible CHECK ((first_eligible_date > start_date)),
    CONSTRAINT ck_schedule_closures_range CHECK ((end_date >= start_date)),
    CONSTRAINT ck_schedule_closures_reason CHECK (((char_length((internal_reason)::text) >= 1) AND (char_length((internal_reason)::text) <= 120)))
);


--
-- Name: schedule_date_overrides; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schedule_date_overrides (
    local_date date NOT NULL,
    open_state character varying(16) NOT NULL,
    daily_physical_limit integer,
    daily_base_limit integer,
    eligibility_mode character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    id uuid NOT NULL,
    CONSTRAINT ck_date_override_bases CHECK (((daily_base_limit IS NULL) OR (daily_base_limit >= 0))),
    CONSTRAINT ck_date_override_eligibility CHECK (((eligibility_mode)::text = ANY ((ARRAY['inherit'::character varying, 'explicit'::character varying])::text[]))),
    CONSTRAINT ck_date_override_open_state CHECK (((open_state)::text = ANY ((ARRAY['inherit'::character varying, 'open'::character varying, 'closed'::character varying])::text[]))),
    CONSTRAINT ck_date_override_physical CHECK (((daily_physical_limit IS NULL) OR (daily_physical_limit >= 0)))
);


--
-- Name: schedule_eligible_bases; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schedule_eligible_bases (
    scope_kind character varying(16) NOT NULL,
    scope_id uuid,
    recipe_base_id uuid NOT NULL,
    id uuid NOT NULL,
    CONSTRAINT ck_schedule_eligible_scope CHECK (((scope_kind)::text = ANY ((ARRAY['default'::character varying, 'week'::character varying, 'date'::character varying])::text[]))),
    CONSTRAINT ck_schedule_eligible_scope_id CHECK (((((scope_kind)::text = 'default'::text) AND (scope_id IS NULL)) OR (((scope_kind)::text <> 'default'::text) AND (scope_id IS NOT NULL))))
);


--
-- Name: schedule_settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schedule_settings (
    id smallint NOT NULL,
    production_weekdays integer[] NOT NULL,
    daily_physical_limit integer NOT NULL,
    daily_base_limit integer NOT NULL,
    horizon_days integer NOT NULL,
    min_advance_hours integer NOT NULL,
    eligibility_mode character varying(16) NOT NULL,
    occupancy_enabled boolean NOT NULL,
    reservation_policy character varying(20) NOT NULL,
    custom_loaf_price_cents integer DEFAULT 7000 NOT NULL,
    custom_loaf_weight_grams integer DEFAULT 500 NOT NULL,
    CONSTRAINT ck_schedule_settings_advance CHECK ((min_advance_hours >= 0)),
    CONSTRAINT ck_schedule_settings_bases CHECK ((daily_base_limit > 0)),
    CONSTRAINT ck_schedule_settings_custom_price CHECK ((custom_loaf_price_cents > 0)),
    CONSTRAINT ck_schedule_settings_custom_weight CHECK ((custom_loaf_weight_grams > 0)),
    CONSTRAINT ck_schedule_settings_eligibility CHECK (((eligibility_mode)::text = ANY ((ARRAY['inherit'::character varying, 'explicit'::character varying])::text[]))),
    CONSTRAINT ck_schedule_settings_horizon CHECK ((horizon_days > 0)),
    CONSTRAINT ck_schedule_settings_physical CHECK ((daily_physical_limit > 0)),
    CONSTRAINT ck_schedule_settings_policy CHECK (((reservation_policy)::text = ANY ((ARRAY['unset'::character varying, 'request'::character varying, 'admin_accept'::character varying, 'payment'::character varying])::text[]))),
    CONSTRAINT ck_schedule_settings_singleton CHECK ((id = 1))
);


--
-- Name: schedule_settings_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.schedule_settings_id_seq
    AS smallint
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: schedule_settings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.schedule_settings_id_seq OWNED BY public.schedule_settings.id;


--
-- Name: schedule_week_overrides; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schedule_week_overrides (
    week_start date NOT NULL,
    production_weekdays integer[],
    daily_physical_limit integer,
    daily_base_limit integer,
    eligibility_mode character varying(16) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    id uuid NOT NULL,
    CONSTRAINT ck_week_override_bases CHECK (((daily_base_limit IS NULL) OR (daily_base_limit >= 0))),
    CONSTRAINT ck_week_override_eligibility CHECK (((eligibility_mode)::text = ANY ((ARRAY['inherit'::character varying, 'explicit'::character varying])::text[]))),
    CONSTRAINT ck_week_override_physical CHECK (((daily_physical_limit IS NULL) OR (daily_physical_limit >= 0)))
);


--
-- Name: showcase_slots; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.showcase_slots (
    "position" integer NOT NULL,
    product_id uuid,
    CONSTRAINT ck_showcase_slots_position CHECK ((("position" >= 1) AND ("position" <= 10)))
);


--
-- Name: showcase_slots_position_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.showcase_slots_position_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: showcase_slots_position_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.showcase_slots_position_seq OWNED BY public.showcase_slots."position";


--
-- Name: week_recipe_breads; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.week_recipe_breads (
    id uuid NOT NULL,
    recipe_id uuid NOT NULL,
    product_id uuid,
    sort_order integer NOT NULL,
    name_snapshot character varying(120) NOT NULL
);


--
-- Name: week_recipe_ingredients; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.week_recipe_ingredients (
    id uuid NOT NULL,
    recipe_id uuid NOT NULL,
    sort_order integer NOT NULL,
    body character varying(280) NOT NULL
);


--
-- Name: week_recipe_steps; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.week_recipe_steps (
    id uuid NOT NULL,
    recipe_id uuid NOT NULL,
    sort_order integer NOT NULL,
    body text NOT NULL
);


--
-- Name: week_recipes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.week_recipes (
    id uuid NOT NULL,
    title character varying(160) DEFAULT ''::character varying NOT NULL,
    slug character varying(80) NOT NULL,
    summary character varying(280) DEFAULT ''::character varying NOT NULL,
    featured_image_id uuid,
    featured_image_alt character varying(160) DEFAULT ''::character varying NOT NULL,
    featured_image_caption character varying(200) DEFAULT ''::character varying NOT NULL,
    image_focus_x integer DEFAULT 50 NOT NULL,
    image_focus_y integer DEFAULT 50 NOT NULL,
    prep_time_text character varying(80) DEFAULT ''::character varying NOT NULL,
    yield_text character varying(80) DEFAULT ''::character varying NOT NULL,
    editorial_status character varying(20) DEFAULT 'draft'::character varying NOT NULL,
    is_featured boolean DEFAULT false NOT NULL,
    published_at timestamp with time zone,
    archived_at timestamp with time zone,
    updated_by_ref character varying(80),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    method_text text,
    CONSTRAINT ck_week_recipes_editorial_status CHECK (((editorial_status)::text = ANY ((ARRAY['draft'::character varying, 'published'::character varying, 'archived'::character varying])::text[]))),
    CONSTRAINT ck_week_recipes_image_focus CHECK ((((image_focus_x >= 0) AND (image_focus_x <= 100)) AND ((image_focus_y >= 0) AND (image_focus_y <= 100))))
);


--
-- Name: schedule_settings id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_settings ALTER COLUMN id SET DEFAULT nextval('public.schedule_settings_id_seq'::regclass);


--
-- Name: showcase_slots position; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.showcase_slots ALTER COLUMN "position" SET DEFAULT nextval('public.showcase_slots_position_seq'::regclass);


--
-- Name: accompaniment_items accompaniment_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.accompaniment_items
    ADD CONSTRAINT accompaniment_items_pkey PRIMARY KEY (id);


--
-- Name: admin_accounts admin_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_accounts
    ADD CONSTRAINT admin_accounts_pkey PRIMARY KEY (id);


--
-- Name: admin_activation_dispatches admin_activation_dispatches_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_activation_dispatches
    ADD CONSTRAINT admin_activation_dispatches_pkey PRIMARY KEY (id);


--
-- Name: admin_activation_tokens admin_activation_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_activation_tokens
    ADD CONSTRAINT admin_activation_tokens_pkey PRIMARY KEY (id);


--
-- Name: admin_login_attempts admin_login_attempts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_login_attempts
    ADD CONSTRAINT admin_login_attempts_pkey PRIMARY KEY (id);


--
-- Name: admin_push_subscriptions admin_push_subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_push_subscriptions
    ADD CONSTRAINT admin_push_subscriptions_pkey PRIMARY KEY (id);


--
-- Name: admin_sessions admin_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_sessions
    ADD CONSTRAINT admin_sessions_pkey PRIMARY KEY (id);


--
-- Name: admin_sessions admin_sessions_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_sessions
    ADD CONSTRAINT admin_sessions_token_hash_key UNIQUE (token_hash);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: allergens allergens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.allergens
    ADD CONSTRAINT allergens_pkey PRIMARY KEY (id);


--
-- Name: allergens allergens_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.allergens
    ADD CONSTRAINT allergens_slug_key UNIQUE (slug);


--
-- Name: articles articles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.articles
    ADD CONSTRAINT articles_pkey PRIMARY KEY (id);


--
-- Name: articles articles_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.articles
    ADD CONSTRAINT articles_slug_key UNIQUE (slug);


--
-- Name: bread_shapes bread_shapes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bread_shapes
    ADD CONSTRAINT bread_shapes_pkey PRIMARY KEY (id);


--
-- Name: bread_shapes bread_shapes_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bread_shapes
    ADD CONSTRAINT bread_shapes_slug_key UNIQUE (slug);


--
-- Name: customer_accounts customer_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_accounts
    ADD CONSTRAINT customer_accounts_pkey PRIMARY KEY (id);


--
-- Name: customer_challenges customer_challenges_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_challenges
    ADD CONSTRAINT customer_challenges_pkey PRIMARY KEY (id);


--
-- Name: customer_sessions customer_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_sessions
    ADD CONSTRAINT customer_sessions_pkey PRIMARY KEY (id);


--
-- Name: customer_sessions customer_sessions_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_sessions
    ADD CONSTRAINT customer_sessions_token_hash_key UNIQUE (token_hash);


--
-- Name: date_request_events date_request_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.date_request_events
    ADD CONSTRAINT date_request_events_pkey PRIMARY KEY (id);


--
-- Name: date_requests date_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.date_requests
    ADD CONSTRAINT date_requests_pkey PRIMARY KEY (id);


--
-- Name: dough_allergens dough_allergens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dough_allergens
    ADD CONSTRAINT dough_allergens_pkey PRIMARY KEY (id);


--
-- Name: dough_ingredient_compatibilities dough_ingredient_compatibilities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dough_ingredient_compatibilities
    ADD CONSTRAINT dough_ingredient_compatibilities_pkey PRIMARY KEY (id);


--
-- Name: dough_shape_compatibilities dough_shape_compatibilities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dough_shape_compatibilities
    ADD CONSTRAINT dough_shape_compatibilities_pkey PRIMARY KEY (id);


--
-- Name: dough_types dough_types_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dough_types
    ADD CONSTRAINT dough_types_pkey PRIMARY KEY (id);


--
-- Name: dough_types dough_types_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dough_types
    ADD CONSTRAINT dough_types_slug_key UNIQUE (slug);


--
-- Name: email_outbox email_outbox_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.email_outbox
    ADD CONSTRAINT email_outbox_pkey PRIMARY KEY (id);


--
-- Name: fulfillment_slots fulfillment_slots_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fulfillment_slots
    ADD CONSTRAINT fulfillment_slots_pkey PRIMARY KEY (id);


--
-- Name: gigio_credit_operations gigio_credit_operations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gigio_credit_operations
    ADD CONSTRAINT gigio_credit_operations_pkey PRIMARY KEY (operation_id);


--
-- Name: gigio_editorial_notes gigio_editorial_notes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gigio_editorial_notes
    ADD CONSTRAINT gigio_editorial_notes_pkey PRIMARY KEY (id);


--
-- Name: gigio_pairing_references gigio_pairing_references_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gigio_pairing_references
    ADD CONSTRAINT gigio_pairing_references_pkey PRIMARY KEY (id);


--
-- Name: gigio_usage_events gigio_usage_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gigio_usage_events
    ADD CONSTRAINT gigio_usage_events_pkey PRIMARY KEY (id);


--
-- Name: house_fidelity_adjustments house_fidelity_adjustments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.house_fidelity_adjustments
    ADD CONSTRAINT house_fidelity_adjustments_pkey PRIMARY KEY (id);


--
-- Name: house_fidelity_campaigns house_fidelity_campaigns_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.house_fidelity_campaigns
    ADD CONSTRAINT house_fidelity_campaigns_pkey PRIMARY KEY (id);


--
-- Name: house_fidelity_credits house_fidelity_credits_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.house_fidelity_credits
    ADD CONSTRAINT house_fidelity_credits_pkey PRIMARY KEY (id);


--
-- Name: house_fidelity_enrollments house_fidelity_enrollments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.house_fidelity_enrollments
    ADD CONSTRAINT house_fidelity_enrollments_pkey PRIMARY KEY (id);


--
-- Name: house_fidelity_events house_fidelity_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.house_fidelity_events
    ADD CONSTRAINT house_fidelity_events_pkey PRIMARY KEY (id);


--
-- Name: house_fidelity_rule_changes house_fidelity_rule_changes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.house_fidelity_rule_changes
    ADD CONSTRAINT house_fidelity_rule_changes_pkey PRIMARY KEY (id);


--
-- Name: hub_authorization_cache hub_authorization_cache_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hub_authorization_cache
    ADD CONSTRAINT hub_authorization_cache_pkey PRIMARY KEY (subject_hmac);


--
-- Name: hub_plans_events hub_plans_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.hub_plans_events
    ADD CONSTRAINT hub_plans_events_pkey PRIMARY KEY (event_id);


--
-- Name: ingredient_allergens ingredient_allergens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingredient_allergens
    ADD CONSTRAINT ingredient_allergens_pkey PRIMARY KEY (id);


--
-- Name: ingredients ingredients_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingredients
    ADD CONSTRAINT ingredients_pkey PRIMARY KEY (id);


--
-- Name: ingredients ingredients_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingredients
    ADD CONSTRAINT ingredients_slug_key UNIQUE (slug);


--
-- Name: inspiration_posts inspiration_posts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inspiration_posts
    ADD CONSTRAINT inspiration_posts_pkey PRIMARY KEY (id);


--
-- Name: inspiration_posts inspiration_posts_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inspiration_posts
    ADD CONSTRAINT inspiration_posts_slug_key UNIQUE (slug);


--
-- Name: managerial_exclusions managerial_exclusions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.managerial_exclusions
    ADD CONSTRAINT managerial_exclusions_pkey PRIMARY KEY (id);


--
-- Name: media_assets media_assets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.media_assets
    ADD CONSTRAINT media_assets_pkey PRIMARY KEY (id);


--
-- Name: media_assets media_assets_stored_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.media_assets
    ADD CONSTRAINT media_assets_stored_name_key UNIQUE (stored_name);


--
-- Name: ops_channel_settings ops_channel_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ops_channel_settings
    ADD CONSTRAINT ops_channel_settings_pkey PRIMARY KEY (channel);


--
-- Name: ops_owner_alerts ops_owner_alerts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ops_owner_alerts
    ADD CONSTRAINT ops_owner_alerts_pkey PRIMARY KEY (id);


--
-- Name: ops_push_deliveries ops_push_deliveries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ops_push_deliveries
    ADD CONSTRAINT ops_push_deliveries_pkey PRIMARY KEY (id);


--
-- Name: order_internal_notes order_internal_notes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_internal_notes
    ADD CONSTRAINT order_internal_notes_pkey PRIMARY KEY (id);


--
-- Name: order_item_adaptation_events order_item_adaptation_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_item_adaptation_events
    ADD CONSTRAINT order_item_adaptation_events_pkey PRIMARY KEY (id);


--
-- Name: order_item_adaptations order_item_adaptations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_item_adaptations
    ADD CONSTRAINT order_item_adaptations_pkey PRIMARY KEY (id);


--
-- Name: order_item_ingredients order_item_ingredients_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_item_ingredients
    ADD CONSTRAINT order_item_ingredients_pkey PRIMARY KEY (id);


--
-- Name: order_items order_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_pkey PRIMARY KEY (id);


--
-- Name: order_status_history order_status_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_status_history
    ADD CONSTRAINT order_status_history_pkey PRIMARY KEY (id);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (id);


--
-- Name: orders orders_public_reference_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_public_reference_key UNIQUE (public_reference);


--
-- Name: pairing_tips pairing_tips_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pairing_tips
    ADD CONSTRAINT pairing_tips_pkey PRIMARY KEY (id);


--
-- Name: payment_integration_events payment_integration_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_integration_events
    ADD CONSTRAINT payment_integration_events_pkey PRIMARY KEY (id);


--
-- Name: payment_records payment_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_records
    ADD CONSTRAINT payment_records_pkey PRIMARY KEY (id);


--
-- Name: product_events product_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_events
    ADD CONSTRAINT product_events_pkey PRIMARY KEY (id);


--
-- Name: product_ingredients product_ingredients_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_ingredients
    ADD CONSTRAINT product_ingredients_pkey PRIMARY KEY (id);


--
-- Name: product_variants product_variants_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_variants
    ADD CONSTRAINT product_variants_pkey PRIMARY KEY (id);


--
-- Name: production_batch_dough_limits production_batch_dough_limits_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.production_batch_dough_limits
    ADD CONSTRAINT production_batch_dough_limits_pkey PRIMARY KEY (id);


--
-- Name: production_batches production_batches_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.production_batches
    ADD CONSTRAINT production_batches_code_key UNIQUE (code);


--
-- Name: production_batches production_batches_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.production_batches
    ADD CONSTRAINT production_batches_pkey PRIMARY KEY (id);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- Name: products products_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_slug_key UNIQUE (slug);


--
-- Name: recipe_bases recipe_bases_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recipe_bases
    ADD CONSTRAINT recipe_bases_code_key UNIQUE (code);


--
-- Name: recipe_bases recipe_bases_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recipe_bases
    ADD CONSTRAINT recipe_bases_pkey PRIMARY KEY (id);


--
-- Name: schedule_closure_events schedule_closure_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_closure_events
    ADD CONSTRAINT schedule_closure_events_pkey PRIMARY KEY (id);


--
-- Name: schedule_closures schedule_closures_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_closures
    ADD CONSTRAINT schedule_closures_pkey PRIMARY KEY (id);


--
-- Name: schedule_date_overrides schedule_date_overrides_local_date_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_date_overrides
    ADD CONSTRAINT schedule_date_overrides_local_date_key UNIQUE (local_date);


--
-- Name: schedule_date_overrides schedule_date_overrides_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_date_overrides
    ADD CONSTRAINT schedule_date_overrides_pkey PRIMARY KEY (id);


--
-- Name: schedule_eligible_bases schedule_eligible_bases_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_eligible_bases
    ADD CONSTRAINT schedule_eligible_bases_pkey PRIMARY KEY (id);


--
-- Name: schedule_settings schedule_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_settings
    ADD CONSTRAINT schedule_settings_pkey PRIMARY KEY (id);


--
-- Name: schedule_week_overrides schedule_week_overrides_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_week_overrides
    ADD CONSTRAINT schedule_week_overrides_pkey PRIMARY KEY (id);


--
-- Name: schedule_week_overrides schedule_week_overrides_week_start_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_week_overrides
    ADD CONSTRAINT schedule_week_overrides_week_start_key UNIQUE (week_start);


--
-- Name: showcase_slots showcase_slots_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.showcase_slots
    ADD CONSTRAINT showcase_slots_pkey PRIMARY KEY ("position");


--
-- Name: accompaniment_items uq_accompaniment_hub_offer; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.accompaniment_items
    ADD CONSTRAINT uq_accompaniment_hub_offer UNIQUE (hub_offer_id);


--
-- Name: admin_accounts uq_admin_accounts_username; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_accounts
    ADD CONSTRAINT uq_admin_accounts_username UNIQUE (username);


--
-- Name: admin_activation_tokens uq_admin_activation_token_hash; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_activation_tokens
    ADD CONSTRAINT uq_admin_activation_token_hash UNIQUE (token_hash);


--
-- Name: admin_push_subscriptions uq_admin_push_endpoint; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.admin_push_subscriptions
    ADD CONSTRAINT uq_admin_push_endpoint UNIQUE (endpoint_hash);


--
-- Name: production_batch_dough_limits uq_batch_dough_limit; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.production_batch_dough_limits
    ADD CONSTRAINT uq_batch_dough_limit UNIQUE (production_batch_id, dough_type_id);


--
-- Name: customer_accounts uq_customer_accounts_cpf_hmac; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_accounts
    ADD CONSTRAINT uq_customer_accounts_cpf_hmac UNIQUE (cpf_hmac);


--
-- Name: customer_accounts uq_customer_accounts_email; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_accounts
    ADD CONSTRAINT uq_customer_accounts_email UNIQUE (email);


--
-- Name: customer_challenges uq_customer_challenges_token; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_challenges
    ADD CONSTRAINT uq_customer_challenges_token UNIQUE (token_hash);


--
-- Name: date_requests uq_date_requests_converted_order; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.date_requests
    ADD CONSTRAINT uq_date_requests_converted_order UNIQUE (converted_order_id);


--
-- Name: date_requests uq_date_requests_idempotency; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.date_requests
    ADD CONSTRAINT uq_date_requests_idempotency UNIQUE (idempotency_key);


--
-- Name: dough_allergens uq_dough_allergen_presence; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dough_allergens
    ADD CONSTRAINT uq_dough_allergen_presence UNIQUE (dough_type_id, allergen_id, presence);


--
-- Name: dough_ingredient_compatibilities uq_dough_ingredient_compat; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dough_ingredient_compatibilities
    ADD CONSTRAINT uq_dough_ingredient_compat UNIQUE (dough_type_id, ingredient_id);


--
-- Name: dough_shape_compatibilities uq_dough_shape_compat; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dough_shape_compatibilities
    ADD CONSTRAINT uq_dough_shape_compat UNIQUE (dough_type_id, bread_shape_id);


--
-- Name: email_outbox uq_email_outbox_dedupe; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.email_outbox
    ADD CONSTRAINT uq_email_outbox_dedupe UNIQUE (dedupe_key);


--
-- Name: gigio_editorial_notes uq_gigio_editorial_topic; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gigio_editorial_notes
    ADD CONSTRAINT uq_gigio_editorial_topic UNIQUE (topic_key);


--
-- Name: gigio_pairing_references uq_gigio_pairing_profile; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gigio_pairing_references
    ADD CONSTRAINT uq_gigio_pairing_profile UNIQUE (profile_key);


--
-- Name: house_fidelity_campaigns uq_house_fidelity_campaigns_slug_version; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.house_fidelity_campaigns
    ADD CONSTRAINT uq_house_fidelity_campaigns_slug_version UNIQUE (slug, version);


--
-- Name: house_fidelity_credits uq_house_fidelity_credits_group; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.house_fidelity_credits
    ADD CONSTRAINT uq_house_fidelity_credits_group UNIQUE (campaign_id, account_id, cycle_year, cycle_month, group_index);


--
-- Name: house_fidelity_enrollments uq_house_fidelity_enrollments_account_campaign; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.house_fidelity_enrollments
    ADD CONSTRAINT uq_house_fidelity_enrollments_account_campaign UNIQUE (account_id, campaign_id);


--
-- Name: house_fidelity_events uq_house_fidelity_events_order_kind; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.house_fidelity_events
    ADD CONSTRAINT uq_house_fidelity_events_order_kind UNIQUE (campaign_id, order_id, kind);


--
-- Name: ingredient_allergens uq_ingredient_allergen_presence; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingredient_allergens
    ADD CONSTRAINT uq_ingredient_allergen_presence UNIQUE (ingredient_id, allergen_id, presence);


--
-- Name: order_item_adaptations uq_item_adaptations_item; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_item_adaptations
    ADD CONSTRAINT uq_item_adaptations_item UNIQUE (order_item_id);


--
-- Name: ops_owner_alerts uq_ops_owner_alerts_event_channel; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ops_owner_alerts
    ADD CONSTRAINT uq_ops_owner_alerts_event_channel UNIQUE (event_key, channel);


--
-- Name: ops_push_deliveries uq_ops_push_event_device; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ops_push_deliveries
    ADD CONSTRAINT uq_ops_push_event_device UNIQUE (event_key, subscription_id);


--
-- Name: order_item_ingredients uq_order_item_ingredient; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_item_ingredients
    ADD CONSTRAINT uq_order_item_ingredient UNIQUE (order_item_id, ingredient_id);


--
-- Name: orders uq_orders_source_date_request; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT uq_orders_source_date_request UNIQUE (source_date_request_id);


--
-- Name: product_ingredients uq_product_ingredient_order; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_ingredients
    ADD CONSTRAINT uq_product_ingredient_order UNIQUE (product_id, sort_order);


--
-- Name: product_variants uq_product_variant_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_variants
    ADD CONSTRAINT uq_product_variant_name UNIQUE (product_id, display_name);


--
-- Name: schedule_eligible_bases uq_schedule_eligible_base; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_eligible_bases
    ADD CONSTRAINT uq_schedule_eligible_base UNIQUE (scope_kind, scope_id, recipe_base_id);


--
-- Name: showcase_slots uq_showcase_slots_product; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.showcase_slots
    ADD CONSTRAINT uq_showcase_slots_product UNIQUE (product_id);


--
-- Name: week_recipe_breads uq_week_recipe_bread_order; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.week_recipe_breads
    ADD CONSTRAINT uq_week_recipe_bread_order UNIQUE (recipe_id, sort_order);


--
-- Name: week_recipe_breads uq_week_recipe_bread_product; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.week_recipe_breads
    ADD CONSTRAINT uq_week_recipe_bread_product UNIQUE (recipe_id, product_id);


--
-- Name: week_recipe_ingredients uq_week_recipe_ingredient_order; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.week_recipe_ingredients
    ADD CONSTRAINT uq_week_recipe_ingredient_order UNIQUE (recipe_id, sort_order);


--
-- Name: week_recipe_steps uq_week_recipe_step_order; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.week_recipe_steps
    ADD CONSTRAINT uq_week_recipe_step_order UNIQUE (recipe_id, sort_order);


--
-- Name: week_recipe_breads week_recipe_breads_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.week_recipe_breads
    ADD CONSTRAINT week_recipe_breads_pkey PRIMARY KEY (id);


--
-- Name: week_recipe_ingredients week_recipe_ingredients_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.week_recipe_ingredients
    ADD CONSTRAINT week_recipe_ingredients_pkey PRIMARY KEY (id);


--
-- Name: week_recipe_steps week_recipe_steps_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.week_recipe_steps
    ADD CONSTRAINT week_recipe_steps_pkey PRIMARY KEY (id);


--
-- Name: week_recipes week_recipes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.week_recipes
    ADD CONSTRAINT week_recipes_pkey PRIMARY KEY (id);


--
-- Name: week_recipes week_recipes_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.week_recipes
    ADD CONSTRAINT week_recipes_slug_key UNIQUE (slug);


--
-- Name: ix_accompaniment_published_sort; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_accompaniment_published_sort ON public.accompaniment_items USING btree (published, sort_order);


--
-- Name: ix_admin_activation_dispatch_sent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_admin_activation_dispatch_sent ON public.admin_activation_dispatches USING btree (username, sent_at);


--
-- Name: ix_admin_activation_username_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_admin_activation_username_created ON public.admin_activation_tokens USING btree (username, created_at);


--
-- Name: ix_admin_login_attempts_user_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_admin_login_attempts_user_created ON public.admin_login_attempts USING btree (username, created_at);


--
-- Name: ix_admin_push_actor_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_admin_push_actor_active ON public.admin_push_subscriptions USING btree (actor_ref, active);


--
-- Name: ix_admin_sessions_expires_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_admin_sessions_expires_at ON public.admin_sessions USING btree (expires_at);


--
-- Name: ix_customer_accounts_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_customer_accounts_created ON public.customer_accounts USING btree (created_at);


--
-- Name: ix_customer_challenges_email_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_customer_challenges_email_created ON public.customer_challenges USING btree (email, created_at);


--
-- Name: ix_customer_sessions_expires; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_customer_sessions_expires ON public.customer_sessions USING btree (expires_at);


--
-- Name: ix_date_request_events_request; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_date_request_events_request ON public.date_request_events USING btree (request_id, created_at);


--
-- Name: ix_date_requests_email_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_date_requests_email_created ON public.date_requests USING btree (customer_email, created_at);


--
-- Name: ix_date_requests_status_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_date_requests_status_created ON public.date_requests USING btree (status, created_at);


--
-- Name: ix_fulfillment_slots_production_batch_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_fulfillment_slots_production_batch_id ON public.fulfillment_slots USING btree (production_batch_id);


--
-- Name: ix_gigio_credit_ops_subject; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gigio_credit_ops_subject ON public.gigio_credit_operations USING btree (subject_hmac);


--
-- Name: ix_gigio_usage_origin_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_gigio_usage_origin_created ON public.gigio_usage_events USING btree (origin, created_at);


--
-- Name: ix_house_fidelity_credits_account_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_house_fidelity_credits_account_status ON public.house_fidelity_credits USING btree (account_id, status);


--
-- Name: ix_house_fidelity_events_account_cycle; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_house_fidelity_events_account_cycle ON public.house_fidelity_events USING btree (account_id, cycle_year, cycle_month);


--
-- Name: ix_hub_plans_events_subject; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_hub_plans_events_subject ON public.hub_plans_events USING btree (subject_hmac, received_at);


--
-- Name: ix_item_adaptation_events_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_item_adaptation_events_created ON public.order_item_adaptation_events USING btree (adaptation_id, created_at);


--
-- Name: ix_order_internal_notes_order_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_order_internal_notes_order_id ON public.order_internal_notes USING btree (order_id);


--
-- Name: ix_order_items_order_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_order_items_order_id ON public.order_items USING btree (order_id);


--
-- Name: ix_order_status_history_order_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_order_status_history_order_created ON public.order_status_history USING btree (order_id, created_at);


--
-- Name: ix_orders_batch_holds_capacity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_orders_batch_holds_capacity ON public.orders USING btree (production_batch_id) WHERE holds_capacity;


--
-- Name: ix_orders_batch_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_orders_batch_status ON public.orders USING btree (production_batch_id, status);


--
-- Name: ix_orders_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_orders_created_at ON public.orders USING btree (created_at);


--
-- Name: ix_orders_slot_holds_capacity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_orders_slot_holds_capacity ON public.orders USING btree (fulfillment_slot_id) WHERE holds_capacity;


--
-- Name: ix_orders_slot_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_orders_slot_status ON public.orders USING btree (fulfillment_slot_id, status);


--
-- Name: ix_orders_status_confirmed_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_orders_status_confirmed_at ON public.orders USING btree (status, confirmed_at);


--
-- Name: ix_payment_records_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payment_records_order ON public.payment_records USING btree (order_id);


--
-- Name: ix_product_events_product_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_product_events_product_created ON public.product_events USING btree (product_id, created_at);


--
-- Name: ix_product_ingredients_product_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_product_ingredients_product_id ON public.product_ingredients USING btree (product_id);


--
-- Name: ix_product_variants_product_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_product_variants_product_id ON public.product_variants USING btree (product_id);


--
-- Name: ix_products_sort_published; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_products_sort_published ON public.products USING btree (sort_order, published_at);


--
-- Name: ix_products_status_available; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_products_status_available ON public.products USING btree (editorial_status, is_available);


--
-- Name: ix_schedule_closure_events_closure; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_schedule_closure_events_closure ON public.schedule_closure_events USING btree (closure_id, created_at);


--
-- Name: ix_schedule_closures_active_start; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_schedule_closures_active_start ON public.schedule_closures USING btree (cancelled_at, start_date);


--
-- Name: ix_week_recipe_breads_recipe_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_week_recipe_breads_recipe_id ON public.week_recipe_breads USING btree (recipe_id);


--
-- Name: ix_week_recipe_ingredients_recipe_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_week_recipe_ingredients_recipe_id ON public.week_recipe_ingredients USING btree (recipe_id);


--
-- Name: ix_week_recipe_steps_recipe_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_week_recipe_steps_recipe_id ON public.week_recipe_steps USING btree (recipe_id);


--
-- Name: uq_managerial_exclusion_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_managerial_exclusion_active ON public.managerial_exclusions USING btree (subject_type, subject_id) WHERE (reversed_at IS NULL);


--
-- Name: uq_orders_access_token_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_orders_access_token_hash ON public.orders USING btree (access_token_hash) WHERE (access_token_hash IS NOT NULL);


--
-- Name: uq_orders_submit_idempotency; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_orders_submit_idempotency ON public.orders USING btree (submit_idempotency_key) WHERE (submit_idempotency_key IS NOT NULL);


--
-- Name: uq_pairing_tips_pair; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_pairing_tips_pair ON public.pairing_tips USING btree (ingredient_id, paired_ingredient_id) WHERE (paired_ingredient_id IS NOT NULL);


--
-- Name: uq_pairing_tips_single; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_pairing_tips_single ON public.pairing_tips USING btree (ingredient_id) WHERE (paired_ingredient_id IS NULL);


--
-- Name: uq_payment_events_external_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_payment_events_external_id ON public.payment_integration_events USING btree (provider, external_event_id);


--
-- Name: uq_payment_records_external_ref; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_payment_records_external_ref ON public.payment_records USING btree (provider, external_reference) WHERE (external_reference IS NOT NULL);


--
-- Name: uq_payment_records_idempotency; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_payment_records_idempotency ON public.payment_records USING btree (provider, idempotency_key) WHERE (idempotency_key IS NOT NULL);


--
-- Name: uq_product_variant_pack; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_product_variant_pack ON public.product_variants USING btree (product_id, units_per_pack) WHERE ((presentation_type)::text = 'pack'::text);


--
-- Name: uq_product_variant_weight; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_product_variant_weight ON public.product_variants USING btree (product_id, net_weight_grams) WHERE ((presentation_type)::text = 'weight'::text);


--
-- Name: uq_schedule_closures_active_period; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_schedule_closures_active_period ON public.schedule_closures USING btree (start_date, end_date) WHERE (cancelled_at IS NULL);


--
-- Name: uq_week_recipes_one_featured; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_week_recipes_one_featured ON public.week_recipes USING btree (is_featured) WHERE (is_featured IS TRUE);


--
-- Name: allergens trg_allergens_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_allergens_updated_at BEFORE UPDATE ON public.allergens FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: articles trg_articles_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_articles_updated_at BEFORE UPDATE ON public.articles FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: bread_shapes trg_bread_shapes_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bread_shapes_updated_at BEFORE UPDATE ON public.bread_shapes FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: dough_types trg_dough_types_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_dough_types_updated_at BEFORE UPDATE ON public.dough_types FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: fulfillment_slots trg_fulfillment_slots_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_fulfillment_slots_updated_at BEFORE UPDATE ON public.fulfillment_slots FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: ingredients trg_ingredients_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_ingredients_updated_at BEFORE UPDATE ON public.ingredients FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: inspiration_posts trg_inspiration_posts_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_inspiration_posts_updated_at BEFORE UPDATE ON public.inspiration_posts FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: order_items trg_order_items_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_order_items_updated_at BEFORE UPDATE ON public.order_items FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: orders trg_orders_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_orders_updated_at BEFORE UPDATE ON public.orders FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: pairing_tips trg_pairing_tips_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_pairing_tips_updated_at BEFORE UPDATE ON public.pairing_tips FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: payment_records trg_payment_records_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_payment_records_updated_at BEFORE UPDATE ON public.payment_records FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: product_variants trg_product_variants_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_product_variants_updated_at BEFORE UPDATE ON public.product_variants FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: production_batches trg_production_batches_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_production_batches_updated_at BEFORE UPDATE ON public.production_batches FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: products trg_products_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_products_updated_at BEFORE UPDATE ON public.products FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


--
-- Name: customer_challenges customer_challenges_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_challenges
    ADD CONSTRAINT customer_challenges_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.customer_accounts(id) ON DELETE CASCADE;


--
-- Name: customer_sessions customer_sessions_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customer_sessions
    ADD CONSTRAINT customer_sessions_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.customer_accounts(id) ON DELETE CASCADE;


--
-- Name: date_request_events date_request_events_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.date_request_events
    ADD CONSTRAINT date_request_events_request_id_fkey FOREIGN KEY (request_id) REFERENCES public.date_requests(id) ON DELETE CASCADE;


--
-- Name: dough_allergens dough_allergens_allergen_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dough_allergens
    ADD CONSTRAINT dough_allergens_allergen_id_fkey FOREIGN KEY (allergen_id) REFERENCES public.allergens(id) ON DELETE RESTRICT;


--
-- Name: dough_allergens dough_allergens_dough_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dough_allergens
    ADD CONSTRAINT dough_allergens_dough_type_id_fkey FOREIGN KEY (dough_type_id) REFERENCES public.dough_types(id) ON DELETE RESTRICT;


--
-- Name: dough_ingredient_compatibilities dough_ingredient_compatibilities_dough_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dough_ingredient_compatibilities
    ADD CONSTRAINT dough_ingredient_compatibilities_dough_type_id_fkey FOREIGN KEY (dough_type_id) REFERENCES public.dough_types(id) ON DELETE RESTRICT;


--
-- Name: dough_ingredient_compatibilities dough_ingredient_compatibilities_ingredient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dough_ingredient_compatibilities
    ADD CONSTRAINT dough_ingredient_compatibilities_ingredient_id_fkey FOREIGN KEY (ingredient_id) REFERENCES public.ingredients(id) ON DELETE RESTRICT;


--
-- Name: dough_shape_compatibilities dough_shape_compatibilities_bread_shape_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dough_shape_compatibilities
    ADD CONSTRAINT dough_shape_compatibilities_bread_shape_id_fkey FOREIGN KEY (bread_shape_id) REFERENCES public.bread_shapes(id) ON DELETE RESTRICT;


--
-- Name: dough_shape_compatibilities dough_shape_compatibilities_dough_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dough_shape_compatibilities
    ADD CONSTRAINT dough_shape_compatibilities_dough_type_id_fkey FOREIGN KEY (dough_type_id) REFERENCES public.dough_types(id) ON DELETE RESTRICT;


--
-- Name: email_outbox email_outbox_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.email_outbox
    ADD CONSTRAINT email_outbox_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
-- Name: date_requests fk_date_requests_converted_order; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.date_requests
    ADD CONSTRAINT fk_date_requests_converted_order FOREIGN KEY (converted_order_id) REFERENCES public.orders(id) ON DELETE SET NULL;


--
-- Name: dough_types fk_dough_types_recipe_base; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dough_types
    ADD CONSTRAINT fk_dough_types_recipe_base FOREIGN KEY (recipe_base_id) REFERENCES public.recipe_bases(id) ON DELETE RESTRICT;


--
-- Name: email_outbox fk_email_outbox_date_request; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.email_outbox
    ADD CONSTRAINT fk_email_outbox_date_request FOREIGN KEY (date_request_id) REFERENCES public.date_requests(id) ON DELETE SET NULL;


--
-- Name: order_items fk_order_items_product; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT fk_order_items_product FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE RESTRICT;


--
-- Name: order_items fk_order_items_recipe_base; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT fk_order_items_recipe_base FOREIGN KEY (recipe_base_id) REFERENCES public.recipe_bases(id) ON DELETE RESTRICT;


--
-- Name: order_items fk_order_items_variant; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT fk_order_items_variant FOREIGN KEY (product_variant_id) REFERENCES public.product_variants(id) ON DELETE RESTRICT;


--
-- Name: orders fk_orders_fidelity_account; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT fk_orders_fidelity_account FOREIGN KEY (fidelity_account_id) REFERENCES public.customer_accounts(id) ON DELETE SET NULL;


--
-- Name: orders fk_orders_fidelity_campaign; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT fk_orders_fidelity_campaign FOREIGN KEY (fidelity_campaign_id) REFERENCES public.house_fidelity_campaigns(id) ON DELETE SET NULL;


--
-- Name: orders fk_orders_source_date_request; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT fk_orders_source_date_request FOREIGN KEY (source_date_request_id) REFERENCES public.date_requests(id) ON DELETE SET NULL;


--
-- Name: products fk_products_recipe_base; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT fk_products_recipe_base FOREIGN KEY (recipe_base_id) REFERENCES public.recipe_bases(id) ON DELETE RESTRICT;


--
-- Name: fulfillment_slots fulfillment_slots_production_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fulfillment_slots
    ADD CONSTRAINT fulfillment_slots_production_batch_id_fkey FOREIGN KEY (production_batch_id) REFERENCES public.production_batches(id) ON DELETE RESTRICT;


--
-- Name: house_fidelity_adjustments house_fidelity_adjustments_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.house_fidelity_adjustments
    ADD CONSTRAINT house_fidelity_adjustments_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.customer_accounts(id) ON DELETE CASCADE;


--
-- Name: house_fidelity_adjustments house_fidelity_adjustments_campaign_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.house_fidelity_adjustments
    ADD CONSTRAINT house_fidelity_adjustments_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES public.house_fidelity_campaigns(id) ON DELETE RESTRICT;


--
-- Name: house_fidelity_credits house_fidelity_credits_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.house_fidelity_credits
    ADD CONSTRAINT house_fidelity_credits_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.customer_accounts(id) ON DELETE CASCADE;


--
-- Name: house_fidelity_credits house_fidelity_credits_campaign_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.house_fidelity_credits
    ADD CONSTRAINT house_fidelity_credits_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES public.house_fidelity_campaigns(id) ON DELETE RESTRICT;


--
-- Name: house_fidelity_credits house_fidelity_credits_reserved_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.house_fidelity_credits
    ADD CONSTRAINT house_fidelity_credits_reserved_order_id_fkey FOREIGN KEY (reserved_order_id) REFERENCES public.orders(id) ON DELETE SET NULL;


--
-- Name: house_fidelity_credits house_fidelity_credits_source_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.house_fidelity_credits
    ADD CONSTRAINT house_fidelity_credits_source_event_id_fkey FOREIGN KEY (source_event_id) REFERENCES public.house_fidelity_events(id) ON DELETE RESTRICT;


--
-- Name: house_fidelity_credits house_fidelity_credits_used_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.house_fidelity_credits
    ADD CONSTRAINT house_fidelity_credits_used_order_id_fkey FOREIGN KEY (used_order_id) REFERENCES public.orders(id) ON DELETE SET NULL;


--
-- Name: house_fidelity_enrollments house_fidelity_enrollments_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.house_fidelity_enrollments
    ADD CONSTRAINT house_fidelity_enrollments_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.customer_accounts(id) ON DELETE CASCADE;


--
-- Name: house_fidelity_enrollments house_fidelity_enrollments_campaign_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.house_fidelity_enrollments
    ADD CONSTRAINT house_fidelity_enrollments_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES public.house_fidelity_campaigns(id) ON DELETE RESTRICT;


--
-- Name: house_fidelity_events house_fidelity_events_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.house_fidelity_events
    ADD CONSTRAINT house_fidelity_events_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.customer_accounts(id) ON DELETE CASCADE;


--
-- Name: house_fidelity_events house_fidelity_events_campaign_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.house_fidelity_events
    ADD CONSTRAINT house_fidelity_events_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES public.house_fidelity_campaigns(id) ON DELETE RESTRICT;


--
-- Name: house_fidelity_events house_fidelity_events_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.house_fidelity_events
    ADD CONSTRAINT house_fidelity_events_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE RESTRICT;


--
-- Name: house_fidelity_rule_changes house_fidelity_rule_changes_campaign_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.house_fidelity_rule_changes
    ADD CONSTRAINT house_fidelity_rule_changes_campaign_id_fkey FOREIGN KEY (campaign_id) REFERENCES public.house_fidelity_campaigns(id) ON DELETE RESTRICT;


--
-- Name: ingredient_allergens ingredient_allergens_allergen_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingredient_allergens
    ADD CONSTRAINT ingredient_allergens_allergen_id_fkey FOREIGN KEY (allergen_id) REFERENCES public.allergens(id) ON DELETE RESTRICT;


--
-- Name: ingredient_allergens ingredient_allergens_ingredient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingredient_allergens
    ADD CONSTRAINT ingredient_allergens_ingredient_id_fkey FOREIGN KEY (ingredient_id) REFERENCES public.ingredients(id) ON DELETE RESTRICT;


--
-- Name: order_internal_notes order_internal_notes_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_internal_notes
    ADD CONSTRAINT order_internal_notes_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
-- Name: order_item_adaptation_events order_item_adaptation_events_adaptation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_item_adaptation_events
    ADD CONSTRAINT order_item_adaptation_events_adaptation_id_fkey FOREIGN KEY (adaptation_id) REFERENCES public.order_item_adaptations(id) ON DELETE CASCADE;


--
-- Name: order_item_adaptations order_item_adaptations_order_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_item_adaptations
    ADD CONSTRAINT order_item_adaptations_order_item_id_fkey FOREIGN KEY (order_item_id) REFERENCES public.order_items(id) ON DELETE CASCADE;


--
-- Name: order_item_ingredients order_item_ingredients_ingredient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_item_ingredients
    ADD CONSTRAINT order_item_ingredients_ingredient_id_fkey FOREIGN KEY (ingredient_id) REFERENCES public.ingredients(id) ON DELETE RESTRICT;


--
-- Name: order_item_ingredients order_item_ingredients_order_item_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_item_ingredients
    ADD CONSTRAINT order_item_ingredients_order_item_id_fkey FOREIGN KEY (order_item_id) REFERENCES public.order_items(id) ON DELETE CASCADE;


--
-- Name: order_items order_items_bread_shape_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_bread_shape_id_fkey FOREIGN KEY (bread_shape_id) REFERENCES public.bread_shapes(id) ON DELETE RESTRICT;


--
-- Name: order_items order_items_dough_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_dough_type_id_fkey FOREIGN KEY (dough_type_id) REFERENCES public.dough_types(id) ON DELETE RESTRICT;


--
-- Name: order_items order_items_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
-- Name: order_status_history order_status_history_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_status_history
    ADD CONSTRAINT order_status_history_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE CASCADE;


--
-- Name: orders orders_fulfillment_slot_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_fulfillment_slot_id_fkey FOREIGN KEY (fulfillment_slot_id) REFERENCES public.fulfillment_slots(id) ON DELETE RESTRICT;


--
-- Name: orders orders_production_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_production_batch_id_fkey FOREIGN KEY (production_batch_id) REFERENCES public.production_batches(id) ON DELETE RESTRICT;


--
-- Name: pairing_tips pairing_tips_ingredient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pairing_tips
    ADD CONSTRAINT pairing_tips_ingredient_id_fkey FOREIGN KEY (ingredient_id) REFERENCES public.ingredients(id) ON DELETE RESTRICT;


--
-- Name: pairing_tips pairing_tips_paired_ingredient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pairing_tips
    ADD CONSTRAINT pairing_tips_paired_ingredient_id_fkey FOREIGN KEY (paired_ingredient_id) REFERENCES public.ingredients(id) ON DELETE RESTRICT;


--
-- Name: payment_integration_events payment_integration_events_payment_record_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_integration_events
    ADD CONSTRAINT payment_integration_events_payment_record_id_fkey FOREIGN KEY (payment_record_id) REFERENCES public.payment_records(id) ON DELETE SET NULL;


--
-- Name: payment_records payment_records_order_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_records
    ADD CONSTRAINT payment_records_order_id_fkey FOREIGN KEY (order_id) REFERENCES public.orders(id) ON DELETE RESTRICT;


--
-- Name: product_events product_events_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_events
    ADD CONSTRAINT product_events_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: product_ingredients product_ingredients_catalog_ingredient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_ingredients
    ADD CONSTRAINT product_ingredients_catalog_ingredient_id_fkey FOREIGN KEY (catalog_ingredient_id) REFERENCES public.ingredients(id) ON DELETE SET NULL;


--
-- Name: product_ingredients product_ingredients_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_ingredients
    ADD CONSTRAINT product_ingredients_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: product_variants product_variants_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_variants
    ADD CONSTRAINT product_variants_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE RESTRICT;


--
-- Name: production_batch_dough_limits production_batch_dough_limits_dough_type_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.production_batch_dough_limits
    ADD CONSTRAINT production_batch_dough_limits_dough_type_id_fkey FOREIGN KEY (dough_type_id) REFERENCES public.dough_types(id) ON DELETE RESTRICT;


--
-- Name: production_batch_dough_limits production_batch_dough_limits_production_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.production_batch_dough_limits
    ADD CONSTRAINT production_batch_dough_limits_production_batch_id_fkey FOREIGN KEY (production_batch_id) REFERENCES public.production_batches(id) ON DELETE RESTRICT;


--
-- Name: products products_featured_image_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_featured_image_id_fkey FOREIGN KEY (featured_image_id) REFERENCES public.media_assets(id) ON DELETE RESTRICT;


--
-- Name: schedule_closure_events schedule_closure_events_closure_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_closure_events
    ADD CONSTRAINT schedule_closure_events_closure_id_fkey FOREIGN KEY (closure_id) REFERENCES public.schedule_closures(id) ON DELETE CASCADE;


--
-- Name: schedule_eligible_bases schedule_eligible_bases_recipe_base_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schedule_eligible_bases
    ADD CONSTRAINT schedule_eligible_bases_recipe_base_id_fkey FOREIGN KEY (recipe_base_id) REFERENCES public.recipe_bases(id) ON DELETE RESTRICT;


--
-- Name: showcase_slots showcase_slots_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.showcase_slots
    ADD CONSTRAINT showcase_slots_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE SET NULL;


--
-- Name: week_recipe_breads week_recipe_breads_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.week_recipe_breads
    ADD CONSTRAINT week_recipe_breads_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE SET NULL;


--
-- Name: week_recipe_breads week_recipe_breads_recipe_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.week_recipe_breads
    ADD CONSTRAINT week_recipe_breads_recipe_id_fkey FOREIGN KEY (recipe_id) REFERENCES public.week_recipes(id) ON DELETE CASCADE;


--
-- Name: week_recipe_ingredients week_recipe_ingredients_recipe_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.week_recipe_ingredients
    ADD CONSTRAINT week_recipe_ingredients_recipe_id_fkey FOREIGN KEY (recipe_id) REFERENCES public.week_recipes(id) ON DELETE CASCADE;


--
-- Name: week_recipe_steps week_recipe_steps_recipe_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.week_recipe_steps
    ADD CONSTRAINT week_recipe_steps_recipe_id_fkey FOREIGN KEY (recipe_id) REFERENCES public.week_recipes(id) ON DELETE CASCADE;


--
-- Name: week_recipes week_recipes_featured_image_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.week_recipes
    ADD CONSTRAINT week_recipes_featured_image_id_fkey FOREIGN KEY (featured_image_id) REFERENCES public.media_assets(id) ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--


