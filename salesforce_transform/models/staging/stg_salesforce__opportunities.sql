{{ config(materialized='view') }}

with source as (
    
    select * from {{ source('salesforce_raw', 'opportunity') }}

),

renamed as (

    select
        "Id" as opportunity_id,
        "ContactId" as contact_id,
        "CampaignId" as campaign_id,
        "Name" as opportunity_name,
        "Amount" as amount,
        "CloseDate" as close_date,
        "StageName" as stage_name,
        "IsClosed" as is_closed,
        "IsWon" as is_won,
        "Type" as opportunity_type,
        "CreatedDate" as created_date
        
    from source

)

select * from renamed
