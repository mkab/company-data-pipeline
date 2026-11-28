{#
    Lets the api role reach the curated tables, whose `grants` config gives it SELECT.
    Skipped when curated does not exist yet, as after a build of staging only
#}
{% macro grant_curated_schema_usage() %}
    {% if execute and adapter.check_schema_exists(target.database, 'curated') %}
        grant usage on schema curated to api
    {% endif %}
{% endmacro %}
