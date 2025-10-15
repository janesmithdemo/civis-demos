{{ config(materialized='table') }}

-- Campaign performance analysis with estimated lifetime value
-- This model calculates key metrics for each campaign including:
-- - Donors acquired
-- - Revenue generated to date
-- - Estimated lifetime value
-- - Campaign ROI

with campaigns as (
    select * from {{ ref('stg_salesforce__campaigns') }}
),

campaign_members as (
    select * from {{ ref('stg_salesforce__campaign_members') }}
),

opportunities as (
    select * from {{ ref('stg_salesforce__opportunities') }}
),

-- Calculate historical average lifetime value across all donors
historical_ltv as (
    select
        avg(donor_total) as avg_lifetime_value
    from (
        select
            contact_id,
            sum(amount) as donor_total
        from opportunities
        where is_won = true
        group by contact_id
    ) donor_totals
),

-- Campaign performance metrics
campaign_metrics as (
    select
        c.campaign_id,
        c.campaign_name,
        c.campaign_type,
        c.campaign_status,
        c.start_date,
        c.end_date,
        c.actual_cost,
        
        -- Count of donors acquired (responded to campaign)
        count(distinct cm.contact_id) as donors_acquired,
        
        -- Total donations from these donors to date
        coalesce(sum(o.amount), 0) as total_revenue_to_date,
        
        -- Average revenue per donor to date
        coalesce(sum(o.amount), 0) / nullif(count(distinct cm.contact_id), 0) as avg_revenue_per_donor,
        
        -- Direct campaign donations (first donation tied to campaign)
        coalesce(sum(case when o.campaign_id = c.campaign_id then o.amount else 0 end), 0) as direct_campaign_revenue
        
    from campaigns c
    inner join campaign_members cm 
        on cm.campaign_id = c.campaign_id
        and cm.has_responded = true  -- Only count actual conversions
    left join opportunities o 
        on o.contact_id = cm.contact_id
        and o.is_won = true
    group by
        c.campaign_id,
        c.campaign_name,
        c.campaign_type,
        c.campaign_status,
        c.start_date,
        c.end_date,
        c.actual_cost
)

-- Final output with calculated metrics
select
    cm.campaign_id,
    cm.campaign_name,
    cm.campaign_type,
    cm.campaign_status,
    cm.start_date,
    cm.end_date,
    cm.donors_acquired,
    cm.total_revenue_to_date,
    cm.avg_revenue_per_donor,
    cm.direct_campaign_revenue,
    
    -- Estimated total lifetime value (donors acquired * avg historical LTV)
    cm.donors_acquired * coalesce(ltv.avg_lifetime_value, 0) as estimated_total_lifetime_value,
    
    -- Campaign costs and ROI
    cm.actual_cost as campaign_cost,
    cm.total_revenue_to_date - coalesce(cm.actual_cost, 0) as net_revenue_to_date,
    
    -- ROI percentage
    case 
        when cm.actual_cost > 0 then
            ((cm.total_revenue_to_date - cm.actual_cost) / cm.actual_cost) * 100
        else null
    end as roi_percent,
    
    -- Projected ROI using estimated LTV
    case 
        when cm.actual_cost > 0 then
            (((cm.donors_acquired * coalesce(ltv.avg_lifetime_value, 0)) - cm.actual_cost) / cm.actual_cost) * 100
        else null
    end as projected_roi_percent

from campaign_metrics cm
cross join historical_ltv ltv

order by estimated_total_lifetime_value desc
