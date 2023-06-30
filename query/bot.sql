SELECT 
    b.bot_id as id, 
    b.name, 
    b.model_id, 
    b.description, 
    b.system_message, 
    b.temperature,
    b.source_id,
    b.created_at,
    b.metadata,
    b.visibility,
    d.name as source_name,
    d.dtype as source_type,
    d.n_tokens as source_n_tokens,
    d.created_at as source_created_at,
    CASE WHEN b.user_id = ? THEN TRUE ELSE FALSE END AS is_owner
FROM bots b
JOIN data_sources d ON d.source_id = b.source_id
WHERE ((CASE WHEN b.user_id = ? THEN 1 ELSE 0 END) = 1
    OR (b.visibility = 'public'))
    AND b.bot_id = ?
    AND CASE WHEN b.user_id = ? THEN 1 ELSE 0 END >= ?
ORDER BY b.created_at DESC