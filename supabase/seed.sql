-- Deliberately anonymous development seed.
-- No users, email addresses, UUIDs, password hashes, names, academic scores,
-- or values copied from a hosted project belong in this file.

insert into public.system_settings (setting_key, setting_value)
values
  ('active_model', 'MobileNetV2'),
  ('auto_run_ai', 'false'),
  ('verbose_logging', 'false'),
  ('future_flags', '{}')
on conflict (setting_key) do update
set setting_value = excluded.setting_value;
