-- Cylentic - PostgreSQL schema
-- Run with psql from a maintenance database:
--   psql -f db.sql

CREATE DATABASE cylentic
    WITH ENCODING 'UTF8'
    TEMPLATE template0;

\connect cylentic

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;

-- ---------------------------------------------------------------------------
-- Enumerations
-- ---------------------------------------------------------------------------

CREATE TYPE institution_type AS ENUM (
    'public_university',
    'private_university',
    'engineering_school',
    'bts',
    'technical_high_school',
    'other'
);

CREATE TYPE user_role AS ENUM (
    'institution_admin',
    'teacher',
    'student'
);

CREATE TYPE user_status AS ENUM (
    'pending_activation',
    'active',
    'disabled'
);

CREATE TYPE subscription_status AS ENUM (
    'trialing',
    'active',
    'past_due',
    'cancelled',
    'expired'
);

CREATE TYPE exam_status AS ENUM (
    'draft',
    'published',
    'in_progress',
    'completed',
    'archived'
);

CREATE TYPE exam_content_type AS ENUM (
    'coding',
    'quiz',
    'mixed'
);

CREATE TYPE grading_mode AS ENUM (
    'automatic',
    'manual'
);

CREATE TYPE programming_language AS ENUM (
    'python',
    'java',
    'c',
    'cpp'
);

CREATE TYPE participation_status AS ENUM (
    'not_started',
    'waiting_room',
    'in_progress',
    'submitted',
    'auto_submitted',
    'expelled',
    'absent'
);

CREATE TYPE incident_type AS ENUM (
    'fullscreen_exit',
    'tab_switch',
    'clipboard_paste',
    'shortcut_blocked',
    'right_click',
    'network_loss',
    'session_close',
    'manual_report'
);

CREATE TYPE run_status AS ENUM (
    'queued',
    'running',
    'accepted',
    'wrong_answer',
    'runtime_error',
    'time_limit_exceeded',
    'compilation_error',
    'internal_error'
);

CREATE TYPE question_type AS ENUM (
    'single_choice',
    'multiple_choice'
);

CREATE TYPE import_status AS ENUM (
    'pending',
    'processing',
    'completed',
    'completed_with_errors',
    'failed'
);

CREATE TYPE audit_actor_type AS ENUM (
    'system',
    'institution_admin',
    'teacher'
);

CREATE TYPE notification_status AS ENUM (
    'queued',
    'sent',
    'failed'
);

-- ---------------------------------------------------------------------------
-- Shared trigger helpers
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION enforce_max_two_active_admins()
RETURNS TRIGGER AS $$
DECLARE
    active_admin_count INTEGER;
BEGIN
    IF NEW.role = 'institution_admin' AND NEW.status <> 'disabled' THEN
        SELECT COUNT(*)
        INTO active_admin_count
        FROM users
        WHERE institution_id = NEW.institution_id
          AND role = 'institution_admin'
          AND status <> 'disabled'
          AND id <> NEW.id;

        IF active_admin_count >= 2 THEN
            RAISE EXCEPTION 'An institution can have at most two active administrators';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ---------------------------------------------------------------------------
-- Plans, institutions and subscriptions
-- ---------------------------------------------------------------------------

CREATE TABLE plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    monthly_price_cfa INTEGER,
    max_teachers INTEGER,
    max_students INTEGER,
    max_exams_per_month INTEGER,
    has_reports BOOLEAN NOT NULL DEFAULT FALSE,
    has_priority_support BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT plans_code_format_chk CHECK (code ~ '^[a-z][a-z0-9_]*$'),
    CONSTRAINT plans_price_non_negative_chk CHECK (monthly_price_cfa IS NULL OR monthly_price_cfa >= 0),
    CONSTRAINT plans_limits_positive_chk CHECK (
        (max_teachers IS NULL OR max_teachers > 0)
        AND (max_students IS NULL OR max_students > 0)
        AND (max_exams_per_month IS NULL OR max_exams_per_month > 0)
    )
);

