
-- --------------------------------------------- --
-- 		Table DDL & DML
-- --------------------------------------------- --

alter table token_pool_info 
add column created_at timestamp default current_timestamp,
add column updated_at timestamp default current_timestamp;

alter table token_pool_info 
add column network varchar;


-- Trigger to updated_at field
create or replace function updated_at_column()
returns trigger as $$
begin
	new.updated_at = (CURRENT_TIMESTAMP AT TIME ZONE 'Australia/Melbourne'::text);
	return new;	
end;
$$ language plpgsql;


-- trigger exec
create trigger set_timestamp_token_pool_info
before update on token_pool_info
for each row
execute function updated_at_column();


create trigger set_timestamp_tele_session_binary_files
before update on tele_session_binary_files
for each row
execute function updated_at_column();


-- Retrieve data from `token_pool_info` table
select tpi.network ,tpi.ca ,tpi.ticker ,tpi.token_name ,tpi.description
    ,case when tpis.market_cap is null then tpi.market_cap else tpis.market_cap end as market_cap
    ,case when tpis.liquidity_pool_value is null then tpi.liquidity_pool_value else tpis.liquidity_pool_value end as liquidity_pool_value
    ,tpis.total_holder ,tpi.gmgn_url
    ,tpis.index_n_smartwallet_bought, tpis.index_n_gmgn_present ,tpis.index_n_bonkbot_present
    ,tpis.index_n_follower_twitter ,tpis.index_n_subscriber_telegram ,tpis.index_n_twitter_search_result
    ,tpis.twitter_url ,tpis.telegram_url ,tpis.website_url ,tpi.created_at 
from token_pool_info tpi 
full outer join (
    select *
    from token_pool_info_summary 
    where scd_current = 1 and ctl_created_at >= CURRENT_TIMESTAMP AT TIME ZONE 'Australia/Melbourne' - interval ' 24 hours'
) tpis
on tpis.ca = tpi.ca
where tpi.network = 'Solana'
    and tpi.created_at >= CURRENT_TIMESTAMP AT TIME ZONE 'Australia/Melbourne' - interval ' 24 hours' -- only token created in the last 24 hours
    and (tpis.market_cap between 10000 and 100000000 or tpis.market_cap is null) and (tpis.liquidity_pool_value >= 5000 or tpis.liquidity_pool_value is null)
order by tpi.created_at desc
--limit 250
;



-- Create table to store Tele session
CREATE TABLE tele_session_binary_files (
    file_name text PRIMARY KEY,
    content BYTEA
);


-- Insert a record to token_pool_info_summary by applying SCD type 2
CREATE OR REPLACE PROCEDURE update_scd_to_token_pool_info_summary(
	p_network varchar,
	p_ca varchar,
	p_ticker varchar,
	p_token_name varchar,
	p_description varchar,
	p_market_cap varchar,
	p_liquidity_pool_value varchar,
	p_gmgn_url varchar,
	p_index_n_smartwallet_bought varchar,
	p_index_n_gmgn_present varchar,
	p_index_n_bonkbot_present varchar,
	p_index_n_follower_twitter varchar,
	p_index_n_subscriber_telegram varchar,
	p_index_n_twitter_search_result varchar,
	p_twitter_url varchar,
	p_telegram_url varchar,
	p_total_holder varchar,
	p_website_url varchar,
	p_created_at varchar
) AS $$
DECLARE
    v_current_record RECORD;
	p_n_market_cap numeric;
	p_n_liquidity_pool_value numeric;
	p_n_index_n_smartwallet_bought int;
	p_n_index_n_gmgn_present int;
	p_n_index_n_bonkbot_present int;
	p_n_index_n_follower_twitter int;
	p_n_index_n_subscriber_telegram int;
	p_n_index_n_twitter_search_result int;
	p_n_total_holder int;
	p_n_created_at timestamp;
