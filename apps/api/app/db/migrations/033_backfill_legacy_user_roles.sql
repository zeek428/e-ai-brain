WITH legacy_roles AS (
  SELECT
    u.id AS user_id,
    role_values.role_code
  FROM users u
  CROSS JOIN LATERAL jsonb_array_elements_text(
    CASE
      WHEN jsonb_typeof(to_jsonb(u.roles)::jsonb) = 'array' THEN to_jsonb(u.roles)::jsonb
      ELSE '[]'::jsonb
    END
  ) AS role_values(role_code)
)
INSERT INTO user_roles (
  user_id,
  role_id,
  grant_reason,
  effective_from,
  status
)
SELECT
  legacy_roles.user_id,
  r.id,
  'compatibility backfill from users.roles',
  now(),
  'active'
FROM legacy_roles
JOIN roles r ON r.code = legacy_roles.role_code
ON CONFLICT (user_id, role_id, status) DO UPDATE SET
  grant_reason = EXCLUDED.grant_reason,
  updated_at = now();
