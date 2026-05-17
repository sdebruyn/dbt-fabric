{#- T-SQL recursive CTEs require explicit column typing; BIT booleans replace
    TRUE/FALSE in the is_dependent_on_chain_of_views logic. #}
{% macro fabric__recursive_dag() %}

with direct_relationships as (
    select
        *
    from {{ ref('int_direct_relationships') }}
    where resource_type <> 'test'
),

all_relationships as (
    -- anchor
    select distinct
        resource_id as parent_id,
        resource_name as parent,
        resource_type as parent_resource_type,
        model_type as parent_model_type,
        materialized as parent_materialized,
        access as parent_access,
        is_public as parent_is_public,
        source_name as parent_source_name,
        file_path as parent_file_path,
        directory_path as parent_directory_path,
        file_name as parent_file_name,
        is_excluded as parent_is_excluded,
        resource_id as child_id,
        resource_name as child,
        resource_type as child_resource_type,
        model_type as child_model_type,
        materialized as child_materialized,
        access as child_access,
        is_public as child_is_public,
        source_name as child_source_name,
        file_path as child_file_path,
        directory_path as child_directory_path,
        file_name as child_file_name,
        is_excluded as child_is_excluded,
        0 as distance,
        {{ dbt.array_construct(['resource_name']) }} as path,
        cast(null as {{ dbt.type_boolean() }}) as is_dependent_on_chain_of_views

    from direct_relationships

    union all

    -- recursive clause
    select
        all_relationships.parent_id as parent_id,
        all_relationships.parent as parent,
        all_relationships.parent_resource_type as parent_resource_type,
        all_relationships.parent_model_type as parent_model_type,
        all_relationships.parent_materialized as parent_materialized,
        all_relationships.parent_access as parent_access,
        all_relationships.parent_is_public as parent_is_public,
        all_relationships.parent_source_name as parent_source_name,
        all_relationships.parent_file_path as parent_file_path,
        all_relationships.parent_directory_path as parent_directory_path,
        all_relationships.parent_file_name as parent_file_name,
        all_relationships.parent_is_excluded as parent_is_excluded,
        direct_relationships.resource_id as child_id,
        direct_relationships.resource_name as child,
        direct_relationships.resource_type as child_resource_type,
        direct_relationships.model_type as child_model_type,
        direct_relationships.materialized as child_materialized,
        direct_relationships.access as child_access,
        direct_relationships.is_public as child_is_public,
        direct_relationships.source_name as child_source_name,
        direct_relationships.file_path as child_file_path,
        direct_relationships.directory_path as child_directory_path,
        direct_relationships.file_name as child_file_name,
        direct_relationships.is_excluded as child_is_excluded,
        all_relationships.distance+1 as distance,
        {{ dbt.array_append('all_relationships.path', 'direct_relationships.resource_name') }} as path,
        case
            when
                all_relationships.child_materialized in ('view', 'ephemeral')
                and coalesce(all_relationships.is_dependent_on_chain_of_views, cast(1 as bit)) = cast(1 as bit)
                then cast(1 as bit)
            else cast(0 as bit)
        end as is_dependent_on_chain_of_views

    from direct_relationships
    inner join all_relationships
        on all_relationships.child_id = direct_relationships.direct_parent_id

    {% if var('max_depth_dag') | int > 0 %}
        {% if var('max_depth_dag') | int < 2 or var('max_depth_dag') | int < var('chained_views_threshold') | int %}
            {% do exceptions.raise_compiler_error(
                'Variable max_depth_dag must be at least 2 and must be greater or equal to than chained_views_threshold.'
                ) %}
        {% else %}
        where distance <= {{ var('max_depth_dag')}}
        {% endif %}
    {% endif %}

)

{% endmacro %}