CREATE TABLE institutions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    official_name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    short_code TEXT NOT NULL UNIQUE,
    type institution_type NOT NULL,
    country TEXT NOT NULL,
    city TEXT NOT NULL,
    timezone TEXT NOT NULL,
    official_email CITEXT NOT NULL,
    phone_number TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT institutions_slug_format_chk CHECK (slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
    CONSTRAINT institutions_short_code_format_chk CHECK (short_code ~ '^[A-Z0-9]{2,10}$'),
    CONSTRAINT institutions_status_chk CHECK (status IN ('active', 'suspended', 'archived'))
);

CREATE TABLE institution_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
    plan_id UUID NOT NULL REFERENCES plans(id) ON DELETE RESTRICT,
    status subscription_status NOT NULL DEFAULT 'trialing',
    trial_starts_at TIMESTAMPTZ,
    trial_ends_at TIMESTAMPTZ,
    current_period_starts_at TIMESTAMPTZ NOT NULL,
    current_period_ends_at TIMESTAMPTZ NOT NULL,
    payment_provider TEXT,
    provider_customer_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT institution_subscriptions_period_chk CHECK (current_period_ends_at > current_period_starts_at),
    CONSTRAINT institution_subscriptions_trial_chk CHECK (
        trial_starts_at IS NULL
        OR trial_ends_at IS NULL
        OR trial_ends_at > trial_starts_at
    )
);

CREATE UNIQUE INDEX institution_subscriptions_one_current_idx
    ON institution_subscriptions(institution_id)
    WHERE status IN ('trialing', 'active', 'past_due');

-- ---------------------------------------------------------------------------
-- Academic structure and users
-- ---------------------------------------------------------------------------

CREATE TABLE academic_years (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
    label TEXT NOT NULL,
    starts_on DATE NOT NULL,
    ends_on DATE NOT NULL,
    is_current BOOLEAN NOT NULL DEFAULT FALSE,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT academic_years_label_unique UNIQUE (institution_id, label),
    CONSTRAINT academic_years_dates_chk CHECK (ends_on > starts_on)
);

CREATE UNIQUE INDEX academic_years_one_current_per_institution_idx
    ON academic_years(institution_id)
    WHERE is_current;

CREATE TABLE classes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
    academic_year_id UUID NOT NULL REFERENCES academic_years(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    track TEXT NOT NULL,
    level TEXT NOT NULL,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT classes_name_unique UNIQUE (institution_id, academic_year_id, name)
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
    public_identifier TEXT NOT NULL UNIQUE,
    role user_role NOT NULL,
    status user_status NOT NULL DEFAULT 'pending_activation',
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email CITEXT NOT NULL,
    password_hash TEXT NOT NULL,
    must_change_password BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    activated_at TIMESTAMPTZ,
    disabled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT users_email_per_institution_unique UNIQUE (institution_id, email),
    CONSTRAINT users_public_identifier_role_chk CHECK (
        (role = 'student' AND public_identifier ~ '^ETU-[A-Z0-9]{2,10}-[0-9]{4}-[0-9]{4}$')
        OR (role = 'teacher' AND public_identifier ~ '^PROF-[A-Z0-9]{2,10}-[0-9]{4}$')
        OR (role = 'institution_admin' AND public_identifier ~ '^ADM-[A-Z0-9]{2,10}-[0-9]{4}$')
    )
);

CREATE INDEX users_institution_role_status_idx
    ON users(institution_id, role, status);

CREATE TABLE student_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE RESTRICT,
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
    student_number TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT student_profiles_number_unique UNIQUE (institution_id, student_number)
);

CREATE TABLE teacher_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE RESTRICT,
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
    position_title TEXT,
    subjects TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE class_enrollments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
    student_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    class_id UUID NOT NULL REFERENCES classes(id) ON DELETE RESTRICT,
    academic_year_id UUID NOT NULL REFERENCES academic_years(id) ON DELETE RESTRICT,
    enrolled_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    left_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT class_enrollments_dates_chk CHECK (left_at IS NULL OR left_at > enrolled_at),
    CONSTRAINT class_enrollments_unique_active_year UNIQUE (student_user_id, academic_year_id)
);

CREATE INDEX class_enrollments_class_idx
    ON class_enrollments(class_id, academic_year_id);

-- ---------------------------------------------------------------------------
-- Exams and content
-- ---------------------------------------------------------------------------

