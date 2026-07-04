insert into public.system_settings (setting_key, setting_value)
values
  ('active_model', 'MobileNetV2'),
  ('auto_run_ai', 'false'),
  ('verbose_logging', 'false'),
  ('future_flags', '{}')
on conflict (setting_key) do nothing;
