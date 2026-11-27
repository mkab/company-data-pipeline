{#
    A model's `schema` config is its schema name exactly.
    dbt's default prefixes it with the target schema (`staging_curated`),
    while the API and the grants expect `staging` and `curated`
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
