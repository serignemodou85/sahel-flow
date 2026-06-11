-- Vérifie que risk_score est toujours entre 0 et 100.
-- LEAST/GREATEST dans le mart devrait garantir ça — ce test le confirme en DB.
-- Retourne les lignes hors bornes (= échec du test).
SELECT *
FROM {{ ref('mart__risk__score_monthly') }}
WHERE risk_score < 0 OR risk_score > 100
