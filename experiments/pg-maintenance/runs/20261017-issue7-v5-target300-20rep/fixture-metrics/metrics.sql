SELECT 'ROWS|weakassoc|' || count(*)::text FROM ess_mcv_weakassoc;
SELECT 'PAIR|weakassoc|ab|' || a::text || '|' || b::text || '|' || count(*)::text FROM ess_mcv_weakassoc GROUP BY a, b ORDER BY a, b;
SELECT 'PAIR|weakassoc|bc|' || b::text || '|' || c::text || '|' || count(*)::text FROM ess_mcv_weakassoc GROUP BY b, c ORDER BY b, c;
SELECT 'PAIR|weakassoc|cd|' || c::text || '|' || d::text || '|' || count(*)::text FROM ess_mcv_weakassoc GROUP BY c, d ORDER BY c, d;
SELECT 'ROWS|correlated|' || count(*)::text FROM ess_mcv_correlated;
SELECT 'PAIR|correlated|ab|' || a::text || '|' || b::text || '|' || count(*)::text FROM ess_mcv_correlated GROUP BY a, b ORDER BY a, b;
SELECT 'PAIR|correlated|bc|' || b::text || '|' || c::text || '|' || count(*)::text FROM ess_mcv_correlated GROUP BY b, c ORDER BY b, c;
SELECT 'PAIR|correlated|cd|' || c::text || '|' || d::text || '|' || count(*)::text FROM ess_mcv_correlated GROUP BY c, d ORDER BY c, d;
