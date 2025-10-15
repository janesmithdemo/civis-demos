{{ config(materialized='table') }}

-- Contact dimension enriched with lifetime giving metrics
-- This model adds lifetime value calculations to each contact

with contacts as (
    select * from {{ ref('stg_salesforce__contacts') }}
),

opportunities as (
    select * from {{ ref('stg_salesforce__opportunities') }}
),

-- Calculate giving metrics for each contact
contact_giving_metrics as (
    select
        c.contact_id,
        
        -- Lifetime giving amount
        coalesce(sum(case when o.is_won = true then o.amount else 0 end), 0) as lifetime_giving_amount,
        
        -- Count of donations
        count(case when o.is_won = true then o.opportunity_id else null end) as lifetime_gift_count,
        
        -- First and last gift dates
        min(case when o.is_won = true then o.close_date else null end) as first_gift_date,
        max(case when o.is_won = true then o.close_date else null end) as last_gift_date,
        
        -- Average gift amount
        avg(case when o.is_won = true then o.amount else null end) as avg_gift_amount,
        
        -- Count of campaigns supported
        count(distinct case when o.is_won = true and o.campaign_id is not null then o.campaign_id else null end) as campaigns_supported
        
    from contacts c
    left join opportunities o 
        on o.contact_id = c.contact_id
    group by c.contact_id
)

-- Final output with all contact fields plus giving metrics
select
    c.contact_id,
    c.first_name,
    c.last_name,
    c.email,
    c.phone,
    c.mailing_city,
    c.mailing_state,
    c.mailing_postal_code,
    c.mailing_country,
    c.created_date,
    
    -- Lifetime value metrics
    cgm.lifetime_giving_amount,
    cgm.lifetime_gift_count,
    cgm.first_gift_date,
    cgm.last_gift_date,
    cgm.avg_gift_amount,
    cgm.campaigns_supported,
    
    -- Donor status
    case 
        when cgm.lifetime_gift_count > 0 then true
        else false
    end as is_donor,
    
    -- Donor tenure in years
    CASE 
        WHEN cgm.first_gift_date IS NOT NULL THEN
            ROUND(
                DATEDIFF(day, cgm.first_gift_date, CURRENT_DATE) / 365.25,
                1
            )
        ELSE NULL
    END AS donor_tenure_years,
    
    -- Giving tier segmentation
    case
        when cgm.lifetime_giving_amount = 0 then 'Non-Donor'
        when cgm.lifetime_giving_amount < 100 then 'Under $100'
        when cgm.lifetime_giving_amount < 500 then '$100 - $499'
        when cgm.lifetime_giving_amount < 1000 then '$500 - $999'
        when cgm.lifetime_giving_amount < 5000 then '$1,000 - $4,999'
        when cgm.lifetime_giving_amount < 10000 then '$5,000 - $9,999'
        else '$10,000+'
    end as giving_tier,
    
    -- Recency (days since last gift)
    CASE 
        WHEN cgm.last_gift_date IS NOT NULL THEN
            DATEDIFF(day, cgm.last_gift_date, CURRENT_DATE)
        ELSE NULL
    END AS days_since_last_gift,
    
    -- Donor frequency category
    case
        when cgm.lifetime_gift_count = 0 then 'Never Donated'
        when cgm.lifetime_gift_count = 1 then 'One-Time Donor'
        when cgm.lifetime_gift_count between 2 and 5 then 'Occasional Donor'
        when cgm.lifetime_gift_count between 6 and 12 then 'Regular Donor'
        else 'Major Donor'
    end as donor_frequency_category

from contacts c
left join contact_giving_metrics cgm
    on cgm.contact_id = c.contact_id

order by cgm.lifetime_giving_amount desc nulls last