BEGIN
	-- Convert parameters into correct format
   	p_n_market_cap := convert_none_to_null(p_market_cap)::numeric;
	p_n_liquidity_pool_value := convert_none_to_null(p_liquidity_pool_value)::numeric;
	p_n_index_n_smartwallet_bought := convert_none_to_null(p_index_n_smartwallet_bought)::int;
	p_n_index_n_gmgn_present := convert_none_to_null(p_index_n_gmgn_present)::int;
	p_n_index_n_bonkbot_present := convert_none_to_null(p_index_n_bonkbot_present)::int;
   	p_n_index_n_follower_twitter := convert_none_to_null(p_index_n_follower_twitter)::int;
	p_n_index_n_subscriber_telegram := convert_none_to_null(p_index_n_subscriber_telegram)::int;
	p_n_index_n_twitter_search_result := convert_none_to_null(p_index_n_twitter_search_result)::int;
	p_n_total_holder := convert_none_to_null(p_total_holder)::int;
	p_n_created_at := convert_none_to_null(p_created_at)::timestamp;

	p_twitter_url := convert_none_to_null(p_twitter_url);
	p_telegram_url := convert_none_to_null(p_telegram_url);
	p_website_url := convert_none_to_null(p_website_url);

    -- Get the current record
    SELECT * INTO v_current_record
    FROM token_pool_info_summary
    WHERE ca = p_ca AND scd_current = 1 LIMIT 1;

	if found then
    -- Update the current record to mark it as not current
	    UPDATE token_pool_info_summary
	    SET scd_current = 0
	    WHERE ca = v_current_record.ca AND scd_current = 1;

--     Insert the new version of the product
	    INSERT INTO token_pool_info_summary (network, ca, ticker, token_name, description, market_cap, 
	    	liquidity_pool_value, gmgn_url, index_n_smartwallet_bought, index_n_gmgn_present, index_n_bonkbot_present, 
	    	index_n_follower_twitter, index_n_subscriber_telegram, index_n_twitter_search_result, scd_version, scd_current, 
	    	twitter_url, telegram_url, total_holder, website_url, created_at)
	    VALUES (p_network, p_ca, p_ticker, p_token_name, p_description, p_n_market_cap, 
			p_n_liquidity_pool_value, p_gmgn_url, p_n_index_n_smartwallet_bought, p_n_index_n_gmgn_present, 
			p_n_index_n_bonkbot_present, p_n_index_n_follower_twitter, p_n_index_n_subscriber_telegram, 
			p_n_index_n_twitter_search_result, v_current_record.scd_version + 1, 1, 
			p_twitter_url, p_telegram_url, p_n_total_holder, p_website_url, p_n_created_at
	   	);
	
	else
--		 Insert as a new record
	    INSERT INTO token_pool_info_summary (network, ca, ticker, token_name, description, market_cap, 
	    	liquidity_pool_value, gmgn_url, index_n_smartwallet_bought, index_n_gmgn_present, index_n_bonkbot_present, 
	    	index_n_follower_twitter, index_n_subscriber_telegram, index_n_twitter_search_result, scd_version, scd_current, 
	    	twitter_url, telegram_url, total_holder, website_url, created_at)
	    VALUES (p_network, p_ca, p_ticker, p_token_name, p_description, p_n_market_cap, 
			p_n_liquidity_pool_value, p_gmgn_url, p_n_index_n_smartwallet_bought, p_n_index_n_gmgn_present, 
			p_n_index_n_bonkbot_present, p_n_index_n_follower_twitter, p_n_index_n_subscriber_telegram, 
			p_n_index_n_twitter_search_result, 1, 1, 
			p_twitter_url, p_telegram_url, p_n_total_holder, p_website_url, p_n_created_at
	   	);
	end if;

END;
$$ LANGUAGE plpgsql;


-- Convert 'None' varchar to Null
CREATE OR REPLACE FUNCTION convert_none_to_null(input_text TEXT)
RETURNS TEXT AS $$
BEGIN
    -- Check if the input_text is 'None', if so return NULL, otherwise return the input_text
    IF input_text = 'None' THEN
        RETURN NULL;
    ELSE
        RETURN input_text;
    END IF;
END;
$$ LANGUAGE plpgsql;


-- Function to calculate percentage increase of a columns, given current version
CREATE OR REPLACE FUNCTION calculate_percentage_increase(p_column text, p_value float, p_ca text, v_current_version int)
RETURNS float AS $$
DECLARE
    v_previous_version INT;
	v_current_value float;
	v_previous_value float;
    v_percentage_increase float;
	v_sql TEXT;
