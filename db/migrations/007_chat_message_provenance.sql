-- Bind each new message to its immutable evidence turn and enforce its owner.
ALTER TABLE ai.chat_threads ADD CONSTRAINT chat_thread_owner UNIQUE(thread_id,user_id);
ALTER TABLE ai.chat_turns ADD CONSTRAINT chat_turn_owner
    FOREIGN KEY(thread_id,user_id) REFERENCES ai.chat_threads(thread_id,user_id);
ALTER TABLE ai.chat_turns ADD CONSTRAINT chat_turn_thread UNIQUE(turn_id,thread_id);
ALTER TABLE ai.chat_messages ADD COLUMN turn_id UUID;
ALTER TABLE ai.chat_messages ADD CONSTRAINT chat_message_turn
    FOREIGN KEY(turn_id,thread_id) REFERENCES ai.chat_turns(turn_id,thread_id);
CREATE INDEX chat_message_turn_idx ON ai.chat_messages(turn_id);
