-- Idempotent schema. All timestamps are UTC timestamptz (see specs/.../data-model.md).

CREATE TABLE IF NOT EXISTS users (
    chat_id    bigint PRIMARY KEY,
    timezone   text,
    created_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS plants (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chat_id         bigint NOT NULL REFERENCES users (chat_id) ON DELETE CASCADE,
    name            text NOT NULL,
    plant_type      text NOT NULL,
    summer_days     integer NOT NULL,
    winter_days     integer NOT NULL,
    last_watered_on date NOT NULL,
    created_at      timestamptz NOT NULL,
    CONSTRAINT plants_name_len CHECK (char_length(btrim(name)) BETWEEN 1 AND 40),
    CONSTRAINT plants_type_len CHECK (char_length(btrim(plant_type)) BETWEEN 1 AND 60),
    CONSTRAINT plants_summer_range CHECK (summer_days BETWEEN 1 AND 365),
    CONSTRAINT plants_winter_range CHECK (winter_days BETWEEN 1 AND 365)
);

CREATE UNIQUE INDEX IF NOT EXISTS plants_chat_name_unique ON plants (chat_id, lower(name));

CREATE TABLE IF NOT EXISTS reminders (
    plant_id     bigint PRIMARY KEY REFERENCES plants (id) ON DELETE CASCADE,
    due_on       date NOT NULL,
    next_send_at timestamptz NOT NULL,
    last_sent_at timestamptz,
    send_count   integer NOT NULL DEFAULT 0,
    message_id   bigint
);

CREATE INDEX IF NOT EXISTS reminders_next_send_at ON reminders (next_send_at);
