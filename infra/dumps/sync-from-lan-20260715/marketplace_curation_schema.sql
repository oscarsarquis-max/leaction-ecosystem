--
-- PostgreSQL database dump
--

\restrict va5eBAQQI65pcgw8g6YOnxW7hSzQ9nRM65tY4JPIcy6xECmoz2NG954LXdQe8rb

-- Dumped from database version 18.4 (Debian 18.4-1.pgdg13+1)
-- Dumped by pg_dump version 18.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: marketplace_curation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.marketplace_curation (
    id character varying(64) NOT NULL,
    search_terms jsonb NOT NULL,
    positive_keywords jsonb NOT NULL,
    negative_keywords jsonb NOT NULL,
    updated_at timestamp with time zone NOT NULL
);


--
-- Name: marketplace_curation marketplace_curation_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.marketplace_curation
    ADD CONSTRAINT marketplace_curation_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--

\unrestrict va5eBAQQI65pcgw8g6YOnxW7hSzQ9nRM65tY4JPIcy6xECmoz2NG954LXdQe8rb

