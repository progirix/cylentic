-- =============================================================================
-- Cylentic — Schéma de base de données complet (PostgreSQL 15+)
-- =============================================================================
-- Plateforme d'examens de programmation en navigateur sécurisé.
--
-- Ce script est idempotent autant que possible et couvre :
--   1. Création de la base et des extensions
--   2. Types énumérés
--   3. Fonction et triggers utilitaires (updated_at)
--   4. Tables (par domaine) avec contraintes et clés étrangères
--   5. Index
--   6. Données de référence (seed) : plans tarifaires
--
-- Voir db.md pour la documentation détaillée du modèle.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Base de données et extensions
-- -----------------------------------------------------------------------------
-- À exécuter une fois en tant que superutilisateur, hors transaction :
--   CREATE DATABASE cylentic
--     WITH ENCODING 'UTF8' LC_COLLATE 'en_US.UTF-8' LC_CTYPE 'en_US.UTF-8'
--     TEMPLATE template0;
-- Puis se connecter à la base `cylentic` et exécuter la suite de ce fichier.
-- \connect cylentic

CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS citext;     -- emails / identifiants insensibles à la casse

-- Schéma applicatif dédié (évite de polluer public)
CREATE SCHEMA IF NOT EXISTS cylentic;
SET search_path TO cylentic, public;

-- -----------------------------------------------------------------------------
-- 2. Types énumérés
-- -----------------------------------------------------------------------------
DO $$
BEGIN
    CREATE TYPE user_role AS ENUM ('admin', 'teacher', 'student');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$
