{#- Fabric DW does not support recursive CTEs. Use a loop-based approach
    (unrolled N CTEs then UNION ALL) like BigQuery/Spark/Trino. -#}
{% macro fabric__recursive_dag() %}

{% set max_depth = var('max_depth_dag') | int %}
{% if max_depth < 2 or max_depth < var('chained_views_threshold') | int %}
    {% do exceptions.raise_compiler_error(
        'Variable max_depth_dag must be at least 2 and must be greater or equal to than chained_views_threshold.'
        ) %}
{% endif %}

with direct_relationships as (
    select
        *
    from {{ ref('int_direct_relationships') }}
    where resource_type <> 'test'
)

, get_distinct as (
    select distinct
        resource_id as parent_id,
        resource_id as child_id,
        resource_name,
        materialized as child_materialized,
        is_public as child_is_public,
        access as child_access,
        is_excluded as child_is_excluded

    from direct_relationships
)

, cte_0 as (
    select
        parent_id,
        child_id,
        child_materialized,
        child_is_public,
        child_access,
        child_is_excluded,
        0 as distance,
        cast({{ dbt.array_construct(['resource_name']) }} as varchar(max)) as path,
        cast(null as {{ dbt.type_boolean() }}) as is_dependent_on_chain_of_views
    from get_distinct
)

{% for i in range(1, max_depth) %}
{% set prev_cte_path %}cte_{{ i - 1 }}.path{% endset %}
, cte_{{ i }} as (
    select
        cte_{{ i - 1 }}.parent_id as parent_id,
        direct_relationships.resource_id as child_id,
        direct_relationships.materialized as child_materialized,
        direct_relationships.is_public as child_is_public,
        direct_relationships.access as child_access,
        direct_relationships.is_excluded as child_is_excluded,
        cte_{{ i - 1 }}.distance+1 as distance,
        cast({{ dbt.array_append(prev_cte_path, 'direct_relationships.resource_name') }} as varchar(max)) as path,
        case
            when
                cte_{{ i - 1 }}.child_materialized in ('view', 'ephemeral')
                and coalesce(cte_{{ i - 1 }}.is_dependent_on_chain_of_views, cast(1 as bit)) = cast(1 as bit)
                then cast(1 as bit)
            else cast(0 as bit)
        end as is_dependent_on_chain_of_views

        from direct_relationships
            inner join cte_{{ i - 1 }}
            on cte_{{ i - 1 }}.child_id = direct_relationships.direct_parent_id
)
{% endfor %}

, all_relationships_unioned as (
    {% for i in range(max_depth) %}
    select * from cte_{{ i }}
    {% if not loop.last %}union all{% endif %}
    {% endfor %}
)

, resource_info as (
    select * from {{ ref('int_all_graph_resources') }}
)

, all_relationships as (
    select
        parent.resource_id as parent_id,
        parent.resource_name as parent,
        parent.resource_type as parent_resource_type,
        parent.model_type as parent_model_type,
        parent.materialized as parent_materialized,
        parent.is_public as parent_is_public,
        parent.access as parent_access,
        parent.source_name as parent_source_name,
        parent.file_path as parent_file_path,
        parent.directory_path as parent_directory_path,
        parent.file_name as parent_file_name,
        parent.is_excluded as parent_is_excluded,
        child.resource_id as child_id,
        child.resource_name as child,
        child.resource_type as child_resource_type,
        child.model_type as child_model_type,
        child.materialized as child_materialized,
        child.is_public as child_is_public,
        child.access as child_access,
        child.source_name as child_source_name,
        child.file_path as child_file_path,
        child.directory_path as child_directory_path,
        child.file_name as child_file_name,
        child.is_excluded as child_is_excluded,
        cast(all_relationships_unioned.distance as {{ dbt.type_int() }}) as distance,
        all_relationships_unioned.path,
        case when all_relationships_unioned.is_dependent_on_chain_of_views = cast(1 as bit) then cast(1 as bit) else cast(0 as bit) end as is_dependent_on_chain_of_views
    from all_relationships_unioned
    left join resource_info as parent
        on all_relationships_unioned.parent_id = parent.resource_id
    left join resource_info as child
        on all_relationships_unioned.child_id = child.resource_id
)

{% endmacro %}
