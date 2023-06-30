SELECT 
    u.user_id, 
    u.user_group, 
    u.created_at,
    COALESCE(usage.n_messages, 0) as n_messages,
    COALESCE(usage.n_chatbots, 0) as n_chatbots,
    COALESCE(usage.n_sources, 0) as n_sources, 
    COALESCE(usage.n_tokens, 0) as n_tokens
FROM users u 
LEFT JOIN usage ON u.user_id = usage.user_id
WHERE u.user_id = ?