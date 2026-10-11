-- Optional profile photo for the header. The value is a same-origin static path under
-- /avatars/ (served by the web image); never a URL, so it cannot point off-site.
-- Only the owner role sets it, through the account CLI: p50k_app keeps column-level
-- INSERT/UPDATE grants that do not include this column.
ALTER TABLE auth.users ADD COLUMN avatar_path TEXT
    CHECK (avatar_path IS NULL OR avatar_path ~ '^/avatars/[a-z0-9][a-z0-9-]{0,39}\.(jpg|png|webp)$');
