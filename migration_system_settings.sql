-- migration_system_settings.sql
-- Ensure the system_settings table exists and is structured properly
CREATE TABLE IF NOT EXISTS public.system_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    setting_key TEXT UNIQUE NOT NULL,
    setting_value TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Seed default settings if they do not exist
INSERT INTO public.system_settings (setting_key, setting_value)
VALUES 
    ('active_model', 'MobileNetV2'),
    ('auto_run_ai', 'false'),
    ('verbose_logging', 'false'),
    ('future_flags', '{}')
ON CONFLICT (setting_key) DO NOTHING;
