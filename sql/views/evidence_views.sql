CREATE VIEW IF NOT EXISTS current_hypothesis_decision AS
WITH ranked AS (
    SELECT
        d.*,
        ROW_NUMBER() OVER (
            PARTITION BY d.hypothesis_id
            ORDER BY d.event_at DESC, d.decision_id DESC
        ) AS row_num
    FROM hypothesis_decision_event d
)
SELECT * FROM ranked WHERE row_num = 1;

CREATE VIEW IF NOT EXISTS hypothesis_evidence_summary AS
SELECT
    h.hypothesis_id,
    h.slug,
    hv.version,
    hv.title,
    cd.lifecycle,
    cd.verdict,
    COUNT(hel.evidence_id) AS evidence_count,
    SUM(CASE WHEN hel.direction = 'SUPPORTS' THEN 1 ELSE 0 END) AS supports_count,
    SUM(CASE WHEN hel.direction = 'CONTRADICTS' THEN 1 ELSE 0 END) AS contradicts_count,
    SUM(CASE WHEN hel.direction = 'QUALIFIES' THEN 1 ELSE 0 END) AS qualifies_count
FROM hypothesis h
JOIN hypothesis_version hv ON hv.hypothesis_id = h.hypothesis_id
LEFT JOIN current_hypothesis_decision cd ON cd.hypothesis_id = h.hypothesis_id
LEFT JOIN hypothesis_evidence_link hel
    ON hel.hypothesis_id = hv.hypothesis_id AND hel.hypothesis_version = hv.version
GROUP BY h.hypothesis_id, h.slug, hv.version, hv.title, cd.lifecycle, cd.verdict;
