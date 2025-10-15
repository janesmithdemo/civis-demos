{{ config(materialized='view') }}

with source as (
    
    select * from {{ source('salesforce_raw', 'contact') }}

),

renamed as (

    select
        "Id" as contact_id,
        "FirstName" as first_name,
        "LastName" as last_name,
        "Email" as email,
        "Phone" as phone,
        "MailingCity" as mailing_city,
        "MailingState" as mailing_state,
        "MailingPostalCode" as mailing_postal_code,
        "MailingCountry" as mailing_country,
        "CreatedDate" as created_date
        
    from source

)

select * from renamed
