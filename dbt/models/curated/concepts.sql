-- Every concept a fact report uses, every taxonomy included.
-- Each report repeats the concept's label and description,
-- so the latest filed report gives them, the same way a fact is picked
select distinct on (taxonomy, concept)
    taxonomy,
    concept,
    label,
    description
from {{ ref('stg_edgar__fact_reports') }}
order by
    taxonomy,
    concept,
    filed desc,
    accession_number desc,
    cik
