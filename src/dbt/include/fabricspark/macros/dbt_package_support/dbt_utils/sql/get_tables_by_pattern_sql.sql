{#- Override: dbt-utils default__get_tables_by_pattern_sql (get_tables_by_pattern_sql.sql)
    queries information_schema.tables which doesn't exist in Spark SQL.
    No spark__ or databricks__ version exists upstream.
    This implementation uses SHOW SCHEMAS + SHOW TABLES to discover relations,
    then returns literal SQL rows via UNION ALL.
    Fabric Lakehouse-specific: SHOW SCHEMAS LIKE is not supported (returns 0 rows),
    so schema filtering is done in Jinja via regex. SHOW SCHEMAS returns dotted
    namespaces (e.g. adapter.lh.schema_name), so only the last segment is used.
    SHOW TABLES LIKE uses glob patterns (* not SQL %). -#}
{% macro fabricspark__get_tables_by_pattern_sql(schema_pattern, table_pattern, exclude='', database=target.database) %}

    {%- if not execute -%}
        select
            cast(null as string) as table_schema,
            cast(null as string) as table_name,
            cast(null as string) as table_type
        where 1 = 0
        {{ return('') }}
    {%- endif -%}

    {#- SHOW TABLES LIKE uses glob (* not SQL %) -#}
    {%- set spark_table_pattern = table_pattern | replace('%', '*') -%}

    {#- Convert SQL LIKE pattern to regex for Jinja-side schema filtering
        (replaces information_schema WHERE clause from upstream) -#}
    {%- set schema_regex = modules.re.escape(schema_pattern) | replace('%', '.*') | replace('_', '.') -%}

    {#- SHOW SCHEMAS instead of information_schema.schemata -#}
    {%- set schema_results = run_query("show schemas") -%}
    {%- set matching_schemas = [] -%}
    {%- for row in schema_results -%}
        {#- Fabric Lakehouse returns dotted namespaces (e.g. adapter.lh.schema) -#}
        {%- set schema_name = row[0].split('.')[-1] -%}
        {%- if modules.re.match('^' ~ schema_regex ~ '$', schema_name, modules.re.IGNORECASE) -%}
            {%- do matching_schemas.append(schema_name) -%}
        {%- endif -%}
    {%- endfor -%}

    {#- SHOW TABLES instead of information_schema.tables -#}
    {%- set all_tables = [] -%}
    {%- for schema_name in matching_schemas -%}
        {%- set table_results = run_query(
            "show tables in `" ~ database ~ "`.`" ~ schema_name ~ "` like '" ~ spark_table_pattern ~ "'"
        ) -%}
        {%- for row in table_results -%}
            {%- do all_tables.append({'schema': schema_name, 'name': row[1]}) -%}
        {%- endfor -%}
    {%- endfor -%}

    {#- Build result set as literal SQL rows instead of querying a catalog view -#}
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