CREATE TABLE exams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
    teacher_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    title TEXT NOT NULL,
    description TEXT,
    status exam_status NOT NULL DEFAULT 'draft',
    content_type exam_content_type NOT NULL DEFAULT 'coding',
    default_grading_mode grading_mode NOT NULL DEFAULT 'automatic',
    starts_at TIMESTAMPTZ NOT NULL,
    duration_minutes INTEGER NOT NULL,
    access_window_minutes INTEGER NOT NULL DEFAULT 15,
    access_code TEXT UNIQUE,
    published_at TIMESTAMPTZ,
    locked_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT exams_duration_positive_chk CHECK (duration_minutes > 0),
    CONSTRAINT exams_access_window_non_negative_chk CHECK (access_window_minutes >= 0),
    CONSTRAINT exams_access_code_format_chk CHECK (
        access_code IS NULL
        OR access_code ~ '^[A-HJ-KM-NP-Z2-9]{4}-[A-HJ-KM-NP-Z2-9]{4}$'
    ),
    CONSTRAINT exams_publication_chk CHECK (
        (status = 'draft' AND access_code IS NULL)
        OR (status <> 'draft' AND access_code IS NOT NULL)
    )
);

CREATE INDEX exams_teacher_status_idx
    ON exams(teacher_user_id, status, starts_at DESC);

CREATE INDEX exams_institution_status_idx
    ON exams(institution_id, status, starts_at DESC);

CREATE TABLE exam_allowed_classes (
    exam_id UUID NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    class_id UUID NOT NULL REFERENCES classes(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (exam_id, class_id)
);

CREATE TABLE exam_security_settings (
    exam_id UUID PRIMARY KEY REFERENCES exams(id) ON DELETE CASCADE,
    force_fullscreen BOOLEAN NOT NULL DEFAULT TRUE,
    block_external_clipboard BOOLEAN NOT NULL DEFAULT TRUE,
    block_browser_shortcuts BOOLEAN NOT NULL DEFAULT TRUE,
    max_incidents_before_expulsion INTEGER NOT NULL DEFAULT 2,
    autosave_interval_seconds INTEGER NOT NULL DEFAULT 30,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT exam_security_incidents_positive_chk CHECK (max_incidents_before_expulsion > 0),
    CONSTRAINT exam_security_autosave_positive_chk CHECK (autosave_interval_seconds BETWEEN 5 AND 300)
);

CREATE TABLE coding_exercises (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_id UUID NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
    position INTEGER NOT NULL,
    title TEXT NOT NULL,
    statement_md TEXT NOT NULL,
    language programming_language NOT NULL DEFAULT 'python',
    points NUMERIC(7,2) NOT NULL,
    grading_mode grading_mode NOT NULL DEFAULT 'automatic',
    starter_code TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT coding_exercises_position_positive_chk CHECK (position > 0),
    CONSTRAINT coding_exercises_points_positive_chk CHECK (points > 0),
    CONSTRAINT coding_exercises_position_unique UNIQUE (exam_id, position)
);

CREATE INDEX coding_exercises_exam_idx
    ON coding_exercises(exam_id, position);

CREATE TABLE coding_test_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exercise_id UUID NOT NULL REFERENCES coding_exercises(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    input_payload TEXT NOT NULL,
    expected_output TEXT NOT NULL,
    is_hidden BOOLEAN NOT NULL DEFAULT FALSE,
    weight NUMERIC(7,2) NOT NULL DEFAULT 1,
    timeout_ms INTEGER NOT NULL DEFAULT 2000,
    memory_kb INTEGER NOT NULL DEFAULT 128000,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT coding_test_cases_position_positive_chk CHECK (position > 0),
    CONSTRAINT coding_test_cases_weight_positive_chk CHECK (weight > 0),
    CONSTRAINT coding_test_cases_timeout_positive_chk CHECK (timeout_ms BETWEEN 100 AND 30000),
    CONSTRAINT coding_test_cases_memory_positive_chk CHECK (memory_kb BETWEEN 16000 AND 1048576),
    CONSTRAINT coding_test_cases_position_unique UNIQUE (exercise_id, position)
);

CREATE TABLE quiz_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_id UUID NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
    position INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    question_type question_type NOT NULL DEFAULT 'single_choice',
    points NUMERIC(7,2) NOT NULL DEFAULT 1,
    explanation_md TEXT,
    shuffle_choices BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT quiz_questions_position_positive_chk CHECK (position > 0),
    CONSTRAINT quiz_questions_points_positive_chk CHECK (points > 0),
    CONSTRAINT quiz_questions_position_unique UNIQUE (exam_id, position)
);