BEGIN
    CREATE TYPE establishment_type AS ENUM (
        'university_public', 'university_private', 'engineering_school',
        'bts', 'technical_highschool', 'other'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$
BEGIN
    CREATE TYPE subscription_status AS ENUM ('trial', 'active', 'expired', 'cancelled');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$
BEGIN
    CREATE TYPE exam_status AS ENUM ('draft', 'published', 'in_progress', 'finished', 'archived');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$
BEGIN
    CREATE TYPE correction_mode AS ENUM ('auto', 'manual');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$
BEGIN
    CREATE TYPE exercise_type AS ENUM ('code', 'qcm');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$
BEGIN
    CREATE TYPE qcm_answer_type AS ENUM ('single', 'multiple');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$
BEGIN
    CREATE TYPE participation_status AS ENUM (
        'connected', 'waiting', 'in_progress', 'submitted', 'excluded', 'absent'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$
BEGIN
    CREATE TYPE submission_reason AS ENUM ('manual', 'timer', 'excluded');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$
BEGIN
    CREATE TYPE incident_type AS ENUM (
        'fullscreen_exit', 'tab_switch', 'session_close', 'network_issue', 'clipboard_paste'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$
BEGIN
    CREATE TYPE notification_status AS ENUM ('pending', 'sent', 'failed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- -----------------------------------------------------------------------------
-- 3. Fonction utilitaire : maintien automatique de updated_at
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- 4. TABLES
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 4.1 Facturation / Tenant
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS subscription_plans (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code                TEXT NOT NULL UNIQUE,
    name                TEXT NOT NULL,
    max_teachers        INT,                       -- NULL = illimité
    max_students        INT,
    max_exams_per_month INT,
    price_min           NUMERIC(12,2),
    price_max           NUMERIC(12,2),
    currency            TEXT NOT NULL DEFAULT 'XOF',
    features            JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE subscription_plans IS 'Catalogue des plans Freemium (Gratuit, Starter, Pro, Enterprise).';

CREATE TABLE IF NOT EXISTS establishments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    acronym         TEXT NOT NULL,
    type            establishment_type NOT NULL,
    country         TEXT NOT NULL,
    city            TEXT NOT NULL,
    timezone        TEXT NOT NULL,                 -- ex. 'Africa/Ouagadougou'
    official_email  CITEXT NOT NULL,
    phone           TEXT NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE establishments IS 'Établissement = tenant. Le fuseau horaire détermine l''heure réelle de début des examens.';

CREATE TABLE IF NOT EXISTS establishment_subscriptions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    establishment_id    UUID NOT NULL REFERENCES establishments(id) ON DELETE CASCADE,
    plan_id             UUID NOT NULL REFERENCES subscription_plans(id) ON DELETE RESTRICT,
    status              subscription_status NOT NULL DEFAULT 'trial',
    is_simulated        BOOLEAN NOT NULL DEFAULT TRUE,   -- MVP : paiement simulé
    trial_ends_at       TIMESTAMPTZ,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    current_period_end  TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- 4.2 Référentiel scolaire
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS academic_years (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    establishment_id    UUID NOT NULL REFERENCES establishments(id) ON DELETE CASCADE,
    label               TEXT NOT NULL,             -- ex. '2025-2026'
    start_date          DATE,
    end_date            DATE,
    is_active           BOOLEAN NOT NULL DEFAULT FALSE,
    is_archived         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (establishment_id, label)
);

CREATE TABLE IF NOT EXISTS classes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    establishment_id    UUID NOT NULL REFERENCES establishments(id) ON DELETE CASCADE,
    name                TEXT NOT NULL,             -- ex. 'L2 INFO'
    track               TEXT,                      -- filière
    level               TEXT,                      -- niveau
    is_archived         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (establishment_id, name)
);

-- -----------------------------------------------------------------------------
-- 4.3 Identité & comptes
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    establishment_id        UUID NOT NULL REFERENCES establishments(id) ON DELETE CASCADE,
    identifier              CITEXT NOT NULL UNIQUE,     -- ETU-…, PROF-…, ADM-…
    role                    user_role NOT NULL,
    email                   CITEXT NOT NULL,
    first_name              TEXT NOT NULL,
    last_name               TEXT NOT NULL,
    password_hash           TEXT NOT NULL,
    must_change_password    BOOLEAN NOT NULL DEFAULT TRUE,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at           TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (establishment_id, email),
    -- Cohérence rôle <-> préfixe d'identifiant
    CONSTRAINT chk_role_identifier CHECK (
        (role = 'student' AND identifier ILIKE 'ETU-%')
        OR (role = 'teacher' AND identifier ILIKE 'PROF-%')
        OR (role = 'admin'   AND identifier ILIKE 'ADM-%')
    )
);
COMMENT ON COLUMN users.role IS 'Rôle déduit du format de l''identifiant (jamais choisi par l''utilisateur).';

CREATE TABLE IF NOT EXISTS admin_profiles (
    user_id     UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    function    TEXT
);

CREATE TABLE IF NOT EXISTS teacher_profiles (
    user_id     UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    subjects    TEXT,
    function    TEXT
);

CREATE TABLE IF NOT EXISTS student_profiles (
    user_id             UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    matricule           TEXT NOT NULL,
    class_id            UUID REFERENCES classes(id) ON DELETE SET NULL,
    academic_year_id    UUID REFERENCES academic_years(id) ON DELETE SET NULL
);

-- -----------------------------------------------------------------------------
-- 4.4 Conception d'examen
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS exams (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    establishment_id            UUID NOT NULL REFERENCES establishments(id) ON DELETE CASCADE,
    teacher_id                  UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    name                        TEXT NOT NULL,
    status                      exam_status NOT NULL DEFAULT 'draft',
    start_at                    TIMESTAMPTZ,
    duration_minutes            INT CHECK (duration_minutes IS NULL OR duration_minutes > 0),
    access_delay_minutes        INT NOT NULL DEFAULT 0 CHECK (access_delay_minutes >= 0),
    correction_mode             correction_mode NOT NULL DEFAULT 'auto',
    access_code                 TEXT UNIQUE,        -- généré à la publication (XXXX-XXXX)
    max_incidents_before_close  INT NOT NULL DEFAULT 2 CHECK (max_incidents_before_close >= 1),
    timezone                    TEXT,
    published_at                TIMESTAMPTZ,
    started_at                  TIMESTAMPTZ,
    ended_at                    TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON COLUMN exams.access_code IS 'Code XXXX-XXXX généré à la publication, NULL en brouillon, unique global.';

CREATE TABLE IF NOT EXISTS exam_classes (
    exam_id     UUID NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    class_id    UUID NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    PRIMARY KEY (exam_id, class_id)
);

CREATE TABLE IF NOT EXISTS exercises (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_id                 UUID NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    type                    exercise_type NOT NULL,
    title                   TEXT NOT NULL,
    statement               TEXT,
    language                TEXT,                  -- 'python' au MVP (exercices code)
    judge0_language_id      INT,                   -- mapping Judge0 (extensible multi-langages)
    points                  NUMERIC(6,2) NOT NULL DEFAULT 0 CHECK (points >= 0),
    correction_mode         correction_mode NOT NULL DEFAULT 'auto',
    order_index             INT NOT NULL DEFAULT 0,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS unit_tests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exercise_id     UUID NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    input           TEXT,
    expected_output TEXT NOT NULL,
    weight          NUMERIC(6,2) NOT NULL DEFAULT 1 CHECK (weight > 0),
    is_hidden       BOOLEAN NOT NULL DEFAULT FALSE,
    order_index     INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS qcm_questions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exercise_id     UUID NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    text            TEXT NOT NULL,
    answer_type     qcm_answer_type NOT NULL DEFAULT 'single',
    points          NUMERIC(6,2) NOT NULL DEFAULT 0 CHECK (points >= 0),
    explanation     TEXT,                          -- post-MVP
    order_index     INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS qcm_choices (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id     UUID NOT NULL REFERENCES qcm_questions(id) ON DELETE CASCADE,
    text            TEXT NOT NULL,
    is_correct      BOOLEAN NOT NULL DEFAULT FALSE,
    order_index     INT NOT NULL DEFAULT 0
);

-- -----------------------------------------------------------------------------
-- 4.5 Passation & copies
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS exam_participations (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_id                 UUID NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    student_id              UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    status                  participation_status NOT NULL DEFAULT 'connected',
    is_completed            BOOLEAN NOT NULL DEFAULT FALSE,
    connected_at            TIMESTAMPTZ,
    ip_address              INET,
    waiting_room_entered_at TIMESTAMPTZ,
    started_at              TIMESTAMPTZ,
    submitted_at            TIMESTAMPTZ,
    submission_reason       submission_reason,
    auto_score              NUMERIC(6,2),
    manual_score            NUMERIC(6,2),
    final_score             NUMERIC(6,2),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (exam_id, student_id)
);
COMMENT ON COLUMN exam_participations.is_completed IS 'true => reconnexion bloquée (anti double-soumission).';

CREATE TABLE IF NOT EXISTS submissions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participation_id    UUID NOT NULL REFERENCES exam_participations(id) ON DELETE CASCADE,
    exercise_id         UUID NOT NULL REFERENCES exercises(id) ON DELETE RESTRICT,
    source_code         TEXT,
    language            TEXT,
    auto_score          NUMERIC(6,2),
    manual_score        NUMERIC(6,2),
    final_score         NUMERIC(6,2),
    comment             TEXT,
    submitted_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (participation_id, exercise_id)
);

CREATE TABLE IF NOT EXISTS submission_test_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id   UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    unit_test_id    UUID NOT NULL REFERENCES unit_tests(id) ON DELETE RESTRICT,
    passed          BOOLEAN NOT NULL,
    actual_output   TEXT,
    stderr          TEXT,
    status          TEXT,                          -- statut Judge0 (Accepted, TLE…)
    time_ms         INT,
    memory_kb       INT,
    executed_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS qcm_answers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id   UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    question_id     UUID NOT NULL REFERENCES qcm_questions(id) ON DELETE RESTRICT,
    choice_id       UUID NOT NULL REFERENCES qcm_choices(id) ON DELETE RESTRICT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (submission_id, question_id, choice_id)
);

CREATE TABLE IF NOT EXISTS code_autosaves (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participation_id    UUID NOT NULL REFERENCES exam_participations(id) ON DELETE CASCADE,
    exercise_id         UUID NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
    content             TEXT,
    saved_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (participation_id, exercise_id)         -- on conserve le dernier état
);

-- -----------------------------------------------------------------------------
-- 4.6 Sécurité & anti-triche
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS incidents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participation_id    UUID NOT NULL REFERENCES exam_participations(id) ON DELETE CASCADE,
    type                incident_type NOT NULL,
    occurred_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    duration_seconds    INT,
    payload             TEXT,                      -- ex. contenu collé (clipboard)
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS login_attempts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identifier          CITEXT NOT NULL,
    establishment_id    UUID REFERENCES establishments(id) ON DELETE SET NULL,
    ip_address          INET,
    success             BOOLEAN NOT NULL,
    attempted_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS exam_code_attempts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_id         UUID REFERENCES exams(id) ON DELETE SET NULL,
    identifier      CITEXT,
    ip_address      INET,
    success         BOOLEAN NOT NULL,
    attempted_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- 4.7 Exploitation
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_activity_logs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    establishment_id    UUID NOT NULL REFERENCES establishments(id) ON DELETE CASCADE,
    actor_user_id       UUID REFERENCES users(id) ON DELETE SET NULL,
    action              TEXT NOT NULL,             -- ex. 'user.create', 'csv.import'
    entity_type         TEXT,
    entity_id           UUID,
    old_value           JSONB,
    new_value           JSONB,
    ip_address          INET,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS csv_imports (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    establishment_id    UUID NOT NULL REFERENCES establishments(id) ON DELETE CASCADE,
    actor_user_id       UUID REFERENCES users(id) ON DELETE SET NULL,
    filename            TEXT,
    total_rows          INT NOT NULL DEFAULT 0,
    imported_count      INT NOT NULL DEFAULT 0,
    rejected_count      INT NOT NULL DEFAULT 0,
    error_report        JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notifications (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    establishment_id    UUID REFERENCES establishments(id) ON DELETE CASCADE,
    recipient_user_id   UUID REFERENCES users(id) ON DELETE SET NULL,
    recipient_email     CITEXT,
    type                TEXT NOT NULL,             -- ex. 'plan.limit_80'
    channel             TEXT NOT NULL DEFAULT 'email',
    subject             TEXT,
    body                TEXT,
    status              notification_status NOT NULL DEFAULT 'pending',
    sent_at             TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =============================================================================
-- 5. INDEX
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_users_establishment      ON users (establishment_id);
CREATE INDEX IF NOT EXISTS idx_users_role               ON users (role);
CREATE INDEX IF NOT EXISTS idx_users_identifier_lower   ON users (lower(identifier::text));

CREATE INDEX IF NOT EXISTS idx_subs_establishment        ON establishment_subscriptions (establishment_id);
CREATE INDEX IF NOT EXISTS idx_academic_years_estab      ON academic_years (establishment_id);
CREATE INDEX IF NOT EXISTS idx_classes_estab             ON classes (establishment_id);
CREATE INDEX IF NOT EXISTS idx_student_profiles_class    ON student_profiles (class_id);
CREATE INDEX IF NOT EXISTS idx_student_profiles_year     ON student_profiles (academic_year_id);

CREATE INDEX IF NOT EXISTS idx_exams_establishment       ON exams (establishment_id);
CREATE INDEX IF NOT EXISTS idx_exams_teacher             ON exams (teacher_id);
CREATE INDEX IF NOT EXISTS idx_exams_status              ON exams (status);

CREATE INDEX IF NOT EXISTS idx_exercises_exam            ON exercises (exam_id);
CREATE INDEX IF NOT EXISTS idx_unit_tests_exercise       ON unit_tests (exercise_id);
CREATE INDEX IF NOT EXISTS idx_qcm_questions_exercise    ON qcm_questions (exercise_id);
CREATE INDEX IF NOT EXISTS idx_qcm_choices_question      ON qcm_choices (question_id);

CREATE INDEX IF NOT EXISTS idx_participations_exam       ON exam_participations (exam_id);
CREATE INDEX IF NOT EXISTS idx_participations_student    ON exam_participations (student_id);
CREATE INDEX IF NOT EXISTS idx_participations_status     ON exam_participations (status);

CREATE INDEX IF NOT EXISTS idx_submissions_participation ON submissions (participation_id);
CREATE INDEX IF NOT EXISTS idx_submissions_exercise      ON submissions (exercise_id);
CREATE INDEX IF NOT EXISTS idx_test_results_submission   ON submission_test_results (submission_id);
CREATE INDEX IF NOT EXISTS idx_qcm_answers_submission    ON qcm_answers (submission_id);

CREATE INDEX IF NOT EXISTS idx_incidents_participation   ON incidents (participation_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_login_attempts_identifier ON login_attempts (identifier, attempted_at);
CREATE INDEX IF NOT EXISTS idx_login_attempts_ip         ON login_attempts (ip_address, attempted_at);
CREATE INDEX IF NOT EXISTS idx_code_attempts_exam        ON exam_code_attempts (exam_id, identifier, attempted_at);

CREATE INDEX IF NOT EXISTS idx_audit_estab              ON admin_activity_logs (establishment_id, created_at);
CREATE INDEX IF NOT EXISTS idx_notifications_recipient  ON notifications (recipient_user_id, created_at);

-- =============================================================================
-- 6. TRIGGERS updated_at
-- =============================================================================
DO $$
DECLARE
    t TEXT;
    tables TEXT[] := ARRAY[
        'subscription_plans', 'establishments', 'establishment_subscriptions',
        'academic_years', 'classes', 'users', 'exams', 'exercises',
        'qcm_questions', 'exam_participations', 'submissions'
    ];
BEGIN
    FOREACH t IN ARRAY tables LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_set_updated_at ON %I;', t);
        EXECUTE format(
            'CREATE TRIGGER trg_set_updated_at BEFORE UPDATE ON %I
             FOR EACH ROW EXECUTE FUNCTION set_updated_at();', t
        );
    END LOOP;
END $$;

-- =============================================================================
-- 7. SEED — Plans tarifaires (Freemium)
-- =============================================================================
INSERT INTO subscription_plans
    (code, name, max_teachers, max_students, max_exams_per_month, price_min, price_max, currency, features)
VALUES
    ('free', 'Gratuit', 1, 10, 3, 0, 0, 'XOF',
     '{"reports": false, "support": false}'::jsonb),
    ('starter', 'Starter', 5, 100, NULL, 15000, 25000, 'XOF',
     '{"reports": true, "support": false}'::jsonb),
    ('pro', 'Pro', 20, 500, NULL, 50000, 80000, 'XOF',
     '{"reports": true, "support": true, "all_features": true}'::jsonb),
    ('enterprise', 'Enterprise', NULL, NULL, NULL, NULL, NULL, 'XOF',
     '{"reports": true, "support": true, "dedicated_hosting": true, "sla": true, "training": true}'::jsonb)
ON CONFLICT (code) DO NOTHING;

-- =============================================================================
-- Fin du schéma Cylentic
-- =============================================================================
