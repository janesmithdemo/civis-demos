{{ config(materialized='view') }}{{ config(materialized='view') }}



with source as (

    select * from {{ source('salesforce_raw', 'campaign') }}

),



renamed as (


   select

        "Id" as campaign_id,       

        "Name" as campaign_name,        

        "Type" as campaign_type,        

        "Status" as campaign_status,        

        "StartDate" as start_date,       

        "EndDate" as end_date,     

        "ActualCost" as actual_cost,       

        "Description" as description,      

        "IsActive" as is_active,      

        "CreatedDate" as created_date       

    from source        

)

select * from renamed