CREATE TABLE quiz_choices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES quiz_questions(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    choice_text TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT quiz_choices_position_positive_chk CHECK (position > 0),
    CONSTRAINT quiz_choices_position_unique UNIQUE (question_id, position),
    CONSTRAINT quiz_choices_id_question_unique UNIQUE (id, question_id)
);

-- ---------------------------------------------------------------------------
-- Exam participation, code execution and grading
-- ---------------------------------------------------------------------------

CREATE TABLE exam_participations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
    exam_id UUID NOT NULL REFERENCES exams(id) ON DELETE RESTRICT,
    student_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    status participation_status NOT NULL DEFAULT 'not_started',
    is_completed BOOLEAN NOT NULL DEFAULT FALSE,
    first_login_at TIMESTAMPTZ,
    waiting_room_entered_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    submitted_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    login_ip INET,
    user_agent TEXT,
    final_score NUMERIC(7,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT exam_participations_unique_student UNIQUE (exam_id, student_user_id),
    CONSTRAINT exam_participations_score_non_negative_chk CHECK (final_score IS NULL OR final_score >= 0),
    CONSTRAINT exam_participations_completed_status_chk CHECK (
        is_completed = FALSE
        OR status IN ('submitted', 'auto_submitted', 'expelled')
    )
);

CREATE INDEX exam_participations_exam_status_idx
    ON exam_participations(exam_id, status);

CREATE INDEX exam_participations_student_idx
    ON exam_participations(student_user_id, created_at DESC);

CREATE TABLE exercise_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participation_id UUID NOT NULL REFERENCES exam_participations(id) ON DELETE CASCADE,
    exercise_id UUID NOT NULL REFERENCES coding_exercises(id) ON DELETE RESTRICT,
    source_code TEXT NOT NULL,
    submitted_at TIMESTAMPTZ,
    run_status run_status NOT NULL DEFAULT 'queued',
    automatic_score NUMERIC(7,2),
    manual_score NUMERIC(7,2),
    teacher_comment TEXT,
    graded_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    graded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT exercise_submissions_unique_exercise UNIQUE (participation_id, exercise_id),
    CONSTRAINT exercise_submissions_scores_non_negative_chk CHECK (
        (automatic_score IS NULL OR automatic_score >= 0)
        AND (manual_score IS NULL OR manual_score >= 0)
    )
);

CREATE INDEX exercise_submissions_participation_idx
    ON exercise_submissions(participation_id);

CREATE TABLE test_case_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exercise_submission_id UUID NOT NULL REFERENCES exercise_submissions(id) ON DELETE CASCADE,
    test_case_id UUID NOT NULL REFERENCES coding_test_cases(id) ON DELETE RESTRICT,
    run_status run_status NOT NULL,
    actual_output TEXT,
    stderr_output TEXT,
    execution_time_ms INTEGER,
    memory_kb INTEGER,
    passed BOOLEAN NOT NULL DEFAULT FALSE,
    judge0_token TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT test_case_results_unique_case UNIQUE (exercise_submission_id, test_case_id),
    CONSTRAINT test_case_results_metrics_non_negative_chk CHECK (
        (execution_time_ms IS NULL OR execution_time_ms >= 0)
        AND (memory_kb IS NULL OR memory_kb >= 0)
    )
);

CREATE TABLE code_run_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participation_id UUID NOT NULL REFERENCES exam_participations(id) ON DELETE CASCADE,
    exercise_id UUID NOT NULL REFERENCES coding_exercises(id) ON DELETE RESTRICT,
    source_code TEXT NOT NULL,
    run_status run_status NOT NULL DEFAULT 'queued',
    stdout_output TEXT,
    stderr_output TEXT,
    execution_time_ms INTEGER,
    memory_kb INTEGER,
    judge0_token TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT code_run_requests_metrics_non_negative_chk CHECK (
        (execution_time_ms IS NULL OR execution_time_ms >= 0)
        AND (memory_kb IS NULL OR memory_kb >= 0)
    )
);

