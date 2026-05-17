{#- Override: Spark SQL has no information_schema.tables. Uses SHOW SCHEMAS
    and SHOW TABLES to discover relations, then returns literal SQL rows.
    Fabric Lakehouse does not support SHOW SCHEMAS LIKE, so schema filtering
    is done in Jinja via regex. SHOW TABLES LIKE uses glob patterns (* not %). -#}
{% macro fabricspark__get_tables_by_pattern_sql(schema_pattern, table_pattern, exclude='', database=target.database) %}

    {%- if not execute -%}
        select
            cast(null as string) as table_schema,
            cast(null as string) as table_name,
            cast(null as string) as table_type
        where 1 = 0
        {{ return('') }}
    {%- endif -%}

    {%- set spark_table_pattern = table_pattern | replace('%', '*') -%}

    {#- Convert SQL LIKE pattern to regex: escape regex chars, then replace
        SQL wildcards (% → .*, _ → .) -#}
    {%- set schema_regex = modules.re.escape(schema_pattern) | replace('%', '.*') | replace('_', '.') -%}

    {%- set schema_results = run_query("show schemas") -%}
    {%- set matching_schemas = [] -%}
    {%- for row in schema_results -%}
        {#- Fabric Lakehouse returns dotted namespaces (e.g. adapter.lh.schema);
            extract just the last segment -#}
        {%- set schema_name = row[0].split('.')[-1] -%}
        {%- if modules.re.match('^' ~ schema_regex ~ '$', schema_name, modules.re.IGNORECASE) -%}
            {%- do matching_schemas.append(schema_name) -%}
        {%- endif -%}
    {%- endfor -%}

    {%- set all_tables = [] -%}
    {%- for schema_name in matching_schemas -%}
        {%- set table_results = run_query(
            "show tables in `" ~ database ~ "`.`" ~ schema_name ~ "` like '" ~ spark_table_pattern ~ "'"
        ) -%}
        {%- for row in table_results -%}
            {%- do all_tables.append({'schema': schema_name, 'name': row[1]}) -%}
        {%- endfor -%}
    {%- endfor -%}

    {%- if all_tables | length > 0 -%}
        select distinct table_schema, table_name, table_type from (
            {%- for tbl in all_tables %}
            select
                '{{ tbl.schema }}' as table_schema,
                '{{ tbl.name }}' as table_name,
                'table' as table_type
            {%- if not loop.last %} union all{% endif -%}
            {%- endfor %}
        )
        {%- if exclude %}
        where table_name not like '{{ exclude }}'
        {%- endif -%}
    {%- else -%}
        select
            cast(null as string) as table_schema,
            cast(null as string) as table_name,
            cast(null as string) as table_type
        where 1 = 0
    {%- endif -%}

{% endmacro %}