BEGIN
    
	IF v_current_version != 1 THEN
		-- Get the current value
		v_sql := 'SELECT ' || quote_ident(p_column) || ' FROM token_pool_info_summary WHERE ca = ''' || p_ca || ''' and scd_version = ' || v_current_version;
		execute v_sql into v_current_value;

		-- Get the previous value
		v_previous_version := v_current_version - 1;
		v_sql := 'SELECT ' || quote_ident(p_column) || ' FROM token_pool_info_summary WHERE ca = ''' || p_ca || ''' and scd_version = ' || v_previous_version;
		execute v_sql into v_previous_value;

		

	    -- Check if previous value exists
	    IF v_previous_value IS NULL OR v_previous_value = 0 THEN
--	        RAISE NOTICE 'No previous version found.';
	        RETURN NULL;
	    ELSE
	        -- Calculate the percentage increase
	        v_percentage_increase := ((v_current_value - v_previous_value) / v_previous_value) * 100;
--			raise notice 'N-Cur_Val: %, Pre_Val: %, Percent: %', v_current_value, v_previous_value, v_percentage_increase;		
	        RETURN round(v_percentage_increase);
	    END IF;
	END IF;
	RETURN Null;
END;
$$ LANGUAGE plpgsql;



-- Function to calculate percentage increase of a columns, given current version
CREATE OR REPLACE FUNCTION tst_calculate_percentage_increase(p_column text, p_value float, p_ca text, v_current_version int)
RETURNS float AS $$
DECLARE
    v_previous_version INT;
	v_current_value float;
	v_previous_value float;
    v_percentage_increase float;
	v_sql TEXT;
BEGIN
    
	IF v_current_version != 1 THEN
		-- Get the current value
		v_sql := 'SELECT ' || quote_ident(p_column) || ' FROM token_pool_info_summary WHERE ca = ''' || p_ca || ''' and scd_version = ' || v_current_version;
		raise notice 'Sql Current value: %', v_sql;
		execute v_sql into v_current_value;

		-- Get the previous value
		v_previous_version := v_current_version - 1;
		v_sql := 'SELECT ' || quote_ident(p_column) || ' FROM token_pool_info_summary WHERE ca = ''' || p_ca || ''' and scd_version = ' || v_previous_version;
		raise notice 'Sql Previous value: %', v_sql;
		execute v_sql into v_previous_value;

		
	    -- Check if previous value exists
	    IF v_previous_value IS NULL OR v_previous_value = 0 THEN
--	        RAISE NOTICE 'No previous version found.';
	        RETURN NULL;
	    ELSE
	        -- Calculate the percentage increase
	        v_percentage_increase := ((v_current_value - v_previous_value) / v_previous_value) * 100;
			raise notice 'Cur_Val: %, Pre_Val: %, Percent: %', v_current_value, v_previous_value, v_percentage_increase;		
	        RETURN round(v_percentage_increase);
	    END IF;
	END IF;
	RETURN Null;
END;
$$ LANGUAGE plpgsql;



-- Proc to insert report data into the table `tbl_reports_records`
CREATE OR REPLACE PROCEDURE insert_report_data_from_view(view_name varchar, tar_table_name varchar)
LANGUAGE plpgsql
AS $$
DECLARE
    v_columns text;
    insert_sql text;
	melbourne_timestamp timestamp;
BEGIN
	-- Get the current timestamp in Melbourne timezone
    melbourne_timestamp := to_char(CURRENT_TIMESTAMP AT TIME ZONE 'Australia/Melbourne', 'YYYY-MM-DD HH24:MI:SS');

    -- Fetch the column names from the view
    SELECT string_agg(column_name, ', ')
    INTO v_columns
    FROM information_schema.columns
    WHERE table_name = view_name;

    -- Construct the dynamic SQL for insertion
    insert_sql := format('INSERT INTO %I (report_name, report_date, %s) SELECT ''%s'', ''%s'', %s FROM %I', tar_table_name, v_columns, view_name, melbourne_timestamp, v_columns, view_name);

    -- Execute the dynamic SQL
    EXECUTE insert_sql;
--	RAISE NOTICE '%', insert_sql;

    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE 'Error inserting data from view: %', SQLERRM;
END;
$$;



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


-- --------------------------------------------- --
-- 		Table DML
-- --------------------------------------------- --

-- Tbl Maintenance -- 
select count(*) from token_pool_info_summary 
where ctl_created_at >= CURRENT_TIMESTAMP AT TIME ZONE 'Australia/Melbourne' - interval '14 days'
	and scd_version 
;

select count(*) from token_pool_info 
where ctl_created_at >= CURRENT_TIMESTAMP AT TIME ZONE 'Australia/Melbourne' - interval '14 days'
	and scd_version 
;


-- Delete records older than 5 days ago
--delete from token_pool_info_summary where ctl_created_at <= CURRENT_TIMESTAMP AT TIME ZONE 'Australia/Melbourne' - interval '5 days'
;


-- Monitoring
select count(*) from token_pool_info tpi 
;
select count(*) from token_pool_info_summary tpis 
;
select count(*) from wallet_tracking_info wti 
;
select count(*) from tbl_reports_records
;