CREATE INDEX code_run_requests_participation_idx
    ON code_run_requests(participation_id, created_at DESC);

CREATE TABLE autosaves (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participation_id UUID NOT NULL REFERENCES exam_participations(id) ON DELETE CASCADE,
    exercise_id UUID NOT NULL REFERENCES coding_exercises(id) ON DELETE RESTRICT,
    source_code TEXT NOT NULL,
    client_saved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX autosaves_latest_idx
    ON autosaves(participation_id, exercise_id, created_at DESC);

CREATE TABLE quiz_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participation_id UUID NOT NULL REFERENCES exam_participations(id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES quiz_questions(id) ON DELETE RESTRICT,
    choice_id UUID NOT NULL REFERENCES quiz_choices(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT quiz_answers_choice_question_fk FOREIGN KEY (choice_id, question_id)
        REFERENCES quiz_choices(id, question_id) ON DELETE RESTRICT,
    CONSTRAINT quiz_answers_unique_choice UNIQUE (participation_id, question_id, choice_id)
);

CREATE INDEX quiz_answers_participation_idx
    ON quiz_answers(participation_id);

-- ---------------------------------------------------------------------------
-- Security, access attempts, imports, audit and notifications
-- ---------------------------------------------------------------------------

CREATE TABLE security_incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participation_id UUID NOT NULL REFERENCES exam_participations(id) ON DELETE CASCADE,
    incident_type incident_type NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    duration_ms INTEGER,
    payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT security_incidents_duration_non_negative_chk CHECK (duration_ms IS NULL OR duration_ms >= 0)
);

CREATE INDEX security_incidents_participation_idx
    ON security_incidents(participation_id, occurred_at);

CREATE INDEX security_incidents_type_idx
    ON security_incidents(incident_type, received_at DESC);

CREATE TABLE exam_access_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID REFERENCES institutions(id) ON DELETE SET NULL,
    public_identifier TEXT NOT NULL,
    access_code TEXT NOT NULL,
    success BOOLEAN NOT NULL DEFAULT FALSE,
    failure_reason TEXT,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX exam_access_attempts_identifier_idx
    ON exam_access_attempts(public_identifier, created_at DESC);

CREATE INDEX exam_access_attempts_ip_idx
    ON exam_access_attempts(ip_address, created_at DESC);

CREATE TABLE import_batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
    uploaded_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    import_type TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    status import_status NOT NULL DEFAULT 'pending',
    total_rows INTEGER NOT NULL DEFAULT 0,
    successful_rows INTEGER NOT NULL DEFAULT 0,
    failed_rows INTEGER NOT NULL DEFAULT 0,
    storage_key TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT import_batches_type_chk CHECK (import_type IN ('students', 'teachers')),
    CONSTRAINT import_batches_counts_non_negative_chk CHECK (
        total_rows >= 0 AND successful_rows >= 0 AND failed_rows >= 0
    )
);

CREATE TABLE import_batch_errors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    import_batch_id UUID NOT NULL REFERENCES import_batches(id) ON DELETE CASCADE,
    row_number INTEGER NOT NULL,
    field_name TEXT,
    error_message TEXT NOT NULL,
    raw_row JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT import_batch_errors_row_positive_chk CHECK (row_number > 0)
);

CREATE INDEX import_batch_errors_batch_idx
    ON import_batch_errors(import_batch_id, row_number);

CREATE TABLE admin_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
    actor_type audit_actor_type NOT NULL,
    actor_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id UUID,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    ip_address INET,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX admin_audit_logs_institution_idx
    ON admin_audit_logs(institution_id, created_at DESC);

CREATE INDEX admin_audit_logs_entity_idx
    ON admin_audit_logs(entity_type, entity_id);

CREATE TABLE notification_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID REFERENCES institutions(id) ON DELETE SET NULL,
    recipient_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    recipient_email CITEXT NOT NULL,
    notification_type TEXT NOT NULL,
    subject TEXT NOT NULL,
    status notification_status NOT NULL DEFAULT 'queued',
    provider_message_id TEXT,
    error_message TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX notification_logs_recipient_idx
    ON notification_logs(recipient_email, created_at DESC);

CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    user_agent TEXT,
    ip_address INET,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT refresh_tokens_expiry_chk CHECK (expires_at > created_at)
);

CREATE INDEX refresh_tokens_user_idx
    ON refresh_tokens(user_id, expires_at DESC);

CREATE TABLE password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT password_reset_tokens_expiry_chk CHECK (expires_at > created_at)
);

CREATE INDEX password_reset_tokens_user_idx
    ON password_reset_tokens(user_id, created_at DESC);

-- ---------------------------------------------------------------------------
-- Triggers
-- ---------------------------------------------------------------------------

CREATE TRIGGER plans_set_updated_at
    BEFORE UPDATE ON plans
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER institutions_set_updated_at
    BEFORE UPDATE ON institutions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER institution_subscriptions_set_updated_at
    BEFORE UPDATE ON institution_subscriptions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER academic_years_set_updated_at
    BEFORE UPDATE ON academic_years
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER classes_set_updated_at
    BEFORE UPDATE ON classes
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER users_set_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER users_enforce_max_two_active_admins
    BEFORE INSERT OR UPDATE OF role, status, institution_id ON users
    FOR EACH ROW EXECUTE FUNCTION enforce_max_two_active_admins();

CREATE TRIGGER student_profiles_set_updated_at
    BEFORE UPDATE ON student_profiles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER teacher_profiles_set_updated_at
    BEFORE UPDATE ON teacher_profiles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER class_enrollments_set_updated_at
    BEFORE UPDATE ON class_enrollments
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER exams_set_updated_at
    BEFORE UPDATE ON exams
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER exam_security_settings_set_updated_at
    BEFORE UPDATE ON exam_security_settings
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER coding_exercises_set_updated_at
    BEFORE UPDATE ON coding_exercises
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER coding_test_cases_set_updated_at
    BEFORE UPDATE ON coding_test_cases
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER quiz_questions_set_updated_at
    BEFORE UPDATE ON quiz_questions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER quiz_choices_set_updated_at
    BEFORE UPDATE ON quiz_choices
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER exam_participations_set_updated_at
    BEFORE UPDATE ON exam_participations
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER exercise_submissions_set_updated_at
    BEFORE UPDATE ON exercise_submissions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER code_run_requests_set_updated_at
    BEFORE UPDATE ON code_run_requests
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER import_batches_set_updated_at
    BEFORE UPDATE ON import_batches
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER notification_logs_set_updated_at
    BEFORE UPDATE ON notification_logs
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------------
-- Seed data
-- ---------------------------------------------------------------------------

INSERT INTO plans (
    code,
    name,
    monthly_price_cfa,
    max_teachers,
    max_students,
    max_exams_per_month,
    has_reports,
    has_priority_support
) VALUES
    ('free', 'Gratuit', 0, 1, 10, 3, FALSE, FALSE),
    ('starter', 'Starter', 20000, 5, 100, NULL, TRUE, FALSE),
    ('pro', 'Pro', 65000, 20, 500, NULL, TRUE, TRUE),
    ('enterprise', 'Enterprise', NULL, NULL, NULL, NULL, TRUE, TRUE);

-- ---------------------------------------------------------------------------
-- Useful comments for schema introspection
-- ---------------------------------------------------------------------------

COMMENT ON TABLE institutions IS 'Tenant root: one school or institution using Cylentic.';
COMMENT ON TABLE users IS 'All user accounts. The role is also encoded in public_identifier.';
COMMENT ON TABLE exams IS 'Exam container created by teachers and published with a unique access code.';
COMMENT ON TABLE exam_participations IS 'One student participation per exam; is_completed blocks reconnection/submission.';
COMMENT ON TABLE security_incidents IS 'Chronological browser and supervision incidents recorded during an exam.';
COMMENT ON TABLE exercise_submissions IS 'Final submitted source code and grading data for one coding exercise.';
COMMENT ON TABLE coding_test_cases IS 'Teacher-defined unit tests executed through Judge0.';
