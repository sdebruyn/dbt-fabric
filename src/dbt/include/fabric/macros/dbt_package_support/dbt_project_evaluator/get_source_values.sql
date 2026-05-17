{#- T-SQL has no native boolean; cast to BIT (1/0) instead of TRUE/FALSE literals. #}
{%- macro fabric__get_source_values() -%}

    {%- if execute -%}
    {%- set nodes_list = graph.sources.values() -%}
    {%- set values = [] -%}

    {%- for node in nodes_list -%}

        {%- set exclude_source = dbt_project_evaluator.set_is_excluded(node, resource_type="source") -%}

         {%- set values_line =
            [
              wrap_string_with_quotes(node.unique_id),
              wrap_string_with_quotes(node.name),
              wrap_string_with_quotes(node.original_file_path | replace("\\","\\\\")),
              wrap_string_with_quotes(node.alias),
              wrap_string_with_quotes(node.resource_type),
              wrap_string_with_quotes(node.source_name),
              "cast(" ~ dbt_project_evaluator.is_not_empty_string(node.source_description) | trim ~ " as " ~ dbt.type_boolean() ~ ")",
              "cast(" ~ dbt_project_evaluator.is_not_empty_string(node.description) | trim ~ " as " ~ dbt.type_boolean() ~ ")",
              "cast(" ~ (1 if node.config.enabled else 0) ~ " as " ~ dbt.type_boolean() ~ ")",
              wrap_string_with_quotes(node.loaded_at_field | replace("'", "_")),

              "cast(" ~ (1 if (
                ((node.config.freshness != None) and (dbt_project_evaluator.is_not_empty_string(node.config.freshness.warn_after.count)
                  or dbt_project_evaluator.is_not_empty_string(node.config.freshness.error_after.count)))
                or ((node.freshness != None) and (dbt_project_evaluator.is_not_empty_string(node.freshness.warn_after.count)
                  or dbt_project_evaluator.is_not_empty_string(node.freshness.error_after.count)))
                ) else 0) ~ " as " ~ dbt.type_boolean() ~ ")",

              wrap_string_with_quotes(node.database),
              wrap_string_with_quotes(node.schema),
              wrap_string_with_quotes(node.package_name),
              wrap_string_with_quotes(node.loader),
              wrap_string_with_quotes(node.identifier),
              wrap_string_with_quotes(node.meta | tojson),
              "cast(" ~ (1 if exclude_source else 0) ~ " as " ~ dbt.type_boolean() ~ ")",
            ]
        %}

        {%- do values.append(values_line) -%}

    {%- endfor -%}
    {%- endif -%}


    {{ return(values) }}

{%- endmacro -%}
