{{ config(materialized='view') }}

with source as (
    
    select * from {{ source('salesforce_raw', 'campaign_member') }}

),

renamed as (

    select
        "Id" as campaign_member_id,
        "CampaignId" as campaign_id,
        "ContactId" as contact_id,
        "Status" as member_status,
        "HasResponded" as has_responded,
        "FirstRespondedDate" as first_responded_date,
        "CreatedDate" as created_date
        
    from source

)

select * from renamed
