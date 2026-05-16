{%- macro fabric__upload_results(results) -%}

    {% if execute %}

        {% set datasets_to_load = ['exposures', 'seeds', 'snapshots', 'invocations', 'sources', 'tests', 'models'] %}
        {% if results != [] %}
            {% set datasets_to_load = ['model_executions', 'seed_executions', 'test_executions', 'snapshot_executions'] + datasets_to_load %}
        {% endif %}

        {% for dataset in datasets_to_load %}

            {% do log("Uploading " ~ dataset.replace("_", " "), true) %}

            {% set objects = dbt_artifacts.get_dataset_content(dataset) %}

            {% set upload_limit = 5000 %}
            {% if dataset == 'models' %}
                {% set upload_limit = 100 %}
            {% endif %}

            {% for i in range(0, objects | length, upload_limit) -%}

                {% set content = dbt_artifacts.get_table_content_values(dataset, objects[i: i + upload_limit]) %}

                {{ dbt_artifacts.insert_into_metadata_table(
                    dataset=dataset,
                    fields=fabric__get_column_name_list(dataset),
                    content=content
                    )
                }}

            {% endfor %}

        {% endfor %}

    {% endif %}

{%- endmacro -%}
