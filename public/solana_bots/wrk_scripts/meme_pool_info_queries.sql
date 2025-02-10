/*
 * 	Transform Views
 * 
 */

select * from token_pool_info_summary
where token_pool_info_summary.total_holder >= 50
order by ctl_created_at desc limit 100;

-- Tele notification view
create or replace view v_search_gems_recent_launched
as
with pre_cal_01 as (
	select report_date, ca, ticker, token_name, market_cap, index_n_subscriber_telegram, gmgn_url, twitter_url, token_created_at, ctl_created_at, index_n_gmgn_present, index_n_smartwallet_bought
		,(l_mc + l_liq + l_sm + l_gmgn + l_tele) as idx_total_inc_per
	from (
		select report_date, ca, ticker, token_name, market_cap, index_n_subscriber_telegram, gmgn_url, twitter_url, token_created_at, ctl_created_at, index_n_gmgn_present, index_n_smartwallet_bought
			,case when market_cap_inc_per >0 then log(market_cap_inc_per) else 0 end as l_mc
			,case when liquidity_pool_value_inc_per >0 then log(liquidity_pool_value_inc_per) else 0 end  as l_liq
			,case when index_n_smartwallet_bought >0 then log(index_n_smartwallet_bought) else 0 end  as l_sm
			,case when index_n_gmgn_present >0 then log(index_n_gmgn_present) else 0 end  as l_gmgn
			,case when index_n_subscriber_telegram_inc_per >0 then log(index_n_subscriber_telegram_inc_per) else 0 end  as l_tele
		from tbl_reports_records
		where report_name = 'tpis_search_gems_recent_launched'
			and report_date = (select report_date from tbl_reports_records order by report_date desc limit 1)
		order by report_date desc, liquidity_pool_value_inc_per desc, total_holder_inc_per desc
	) 
	order by idx_total_inc_per desc
)
select *
from pre_cal_01
;


-- Master View
create or replace view tpis_search_gems_recent_launched
as select *
from (
	select
		tpis.ca, tpis.ticker, tpis.token_name, tpis.description,
		tpis.market_cap, calculate_percentage_increase('market_cap', tpis.market_cap, tpis.ca, tpis.scd_version) as market_cap_inc_per,
		tpis.liquidity_pool_value, calculate_percentage_increase('liquidity_pool_value', tpis.liquidity_pool_value, tpis.ca, tpis.scd_version) as liquidity_pool_value_inc_per,
		tpis.index_n_smartwallet_bought, (select count(*) from wallet_tracking_info wti where wti.ticker_ca=tpis.ca group by ticker_ca) as index_n_smartwallet_txn,
		tpis.index_n_gmgn_present, calculate_percentage_increase('index_n_gmgn_present', tpis.index_n_gmgn_present, tpis.ca, tpis.scd_version) as index_n_gmgn_present_inc_per,
		tpis.index_n_subscriber_telegram, case when tpis.index_n_subscriber_telegram != 0 then calculate_percentage_increase('index_n_subscriber_telegram', tpis.index_n_subscriber_telegram, tpis.ca, tpis.scd_version) else 0 end as index_n_subscriber_telegram_inc_per,
		tpis.total_holder, calculate_percentage_increase('total_holder', tpis.total_holder, tpis.ca, tpis.scd_version) as total_holder_inc_per,
		tpis.scd_version, tpis.created_at as token_created_at, tpis.ctl_created_at,
		tpis.twitter_url, tpis.website_url, tpis.gmgn_url
	from token_pool_info_summary tpis 
	where
		tpis.liquidity_pool_value >= 10000 
		and tpis.market_cap between 20000 and 50000000
		and (tpis.website_url is not null or tpis.telegram_url is not null or tpis.twitter_url is not null)
		and tpis.index_n_gmgn_present >= 3
		and tpis.scd_version >= 2
		and tpis.scd_current = 1
		and tpis.ctl_created_at >= CURRENT_TIMESTAMP AT TIME ZONE 'Australia/Melbourne' - interval ' 24 hours' -- only tokens have been refreshed in the last 24 hrs
	order by tpis.ctl_created_at desc
)
where (market_cap_inc_per >= 20 or total_holder_inc_per >= 15 or liquidity_pool_value_inc_per >= 20 or index_n_gmgn_present >= 2)
	and market_cap_inc_per is not null and liquidity_pool_value_inc_per is not null
	and liquidity_pool_value_inc_per != 0
order by liquidity_pool_value_inc_per desc, total_holder_inc_per desc
limit 50
;


-- Low cap view
create or replace view tpis_search_gems_low_mc
as select
	tpis.ca, tpis.ticker, tpis.token_name, tpis.description,
	tpis.market_cap, calculate_percentage_increase('market_cap', tpis.market_cap, tpis.ca, tpis.scd_version) as market_cap_inc_per,
	tpis.liquidity_pool_value, calculate_percentage_increase('liquidity_pool_value', tpis.liquidity_pool_value, tpis.ca, tpis.scd_version) as liquidity_pool_value_inc_per,
	tpis.index_n_smartwallet_bought, (select count(*) from wallet_tracking_info wti where wti.ticker_ca=tpis.ca group by ticker_ca) as index_n_smartwallet_txn,
	tpis.index_n_gmgn_present, calculate_percentage_increase('index_n_gmgn_present', tpis.index_n_gmgn_present, tpis.ca, tpis.scd_version) as index_n_gmgn_present_inc_per,
	tpis.index_n_subscriber_telegram, case when tpis.index_n_subscriber_telegram != 0 then calculate_percentage_increase('index_n_subscriber_telegram', tpis.index_n_subscriber_telegram, tpis.ca, tpis.scd_version) else 0 end as index_n_subscriber_telegram_inc_per,
	tpis.total_holder, calculate_percentage_increase('total_holder', tpis.total_holder, tpis.ca, tpis.scd_version) as total_holder_inc_per,
	tpis.scd_version, tpis.created_at,
	tpis.twitter_url, tpis.website_url, tpis.gmgn_url
