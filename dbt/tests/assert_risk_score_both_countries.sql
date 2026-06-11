-- Vérifie que SEN et CIV ont chacun un score pour au moins 3 des 6 derniers mois.
-- Retourne des lignes (= échec du test) si un pays manque de données récentes.
-- Convention dbt : 0 ligne = test OK, 1+ lignes = test FAIL.
SELECT
    country_code,
    COUNT(*) AS months_with_score
FROM {{ ref('mart__risk__score_monthly') }}
WHERE period >= CURRENT_DATE - INTERVAL '6 months'
GROUP BY country_code
HAVING COUNT(*) < 3
