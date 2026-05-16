{% macro fabric__get_invocations_dml_sql(invocation_args=invocation_args_dict) -%}
    {% set invocation_values %}
    select
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
        nullif("11", ''),
        nullif("12", ''),
        nullif("13", ''),
        nullif("14", ''),
        nullif("15", ''),
        "16",
        "17",
        "18",
        "19"
    from (values
    (
        '{{ invocation_id }}', {# command_invocation_id #}
        '{{ dbt_version }}', {# dbt_version #}
        '{{ project_name }}', {# project_name #}
        '{{ run_started_at }}', {# run_started_at #}
        '{{ flags.WHICH }}', {# dbt_command #}
        '{{ flags.FULL_REFRESH }}', {# full_refresh_flag #}
        '{{ target.profile_name }}', {# target_profile_name #}
        '{{ target.name }}', {# target_name #}
        '{{ target.schema }}', {# target_schema #}
        {{ target.threads }}, {# target_threads #}

        '{{ env_var('DBT_CLOUD_PROJECT_ID', '') }}', {# dbt_cloud_project_id #}
        '{{ env_var('DBT_CLOUD_JOB_ID', '') }}', {# dbt_cloud_job_id #}
        '{{ env_var('DBT_CLOUD_RUN_ID', '') }}', {# dbt_cloud_run_id #}
        '{{ env_var('DBT_CLOUD_RUN_REASON_CATEGORY', '') }}', {# dbt_cloud_run_reason_category #}
        '{{ env_var('DBT_CLOUD_RUN_REASON', '') | replace("'","''") }}', {# dbt_cloud_run_reason #}
        {% if var('env_vars', none) %}
            {% set env_vars_dict = {} %}
            {% for env_variable in var('env_vars') %}
                {% do env_vars_dict.update({env_variable: (env_var(env_variable, '') | replace("'", "''"))}) %}
            {% endfor %}
            '{{ tojson(env_vars_dict) }}', {# env_vars #}
        {% else %}
            null, {# env_vars #}
        {% endif %}
        {% if var('dbt_vars', none) %}
            {% set dbt_vars_dict = {} %}
            {% for dbt_var in var('dbt_vars') %}
                {% do dbt_vars_dict.update({dbt_var: (var(dbt_var, '') | replace("'", "''"))}) %}
            {% endfor %}
            '{{ tojson(dbt_vars_dict) }}', {# dbt_vars #}
        {% else %}
            null, {# dbt_vars #}
        {% endif %}
        '{{ tojson(invocation_args) | replace("'", "''") }}', {# invocation_args #}

        {% set metadata_env = {} %}
        {% for key, value in dbt_metadata_envs.items() %}
            {% do metadata_env.update({key: (value | replace("'", "''"))}) %}
        {% endfor %}
        '{{ tojson(metadata_env) }}' {# dbt_custom_envs #}

    )

        ) v ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19")

    {% endset %}
    {{ invocation_values }}

{% endmacro -%}