from token_pool_info_summary tpis 
where
	tpis.market_cap >= 8000 and tpis.total_holder >= 10
	and (tpis.website_url is not null or tpis.telegram_url is not null or tpis.twitter_url is not null)
--	and tpis.index_n_gmgn_present >= 5
	and right(tpis.ca, 4) = 'pump' -- only Pump.fun tokens
	and tpis.scd_version <= 5
	and tpis.scd_current = 1
order by total_holder_inc_per desc
limit 50
;


-- Big smart wallets bought view
create or replace view wti_big_buy_smartwallet
as select *
	from wallet_tracking_info
	where ticker_amt_usd >= 1000
	order by created_at desc
	limit 20
;


-- Pull out data for Telegram message
SELECT ca, ticker, token_name, market_cap, market_cap_inc_per, liquidity_pool_value, 
    liquidity_pool_value_inc_per, index_n_gmgn_present, index_n_smartwallet_txn, 
    total_holder, total_holder_inc_per, gmgn_url, created_at
FROM tpis_search_gems_recent_launched
ORDER BY liquidity_pool_value_inc_per DESC
LIMIT 10;

	
/*
 * 	Analysis
 * 
 */

select * from token_pool_info order by created_at desc
;
select * from token_pool_info where ticker like '%muni%' order by created_at asc
;
select * from token_pool_info where ca  like lower('6bWmri32vqayHiGozegmHT9fXyHnkwF7VfAfPWHnpump') order by created_at desc
;
select * from token_pool_info_summary where ca like lower('7Hq4rpDPLqTrxuey4vpqZ8tCQJZBUAZ1NBpxNiafpump') order by scd_version asc
;
select * from tbl_reports_records where ca like lower('7Hq4rpDPLqTrxuey4vpqZ8tCQJZBUAZ1NBpxNiafpump') order by report_date asc
;
with pre_cal_01 as (
	select ca, ticker, report_date, (l_mc + l_liq + l_sm + l_gmgn + l_tele) as idx_total_inc_per
	from (
		select ca, ticker, report_date
			,case when market_cap_inc_per >0 then log(market_cap_inc_per) else 0 end as l_mc
			,case when liquidity_pool_value_inc_per >0 then log(liquidity_pool_value_inc_per) else 0 end  as l_liq
			,case when index_n_smartwallet_bought >0 then log(index_n_smartwallet_bought) else 0 end  as l_sm
			,case when index_n_gmgn_present >0 then log(index_n_gmgn_present) else 0 end  as l_gmgn
			,case when index_n_subscriber_telegram_inc_per >0 then log(index_n_subscriber_telegram_inc_per) else 0 end  as l_tele
		from tbl_reports_records
		where report_name = 'tpis_search_gems_recent_launched'
	--		and report_date like '2024-08-20 09:52:03.084553%'
			and report_date in (select distinct report_date from tbl_reports_records where ca like lower('7Hq4rpDPLqTrxuey4vpqZ8tCQJZBUAZ1NBpxNiafpump'))
		order by report_date desc, liquidity_pool_value_inc_per desc, total_holder_inc_per desc
	--	limit 100
	) order by report_date desc, idx_total_inc_per desc
),
pre_cal_02 as (
	select ca, ticker, report_date, idx_total_inc_per
		,row_number() over (partition by report_date order by idx_total_inc_per desc) as top_ca_num
	from pre_cal_01
)
select *
from pre_cal_02
where top_ca_num in (1, 2)

;
select * from tbl_reports_records
where report_date = '2024-08-20 09:52:03.084553'
order by liquidity_pool_value_inc_per desc
;

select * from tpis_search_gems_recent_launched
;
select * from tpis_search_gems_low_mc
;
select * from wti_big_buy_smartwallet
;
select * from token_pool_info_summary
order by ctl_created_at desc
limit 100
;



select to_char(CURRENT_TIMESTAMP AT TIME ZONE 'Australia/Melbourne' - interval ' 24 hours', 'YYYY-MM-DD HH24:MI:SS')

select to_char(CURRENT_TIMESTAMP AT TIME ZONE 'Australia/Melbourne', 'YYYY-MM-DD HH24:MI:SS')

select now() AT TIME ZONE 'Australia/Melbourne'

select *
from tbl_reports_records
where report_name = 'tpis_search_gems_recent_launched'
	and ca like lower('4m83aJRxUKYCc7bMS9jQQT4enFg5driBTaiZgfyxpump')
order by ctl_created_at desc
limit 100
;


2024-08-20 19:36:48.316436
2024-08-19 21:43:04.966
Token Created At: 2024-08-19 06:52:57.192465
Last time retrieve info: 2024-08-19 21:43:04.966903

