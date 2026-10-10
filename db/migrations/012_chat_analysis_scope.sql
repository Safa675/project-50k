-- Existing chat was created against the live view. Keep that context explicit.
-- Adding a constant column preserves the original immutable thread/message rows.
ALTER TABLE ai.chat_threads ADD COLUMN analysis_scope_key TEXT NOT NULL DEFAULT 'live'
    CHECK (analysis_scope_key ~ '^(live|asof:[0-9]{4}-[0-9]{2}-[0-9]{2})$');
CREATE INDEX chat_thread_owner_scope_idx
    ON ai.chat_threads(user_id,fund_code,analysis_scope_key,created_at DESC,thread_id);
CREATE INDEX chat_message_thread_order_idx ON ai.chat_messages(thread_id,message_id DESC);
