SELECT 
    source_id, 
    status, 
    n_tokens, 
    name 
FROM data_sources 
WHERE source_id = ? 
AND user_id = ?