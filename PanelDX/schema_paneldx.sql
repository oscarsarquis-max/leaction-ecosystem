--
-- PostgreSQL database dump
--

\restrict YT1oL5dMWofZKp4Of1aTGZYg6aS78KTQAHOhZ7fXf13aUyCvGsb7VdNGrxVhTvb

-- Dumped from database version 18.3
-- Dumped by pg_dump version 18.1

-- Started on 2026-06-12 14:44:09

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

--
-- TOC entry 309 (class 1255 OID 17757)
-- Name: fn_recalcular_progresso_kr(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.fn_recalcular_progresso_kr() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_total_ativ integer;
    v_concluidas_ativ integer;
    v_val_inicial numeric(15,2);
    v_val_alvo numeric(15,2);
    v_novo_atual numeric(15,2);
BEGIN
    -- 1. Captura o ID do KR afetado (seja inserção, atualização ou deleção)
    DECLARE
        target_kr integer := CASE WHEN TG_OP = 'DELETE' THEN OLD.id_kr ELSE NEW.id_kr END;
    BEGIN
        -- 2. Conta o volume total de atividades e quantas já foram concluídas para este KR
        SELECT COUNT(*), COUNT(*) FILTER (WHERE status_ativ = 'Entregue')
        INTO v_total_ativ, v_concluidas_ativ
        FROM public.ctdi_okr_atividades
        WHERE id_kr = target_kr;

        -- 3. Busca a linha de base e a meta matemática do KR
        SELECT valor_inicial, valor_alvo
        INTO v_val_inicial, v_val_alvo
        FROM public.ctdi_okr_krs
        WHERE id_kr = target_kr;

        -- 4. Se existirem atividades vinculadas, calcula a evolução proporcional na régua do KR
        IF v_total_ativ > 0 THEN
            v_novo_atual := v_val_inicial + ((v_val_alvo - v_val_inicial) * v_concluidas_ativ / v_total_ativ);
            
            UPDATE public.ctdi_okr_krs
            SET valor_atual = v_novo_atual,
                status_kr = CASE WHEN v_concluidas_ativ = v_total_ativ THEN 'Atingido' ELSE 'Em Andamento' END,
                data_revisao = CURRENT_TIMESTAMP
            WHERE id_kr = target_kr;
        ELSE
            -- Se todas as atividades forem deletadas, reseta o valor atual para o ponto de partida
            UPDATE public.ctdi_okr_krs
            SET valor_atual = v_val_inicial,
                status_kr = 'Em Andamento',
                data_revisao = CURRENT_TIMESTAMP
            WHERE id_kr = target_kr;
        END IF;
    END;
    RETURN NULL;
END;
$$;


ALTER FUNCTION public.fn_recalcular_progresso_kr() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 219 (class 1259 OID 16389)
-- Name: bloc_derv; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.bloc_derv (
    id_bloc integer NOT NULL,
    id_derv integer NOT NULL,
    id_movi integer,
    desc_seca text
);


ALTER TABLE public.bloc_derv OWNER TO postgres;

--
-- TOC entry 261 (class 1259 OID 16774)
-- Name: ctdi_bussola; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ctdi_bussola (
    id_bussola integer NOT NULL,
    id_ques integer NOT NULL,
    insight_chave text NOT NULL,
    target_context text
);


ALTER TABLE public.ctdi_bussola OWNER TO postgres;

--
-- TOC entry 5383 (class 0 OID 0)
-- Dependencies: 261
-- Name: COLUMN ctdi_bussola.insight_chave; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.ctdi_bussola.insight_chave IS 'Interpretação técnica que o MASTER apresenta no diagnóstico';


--
-- TOC entry 5384 (class 0 OID 0)
-- Dependencies: 261
-- Name: COLUMN ctdi_bussola.target_context; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.ctdi_bussola.target_context IS 'String de match para o MASTER. Ex: K12;2 UNIDADES;SUPERIOR';


--
-- TOC entry 260 (class 1259 OID 16773)
-- Name: ctdi_bussola_id_bussola_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ctdi_bussola_id_bussola_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ctdi_bussola_id_bussola_seq OWNER TO postgres;

--
-- TOC entry 5385 (class 0 OID 0)
-- Dependencies: 260
-- Name: ctdi_bussola_id_bussola_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ctdi_bussola_id_bussola_seq OWNED BY public.ctdi_bussola.id_bussola;


--
-- TOC entry 265 (class 1259 OID 17244)
-- Name: ctdi_cermls; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ctdi_cermls (
    id_cermls integer NOT NULL,
    id_sprn integer NOT NULL,
    tp_cermls character varying(50) NOT NULL,
    note_cermls text NOT NULL,
    dt_cermls date NOT NULL,
    dt_regis timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.ctdi_cermls OWNER TO postgres;

--
-- TOC entry 264 (class 1259 OID 17243)
-- Name: ctdi_cermls_id_cermls_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ctdi_cermls_id_cermls_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ctdi_cermls_id_cermls_seq OWNER TO postgres;

--
-- TOC entry 5386 (class 0 OID 0)
-- Dependencies: 264
-- Name: ctdi_cermls_id_cermls_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ctdi_cermls_id_cermls_seq OWNED BY public.ctdi_cermls.id_cermls;


--
-- TOC entry 220 (class 1259 OID 16396)
-- Name: ctdi_clie; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ctdi_clie (
    id_clie integer NOT NULL,
    docu_clie text,
    nome_clie text NOT NULL,
    mail_clie text,
    fone_clie text,
    adre_clie text,
    zipn_clie text,
    empresa_clie text,
    tipo_ensino text,
    qtd_alunos integer,
    qtd_colaboradores integer,
    qtd_unidades integer,
    localizacao_sede text,
    rede_ensino boolean DEFAULT false,
    clima_organizacional text,
    has_active_project boolean DEFAULT false,
    init_role character varying(10) DEFAULT 'GENERAL'::character varying,
    justificativa_solo text,
    id_rede character varying(100),
    is_holding boolean DEFAULT false
);


ALTER TABLE public.ctdi_clie OWNER TO postgres;

--
-- TOC entry 221 (class 1259 OID 16405)
-- Name: ctdi_clie_id_clie_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ctdi_clie_id_clie_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ctdi_clie_id_clie_seq OWNER TO postgres;

--
-- TOC entry 5387 (class 0 OID 0)
-- Dependencies: 221
-- Name: ctdi_clie_id_clie_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ctdi_clie_id_clie_seq OWNED BY public.ctdi_clie.id_clie;


--
-- TOC entry 267 (class 1259 OID 17343)
-- Name: ctdi_doc_specs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ctdi_doc_specs (
    id_spec integer NOT NULL,
    nome_componente character varying(100) NOT NULL,
    descritivo_doc text,
    criterios_aceite jsonb,
    peso_auditoria integer DEFAULT 1,
    ativo boolean DEFAULT true,
    data_criacao timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.ctdi_doc_specs OWNER TO postgres;

--
-- TOC entry 266 (class 1259 OID 17342)
-- Name: ctdi_doc_specs_id_spec_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ctdi_doc_specs_id_spec_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ctdi_doc_specs_id_spec_seq OWNER TO postgres;

--
-- TOC entry 5388 (class 0 OID 0)
-- Dependencies: 266
-- Name: ctdi_doc_specs_id_spec_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ctdi_doc_specs_id_spec_seq OWNED BY public.ctdi_doc_specs.id_spec;


--
-- TOC entry 269 (class 1259 OID 17385)
-- Name: ctdi_evidencias; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ctdi_evidencias (
    id_evid integer NOT NULL,
    id_sprn integer NOT NULL,
    id_spec integer,
    componente_vinculado character varying(100),
    url_evid text NOT NULL,
    status_modulador character varying(50) DEFAULT 'Pendente'::character varying,
    analise_ia text,
    data_vinculo timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    transcricao_audio text
);


ALTER TABLE public.ctdi_evidencias OWNER TO postgres;

--
-- TOC entry 268 (class 1259 OID 17384)
-- Name: ctdi_evidencias_id_evid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ctdi_evidencias_id_evid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ctdi_evidencias_id_evid_seq OWNER TO postgres;

--
-- TOC entry 5389 (class 0 OID 0)
-- Dependencies: 268
-- Name: ctdi_evidencias_id_evid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ctdi_evidencias_id_evid_seq OWNED BY public.ctdi_evidencias.id_evid;


--
-- TOC entry 222 (class 1259 OID 16406)
-- Name: ctdi_itera; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ctdi_itera (
    id_itera integer NOT NULL,
    id_ctdi integer,
    id_phase integer,
    name_itera text,
    dtini_itera date,
    dtend_itera date,
    stat_itera text DEFAULT 'planejada'::text
);


ALTER TABLE public.ctdi_itera OWNER TO postgres;

--
-- TOC entry 223 (class 1259 OID 16413)
-- Name: ctdi_itera_id_itera_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ctdi_itera_id_itera_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ctdi_itera_id_itera_seq OWNER TO postgres;

--
-- TOC entry 5390 (class 0 OID 0)
-- Dependencies: 223
-- Name: ctdi_itera_id_itera_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ctdi_itera_id_itera_seq OWNED BY public.ctdi_itera.id_itera;


--
-- TOC entry 224 (class 1259 OID 16414)
-- Name: ctdi_lead_access; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ctdi_lead_access (
    id_access integer NOT NULL,
    id_clie integer NOT NULL,
    access_code character varying(10) NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.ctdi_lead_access OWNER TO postgres;

--
-- TOC entry 225 (class 1259 OID 16421)
-- Name: ctdi_lead_access_id_access_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ctdi_lead_access_id_access_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ctdi_lead_access_id_access_seq OWNER TO postgres;

--
-- TOC entry 5391 (class 0 OID 0)
-- Dependencies: 225
-- Name: ctdi_lead_access_id_access_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ctdi_lead_access_id_access_seq OWNED BY public.ctdi_lead_access.id_access;


--
-- TOC entry 226 (class 1259 OID 16422)
-- Name: ctdi_main; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ctdi_main (
    id_ctdi integer NOT NULL,
    id_dime integer NOT NULL,
    name_ctdi text,
    stat_ctdi text DEFAULT 'ativo'::text,
    id_matu integer
);


ALTER TABLE public.ctdi_main OWNER TO postgres;

--
-- TOC entry 227 (class 1259 OID 16430)
-- Name: ctdi_main_id_ctdi_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ctdi_main_id_ctdi_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ctdi_main_id_ctdi_seq OWNER TO postgres;

--
-- TOC entry 5392 (class 0 OID 0)
-- Dependencies: 227
-- Name: ctdi_main_id_ctdi_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ctdi_main_id_ctdi_seq OWNED BY public.ctdi_main.id_ctdi;


--
-- TOC entry 228 (class 1259 OID 16431)
-- Name: ctdi_matu; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ctdi_matu (
    id_matu integer NOT NULL,
    id_clie integer NOT NULL,
    pdom_pres jsonb,
    pdim_pres jsonb,
    pgen_pres numeric(5,2),
    pdom_fut jsonb,
    pdim_fut jsonb,
    pgen_fut numeric(3,2),
    pdom_gap jsonb,
    pdim_gap jsonb,
    pgen_gap numeric(3,2),
    txt_diagnostico_ia text,
    status_ia character varying(20) DEFAULT 'PENDENTE'::character varying,
    dt_fim_ia timestamp without time zone,
    pgen_sect_pres numeric(5,2),
    pgen_sect_fut numeric(3,2),
    pgen_sect_gap numeric(3,2),
    pdom_sect_pres jsonb,
    pdom_sect_fut jsonb,
    pdom_sect_gap jsonb,
    pdim_sect_pres jsonb,
    pdim_sect_fut jsonb,
    pdim_sect_gap jsonb,
    json_plano_estrategico jsonb,
    url_pdf_ia text
);


ALTER TABLE public.ctdi_matu OWNER TO postgres;

--
-- TOC entry 229 (class 1259 OID 16439)
-- Name: ctdi_matu_id_matu_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ctdi_matu_id_matu_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ctdi_matu_id_matu_seq OWNER TO postgres;

--
-- TOC entry 5393 (class 0 OID 0)
-- Dependencies: 229
-- Name: ctdi_matu_id_matu_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ctdi_matu_id_matu_seq OWNED BY public.ctdi_matu.id_matu;


--
-- TOC entry 271 (class 1259 OID 17451)
-- Name: ctdi_matu_presurvey; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ctdi_matu_presurvey (
    id_presurvey integer NOT NULL,
    id_matu integer NOT NULL,
    score_estrat_p numeric(3,2),
    score_estrat_f numeric(3,2),
    score_organiz_p numeric(3,2),
    score_organiz_f numeric(3,2),
    score_humana_p numeric(3,2),
    score_humana_f numeric(3,2),
    score_pedag_p numeric(3,2),
    score_pedag_f numeric(3,2),
    score_tecno_p numeric(3,2),
    score_tecno_f numeric(3,2),
    data_criacao timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    json_insights text
);


ALTER TABLE public.ctdi_matu_presurvey OWNER TO postgres;

--
-- TOC entry 270 (class 1259 OID 17450)
-- Name: ctdi_matu_presurvey_id_presurvey_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ctdi_matu_presurvey_id_presurvey_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ctdi_matu_presurvey_id_presurvey_seq OWNER TO postgres;

--
-- TOC entry 5394 (class 0 OID 0)
-- Dependencies: 270
-- Name: ctdi_matu_presurvey_id_presurvey_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ctdi_matu_presurvey_id_presurvey_seq OWNED BY public.ctdi_matu_presurvey.id_presurvey;


--
-- TOC entry 230 (class 1259 OID 16440)
-- Name: ctdi_movi; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ctdi_movi (
    id_movi integer NOT NULL,
    name_movi text NOT NULL,
    desc_movi text,
    diag_movi text,
    crtr_movi text,
    intv_movi numrange
);


ALTER TABLE public.ctdi_movi OWNER TO postgres;

--
-- TOC entry 5395 (class 0 OID 0)
-- Dependencies: 230
-- Name: COLUMN ctdi_movi.crtr_movi; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.ctdi_movi.crtr_movi IS 'Característica da Movimentação';


--
-- TOC entry 231 (class 1259 OID 16447)
-- Name: ctdi_movi_id_movi_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ctdi_movi_id_movi_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ctdi_movi_id_movi_seq OWNER TO postgres;

--
-- TOC entry 5396 (class 0 OID 0)
-- Dependencies: 231
-- Name: ctdi_movi_id_movi_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ctdi_movi_id_movi_seq OWNED BY public.ctdi_movi.id_movi;


--
-- TOC entry 279 (class 1259 OID 17730)
-- Name: ctdi_okr_atividades; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ctdi_okr_atividades (
    id_ativ integer NOT NULL,
    id_kr integer NOT NULL,
    id_sprn integer NOT NULL,
    nome_ativ character varying(250) NOT NULL,
    desc_ativ text,
    status_ativ character varying(50) DEFAULT 'A Fazer'::character varying,
    data_criacao timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_conclusao timestamp without time zone,
    id_team integer,
    data_planejamento date
);


ALTER TABLE public.ctdi_okr_atividades OWNER TO postgres;

--
-- TOC entry 5397 (class 0 OID 0)
-- Dependencies: 279
-- Name: TABLE ctdi_okr_atividades; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.ctdi_okr_atividades IS 'Nível 4 do módulo OKR: Armazena as ações operacionais da Sprint associando membros do time, prazos e KRs.';


--
-- TOC entry 278 (class 1259 OID 17729)
-- Name: ctdi_okr_atividades_id_ativ_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ctdi_okr_atividades_id_ativ_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ctdi_okr_atividades_id_ativ_seq OWNER TO postgres;

--
-- TOC entry 5398 (class 0 OID 0)
-- Dependencies: 278
-- Name: ctdi_okr_atividades_id_ativ_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ctdi_okr_atividades_id_ativ_seq OWNED BY public.ctdi_okr_atividades.id_ativ;


--
-- TOC entry 273 (class 1259 OID 17664)
-- Name: ctdi_okr_direcionadores; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ctdi_okr_direcionadores (
    id_direc integer NOT NULL,
    id_clie integer NOT NULL,
    nome_direc character varying(200) NOT NULL,
    desc_direc text,
    kpi_descricao character varying(250),
    meta_receita_alvo numeric(15,2) DEFAULT 0.00,
    meta_custo_alvo numeric(15,2) DEFAULT 0.00,
    status_direc character varying(50) DEFAULT 'Ativo'::character varying,
    data_criacao timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_revisao timestamp without time zone
);


ALTER TABLE public.ctdi_okr_direcionadores OWNER TO postgres;

--
-- TOC entry 5399 (class 0 OID 0)
-- Dependencies: 273
-- Name: TABLE ctdi_okr_direcionadores; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.ctdi_okr_direcionadores IS 'Nível 1 do módulo OKR: Armazena os Direcionadores Estratégicos e metas organizacionais de Receita e Custo da instituição.';


--
-- TOC entry 272 (class 1259 OID 17663)
-- Name: ctdi_okr_direcionadores_id_direc_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ctdi_okr_direcionadores_id_direc_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ctdi_okr_direcionadores_id_direc_seq OWNER TO postgres;

--
-- TOC entry 5400 (class 0 OID 0)
-- Dependencies: 272
-- Name: ctdi_okr_direcionadores_id_direc_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ctdi_okr_direcionadores_id_direc_seq OWNED BY public.ctdi_okr_direcionadores.id_direc;


--
-- TOC entry 277 (class 1259 OID 17705)
-- Name: ctdi_okr_krs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ctdi_okr_krs (
    id_kr integer NOT NULL,
    id_obj_dt integer NOT NULL,
    nome_kr character varying(200) NOT NULL,
    desc_kr text,
    kpi_nome character varying(150) NOT NULL,
    valor_inicial numeric(15,2) DEFAULT 0.00 NOT NULL,
    valor_alvo numeric(15,2) NOT NULL,
    valor_atual numeric(15,2) DEFAULT 0.00 NOT NULL,
    status_kr character varying(50) DEFAULT 'Em Andamento'::character varying,
    data_criacao timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_revisao timestamp without time zone
);


ALTER TABLE public.ctdi_okr_krs OWNER TO postgres;

--
-- TOC entry 5401 (class 0 OID 0)
-- Dependencies: 277
-- Name: TABLE ctdi_okr_krs; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.ctdi_okr_krs IS 'Nível 3 do módulo OKR: Armazena os Resultados Chaves (KRs) quantitativos e o progresso das métricas vinculadas aos Objetivos de TD.';


--
-- TOC entry 276 (class 1259 OID 17704)
-- Name: ctdi_okr_krs_id_kr_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ctdi_okr_krs_id_kr_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ctdi_okr_krs_id_kr_seq OWNER TO postgres;

--
-- TOC entry 5402 (class 0 OID 0)
-- Dependencies: 276
-- Name: ctdi_okr_krs_id_kr_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ctdi_okr_krs_id_kr_seq OWNED BY public.ctdi_okr_krs.id_kr;


--
-- TOC entry 275 (class 1259 OID 17686)
-- Name: ctdi_okr_objetivos_dt; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ctdi_okr_objetivos_dt (
    id_obj_dt integer NOT NULL,
    id_direc integer NOT NULL,
    nome_obj character varying(200) NOT NULL,
    desc_obj text,
    kpi_descricao character varying(250),
    status_obj character varying(50) DEFAULT 'Ativo'::character varying,
    data_criacao timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_revisao timestamp without time zone
);


ALTER TABLE public.ctdi_okr_objetivos_dt OWNER TO postgres;

--
-- TOC entry 5403 (class 0 OID 0)
-- Dependencies: 275
-- Name: TABLE ctdi_okr_objetivos_dt; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.ctdi_okr_objetivos_dt IS 'Nível 2 do módulo OKR: Armazena os Objetivos específicos de Transformação Digital vinculados aos Direcionadores Estratégicos.';


--
-- TOC entry 274 (class 1259 OID 17685)
-- Name: ctdi_okr_objetivos_dt_id_obj_dt_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ctdi_okr_objetivos_dt_id_obj_dt_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ctdi_okr_objetivos_dt_id_obj_dt_seq OWNER TO postgres;

--
-- TOC entry 5404 (class 0 OID 0)
-- Dependencies: 274
-- Name: ctdi_okr_objetivos_dt_id_obj_dt_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ctdi_okr_objetivos_dt_id_obj_dt_seq OWNED BY public.ctdi_okr_objetivos_dt.id_obj_dt;


--
-- TOC entry 232 (class 1259 OID 16448)
-- Name: ctdi_phase; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ctdi_phase (
    id_phase integer NOT NULL,
    name_phase text NOT NULL,
    desc_phase text
);


ALTER TABLE public.ctdi_phase OWNER TO postgres;

--
-- TOC entry 233 (class 1259 OID 16455)
-- Name: ctdi_phase_id_phase_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ctdi_phase_id_phase_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ctdi_phase_id_phase_seq OWNER TO postgres;

--
-- TOC entry 5405 (class 0 OID 0)
-- Dependencies: 233
-- Name: ctdi_phase_id_phase_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ctdi_phase_id_phase_seq OWNED BY public.ctdi_phase.id_phase;


--
-- TOC entry 289 (class 1259 OID 18140)
-- Name: ctdi_problemas_referencia; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ctdi_problemas_referencia (
    id_prob integer NOT NULL,
    grupo_prob character varying(150) NOT NULL,
    categoria_prob character varying(150) NOT NULL,
    desc_prob text NOT NULL,
    razoes_prob text NOT NULL,
    solucoes_prob text NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.ctdi_problemas_referencia OWNER TO postgres;

--
-- TOC entry 234 (class 1259 OID 16456)
-- Name: ctdi_projetos; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ctdi_projetos (
    id_proj integer NOT NULL,
    id_clie integer NOT NULL,
    status character varying(20) DEFAULT 'ATIVO'::character varying,
    fase_atual character varying(100) DEFAULT 'Onda 1: Diagnóstico e Visão'::character varying,
    data_inicio timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    id_team integer,
    data_geracao_plano timestamp without time zone,
    id_ctdi integer
);


ALTER TABLE public.ctdi_projetos OWNER TO postgres;

--
-- TOC entry 235 (class 1259 OID 16464)
-- Name: ctdi_projetos_id_proj_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ctdi_projetos_id_proj_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ctdi_projetos_id_proj_seq OWNER TO postgres;

--
-- TOC entry 5406 (class 0 OID 0)
-- Dependencies: 235
-- Name: ctdi_projetos_id_proj_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ctdi_projetos_id_proj_seq OWNED BY public.ctdi_projetos.id_proj;


--
-- TOC entry 236 (class 1259 OID 16465)
-- Name: ctdi_quest; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ctdi_quest (
    id_ques integer NOT NULL,
    desc_ques text NOT NULL,
    id_dime integer,
    id_doma integer,
    prefu_ques text,
    setor_ques character varying(50) DEFAULT 'GERAL'::character varying,
    presurvey_ques boolean DEFAULT false,
    quali_ques text
);


ALTER TABLE public.ctdi_quest OWNER TO postgres;

--
-- TOC entry 237 (class 1259 OID 16473)
-- Name: ctdi_quest_id_ques_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ctdi_quest_id_ques_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ctdi_quest_id_ques_seq OWNER TO postgres;

--
-- TOC entry 5407 (class 0 OID 0)
-- Dependencies: 237
-- Name: ctdi_quest_id_ques_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ctdi_quest_id_ques_seq OWNED BY public.ctdi_quest.id_ques;


--
-- TOC entry 238 (class 1259 OID 16474)
-- Name: ctdi_refb; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ctdi_refb (
    id_refb integer NOT NULL,
    setr_refb character varying(100) NOT NULL,
    id_dime integer NOT NULL,
    id_doma integer NOT NULL,
    id_movi integer NOT NULL,
    grad_refb numrange NOT NULL
);


ALTER TABLE public.ctdi_refb OWNER TO postgres;

--
-- TOC entry 239 (class 1259 OID 16485)
-- Name: ctdi_refb_id_refb_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ctdi_refb_id_refb_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ctdi_refb_id_refb_seq OWNER TO postgres;

--
-- TOC entry 5408 (class 0 OID 0)
-- Dependencies: 239
-- Name: ctdi_refb_id_refb_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ctdi_refb_id_refb_seq OWNED BY public.ctdi_refb.id_refb;


--
-- TOC entry 240 (class 1259 OID 16486)
-- Name: ctdi_roun; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ctdi_roun (
    id_roun integer NOT NULL,
    id_dime integer,
    name_roun text,
    desc_roun text,
    ordr_roun integer
);


ALTER TABLE public.ctdi_roun OWNER TO postgres;

--
-- TOC entry 241 (class 1259 OID 16492)
-- Name: ctdi_roun_id_roun_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ctdi_roun_id_roun_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ctdi_roun_id_roun_seq OWNER TO postgres;

--
-- TOC entry 5409 (class 0 OID 0)
-- Dependencies: 241
-- Name: ctdi_roun_id_roun_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ctdi_roun_id_roun_seq OWNED BY public.ctdi_roun.id_roun;


--
-- TOC entry 259 (class 1259 OID 16708)
-- Name: ctdi_rubricas; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ctdi_rubricas (
    id_rubr integer NOT NULL,
    id_ques integer NOT NULL,
    grad_rubr integer NOT NULL,
    label_rubr character varying(50),
    desc_rubr text NOT NULL,
    CONSTRAINT ctdi_rubricas_grad_rubr_check CHECK (((grad_rubr >= 0) AND (grad_rubr <= 5)))
);


ALTER TABLE public.ctdi_rubricas OWNER TO postgres;

--
-- TOC entry 258 (class 1259 OID 16707)
-- Name: ctdi_rubricas_id_rubr_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ctdi_rubricas_id_rubr_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ctdi_rubricas_id_rubr_seq OWNER TO postgres;

--
-- TOC entry 5410 (class 0 OID 0)
-- Dependencies: 258
-- Name: ctdi_rubricas_id_rubr_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ctdi_rubricas_id_rubr_seq OWNED BY public.ctdi_rubricas.id_rubr;


--
-- TOC entry 242 (class 1259 OID 16493)
-- Name: ctdi_sprn; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ctdi_sprn (
    id_sprn integer NOT NULL,
    id_bloc integer NOT NULL,
    name_sprn text NOT NULL,
    desc_sprn text,
    ordr_sprn integer,
    dtini_sprn date,
    dtend_sprn date,
    stat_sprn text DEFAULT 'em analise'::text,
    week_sprn integer,
    targv_sprn integer,
    realv_sprn integer,
    id_itera integer,
    url_kanban text,
    swot_type text,
    swot_justification text,
    metrics_scores jsonb DEFAULT '{}'::jsonb,
    evidence_url text,
    exec_notes text,
    id_team integer,
    id_squad integer
);


ALTER TABLE public.ctdi_sprn OWNER TO postgres;

--
-- TOC entry 243 (class 1259 OID 16502)
-- Name: ctdi_sprn_id_sprn_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ctdi_sprn_id_sprn_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ctdi_sprn_id_sprn_seq OWNER TO postgres;

--
-- TOC entry 5411 (class 0 OID 0)
-- Dependencies: 243
-- Name: ctdi_sprn_id_sprn_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ctdi_sprn_id_sprn_seq OWNED BY public.ctdi_sprn.id_sprn;


--
-- TOC entry 263 (class 1259 OID 17218)
-- Name: ctdi_squads; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ctdi_squads (
    id_squad integer NOT NULL,
    nome_squad text NOT NULL,
    id_proj integer NOT NULL,
    data_criacao timestamp without time zone DEFAULT now()
);


ALTER TABLE public.ctdi_squads OWNER TO postgres;

--
-- TOC entry 262 (class 1259 OID 17217)
-- Name: ctdi_squads_id_squad_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ctdi_squads_id_squad_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ctdi_squads_id_squad_seq OWNER TO postgres;

--
-- TOC entry 5412 (class 0 OID 0)
-- Dependencies: 262
-- Name: ctdi_squads_id_squad_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ctdi_squads_id_squad_seq OWNED BY public.ctdi_squads.id_squad;


--
-- TOC entry 244 (class 1259 OID 16503)
-- Name: ctdi_surv; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ctdi_surv (
    id_surv integer NOT NULL,
    id_matu integer NOT NULL,
    id_dime integer NOT NULL,
    id_doma integer NOT NULL,
    id_ques integer NOT NULL,
    grad_ques integer,
    quali_ques text
);


ALTER TABLE public.ctdi_surv OWNER TO postgres;

--
-- TOC entry 5413 (class 0 OID 0)
-- Dependencies: 244
-- Name: COLUMN ctdi_surv.quali_ques; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.ctdi_surv.quali_ques IS 'Texto qualitativo, justificativa ou evidência da resposta coletada no Assessment de Projeto';


--
-- TOC entry 245 (class 1259 OID 16511)
-- Name: ctdi_surv_id_surv_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ctdi_surv_id_surv_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ctdi_surv_id_surv_seq OWNER TO postgres;

--
-- TOC entry 5414 (class 0 OID 0)
-- Dependencies: 245
-- Name: ctdi_surv_id_surv_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ctdi_surv_id_surv_seq OWNED BY public.ctdi_surv.id_surv;


--
-- TOC entry 246 (class 1259 OID 16512)
-- Name: ctdi_team; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ctdi_team (
    id_team integer NOT NULL,
    nome text NOT NULL,
    email text NOT NULL,
    role text DEFAULT 'CONSULTOR'::text,
    ativo boolean DEFAULT true,
    data_cadastro timestamp without time zone DEFAULT now(),
    password_hash text,
    id_member integer NOT NULL,
    "position" character varying(100),
    id_squad integer
);


ALTER TABLE public.ctdi_team OWNER TO postgres;

--
-- TOC entry 247 (class 1259 OID 16524)
-- Name: ctdi_team_id_member_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ctdi_team_id_member_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ctdi_team_id_member_seq OWNER TO postgres;

--
-- TOC entry 5415 (class 0 OID 0)
-- Dependencies: 247
-- Name: ctdi_team_id_member_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ctdi_team_id_member_seq OWNED BY public.ctdi_team.id_member;


--
-- TOC entry 248 (class 1259 OID 16525)
-- Name: ctdi_team_id_team_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ctdi_team_id_team_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ctdi_team_id_team_seq OWNER TO postgres;

--
-- TOC entry 5416 (class 0 OID 0)
-- Dependencies: 248
-- Name: ctdi_team_id_team_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ctdi_team_id_team_seq OWNED BY public.ctdi_team.id_team;


--
-- TOC entry 288 (class 1259 OID 18121)
-- Name: espex_acao; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.espex_acao (
    id_espex integer NOT NULL,
    id_acao integer NOT NULL,
    hipo_espex text NOT NULL,
    desc_espex text NOT NULL,
    result_espex text NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.espex_acao OWNER TO postgres;

--
-- TOC entry 287 (class 1259 OID 18120)
-- Name: espex_acao_id_espex_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.espex_acao_id_espex_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.espex_acao_id_espex_seq OWNER TO postgres;

--
-- TOC entry 5417 (class 0 OID 0)
-- Dependencies: 287
-- Name: espex_acao_id_espex_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.espex_acao_id_espex_seq OWNED BY public.espex_acao.id_espex;


--
-- TOC entry 286 (class 1259 OID 17827)
-- Name: inov_acao_notas_mapping; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.inov_acao_notas_mapping (
    id_acao integer NOT NULL,
    id_nota integer NOT NULL
);


ALTER TABLE public.inov_acao_notas_mapping OWNER TO postgres;

--
-- TOC entry 285 (class 1259 OID 17809)
-- Name: inov_acoes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.inov_acoes (
    id_acao integer NOT NULL,
    id_clie integer NOT NULL,
    bloco_leaction character varying(50) NOT NULL,
    nome_acao text,
    justificativa_pedagogica text,
    impacto_negocio text,
    composicao_estruturada jsonb,
    status_acao character varying(30) DEFAULT 'Em Estruturacao'::character varying,
    id_sprn_gerada integer,
    created_at timestamp without time zone DEFAULT now(),
    status_acoplamento character varying(50) DEFAULT 'Isolado'::character varying,
    id_prob integer,
    rotas_metodologicas jsonb DEFAULT '[]'::jsonb
);


ALTER TABLE public.inov_acoes OWNER TO postgres;

--
-- TOC entry 5418 (class 0 OID 0)
-- Dependencies: 285
-- Name: COLUMN inov_acoes.rotas_metodologicas; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.inov_acoes.rotas_metodologicas IS 'Armazena a lista de amarrações científicas estruturadas da experimentação: [{"id_meta": X, "id_prat": Y}]';


--
-- TOC entry 291 (class 1259 OID 18157)
-- Name: inov_acoes_escolas_vinculo; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.inov_acoes_escolas_vinculo (
    id_vinculo integer NOT NULL,
    id_acao integer NOT NULL,
    id_matu integer NOT NULL,
    status_acoplamento character varying(50) DEFAULT 'Aguardando_Aprovacao'::character varying,
    data_vinculo timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.inov_acoes_escolas_vinculo OWNER TO postgres;

--
-- TOC entry 290 (class 1259 OID 18156)
-- Name: inov_acoes_escolas_vinculo_id_vinculo_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.inov_acoes_escolas_vinculo_id_vinculo_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.inov_acoes_escolas_vinculo_id_vinculo_seq OWNER TO postgres;

--
-- TOC entry 5419 (class 0 OID 0)
-- Dependencies: 290
-- Name: inov_acoes_escolas_vinculo_id_vinculo_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.inov_acoes_escolas_vinculo_id_vinculo_seq OWNED BY public.inov_acoes_escolas_vinculo.id_vinculo;


--
-- TOC entry 284 (class 1259 OID 17808)
-- Name: inov_acoes_id_acao_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.inov_acoes_id_acao_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.inov_acoes_id_acao_seq OWNER TO postgres;

--
-- TOC entry 5420 (class 0 OID 0)
-- Dependencies: 284
-- Name: inov_acoes_id_acao_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.inov_acoes_id_acao_seq OWNED BY public.inov_acoes.id_acao;


--
-- TOC entry 283 (class 1259 OID 17785)
-- Name: inov_agenda_notas; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.inov_agenda_notas (
    id_nota integer NOT NULL,
    id_clie integer NOT NULL,
    id_rotina integer,
    conteudo_bruto text NOT NULL,
    tipo_observacao character varying(50),
    status_nota character varying(20) DEFAULT 'Pendente'::character varying,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.inov_agenda_notas OWNER TO postgres;

--
-- TOC entry 282 (class 1259 OID 17784)
-- Name: inov_agenda_notas_id_nota_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.inov_agenda_notas_id_nota_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.inov_agenda_notas_id_nota_seq OWNER TO postgres;

--
-- TOC entry 5421 (class 0 OID 0)
-- Dependencies: 282
-- Name: inov_agenda_notas_id_nota_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.inov_agenda_notas_id_nota_seq OWNED BY public.inov_agenda_notas.id_nota;


--
-- TOC entry 281 (class 1259 OID 17765)
-- Name: inov_agenda_rotina; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.inov_agenda_rotina (
    id_rotina integer NOT NULL,
    id_clie integer NOT NULL,
    titulo_atividade text NOT NULL,
    data_atividade date DEFAULT CURRENT_DATE NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.inov_agenda_rotina OWNER TO postgres;

--
-- TOC entry 280 (class 1259 OID 17764)
-- Name: inov_agenda_rotina_id_rotina_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.inov_agenda_rotina_id_rotina_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.inov_agenda_rotina_id_rotina_seq OWNER TO postgres;

--
-- TOC entry 5422 (class 0 OID 0)
-- Dependencies: 280
-- Name: inov_agenda_rotina_id_rotina_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.inov_agenda_rotina_id_rotina_seq OWNED BY public.inov_agenda_rotina.id_rotina;


--
-- TOC entry 293 (class 1259 OID 18807)
-- Name: inov_metod_ativas; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.inov_metod_ativas (
    id_meta integer NOT NULL,
    cate_metodo character varying(150) NOT NULL,
    foco_plan text NOT NULL,
    abor_teorica text NOT NULL,
    prop_pratico text NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.inov_metod_ativas OWNER TO postgres;

--
-- TOC entry 5423 (class 0 OID 0)
-- Dependencies: 293
-- Name: TABLE inov_metod_ativas; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.inov_metod_ativas IS 'Tabela descritiva de taxonomia e fundamentação das Metodologias (Cri)ativas.';


--
-- TOC entry 292 (class 1259 OID 18806)
-- Name: inov_metod_ativas_id_meta_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.inov_metod_ativas_id_meta_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.inov_metod_ativas_id_meta_seq OWNER TO postgres;

--
-- TOC entry 5424 (class 0 OID 0)
-- Dependencies: 292
-- Name: inov_metod_ativas_id_meta_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.inov_metod_ativas_id_meta_seq OWNED BY public.inov_metod_ativas.id_meta;


--
-- TOC entry 297 (class 1259 OID 18925)
-- Name: inov_subtasks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.inov_subtasks (
    id_subtask integer NOT NULL,
    id_acao integer,
    pilar_subtask character varying(20),
    desc_subtask text
);


ALTER TABLE public.inov_subtasks OWNER TO postgres;

--
-- TOC entry 296 (class 1259 OID 18924)
-- Name: inov_subtasks_id_subtask_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.inov_subtasks_id_subtask_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.inov_subtasks_id_subtask_seq OWNER TO postgres;

--
-- TOC entry 5425 (class 0 OID 0)
-- Dependencies: 296
-- Name: inov_subtasks_id_subtask_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.inov_subtasks_id_subtask_seq OWNED BY public.inov_subtasks.id_subtask;


--
-- TOC entry 249 (class 1259 OID 16526)
-- Name: leaf_bloc; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.leaf_bloc (
    id_bloc integer NOT NULL,
    name_bloc text NOT NULL,
    desc_bloc text,
    id_dime integer NOT NULL,
    id_doma integer NOT NULL,
    level_bloc integer DEFAULT 1,
    quali_bloc text
);


ALTER TABLE public.leaf_bloc OWNER TO postgres;

--
-- TOC entry 250 (class 1259 OID 16536)
-- Name: leaf_bloc_id_bloc_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.leaf_bloc_id_bloc_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.leaf_bloc_id_bloc_seq OWNER TO postgres;

--
-- TOC entry 5426 (class 0 OID 0)
-- Dependencies: 250
-- Name: leaf_bloc_id_bloc_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.leaf_bloc_id_bloc_seq OWNED BY public.leaf_bloc.id_bloc;


--
-- TOC entry 251 (class 1259 OID 16537)
-- Name: leaf_derv; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.leaf_derv (
    id_derv integer NOT NULL,
    name_derv text NOT NULL,
    desc_derv text,
    derv_defi text,
    derv_comp text,
    derv_metr text,
    id_bloc integer,
    criteria_dod jsonb DEFAULT '{}'::jsonb
);


ALTER TABLE public.leaf_derv OWNER TO postgres;

--
-- TOC entry 5427 (class 0 OID 0)
-- Dependencies: 251
-- Name: COLUMN leaf_derv.criteria_dod; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.leaf_derv.criteria_dod IS 'Estrutura JSON contendo listas: "required" (geral) e "context_education" (específico)';


--
-- TOC entry 252 (class 1259 OID 16545)
-- Name: leaf_derv_id_derv_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.leaf_derv_id_derv_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.leaf_derv_id_derv_seq OWNER TO postgres;

--
-- TOC entry 5428 (class 0 OID 0)
-- Dependencies: 252
-- Name: leaf_derv_id_derv_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.leaf_derv_id_derv_seq OWNED BY public.leaf_derv.id_derv;


--
-- TOC entry 253 (class 1259 OID 16546)
-- Name: leaf_dime; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.leaf_dime (
    id_dime integer NOT NULL,
    name_dime text NOT NULL,
    desc_dime text,
    long_description text,
    code_dime character varying(10),
    perspective_dime text
);


ALTER TABLE public.leaf_dime OWNER TO postgres;

--
-- TOC entry 5429 (class 0 OID 0)
-- Dependencies: 253
-- Name: COLUMN leaf_dime.long_description; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.leaf_dime.long_description IS 'Conceituação detalhada baseada no LeAction F e em padrões de mercado';


--
-- TOC entry 254 (class 1259 OID 16553)
-- Name: leaf_dime_id_dime_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.leaf_dime_id_dime_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.leaf_dime_id_dime_seq OWNER TO postgres;

--
-- TOC entry 5430 (class 0 OID 0)
-- Dependencies: 254
-- Name: leaf_dime_id_dime_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.leaf_dime_id_dime_seq OWNED BY public.leaf_dime.id_dime;


--
-- TOC entry 255 (class 1259 OID 16554)
-- Name: leaf_doma; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.leaf_doma (
    id_doma integer NOT NULL,
    name_doma text NOT NULL,
    desc_doma text,
    vetor_estrategico character varying(255)
);


ALTER TABLE public.leaf_doma OWNER TO postgres;

--
-- TOC entry 256 (class 1259 OID 16561)
-- Name: leaf_doma_id_doma_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.leaf_doma_id_doma_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.leaf_doma_id_doma_seq OWNER TO postgres;

--
-- TOC entry 5431 (class 0 OID 0)
-- Dependencies: 256
-- Name: leaf_doma_id_doma_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.leaf_doma_id_doma_seq OWNED BY public.leaf_doma.id_doma;


--
-- TOC entry 295 (class 1259 OID 18822)
-- Name: metodo_ativas_praticas; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.metodo_ativas_praticas (
    id_prat integer NOT NULL,
    id_meta integer NOT NULL,
    estra_pratica character varying(200) NOT NULL,
    meca_func text NOT NULL,
    recursos_impacto text NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.metodo_ativas_praticas OWNER TO postgres;

--
-- TOC entry 5432 (class 0 OID 0)
-- Dependencies: 295
-- Name: TABLE metodo_ativas_praticas; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON TABLE public.metodo_ativas_praticas IS 'Detalhamento operacional, mecânicas e recursos das práticas vinculadas às Metodologias Inovativas.';


--
-- TOC entry 294 (class 1259 OID 18821)
-- Name: metodo_ativas_praticas_id_prat_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.metodo_ativas_praticas_id_prat_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.metodo_ativas_praticas_id_prat_seq OWNER TO postgres;

--
-- TOC entry 5433 (class 0 OID 0)
-- Dependencies: 294
-- Name: metodo_ativas_praticas_id_prat_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.metodo_ativas_praticas_id_prat_seq OWNED BY public.metodo_ativas_praticas.id_prat;


--
-- TOC entry 257 (class 1259 OID 16562)
-- Name: vw_dashboard_genese; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.vw_dashboard_genese AS
 SELECT p.id_proj,
    c.nome_clie AS cliente,
    m.id_matu AS id_diagnostico,
    m.status_ia AS status_worker,
    p.id_ctdi AS id_ciclo,
    p.fase_atual,
    p.status AS status_projeto,
    p.data_geracao_plano AS nascimento_plano
   FROM ((public.ctdi_matu m
     JOIN public.ctdi_projetos p ON ((m.id_clie = p.id_clie)))
     JOIN public.ctdi_clie c ON ((m.id_clie = c.id_clie)))
  ORDER BY p.data_geracao_plano DESC;


ALTER VIEW public.vw_dashboard_genese OWNER TO postgres;

--
-- TOC entry 5046 (class 2604 OID 16777)
-- Name: ctdi_bussola id_bussola; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_bussola ALTER COLUMN id_bussola SET DEFAULT nextval('public.ctdi_bussola_id_bussola_seq'::regclass);


--
-- TOC entry 5049 (class 2604 OID 17247)
-- Name: ctdi_cermls id_cermls; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_cermls ALTER COLUMN id_cermls SET DEFAULT nextval('public.ctdi_cermls_id_cermls_seq'::regclass);


--
-- TOC entry 5007 (class 2604 OID 16567)
-- Name: ctdi_clie id_clie; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_clie ALTER COLUMN id_clie SET DEFAULT nextval('public.ctdi_clie_id_clie_seq'::regclass);


--
-- TOC entry 5051 (class 2604 OID 17346)
-- Name: ctdi_doc_specs id_spec; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_doc_specs ALTER COLUMN id_spec SET DEFAULT nextval('public.ctdi_doc_specs_id_spec_seq'::regclass);


--
-- TOC entry 5055 (class 2604 OID 17388)
-- Name: ctdi_evidencias id_evid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_evidencias ALTER COLUMN id_evid SET DEFAULT nextval('public.ctdi_evidencias_id_evid_seq'::regclass);


--
-- TOC entry 5011 (class 2604 OID 16568)
-- Name: ctdi_itera id_itera; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_itera ALTER COLUMN id_itera SET DEFAULT nextval('public.ctdi_itera_id_itera_seq'::regclass);


--
-- TOC entry 5013 (class 2604 OID 16569)
-- Name: ctdi_lead_access id_access; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_lead_access ALTER COLUMN id_access SET DEFAULT nextval('public.ctdi_lead_access_id_access_seq'::regclass);


--
-- TOC entry 5015 (class 2604 OID 16570)
-- Name: ctdi_main id_ctdi; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_main ALTER COLUMN id_ctdi SET DEFAULT nextval('public.ctdi_main_id_ctdi_seq'::regclass);


--
-- TOC entry 5017 (class 2604 OID 16571)
-- Name: ctdi_matu id_matu; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_matu ALTER COLUMN id_matu SET DEFAULT nextval('public.ctdi_matu_id_matu_seq'::regclass);


--
-- TOC entry 5058 (class 2604 OID 17454)
-- Name: ctdi_matu_presurvey id_presurvey; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_matu_presurvey ALTER COLUMN id_presurvey SET DEFAULT nextval('public.ctdi_matu_presurvey_id_presurvey_seq'::regclass);


--
-- TOC entry 5019 (class 2604 OID 16572)
-- Name: ctdi_movi id_movi; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_movi ALTER COLUMN id_movi SET DEFAULT nextval('public.ctdi_movi_id_movi_seq'::regclass);


--
-- TOC entry 5073 (class 2604 OID 17733)
-- Name: ctdi_okr_atividades id_ativ; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_okr_atividades ALTER COLUMN id_ativ SET DEFAULT nextval('public.ctdi_okr_atividades_id_ativ_seq'::regclass);


--
-- TOC entry 5060 (class 2604 OID 17667)
-- Name: ctdi_okr_direcionadores id_direc; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_okr_direcionadores ALTER COLUMN id_direc SET DEFAULT nextval('public.ctdi_okr_direcionadores_id_direc_seq'::regclass);


--
-- TOC entry 5068 (class 2604 OID 17708)
-- Name: ctdi_okr_krs id_kr; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_okr_krs ALTER COLUMN id_kr SET DEFAULT nextval('public.ctdi_okr_krs_id_kr_seq'::regclass);


--
-- TOC entry 5065 (class 2604 OID 17689)
-- Name: ctdi_okr_objetivos_dt id_obj_dt; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_okr_objetivos_dt ALTER COLUMN id_obj_dt SET DEFAULT nextval('public.ctdi_okr_objetivos_dt_id_obj_dt_seq'::regclass);


--
-- TOC entry 5020 (class 2604 OID 16573)
-- Name: ctdi_phase id_phase; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_phase ALTER COLUMN id_phase SET DEFAULT nextval('public.ctdi_phase_id_phase_seq'::regclass);


--
-- TOC entry 5021 (class 2604 OID 16574)
-- Name: ctdi_projetos id_proj; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_projetos ALTER COLUMN id_proj SET DEFAULT nextval('public.ctdi_projetos_id_proj_seq'::regclass);


--
-- TOC entry 5025 (class 2604 OID 16575)
-- Name: ctdi_quest id_ques; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_quest ALTER COLUMN id_ques SET DEFAULT nextval('public.ctdi_quest_id_ques_seq'::regclass);


--
-- TOC entry 5028 (class 2604 OID 16576)
-- Name: ctdi_refb id_refb; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_refb ALTER COLUMN id_refb SET DEFAULT nextval('public.ctdi_refb_id_refb_seq'::regclass);


--
-- TOC entry 5029 (class 2604 OID 16577)
-- Name: ctdi_roun id_roun; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_roun ALTER COLUMN id_roun SET DEFAULT nextval('public.ctdi_roun_id_roun_seq'::regclass);


--
-- TOC entry 5045 (class 2604 OID 16711)
-- Name: ctdi_rubricas id_rubr; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_rubricas ALTER COLUMN id_rubr SET DEFAULT nextval('public.ctdi_rubricas_id_rubr_seq'::regclass);


--
-- TOC entry 5030 (class 2604 OID 16578)
-- Name: ctdi_sprn id_sprn; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_sprn ALTER COLUMN id_sprn SET DEFAULT nextval('public.ctdi_sprn_id_sprn_seq'::regclass);


--
-- TOC entry 5047 (class 2604 OID 17221)
-- Name: ctdi_squads id_squad; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_squads ALTER COLUMN id_squad SET DEFAULT nextval('public.ctdi_squads_id_squad_seq'::regclass);


--
-- TOC entry 5033 (class 2604 OID 16579)
-- Name: ctdi_surv id_surv; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_surv ALTER COLUMN id_surv SET DEFAULT nextval('public.ctdi_surv_id_surv_seq'::regclass);


--
-- TOC entry 5034 (class 2604 OID 16580)
-- Name: ctdi_team id_team; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_team ALTER COLUMN id_team SET DEFAULT nextval('public.ctdi_team_id_team_seq'::regclass);


--
-- TOC entry 5038 (class 2604 OID 16581)
-- Name: ctdi_team id_member; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_team ALTER COLUMN id_member SET DEFAULT nextval('public.ctdi_team_id_member_seq'::regclass);


--
-- TOC entry 5087 (class 2604 OID 18124)
-- Name: espex_acao id_espex; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.espex_acao ALTER COLUMN id_espex SET DEFAULT nextval('public.espex_acao_id_espex_seq'::regclass);


--
-- TOC entry 5082 (class 2604 OID 17812)
-- Name: inov_acoes id_acao; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inov_acoes ALTER COLUMN id_acao SET DEFAULT nextval('public.inov_acoes_id_acao_seq'::regclass);


--
-- TOC entry 5090 (class 2604 OID 18160)
-- Name: inov_acoes_escolas_vinculo id_vinculo; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inov_acoes_escolas_vinculo ALTER COLUMN id_vinculo SET DEFAULT nextval('public.inov_acoes_escolas_vinculo_id_vinculo_seq'::regclass);


--
-- TOC entry 5079 (class 2604 OID 17788)
-- Name: inov_agenda_notas id_nota; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inov_agenda_notas ALTER COLUMN id_nota SET DEFAULT nextval('public.inov_agenda_notas_id_nota_seq'::regclass);


--
-- TOC entry 5076 (class 2604 OID 17768)
-- Name: inov_agenda_rotina id_rotina; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inov_agenda_rotina ALTER COLUMN id_rotina SET DEFAULT nextval('public.inov_agenda_rotina_id_rotina_seq'::regclass);


--
-- TOC entry 5093 (class 2604 OID 18810)
-- Name: inov_metod_ativas id_meta; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inov_metod_ativas ALTER COLUMN id_meta SET DEFAULT nextval('public.inov_metod_ativas_id_meta_seq'::regclass);


--
-- TOC entry 5097 (class 2604 OID 18928)
-- Name: inov_subtasks id_subtask; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inov_subtasks ALTER COLUMN id_subtask SET DEFAULT nextval('public.inov_subtasks_id_subtask_seq'::regclass);


--
-- TOC entry 5039 (class 2604 OID 16582)
-- Name: leaf_bloc id_bloc; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.leaf_bloc ALTER COLUMN id_bloc SET DEFAULT nextval('public.leaf_bloc_id_bloc_seq'::regclass);


--
-- TOC entry 5041 (class 2604 OID 16583)
-- Name: leaf_derv id_derv; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.leaf_derv ALTER COLUMN id_derv SET DEFAULT nextval('public.leaf_derv_id_derv_seq'::regclass);


--
-- TOC entry 5043 (class 2604 OID 16584)
-- Name: leaf_dime id_dime; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.leaf_dime ALTER COLUMN id_dime SET DEFAULT nextval('public.leaf_dime_id_dime_seq'::regclass);


--
-- TOC entry 5044 (class 2604 OID 16585)
-- Name: leaf_doma id_doma; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.leaf_doma ALTER COLUMN id_doma SET DEFAULT nextval('public.leaf_doma_id_doma_seq'::regclass);


--
-- TOC entry 5095 (class 2604 OID 18825)
-- Name: metodo_ativas_praticas id_prat; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.metodo_ativas_praticas ALTER COLUMN id_prat SET DEFAULT nextval('public.metodo_ativas_praticas_id_prat_seq'::regclass);


--
-- TOC entry 5100 (class 2606 OID 16589)
-- Name: bloc_derv bloc_derv_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bloc_derv
    ADD CONSTRAINT bloc_derv_pkey PRIMARY KEY (id_bloc, id_derv);


--
-- TOC entry 5149 (class 2606 OID 16784)
-- Name: ctdi_bussola ctdi_bussola_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_bussola
    ADD CONSTRAINT ctdi_bussola_pkey PRIMARY KEY (id_bussola);


--
-- TOC entry 5153 (class 2606 OID 17257)
-- Name: ctdi_cermls ctdi_cermls_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_cermls
    ADD CONSTRAINT ctdi_cermls_pkey PRIMARY KEY (id_cermls);


--
-- TOC entry 5102 (class 2606 OID 16591)
-- Name: ctdi_clie ctdi_clie_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_clie
    ADD CONSTRAINT ctdi_clie_pkey PRIMARY KEY (id_clie);


--
-- TOC entry 5155 (class 2606 OID 17355)
-- Name: ctdi_doc_specs ctdi_doc_specs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_doc_specs
    ADD CONSTRAINT ctdi_doc_specs_pkey PRIMARY KEY (id_spec);


--
-- TOC entry 5157 (class 2606 OID 17397)
-- Name: ctdi_evidencias ctdi_evidencias_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_evidencias
    ADD CONSTRAINT ctdi_evidencias_pkey PRIMARY KEY (id_evid);


--
-- TOC entry 5104 (class 2606 OID 16593)
-- Name: ctdi_itera ctdi_itera_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_itera
    ADD CONSTRAINT ctdi_itera_pkey PRIMARY KEY (id_itera);


--
-- TOC entry 5106 (class 2606 OID 16595)
-- Name: ctdi_lead_access ctdi_lead_access_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_lead_access
    ADD CONSTRAINT ctdi_lead_access_pkey PRIMARY KEY (id_access);


--
-- TOC entry 5110 (class 2606 OID 16597)
-- Name: ctdi_main ctdi_main_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_main
    ADD CONSTRAINT ctdi_main_pkey PRIMARY KEY (id_ctdi);


--
-- TOC entry 5112 (class 2606 OID 16599)
-- Name: ctdi_matu ctdi_matu_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_matu
    ADD CONSTRAINT ctdi_matu_pkey PRIMARY KEY (id_matu);


--
-- TOC entry 5159 (class 2606 OID 17468)
-- Name: ctdi_matu_presurvey ctdi_matu_presurvey_id_matu_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_matu_presurvey
    ADD CONSTRAINT ctdi_matu_presurvey_id_matu_key UNIQUE (id_matu);


--
-- TOC entry 5161 (class 2606 OID 17461)
-- Name: ctdi_matu_presurvey ctdi_matu_presurvey_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_matu_presurvey
    ADD CONSTRAINT ctdi_matu_presurvey_pkey PRIMARY KEY (id_presurvey);


--
-- TOC entry 5115 (class 2606 OID 16601)
-- Name: ctdi_movi ctdi_movi_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_movi
    ADD CONSTRAINT ctdi_movi_pkey PRIMARY KEY (id_movi);


--
-- TOC entry 5169 (class 2606 OID 17746)
-- Name: ctdi_okr_atividades ctdi_okr_atividades_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_okr_atividades
    ADD CONSTRAINT ctdi_okr_atividades_pkey PRIMARY KEY (id_ativ);


--
-- TOC entry 5163 (class 2606 OID 17678)
-- Name: ctdi_okr_direcionadores ctdi_okr_direcionadores_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_okr_direcionadores
    ADD CONSTRAINT ctdi_okr_direcionadores_pkey PRIMARY KEY (id_direc);


--
-- TOC entry 5167 (class 2606 OID 17723)
-- Name: ctdi_okr_krs ctdi_okr_krs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_okr_krs
    ADD CONSTRAINT ctdi_okr_krs_pkey PRIMARY KEY (id_kr);


--
-- TOC entry 5165 (class 2606 OID 17698)
-- Name: ctdi_okr_objetivos_dt ctdi_okr_objetivos_dt_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_okr_objetivos_dt
    ADD CONSTRAINT ctdi_okr_objetivos_dt_pkey PRIMARY KEY (id_obj_dt);


--
-- TOC entry 5117 (class 2606 OID 16603)
-- Name: ctdi_phase ctdi_phase_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_phase
    ADD CONSTRAINT ctdi_phase_pkey PRIMARY KEY (id_phase);


--
-- TOC entry 5181 (class 2606 OID 18153)
-- Name: ctdi_problemas_referencia ctdi_problemas_referencia_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_problemas_referencia
    ADD CONSTRAINT ctdi_problemas_referencia_pkey PRIMARY KEY (id_prob);


--
-- TOC entry 5119 (class 2606 OID 16605)
-- Name: ctdi_projetos ctdi_projetos_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_projetos
    ADD CONSTRAINT ctdi_projetos_pkey PRIMARY KEY (id_proj);


--
-- TOC entry 5123 (class 2606 OID 16607)
-- Name: ctdi_quest ctdi_quest_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_quest
    ADD CONSTRAINT ctdi_quest_pkey PRIMARY KEY (id_ques);


--
-- TOC entry 5125 (class 2606 OID 16609)
-- Name: ctdi_refb ctdi_refb_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_refb
    ADD CONSTRAINT ctdi_refb_pkey PRIMARY KEY (id_refb);


--
-- TOC entry 5127 (class 2606 OID 16611)
-- Name: ctdi_roun ctdi_roun_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_roun
    ADD CONSTRAINT ctdi_roun_pkey PRIMARY KEY (id_roun);


--
-- TOC entry 5146 (class 2606 OID 16720)
-- Name: ctdi_rubricas ctdi_rubricas_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_rubricas
    ADD CONSTRAINT ctdi_rubricas_pkey PRIMARY KEY (id_rubr);


--
-- TOC entry 5129 (class 2606 OID 16613)
-- Name: ctdi_sprn ctdi_sprn_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_sprn
    ADD CONSTRAINT ctdi_sprn_pkey PRIMARY KEY (id_sprn);


--
-- TOC entry 5151 (class 2606 OID 17229)
-- Name: ctdi_squads ctdi_squads_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_squads
    ADD CONSTRAINT ctdi_squads_pkey PRIMARY KEY (id_squad);


--
-- TOC entry 5131 (class 2606 OID 16615)
-- Name: ctdi_surv ctdi_surv_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_surv
    ADD CONSTRAINT ctdi_surv_pkey PRIMARY KEY (id_matu, id_ques);


--
-- TOC entry 5135 (class 2606 OID 16617)
-- Name: ctdi_team ctdi_team_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_team
    ADD CONSTRAINT ctdi_team_pkey PRIMARY KEY (id_member);


--
-- TOC entry 5179 (class 2606 OID 18134)
-- Name: espex_acao espex_acao_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.espex_acao
    ADD CONSTRAINT espex_acao_pkey PRIMARY KEY (id_espex);


--
-- TOC entry 5177 (class 2606 OID 17833)
-- Name: inov_acao_notas_mapping inov_acao_notas_mapping_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inov_acao_notas_mapping
    ADD CONSTRAINT inov_acao_notas_mapping_pkey PRIMARY KEY (id_acao, id_nota);


--
-- TOC entry 5185 (class 2606 OID 18167)
-- Name: inov_acoes_escolas_vinculo inov_acoes_escolas_vinculo_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inov_acoes_escolas_vinculo
    ADD CONSTRAINT inov_acoes_escolas_vinculo_pkey PRIMARY KEY (id_vinculo);


--
-- TOC entry 5175 (class 2606 OID 17821)
-- Name: inov_acoes inov_acoes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inov_acoes
    ADD CONSTRAINT inov_acoes_pkey PRIMARY KEY (id_acao);


--
-- TOC entry 5173 (class 2606 OID 17797)
-- Name: inov_agenda_notas inov_agenda_notas_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inov_agenda_notas
    ADD CONSTRAINT inov_agenda_notas_pkey PRIMARY KEY (id_nota);


--
-- TOC entry 5171 (class 2606 OID 17778)
-- Name: inov_agenda_rotina inov_agenda_rotina_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inov_agenda_rotina
    ADD CONSTRAINT inov_agenda_rotina_pkey PRIMARY KEY (id_rotina);


--
-- TOC entry 5187 (class 2606 OID 18820)
-- Name: inov_metod_ativas inov_metod_ativas_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inov_metod_ativas
    ADD CONSTRAINT inov_metod_ativas_pkey PRIMARY KEY (id_meta);


--
-- TOC entry 5191 (class 2606 OID 18933)
-- Name: inov_subtasks inov_subtasks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inov_subtasks
    ADD CONSTRAINT inov_subtasks_pkey PRIMARY KEY (id_subtask);


--
-- TOC entry 5138 (class 2606 OID 16619)
-- Name: leaf_bloc leaf_bloc_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.leaf_bloc
    ADD CONSTRAINT leaf_bloc_pkey PRIMARY KEY (id_bloc);


--
-- TOC entry 5140 (class 2606 OID 16621)
-- Name: leaf_derv leaf_derv_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.leaf_derv
    ADD CONSTRAINT leaf_derv_pkey PRIMARY KEY (id_derv);


--
-- TOC entry 5142 (class 2606 OID 16623)
-- Name: leaf_dime leaf_dime_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.leaf_dime
    ADD CONSTRAINT leaf_dime_pkey PRIMARY KEY (id_dime);


--
-- TOC entry 5144 (class 2606 OID 16625)
-- Name: leaf_doma leaf_doma_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.leaf_doma
    ADD CONSTRAINT leaf_doma_pkey PRIMARY KEY (id_doma);


--
-- TOC entry 5189 (class 2606 OID 18835)
-- Name: metodo_ativas_praticas metodo_ativas_praticas_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.metodo_ativas_praticas
    ADD CONSTRAINT metodo_ativas_praticas_pkey PRIMARY KEY (id_prat);


--
-- TOC entry 5121 (class 2606 OID 17021)
-- Name: ctdi_projetos unique_id_clie; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_projetos
    ADD CONSTRAINT unique_id_clie UNIQUE (id_clie);


--
-- TOC entry 5133 (class 2606 OID 16925)
-- Name: ctdi_surv unique_survey_response; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_surv
    ADD CONSTRAINT unique_survey_response UNIQUE (id_matu, id_ques);


--
-- TOC entry 5108 (class 2606 OID 16627)
-- Name: ctdi_lead_access uq_lead_access_clie; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_lead_access
    ADD CONSTRAINT uq_lead_access_clie UNIQUE (id_clie);


--
-- TOC entry 5113 (class 1259 OID 16628)
-- Name: idx_ctdi_matu_status_ia; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_ctdi_matu_status_ia ON public.ctdi_matu USING btree (status_ia);


--
-- TOC entry 5136 (class 1259 OID 16629)
-- Name: idx_ctdi_team_group; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_ctdi_team_group ON public.ctdi_team USING btree (id_team);


--
-- TOC entry 5147 (class 1259 OID 16726)
-- Name: idx_rubrica_questao; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_rubrica_questao ON public.ctdi_rubricas USING btree (id_ques);


--
-- TOC entry 5182 (class 1259 OID 18174)
-- Name: idx_vinculo_id_acao; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_vinculo_id_acao ON public.inov_acoes_escolas_vinculo USING btree (id_acao);


--
-- TOC entry 5183 (class 1259 OID 18173)
-- Name: idx_vinculo_id_matu; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_vinculo_id_matu ON public.inov_acoes_escolas_vinculo USING btree (id_matu);


--
-- TOC entry 5229 (class 2620 OID 17758)
-- Name: ctdi_okr_atividades tg_atualizar_hierarquia_okr; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER tg_atualizar_hierarquia_okr AFTER INSERT OR DELETE OR UPDATE OF status_ativ ON public.ctdi_okr_atividades FOR EACH ROW EXECUTE FUNCTION public.fn_recalcular_progresso_kr();


--
-- TOC entry 5192 (class 2606 OID 16630)
-- Name: bloc_derv bloc_derv_id_derv_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bloc_derv
    ADD CONSTRAINT bloc_derv_id_derv_fkey FOREIGN KEY (id_derv) REFERENCES public.leaf_derv(id_derv);


--
-- TOC entry 5207 (class 2606 OID 16785)
-- Name: ctdi_bussola ctdi_bussola_id_ques_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_bussola
    ADD CONSTRAINT ctdi_bussola_id_ques_fkey FOREIGN KEY (id_ques) REFERENCES public.ctdi_quest(id_ques);


--
-- TOC entry 5194 (class 2606 OID 16635)
-- Name: ctdi_matu ctdi_matu_id_clie_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_matu
    ADD CONSTRAINT ctdi_matu_id_clie_fkey FOREIGN KEY (id_clie) REFERENCES public.ctdi_clie(id_clie);


--
-- TOC entry 5212 (class 2606 OID 17462)
-- Name: ctdi_matu_presurvey ctdi_matu_presurvey_id_matu_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_matu_presurvey
    ADD CONSTRAINT ctdi_matu_presurvey_id_matu_fkey FOREIGN KEY (id_matu) REFERENCES public.ctdi_matu(id_matu);


--
-- TOC entry 5200 (class 2606 OID 16640)
-- Name: ctdi_surv ctdi_surv_id_doma_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_surv
    ADD CONSTRAINT ctdi_surv_id_doma_fkey FOREIGN KEY (id_doma) REFERENCES public.leaf_doma(id_doma);


--
-- TOC entry 5201 (class 2606 OID 16645)
-- Name: ctdi_surv ctdi_surv_id_matu_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_surv
    ADD CONSTRAINT ctdi_surv_id_matu_fkey FOREIGN KEY (id_matu) REFERENCES public.ctdi_matu(id_matu);


--
-- TOC entry 5202 (class 2606 OID 16650)
-- Name: ctdi_surv ctdi_surv_id_ques_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_surv
    ADD CONSTRAINT ctdi_surv_id_ques_fkey FOREIGN KEY (id_ques) REFERENCES public.ctdi_quest(id_ques);


--
-- TOC entry 5216 (class 2606 OID 17759)
-- Name: ctdi_okr_atividades fk_atividade_team; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_okr_atividades
    ADD CONSTRAINT fk_atividade_team FOREIGN KEY (id_team) REFERENCES public.ctdi_team(id_member) ON DELETE SET NULL;


--
-- TOC entry 5204 (class 2606 OID 16655)
-- Name: leaf_bloc fk_bloc_dime; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.leaf_bloc
    ADD CONSTRAINT fk_bloc_dime FOREIGN KEY (id_dime) REFERENCES public.leaf_dime(id_dime);


--
-- TOC entry 5205 (class 2606 OID 16660)
-- Name: leaf_bloc fk_bloc_doma; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.leaf_bloc
    ADD CONSTRAINT fk_bloc_doma FOREIGN KEY (id_doma) REFERENCES public.leaf_doma(id_doma);


--
-- TOC entry 5213 (class 2606 OID 17679)
-- Name: ctdi_okr_direcionadores fk_clie_direc; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_okr_direcionadores
    ADD CONSTRAINT fk_clie_direc FOREIGN KEY (id_clie) REFERENCES public.ctdi_clie(id_clie) ON DELETE CASCADE;


--
-- TOC entry 5195 (class 2606 OID 16665)
-- Name: ctdi_projetos fk_cliente_projeto; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_projetos
    ADD CONSTRAINT fk_cliente_projeto FOREIGN KEY (id_clie) REFERENCES public.ctdi_clie(id_clie);


--
-- TOC entry 5214 (class 2606 OID 17699)
-- Name: ctdi_okr_objetivos_dt fk_direc_objetivo; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_okr_objetivos_dt
    ADD CONSTRAINT fk_direc_objetivo FOREIGN KEY (id_direc) REFERENCES public.ctdi_okr_direcionadores(id_direc) ON DELETE CASCADE;


--
-- TOC entry 5225 (class 2606 OID 18135)
-- Name: espex_acao fk_espex_inov_acoes; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.espex_acao
    ADD CONSTRAINT fk_espex_inov_acoes FOREIGN KEY (id_acao) REFERENCES public.inov_acoes(id_acao) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 5222 (class 2606 OID 17822)
-- Name: inov_acoes fk_inov_acoes_clie; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inov_acoes
    ADD CONSTRAINT fk_inov_acoes_clie FOREIGN KEY (id_clie) REFERENCES public.ctdi_clie(id_clie) ON DELETE CASCADE;


--
-- TOC entry 5220 (class 2606 OID 17798)
-- Name: inov_agenda_notas fk_inov_notas_clie; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inov_agenda_notas
    ADD CONSTRAINT fk_inov_notas_clie FOREIGN KEY (id_clie) REFERENCES public.ctdi_clie(id_clie) ON DELETE CASCADE;


--
-- TOC entry 5221 (class 2606 OID 17803)
-- Name: inov_agenda_notas fk_inov_notas_rotina; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inov_agenda_notas
    ADD CONSTRAINT fk_inov_notas_rotina FOREIGN KEY (id_rotina) REFERENCES public.inov_agenda_rotina(id_rotina) ON DELETE SET NULL;


--
-- TOC entry 5219 (class 2606 OID 17779)
-- Name: inov_agenda_rotina fk_inov_rotina_clie; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inov_agenda_rotina
    ADD CONSTRAINT fk_inov_rotina_clie FOREIGN KEY (id_clie) REFERENCES public.ctdi_clie(id_clie) ON DELETE CASCADE;


--
-- TOC entry 5217 (class 2606 OID 17747)
-- Name: ctdi_okr_atividades fk_kr_atividade; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_okr_atividades
    ADD CONSTRAINT fk_kr_atividade FOREIGN KEY (id_kr) REFERENCES public.ctdi_okr_krs(id_kr) ON DELETE CASCADE;


--
-- TOC entry 5193 (class 2606 OID 16670)
-- Name: ctdi_lead_access fk_lead_client; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_lead_access
    ADD CONSTRAINT fk_lead_client FOREIGN KEY (id_clie) REFERENCES public.ctdi_clie(id_clie);


--
-- TOC entry 5223 (class 2606 OID 17834)
-- Name: inov_acao_notas_mapping fk_map_acao; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inov_acao_notas_mapping
    ADD CONSTRAINT fk_map_acao FOREIGN KEY (id_acao) REFERENCES public.inov_acoes(id_acao) ON DELETE CASCADE;


--
-- TOC entry 5224 (class 2606 OID 17839)
-- Name: inov_acao_notas_mapping fk_map_nota; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inov_acao_notas_mapping
    ADD CONSTRAINT fk_map_nota FOREIGN KEY (id_nota) REFERENCES public.inov_agenda_notas(id_nota) ON DELETE CASCADE;


--
-- TOC entry 5203 (class 2606 OID 17235)
-- Name: ctdi_team fk_membro_squad_novo; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_team
    ADD CONSTRAINT fk_membro_squad_novo FOREIGN KEY (id_squad) REFERENCES public.ctdi_squads(id_squad);


--
-- TOC entry 5227 (class 2606 OID 18836)
-- Name: metodo_ativas_praticas fk_metodo_praticas_meta; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.metodo_ativas_praticas
    ADD CONSTRAINT fk_metodo_praticas_meta FOREIGN KEY (id_meta) REFERENCES public.inov_metod_ativas(id_meta) ON DELETE CASCADE;


--
-- TOC entry 5215 (class 2606 OID 17724)
-- Name: ctdi_okr_krs fk_objetivo_kr; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_okr_krs
    ADD CONSTRAINT fk_objetivo_kr FOREIGN KEY (id_obj_dt) REFERENCES public.ctdi_okr_objetivos_dt(id_obj_dt) ON DELETE CASCADE;


--
-- TOC entry 5196 (class 2606 OID 16675)
-- Name: ctdi_quest fk_quest_doma; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_quest
    ADD CONSTRAINT fk_quest_doma FOREIGN KEY (id_doma) REFERENCES public.leaf_doma(id_doma);


--
-- TOC entry 5206 (class 2606 OID 16721)
-- Name: ctdi_rubricas fk_questao; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_rubricas
    ADD CONSTRAINT fk_questao FOREIGN KEY (id_ques) REFERENCES public.ctdi_quest(id_ques) ON DELETE CASCADE;


--
-- TOC entry 5197 (class 2606 OID 16680)
-- Name: ctdi_refb fk_refb_dime; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_refb
    ADD CONSTRAINT fk_refb_dime FOREIGN KEY (id_dime) REFERENCES public.leaf_dime(id_dime);


--
-- TOC entry 5198 (class 2606 OID 16685)
-- Name: ctdi_refb fk_refb_doma; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_refb
    ADD CONSTRAINT fk_refb_doma FOREIGN KEY (id_doma) REFERENCES public.leaf_doma(id_doma);


--
-- TOC entry 5199 (class 2606 OID 16690)
-- Name: ctdi_refb fk_refb_movi; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_refb
    ADD CONSTRAINT fk_refb_movi FOREIGN KEY (id_movi) REFERENCES public.ctdi_movi(id_movi);


--
-- TOC entry 5210 (class 2606 OID 17403)
-- Name: ctdi_evidencias fk_spec; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_evidencias
    ADD CONSTRAINT fk_spec FOREIGN KEY (id_spec) REFERENCES public.ctdi_doc_specs(id_spec);


--
-- TOC entry 5209 (class 2606 OID 17258)
-- Name: ctdi_cermls fk_sprint; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_cermls
    ADD CONSTRAINT fk_sprint FOREIGN KEY (id_sprn) REFERENCES public.ctdi_sprn(id_sprn) ON DELETE CASCADE;


--
-- TOC entry 5211 (class 2606 OID 17398)
-- Name: ctdi_evidencias fk_sprint; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_evidencias
    ADD CONSTRAINT fk_sprint FOREIGN KEY (id_sprn) REFERENCES public.ctdi_sprn(id_sprn) ON DELETE CASCADE;


--
-- TOC entry 5218 (class 2606 OID 17752)
-- Name: ctdi_okr_atividades fk_sprint_atividade; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_okr_atividades
    ADD CONSTRAINT fk_sprint_atividade FOREIGN KEY (id_sprn) REFERENCES public.ctdi_sprn(id_sprn) ON DELETE CASCADE;


--
-- TOC entry 5208 (class 2606 OID 17230)
-- Name: ctdi_squads fk_squad_projeto; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ctdi_squads
    ADD CONSTRAINT fk_squad_projeto FOREIGN KEY (id_proj) REFERENCES public.ctdi_projetos(id_proj);


--
-- TOC entry 5226 (class 2606 OID 18168)
-- Name: inov_acoes_escolas_vinculo fk_vinculo_acao; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inov_acoes_escolas_vinculo
    ADD CONSTRAINT fk_vinculo_acao FOREIGN KEY (id_acao) REFERENCES public.inov_acoes(id_acao) ON DELETE CASCADE;


--
-- TOC entry 5228 (class 2606 OID 18934)
-- Name: inov_subtasks inov_subtasks_id_acao_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.inov_subtasks
    ADD CONSTRAINT inov_subtasks_id_acao_fkey FOREIGN KEY (id_acao) REFERENCES public.inov_acoes(id_acao) ON DELETE CASCADE;


-- Completed on 2026-06-12 14:44:09

--
-- Micro-CMS PanelDX (conteúdo landing + instruções)
--
CREATE TABLE IF NOT EXISTS public.ctdi_cms_config (
    id_cms              SERIAL PRIMARY KEY,
    config_key          VARCHAR(50) NOT NULL DEFAULT 'default',
    landing_page_data   JSONB NOT NULL DEFAULT '{}'::jsonb,
    instructions_data   TEXT,
    updated_at          TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_ctdi_cms_config_key UNIQUE (config_key)
);

--
-- PostgreSQL database dump complete
--

\unrestrict YT1oL5dMWofZKp4Of1aTGZYg6aS78KTQAHOhZ7fXf13aUyCvGsb7VdNGrxVhTvb

