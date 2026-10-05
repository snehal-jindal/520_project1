"""Reproducible, scope-restricted EDA. No final outcomes or fitted forecasts."""
from pathlib import Path
import json, html, os
import numpy as np
import pandas as pd
from scipy.stats import linregress
from .data_access import *

def gfs_calibration_pairs(root, observations):
    """Compare frozen forecasts with routine reports at their actual timestamps.

    Interpolation uses only values from the same already-issued forecast. July 30
    is excluded because its labels overlap the August confirmation origins.
    """
    history = pd.read_csv(root/'data/pre_eda/prepared/gfs_2026_historical_fixed_run_forecasts.csv')
    history['valid_time'] = pd.to_datetime(history.valid_time_utc, utc=True)
    history['origin'] = pd.to_datetime(history.forecast_origin_utc, utc=True)
    history['init'] = pd.to_datetime(history.model_initialization_utc, utc=True)
    history = history.loc[history.init.le(pd.Timestamp('2026-07-23T18:00Z'))].copy()
    rows = []
    for source, run in history.groupby('source_file'):
        payload = json.loads((root/'data/pre_eda/raw/gfs_single_runs'/source).read_text())
        times = pd.to_datetime(payload['hourly']['time'], utc=True)
        values = np.array(payload['hourly']['temperature_2m'], dtype=float)
        obs = observations.reindex(pd.DatetimeIndex(run.valid_time)).copy()
        actual_times = obs.observed_at
        # Guard np.interp's endpoint behavior: no extrapolation, no missing input.
        usable = (obs.temperature.notna() & actual_times.notna() &
                  actual_times.ge(times.min()) & actual_times.le(times.max()))
        prediction = np.full(len(obs), np.nan)
        prediction[usable] = np.interp(actual_times.loc[usable].astype('int64'),
                                      times.astype('int64'), values)
        out = pd.DataFrame({'valid_time_utc':run.valid_time.to_numpy(),
                            'origin_utc':run.origin.to_numpy(),
                            'actual_report_utc':actual_times.to_numpy(),
                            'day':np.floor(run.hours_from_forecast_origin.to_numpy()/24).astype(int)+1,
                            'prediction_f':prediction,'observation_f':obs.temperature.to_numpy(),
                            'source_file':source})
        out['error_f'] = out.prediction_f-out.observation_f
        rows.append(out)
    pairs = pd.concat(rows, ignore_index=True)
    assert pd.to_datetime(pairs.actual_report_utc, utc=True).dropna().lt(FINAL_ORIGIN).all()
    assert pd.to_datetime(pairs.origin_utc, utc=True).max() == pd.Timestamp('2026-07-24T04:00Z')
    return pairs

def metric_summary(group):
    e=group.error_f.dropna()
    return pd.Series({'scored_pairs':len(e),'mae_f':e.abs().mean(),
                      'rmse_f':np.sqrt((e**2).mean()),'bias_f':e.mean()})

def run_eda(root: Path):
    out=root/'reports/eda'; figures=out/'figures'; tables=out/'tables'
    for p in (out,figures,tables): p.mkdir(parents=True,exist_ok=True)
    os.environ.setdefault('MPLCONFIGDIR', str(out/'.mpl-cache'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'figure.dpi':130,'savefig.dpi':160,'font.size':10,
                         'axes.spines.top':False,'axes.spines.right':False,
                         'axes.grid':True,'grid.alpha':.18})
    df=load_observations(root); core=training_eda_scope(df)
    full=core.loc[core.local_year.le(2020)].copy()
    seasonal=full.loc[full.local_month.isin([8,9,10])].copy()
    target=full.loc[full.local_month.eq(9)&full.local_day.between(17,30)].copy()
    sections=[]; summary={}
    def table(name, frame):
        frame.to_csv(tables/(name+'.csv'),index=True)
    def figure(name,title,question,scope,finding,implication,limitation):
        fig=plt.gcf(); fig.suptitle(title,fontsize=13,y=1.015)
        fig.tight_layout(); fig.savefig(figures/(name+'.png'),bbox_inches='tight')
        fig.savefig(figures/(name+'.svg'),bbox_inches='tight'); plt.close(fig)
        sections.append(dict(name=name,title=title,question=question,scope=scope,
                             finding=finding,implication=implication,limitation=limitation))
    scope='Complete training years 2011–2020; RDU routine reports; screened temperature in °F.'
    n=len(core); missing=int(core.temperature.isna().sum())
    summary['core']={'start_utc':core.time.min().isoformat(),'end_hour_utc':core.time.max().isoformat(),
                     'hours':n,'usable':n-missing,'missing_or_quarantined':missing,
                     'complete_years':10,'historical_target_hours':len(target),
                     'historical_target_usable':int(target.temperature.notna().sum())}
    coverage=core.groupby(['local_year','local_month']).agg(hours=('temperature','size'),usable=('temperature','count'))
    coverage['unavailable_pct']=100*(1-coverage.usable/coverage.hours);table('core_monthly_coverage',coverage)
    gaps=missing_runs(core);table('core_missing_runs',gaps)
    plt.figure(figsize=(10,3.4)); daily=core.set_index('time').temperature.resample('D').mean()
    plt.plot(daily.index,daily.values,lw=.65,color='#236b8e');plt.ylabel('Daily mean of hourly reports (°F)')
    figure('01_history','The annual temperature cycle dominates the history',
           'What patterns must a model represent?', '2011 through September 16, 2021, before the first development origin.',
           f'{n:,} expected hourly slots; {n-missing:,} usable temperatures. Warm and cold seasons repeat, with substantial daily variation.',
           'Use calendar and hour features. Compare training seasons using matched September backtests.',
           'Daily means describe hourly reports, not continuous daily extrema. Partial 2021 is not compared as a complete year.')
    plt.figure(figsize=(9,4)); matrix=coverage.unavailable_pct.unstack().reindex(columns=range(1,13))
    plt.imshow(matrix,aspect='auto',cmap='YlOrRd',vmin=0);plt.colorbar(label='Unavailable temperature (%)')
    plt.xticks(range(12),range(1,13));plt.yticks(range(len(matrix)),matrix.index);plt.xlabel('Local month');plt.ylabel('Local year')
    figure('02_missingness','Quality exclusions and missing observations',
           'Are there gaps that affect lags, fitting, or scoring?', 'Training scope only; absent or quarantined targets counted as unavailable.',
           f'{missing:,} unavailable hours ({100*missing/n:.3f}%); longest consecutive run is {int(gaps.hours.max())} hours.',
           'Keep the hourly grid, retain quality flags, and score only available targets on a shared mask.',
           'Gray/empty cells after the 2021 cutoff were not analyzed; unavailable includes source disagreements, not just absent reports.')
    descriptions=pd.concat({'all_months':full.temperature.describe(percentiles=[.01,.1,.5,.9,.99]),
                            'aug_oct':seasonal.temperature.describe(percentiles=[.01,.1,.5,.9,.99]),
                            'sep17_30':target.temperature.describe(percentiles=[.01,.1,.5,.9,.99])},axis=1)
    table('temperature_distributions',descriptions)
    monthly=full.groupby('local_month').temperature.agg(['count','mean','std','min','max']);table('monthly_temperature',monthly)
    plt.figure(figsize=(9,4));plt.boxplot([full.loc[full.local_month.eq(m),'temperature'].dropna() for m in range(1,13)],
                                        tick_labels=range(1,13),showfliers=False)
    plt.ylabel('Temperature (°F)');plt.xlabel('Month')
    figure('03_months','All months provide more examples, but different temperature regimes',
           'Why not choose all months purely because there are more rows?',scope,
           f'September mean is {monthly.loc[9,"mean"]:.1f}°F; January {monthly.loc[1,"mean"]:.1f}°F and July {monthly.loc[7,"mean"]:.1f}°F.',
           'Aug–Oct is the initial candidate because it brackets September. Retain all months to test whether season-aware modeling improves September errors.',
           'Boxes show quartiles and whiskers; hidden outlier markers are retained in data. Row count does not equal independent weather episodes.')
    plt.figure(figsize=(9,4))
    for m,label,color in [(8,'August','#db9842'),(9,'September','#207d8d'),(10,'October','#6f62a1')]:
        plt.hist(seasonal.loc[seasonal.local_month.eq(m),'temperature'].dropna(),bins=np.arange(25,109,2),density=True,histtype='step',label=label,color=color,lw=1.7)
    plt.hist(target.temperature.dropna(),bins=np.arange(25,109,2),density=True,histtype='step',lw=2,label='Sep 17–30',color='black');plt.legend();plt.xlabel('Temperature (°F)');plt.ylabel('Density')
    q=target.temperature.quantile([.1,.5,.9]);summary['target_distribution']={str(k):float(v) for k,v in q.items()}
    figure('04_season_distributions','The target fortnight sits within a changing autumn distribution',
           'How representative are neighboring months?',scope,
           f'Historical target-window median {q.loc[.5]:.1f}°F; middle 80% spans {q.loc[.1]:.1f}–{q.loc[.9]:.1f}°F.',
           'Neighboring months add examples of fronts and daily cycles, but month/day features must represent the autumn cooling.',
           'These are descriptive historical quantiles, not calibrated forecast intervals for 2026.')
    hour_month=full.groupby(['local_month','local_hour']).temperature.mean().unstack();table('monthly_hourly_means',hour_month)
    plt.figure(figsize=(9,4));plt.imshow(hour_month,aspect='auto',cmap='coolwarm');plt.colorbar(label='Mean temperature (°F)');plt.xticks(range(0,24,3),range(0,24,3));plt.yticks(range(12),range(1,13));plt.xlabel('Raleigh civil hour');plt.ylabel('Month')
    figure('05_month_hour','The daily cycle changes with season', 'Should hour and season interact?',scope,
           'The warmest average hours occur in the afternoon; nights and mornings are cooler. Seasonal means and daily ranges differ.',
           'Use cyclic hour/day-of-year features and consider hour-by-season interactions in linear regression.',
           'Civil-hour grouping respects DST; it is not an elapsed-time lag. Means conceal cloudy, wet, and frontal regimes.')
    plt.figure(figsize=(9,4));diurnal=[]
    for m,label in [(8,'August'),(9,'September'),(10,'October')]:
        g=seasonal.loc[seasonal.local_month.eq(m)].groupby('local_hour').temperature
        mean=g.mean();low=g.quantile(.1);high=g.quantile(.9)
        line=plt.plot(mean.index,mean.values,label=label)[0];plt.fill_between(mean.index,low,high,color=line.get_color(),alpha=.09)
        diurnal.append({'month':m,'mean_cycle_range_f':mean.max()-mean.min(),'peak_hour':int(mean.idxmax()),'coolest_hour':int(mean.idxmin())})
    table('diurnal_cycle',pd.DataFrame(diurnal));plt.xlabel('Raleigh civil hour');plt.ylabel('Temperature (°F)');plt.legend()
    figure('06_daily_cycle','Weather variation is wider than the average daily cycle', 'How much variation does a calendar-only forecast miss?',scope,
           f'September mean cycle range is {diurnal[1]["mean_cycle_range_f"]:.1f}°F, peaking at civil hour {diurnal[1]["peak_hour"]}.',
           'Calendar averages are useful baselines; forecast weather inputs may explain departures.',
           'Shaded 10th–90th percentiles are weather dispersion, not uncertainty in the mean or forecast coverage.')
    seasonal['season_day']=pd.to_datetime('2001-'+seasonal.local_month.astype(str)+'-'+seasonal.local_day.astype(str)).dt.dayofyear-212
    # Equal weight for years: summarize each year/day before combining years.
    yd=seasonal.groupby(['local_year','season_day']).temperature.mean().unstack(0)
    day_stats=pd.DataFrame({'mean':yd.mean(axis=1),'q25':yd.quantile(.25,axis=1),'q75':yd.quantile(.75,axis=1),'years':yd.count(axis=1)})
    table('autumn_daily_climatology',day_stats)
    plt.figure(figsize=(9,4));x=day_stats.index
    plt.plot(x,day_stats['mean'].rolling(7,center=True,min_periods=1).mean(),label='7-day smooth of equal-year daily mean')
    plt.fill_between(x,day_stats.q25,day_stats.q75,alpha=.2,label='Between-year middle 50%');plt.axvspan(48,61,color='#e5b643',alpha=.15,label='Sep 17–30')
    plt.xticks([1,32,48,61,62,92],['Aug 1','Sep 1','Sep 17','Sep 30','Oct 1','Oct 31']);plt.ylabel('Daily mean (°F)');plt.legend(fontsize=8)
    figure('07_autumn_transition','The forecast window is part of an autumn cooling transition', 'Is September interchangeable with August and October?',scope,
           'Average temperature declines through the candidate season; individual years depart considerably from that pattern.',
           'Use continuous calendar features rather than assigning one September constant.',
           'Smoothing is descriptive and uses neighboring training days; it is not a forecast and is not applied across evaluation cutoffs.')
    td=target.groupby(['local_year','local_day']).temperature.mean().unstack(0);table('historical_target_daily_means',td)
    plt.figure(figsize=(9,4))
    for y in td:plt.plot(td.index,td[y],alpha=.7,lw=1,label=str(y))
    plt.xlabel('September day');plt.ylabel('Daily mean (°F)');plt.legend(ncol=5,fontsize=8)
    figure('08_target_weather','Ten historical Septembers show different two-week weather paths', 'How variable is the exact target fortnight?',scope,
           f'{target.temperature.notna().sum():,} usable target-like hours represent only ten annual fortnights.',
           'Validate whole 336-hour forecasts at historical origins; random hourly splitting would share weather events across train and test.',
           'Training-era examples are descriptive; 2021–2025 evaluation fortnight outcomes are not plotted here.')
    september=full.loc[full.local_month.eq(9)].copy()
    annual=pd.DataFrame({'all_hours':september.groupby('local_year').temperature.mean(),
                         'night_00_06':september.loc[september.local_hour.between(0,6)].groupby('local_year').temperature.mean(),
                         'afternoon_12_18':september.loc[september.local_hour.between(12,18)].groupby('local_year').temperature.mean()})
    table('september_yearly_means',annual);trend=linregress(annual.index,annual.all_hours)
    summary['descriptive_september_trend']={'n_years':len(annual),'slope_f_per_decade':float(trend.slope*10),
                                          'slope_standard_error_f_per_decade':float(trend.stderr*10)}
    plt.figure(figsize=(9,4))
    for c in annual:plt.plot(annual.index,annual[c],marker='o',label=c.replace('_',' '))
    plt.ylabel('September mean (°F)');plt.legend()
    figure('09_recency','Year-to-year weather complicates a short-record warming estimate', 'How should environmental change affect history selection?',scope,
           f'The descriptive September slope is {trend.slope*10:+.2f}°F/decade (slope SE {trend.stderr*10:.2f}); only ten yearly means support it.',
           'Compare five- and ten-year histories on matched September folds. Do not select a start year as an assumed climate break or add an arbitrary warming correction.',
           'Night/afternoon groups are proxies, not observed daily minima/maxima. Ten years cannot isolate global warming, urban development, station changes, or circulation effects.')
    old=target.groupby('local_hour').temperature.mean();recent=target.loc[target.local_year.ge(2016)].groupby('local_hour').temperature.mean()
    table('five_vs_ten_year_target_climatology',pd.DataFrame({'ten_year_f':old,'five_year_f':recent,'difference_f':recent-old}))
    summary['five_vs_ten_mean_abs_hourly_difference_f']=float((recent-old).abs().mean())
    plt.figure(figsize=(9,4));plt.plot(old.index,old,label='2011–2020 (10 years)');plt.plot(recent.index,recent,label='2016–2020 (5 years)');plt.legend();plt.xlabel('Civil hour');plt.ylabel('Sep 17–30 mean (°F)')
    figure('10_history_sensitivity','History length changes the estimated seasonal baseline', 'Does using less history visibly change the baseline?',scope,
           f'Five- vs ten-year target-window hourly means differ by {float((recent-old).abs().mean()):.2f}°F on average in absolute value.',
           'This motivates a backtest comparison; it does not establish which window forecasts better.',
           'This is the 2021-origin comparison. The final 2026 ten-year candidate is 2016–2025; its optimality has not been established.')
    calendar=core.groupby(['local_month','local_hour']).temperature.transform('mean')
    anomaly=core.temperature-calendar;eligible=core.local_month.isin([8,9,10])
    lagrows=[]
    for lag in range(1,337):
        a,n1=pairwise_lag_correlation(core.temperature,lag,eligible);b,n2=pairwise_lag_correlation(anomaly,lag,eligible)
        lagrows.append({'lag_hours':lag,'raw_correlation':a,'calendar_demeaned_correlation':b,'pairs':n1,'demeaned_pairs':n2})
    lagtable=pd.DataFrame(lagrows).set_index('lag_hours');table('elapsed_lag_correlations',lagtable)
    plt.figure(figsize=(9,4));plt.plot(lagtable.index,lagtable.raw_correlation,label='Raw temperature');plt.plot(lagtable.index,lagtable.calendar_demeaned_correlation,label='Month/hour mean removed');plt.axhline(0,color='gray',lw=.6);plt.legend();plt.xlabel('Elapsed lag (hours)');plt.ylabel('Pairwise correlation')
    figure('11_lag_dependence','Recent temperatures are informative, but dependence changes with horizon',
           'How far does recent-weather dependence persist?', 'Core pre-2021-origin history; both ends of each pair must fall in Aug–Oct.',
           f'Calendar-demeaned lag correlations: 24h {lagtable.loc[24,"calendar_demeaned_correlation"]:.2f}; 168h {lagtable.loc[168,"calendar_demeaned_correlation"]:.2f}; 336h {lagtable.loc[336,"calendar_demeaned_correlation"]:.2f}.',
           'At a fixed origin, future lags must be recursively predicted or replaced by origin-known summaries. Never feed observed target-window lags into later forecast hours.',
           'These pairwise descriptive correlations are not forecast skill. Calendar means are calculated in the same training sample; no significance bands assume independent hours.')
    features=['temperature','dew_point_f','relative_humidity_pct','wind_speed_ms','wind_east_ms','wind_north_ms','sea_level_pressure_hpa','precipitation_1h_mm']
    corr=seasonal[features].corr();counts=seasonal[features].notna().astype(int).T.dot(seasonal[features].notna().astype(int))
    table('same_hour_correlations',corr);table('same_hour_pair_counts',counts)
    plt.figure(figsize=(9,7));plt.imshow(corr,cmap='RdBu_r',vmin=-1,vmax=1);plt.colorbar(label='Pearson correlation');plt.xticks(range(len(features)),features,rotation=45,ha='right');plt.yticks(range(len(features)),features)
    for i in range(len(features)):
        for j in range(len(features)):plt.text(j,i,f'{corr.iloc[i,j]:.2f}',ha='center',va='center',fontsize=8,color='black')
    figure('12_feature_relationships','Same-hour weather relationships require an availability check', 'Which variables relate to temperature, and can they be used?',scope+' Aug–Oct only.',
           f'Temperature/dew-point correlation is {corr.loc["temperature","dew_point_f"]:.2f}; temperature/RH {corr.loc["temperature","relative_humidity_pct"]:.2f}.',
           'Use observations only as origin-known summaries. Future weather features must come from frozen pre-origin forecasts; RH is also mathematically related to temperature and dew point.',
           'Associations combine daily/seasonal cycles and weather effects; they are not causal effects or evidence of incremental predictive value.')
    featmissing=pd.DataFrame({'available':seasonal[features+['skyc1']].apply(lambda s: s.notna().sum() if s.name!='skyc1' else s.fillna('').str.strip().ne('').sum()),'expected':len(seasonal)})
    featmissing['missing_pct']=100*(1-featmissing.available/featmissing.expected);table('seasonal_feature_availability',featmissing)
    plt.figure(figsize=(9,4));plt.barh(featmissing.index,featmissing.missing_pct);plt.xlabel('Missing/blank (%)')
    figure('13_feature_availability','Observation fields have different completeness and meanings', 'What cleaning is needed before feature engineering?',scope+' Aug–Oct only.',
           'Availability varies by field; target screening and covariate missingness have different causes.',
           'Fit any imputation only on each training fold; retain trace-rain and variable-wind flags. Do not fill missing wind direction with north or empty cloud layers with an invented cloud amount.',
           'Numeric precipitation blanks may mean no reported amount, not confirmed zero. Some calm METARs have blank parsed speed; preserve originals pending explicit parsing rules.')
    associations=[]
    for lag in [1,6,24,72,168,336]:
        for feature in features[1:]:
            earlier=core[feature].reindex(core.index-pd.Timedelta(hours=lag));earlier.index=core.index
            old_eligible=eligible.reindex(core.index-pd.Timedelta(hours=lag),fill_value=False);old_eligible.index=core.index
            mask=eligible&old_eligible&anomaly.notna()&earlier.notna()
            associations.append({'lag_hours':lag,'feature':feature,'correlation_with_temperature_anomaly':anomaly[mask].corr(earlier[mask]),'pairs':int(mask.sum())})
    assoc=pd.DataFrame(associations);table('lagged_feature_associations',assoc)
    pivot=assoc.pivot(index='feature',columns='lag_hours',values='correlation_with_temperature_anomaly')
    plt.figure(figsize=(9,4));plt.imshow(pivot,cmap='RdBu_r',vmin=-1,vmax=1,aspect='auto');plt.colorbar(label='Correlation with future temperature anomaly');plt.xticks(range(6),pivot.columns);plt.yticks(range(len(pivot)),pivot.index);plt.xlabel('Elapsed hours from input to target')
    figure('14_lagged_features','Observed inputs have a horizon-dependent relationship with temperature',
           'Do same-hour relationships persist for a two-week forecast?', 'Core Aug–Oct pairs; temperature has training month/hour mean removed.',
           'The table reports exact-time associations at 1, 6, 24, 72, 168 and 336 hours, with the number of available pairs.',
           'Test origin-known weather summaries; do not assume same-hour correlations imply 14-day usefulness.',
           'Predictor calendar patterns are not removed. These associations are exploratory; only out-of-sample comparisons can establish useful features.')
    seasonal['anomaly']=seasonal.temperature-seasonal.groupby(['local_month','local_hour']).temperature.transform('mean')
    seasonal['cloud']=seasonal.skyc1.fillna('').str.strip().replace({'':'Unknown'})
    cloudrows=[];plt.figure(figsize=(10,4))
    for label,hours,offset,color in [('Night 00–06',range(0,7),-.17,'#486d99'),('Afternoon 12–18',range(12,19),.17,'#c18b43')]:
        c=seasonal.loc[seasonal.local_hour.isin(hours)].groupby('cloud').anomaly.agg(['mean','count'])
        c['period']=label;cloudrows.append(c.reset_index())
    cloud=pd.concat(cloudrows);cats=['CLR','FEW','SCT','BKN','OVC','VV','Unknown']
    for label,offset,color in [('Night 00–06',-.17,'#486d99'),('Afternoon 12–18',.17,'#c18b43')]:
        c=cloud.loc[cloud.period.eq(label)].set_index('cloud').reindex(cats)
        plt.bar(np.arange(len(cats))+offset,c['mean'],width=.32,label=label,color=color)
    table('cloud_temperature_anomalies',cloud);plt.xticks(range(len(cats)),cats);plt.ylabel('Month/hour-demeaned temperature (°F)');plt.axhline(0,color='gray');plt.legend()
    figure('15_cloud_regimes','Cloud categories accompany different daytime and nighttime regimes',
           'Should clouds be treated as a simple ordered numeric feature?',scope+' Aug–Oct only; first reported cloud layer.',
           'Mean temperature departures differ by cloud category and time of day; category sample counts are supplied.',
           'If used, encode observed categories explicitly; future cloud features must be forecast values, with their own representation.',
           'The first layer does not measure total cloud cover. Weather regimes confound associations, and categories with small counts are unstable.')
    precision=(core.temperature_f-core.metar_temperature_f).dropna();table('target_precision_difference',precision.describe().to_frame('iem_minus_metar_t_f'))
    archive=core.loc[core.noaa_temperature_crosscheck_present & core.temperature_f.notna()].copy()
    quality=pd.DataFrame({'count':archive.groupby('noaa_temperature_quality_code').size(),
                          'quarantined':archive.groupby('noaa_temperature_quality_code').temperature_archive_review_flag.sum()})
    table('core_noaa_quality_codes',quality)
    plt.figure(figsize=(9,4));plt.hist(precision,bins=50);plt.xlabel('IEM temperature − parsed METAR T-group (°F)');plt.ylabel('Reports')
    figure('16_source_precision','Two archives verify the same observations; precision is a separate issue',
           'Do archive agreement and displayed precision justify treating all values as exact?', 'Core pre-2021-origin reports; paired values only.',
           f'{len(precision):,} IEM/T-group pairs; median absolute difference {precision.abs().median():.3f}°F; {int(core.temperature_archive_review_flag.sum())} core targets are quarantined.',
           'Keep raw values, quality codes, provenance and alternate precision. Resolve target definitions before any final scoring.',
           'IEM and NOAA share airport observations and are not independent sensors. Parsed T-group temperature must never be used as a predictor of the same temperature target.')
    extremes=seasonal.nsmallest(10,'temperature')[['time','observed_at','temperature','metar']]
    extremes=pd.concat([extremes.assign(tail='low'),seasonal.nlargest(10,'temperature')[['time','observed_at','temperature','metar']].assign(tail='high')]);table('training_season_extreme_reports',extremes)
    florence=core.loc[core.time.between('2018-09-10T04:00Z','2018-09-20T03:00Z')]
    fig,ax=plt.subplots(2,1,figsize=(10,5),sharex=True);ax[0].plot(florence.time,florence.temperature);ax[0].set_ylabel('Temperature (°F)');ax[1].plot(florence.time,florence.sea_level_pressure_hpa,color='#7d6094');ax[1].set_ylabel('Sea-level pressure (hPa)')
    import matplotlib.dates as mdates
    ax[1].xaxis.set_major_locator(mdates.DayLocator(interval=2));ax[1].xaxis.set_major_formatter(mdates.DateFormatter('%b %d',tz=NY))
    figure('17_event_context','A September 2018 event illustrates a changing weather regime',
           'Should unusual weather be removed as an outlier?', 'September 10–19, 2018, training history surrounding Hurricane Florence.',
           'Temperature and pressure evolve together across this event; unusually persistent weather is part of the forecasting problem.',
           'Retain physically plausible extremes and events. Flag source errors separately from rare weather.',
           'This plot does not attribute every fluctuation to the hurricane, and hourly samples are not true continuous extrema.')
    # Optional decomposition on a genuinely contiguous observed block, no gap filling.
    from statsmodels.tsa.seasonal import STL
    from statsmodels.tsa.stattools import pacf
    block=core.loc[core.local_year.eq(2020)&core.local_month.isin([8,9,10])]
    groups=block.temperature.notna().ne(block.temperature.notna().shift()).cumsum()
    runs=[b for _,b in block.loc[block.temperature.notna()].groupby(groups.loc[block.temperature.notna()])]
    longest=max(runs,key=len)
    if len(longest)>168:
        segment=longest.temperature
        decomposition=STL(segment,period=24,seasonal=13,trend=169,robust=True).fit()
        dec=pd.DataFrame({'observed':segment,'daily_component':decomposition.seasonal,'smooth_trend':decomposition.trend,'remainder':decomposition.resid});table('contiguous_daily_decomposition',dec)
        fig,axes=plt.subplots(4,1,figsize=(10,7),sharex=True)
        for ax,c in zip(axes,dec):ax.plot(dec.index,dec[c],lw=.7);ax.set_ylabel(c.replace('_','\n')+'\n(°F)',fontsize=8)
        figure('18_contiguous_decomposition','A continuous training segment separates daily cycle and slower change',
               'Can daily structure be separated without filling gaps?',f'Longest gap-free Aug–Oct 2020 run: {segment.index.min()} to {segment.index.max()}; {len(segment)} hours.',
               'STL separates a repeating 24-hour component, a smooth trend, and residual weather variation.',
               'This supports explicit daily-cycle features; it is a descriptive diagnostic, not a fitted forecast.',
               'The two-sided smoother is training-only. One segment and a chosen 24-hour period do not establish the optimal model. DST is handled in elapsed UTC hours.')
        p=pacf(decomposition.resid,nlags=48,method='ywm');table('contiguous_residual_pacf',pd.DataFrame({'lag_hours':range(49),'partial_correlation':p}).set_index('lag_hours'))
        plt.figure(figsize=(9,3.5));plt.stem(range(1,49),p[1:]);plt.xlabel('Elapsed lag (hours)');plt.ylabel('Residual partial correlation')
        figure('19_residual_pacf','Residual dependence remains after descriptive decomposition', 'Does removing a daily cycle make hours independent?',f'Same {len(segment)}-hour gap-free 2020 training segment.',
               'The PACF reports remaining short-lag dependence conditional on intermediate lags.',
               'Use time-respecting validation and weather-event/year-level uncertainty summaries.',
               'This segment is not a model-selection test. No confidence bands are shown because iid-hour assumptions are inappropriate.')
    context=current_context_scope(df)
    ref=full.groupby(['local_month','local_day','local_hour']).temperature.mean()
    lookup=pd.MultiIndex.from_frame(context[['local_month','local_day','local_hour']]);reference=ref.reindex(lookup).to_numpy()
    context=context.assign(training_calendar_reference_f=reference,anomaly_f=context.temperature-reference)
    table('2026_preorigin_context',context[['time','observed_at','temperature','training_calendar_reference_f','anomaly_f']])
    summary['preorigin_2026']={'hours':len(context),'usable':int(context.temperature.notna().sum()),'mean_anomaly_f':float(context.anomaly_f.mean())}
    plt.figure(figsize=(10,4));cd=context.set_index('time')[['temperature','training_calendar_reference_f']].resample('D').mean()
    plt.plot(cd.index,cd.temperature,label='2026 observed daily mean');plt.plot(cd.index,cd.training_calendar_reference_f,label='2011–2020 calendar reference');plt.ylabel('Temperature (°F)');plt.legend()
    figure('20_2026_known_context','Weather known before the final forecast origin', 'What does the latest permissible station history look like?', 'August 1–September 16, 2026 only; separate from the initial model-design EDA.',
           f'{len(context):,} known-hour slots; mean departure from the 2011–2020 calendar/hour reference is {context.anomaly_f.mean():+.2f}°F.',
           'Origin-known recent-weather summaries are candidates for later models.',
           'A few weeks of weather are not evidence of a climate shift; no September 17–30, 2026 observations were accessed.')
    final=pd.read_csv(root/'data/pre_eda/prepared/gfs_20260916_18Z_target_forecast_inputs.csv')
    normals=pd.read_csv(root/'data/pre_eda/prepared/target_336_hour_index_and_normals.csv')
    vt=pd.to_datetime(final.valid_time_utc,utc=True)
    assert len(final)==336 and vt.is_unique and vt.min()==FINAL_ORIGIN
    assert vt.max()==FINAL_ORIGIN+pd.Timedelta(hours=335)
    assert pd.to_datetime(final.model_initialization_utc,utc=True).lt(FINAL_ORIGIN).all()
    assert final.temperature_2m.notna().all() and normals.normal_temperature_f.notna().all()
    table('final_forecast_input_summary',final.select_dtypes('number').describe())
    plt.figure(figsize=(10,4));plt.plot(vt,final.temperature_2m,label='Frozen GFS Sep 16 18Z run');plt.plot(vt,normals.normal_temperature_f,label='1991–2020 hourly normal');plt.ylabel('Temperature (°F)');plt.legend()
    figure('21_frozen_forecast_input','A complete pre-origin GFS trajectory covers the required 336 hours',
           'Do the selected forecast and climatology sources cover every required hour?', 'Forecast inputs for Sep 17 00:00–Sep 30 23:00 Raleigh civil time; no final observed outcomes.',
           f'All 336 GFS temperature values and 336 normal lookups are present; {int(final.api_hourly_interpolation_after_120h.sum())} GFS target slots fall after native hourly resolution ends.',
           'This is a candidate forecast input/baseline, not the project prediction. Preserve issuance, lead time and interpolation flags.',
           'GFS is gridded and one forecast trajectory supplies no calibrated uncertainty. Normals use local standard time (UTC−5), correctly offset from September EDT (UTC−4). Routine-report :51 scoring still needs agreed alignment.')
    pairs=gfs_calibration_pairs(root,df);table('gfs_calibration_only_routine_report_pairs',pairs)
    byday=pairs.groupby('day').apply(metric_summary,include_groups=False);byrun=pairs.groupby('origin_utc').apply(metric_summary,include_groups=False)
    table('gfs_calibration_metrics_by_day',byday);table('gfs_calibration_metrics_by_origin',byrun)
    metrics=metric_summary(pairs);summary['gfs_exploratory_benchmark']={k:float(v) for k,v in metrics.items()}
    summary['gfs_exploratory_benchmark'].update({'origins':len(byrun),'unique_scored_report_times':int(pairs.loc[pairs.error_f.notna(),'actual_report_utc'].nunique()),'not_project_model_performance':True})
    plt.figure(figsize=(9,4));plt.plot(byday.index,byday.mae_f,marker='o',label='MAE');plt.plot(byday.index,byday.rmse_f,marker='o',label='RMSE');plt.plot(byday.index,byday.bias_f,marker='o',label='Bias (prediction−observation)');plt.axhline(0,color='gray',lw=.6);plt.xlabel('Forecast day from origin');plt.ylabel('Error (°F)');plt.legend()
    figure('22_gfs_calibration_diagnostic','Frozen GFS error varies across the two-week horizon',
           'Is raw forecast guidance equally accurate at every lead?', 'Calibration-only April 2–July 23, 2026 initializations; July 30 and August confirmation runs excluded.',
           f'{len(byrun)} origins; {int(metrics.scored_pairs):,} scored forecast/report pairs. Pooled MAE {metrics.mae_f:.2f}°F, RMSE {metrics.rmse_f:.2f}°F, bias {metrics.bias_f:+.2f}°F.',
           'Consider lead-dependent calibration later, and compare candidates on the same origins and observation mask. This analysis fits no correction.',
           'An exploratory routine-report benchmark: interpolate the same frozen run to each actual :51 report timestamp. Weekly valid windows overlap, so pairs are not independent. Spring/summer errors are not September or final-project scores. Historical API publication times were not individually logged.')
    table('gfs_raw_fields_completeness',pd.read_csv(root/'data/pre_eda/prepared/gfs_2026_historical_fixed_run_forecasts.csv').isna().sum().to_frame('missing_count'))
    table('seasonal_weather_field_distributions',seasonal[features[1:]].describe(percentiles=[.01,.1,.5,.9,.99]).T)
    seasonal['rain_regime']=np.select([seasonal.precipitation_1h_mm.gt(0),seasonal.precipitation_trace,
                                      seasonal.precipitation_1h_mm.eq(0)],
                                     ['Measured positive','Trace','Explicit numeric zero'],default='No numeric amount')
    rain=seasonal.groupby('rain_regime').agg(hours=('temperature','size'),usable_temperature=('anomaly','count'),
                                            mean_temperature_departure_f=('anomaly','mean'))
    table('rain_regime_associations',rain)
    plt.figure(figsize=(9,4));plt.barh(rain.index,rain.mean_temperature_departure_f);plt.axvline(0,color='gray');plt.xlabel('Month/hour-demeaned mean temperature (°F)')
    figure('23_rain_regimes','Trace rain, explicit zero and missing amounts have different meanings',
           'Can precipitation be reduced to a simple missing-equals-zero rule?',scope+' Aug–Oct only.',
           'The table distinguishes positive measured precipitation, trace, explicit numeric zero, and no numeric amount, with counts and temperature associations.',
           'Retain trace and missing indicators; use rainfall as an origin-known summary or forecast input only after its reporting convention is explicit.',
           'These are contemporaneous associations, not a causal rain effect or a forecast test. A missing numeric amount does not establish dry weather.')
    cross=pd.read_csv(root/'data/pre_eda/reports/noaa_2011_2025_exact_timestamp_crosscheck.csv',low_memory=False)
    cross=cross.loc[pd.to_datetime(cross.observation_time_utc,utc=True).lt(EDA_ORIGIN)].copy()
    source_summary={'paired_reports':len(cross),'requires_review':int(cross.requires_review.sum()),
                    'source_quality_failures':int(cross.source_quality_failure.sum()),
                    'temperature_disagreements':int(cross.source_temperature_disagreement.sum()),
                    'whole_celsius_rounding_consistent':int(cross.whole_celsius_precision_consistent.sum()),
                    'median_absolute_difference_f':float(cross.difference_f.abs().median())}
    summary['core_archive_agreement']=source_summary
    table('core_archive_agreement_summary',pd.Series(source_summary).to_frame('value'))
    table('core_archive_difference_distribution',cross[['difference_f','precision_difference_f']].describe(percentiles=[.01,.5,.99]))
    plt.figure(figsize=(9,4));plt.hist(cross.loc[~cross.requires_review,'difference_f'].dropna(),bins=np.arange(-1.02,1.03,.04));plt.xlabel('IEM − NOAA temperature (°F), non-quarantined pairs');plt.ylabel('Matched reports')
    figure('24_archive_agreement','Exact-timestamp archive comparisons separate rounding from disagreements',
           'How consistent is the airport temperature target across the two archives?', 'Matched IEM/NOAA reports strictly before the first September 2021 origin.',
           f'{len(cross):,} matched reports; median absolute archive difference {source_summary["median_absolute_difference_f"]:.3f}°F; {source_summary["requires_review"]} require review.',
           'Preserve source codes and match actual timestamps. Review disagreements instead of silently averaging archives or assuming displayed precision is accuracy.',
           'Histogram omits quarantined pairs but their counts are reported. Both archives derive from the same station; later archive revisions cannot be proven to match what was distributed historically.')
    # A source-level coverage audit uses metadata/completeness, never held-out outcomes.
    summary['scope_guards']={'final_outcomes_accessed':False,'2021_2025_test_outcomes_in_core_eda':False,
                            'august_gfs_confirmation_errors_examined':False,'imputation_used':False,
                            'final_models_fitted':False,'figures':len(sections)}
    (out/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    (out/'figure_explanations.json').write_text(json.dumps(sections,indent=2)+'\n')
    intro='''# RDU exploratory analysis: working notes, not the graded writeup

The goal is a **single fixed-origin forecast of 336 hourly RDU temperatures**, issued at September 17, 2026, 00:00 Raleigh civil time, covering September 17–30. September is **EDT (UTC−4)**, not fixed EST. The cutoff is September 17 04:00 UTC; the last required label is October 1 03:00 UTC. No observations from the final window are loaded. Forecast values valid in that window are permitted only when from a pre-cutoff issuance.

The deck permits any pre-origin inputs and requires linear regression plus at least one other model. This EDA prepares those decisions; neither required predictive model nor final predictions have been produced. The deck says the graded writing and slides must be the student's own. These are transparent working notes and evidence for that work.

**Target-definition limitation:** most routine reports occur at :51. The current target is the report provisionally assigned to its clock-hour label, not a measurement exactly on the hour or an hourly average. The deck does not settle that distinction or specify units. Resolve it with the instructor before scoring; all current tables explicitly use °F. Final forecast inputs are clock-hour values, so alignment must follow the agreed definition.

**Scopes:** Main model-design EDA stops before the first September 2021 development origin, and full-year comparisons use 2011–2020 only. Historical September 2021–2023 development and 2024–2025 confirmation outcomes remain outside that EDA. A separate 2026 section describes observations already known before the final origin. GFS diagnostics use April–July calibration runs only; August confirmation outcomes remain untouched. General preparation QC can identify missingness/source conflicts in the reserved periods, but does not select a model from their weather patterns.

**Sources and coverage:** IEM routine RDU METAR observations supply the airport target and observed covariates; NOAA GHCNh cross-checks exact timestamps and quality codes through 2025, using the same underlying airport reports. This is archive verification, not independent sensor replication. The 1991–2020 NOAA hourly normals are a fixed climatology benchmark, available from 2021 and mapped using local standard time. Open-Meteo's explicitly frozen GFS single runs supply future weather guidance and a separate 2026 calibration dataset. The full reasoning, discarded alternatives, station history and environmental context are in [DATA_DECISIONS](../../docs/DATA_DECISIONS.md); provenance and original acquisition code are in the data snapshots.

**History and season choice:** Extract continuous all-month observations from 2011 to the exclusive 2026 cutoff. 2011 is needed to test a ten-year history at the 2021 origin; it is not the proposed start of the final fit. The final initial candidate is Aug–Oct 2016–2025 plus Aug 1–Sep 16, 2026, with a five-year alternative and September-only/all-month alternatives tested later. Ten years offer more weather episodes; five years may better represent the recent climate but estimate rare situations less reliably. Aug–Oct matches the autumn transition better than pooling all seasons without adjustment, while providing more examples than September alone. **EDA does not prove this is optimal:** matched-origin September forecasting errors must choose the final configuration.

**Environmental reasoning:** NOAA station history places ASOS commissioning in February 1996 and records no subsequent site move since commissioning; older rain-gauge/shield changes and a 2018 obstruction do not establish a temperature break at 2016. Metadata corrections are not automatically relocations. Regional warming motivates recency comparisons, especially nights; ten annual observations cannot attribute a trend to warming, urbanization, instrument change, or ENSO. Real weather extremes and Florence-era observations stay in the sample unless separately supported quality evidence requires quarantine. No arbitrary warming offset is applied.

**Preparation and feature rules:** Missing values and disputed targets stay flagged; no temperature interpolation/imputation is performed. UTC keeps elapsed lags correct across DST and gaps; local time defines calendar features. Wind direction is circular and represented as components where measured speed/direction permit; measured calm is zero, unknown direction remains unknown. Trace precipitation is retained separately. Blank higher cloud layers do not mean sensor failure. Same-hour METAR temperature is another representation of the target and is prohibited as a predictor. Future actual dew point, humidity, clouds, pressure, rain, wind, and future temperature lags are prohibited; use origin-known summaries or frozen forecast covariates instead. Any later imputation, scaling, feature selection or calibration is fitted inside each training fold.

**Evaluation contract for the next phase:** Simulate one 336-hour forecast at each September origin. Primary MAE, secondary RMSE and signed bias, all in °F, reported with scored counts, per year/day and days 1–3, 4–7, 8–14/day/night. Compare identical masks. Report baseline errors and skill relative to climatology/persistence where appropriate. Do not use random hourly splits, training R², or temperature MAPE to claim forecast quality. Weekly GFS windows overlap; use per-origin summaries and explicit overlap when quantifying uncertainty. GFS 2026 calibration results and station-only 2021–2025 errors are different evaluation cohorts and cannot rank models against each other without matched origins.

The diagnostic methods follow [Forecasting: Principles and Practice on exploratory graphics](https://otexts.com/fpp3/graphics.html), [autocorrelation](https://otexts.com/fpp3/acf.html), and [rolling-origin evaluation](https://otexts.com/fpp3/tscv.html). NOAA documents the normals' [local-standard-time convention](https://www.ncei.noaa.gov/pub/data/cdo/documentation/normals-hourly-1991-2020_documentation.pdf). Figures report weather dispersion rather than unsupported forecast uncertainty.

## Diagnostic findings and their consequences
'''
    md=[intro]
    for s in sections:
        md.append(f'\n### {s["title"]}\n\n**Question:** {s["question"]}\n\n**Data:** {s["scope"]}\n\n![{s["title"]}](figures/{s["name"]}.png)\n\n**Finding:** {s["finding"]}\n\n**Decision/implication:** {s["implication"]}\n\n**Limits:** {s["limitation"]}\n')
    md.append('''
## Completion audit and remaining decisions

EDA covers source agreement/precision, target and covariate missingness, monthly and hourly seasonality, the exact September fortnight, autumn transition, annual/recency sensitivity, dependence and lagged relationships, weather covariates, cloud regimes, extremes/event context, continuous-segment decomposition, latest permissible context, normals and frozen forecast coverage, and calibration-only GFS diagnostics. Each figure has a scope, explanation and limitation; numeric tables and code accompany it.

Before model scoring: confirm the instructor's hourly target and units; decide and document treatment of source disagreements, especially two September 2024 targets; apply that same scoring mask to every comparison. A 2025 fortnight also has two unavailable targets. These exclusions are audit findings, not model-selected deletions. Compare five-/ten-year and seasonal/all-month candidates using September 2021–2023 development folds, then lock choices before 2024–2025 confirmation. Frozen GFS correction candidates need their separate April–July/August chronology; no August outcomes were used here. Later fit linear regression and another model, create the final 336 predictions, and complete the student's own presentation/writeup. No result in this report claims those tasks are complete.
''')
    text='\n'.join(md);(out/'EDA_REPORT.md').write_text(text)
    import markdown
    rendered=markdown.markdown(text,extensions=['tables','fenced_code'])
    page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>RDU EDA working report</title><style>body{max-width:1000px;margin:40px auto;padding:0 24px;font:17px/1.6 system-ui;color:#182a37}img{max-width:100%;height:auto}h1,h2,h3{line-height:1.25}h3{margin-top:52px}a{color:#126787}table{border-collapse:collapse}td,th{padding:8px;border:1px solid #ddd}@media print{h3{break-before:page}img{max-height:400px}}</style>'+rendered+'</html>'
    (out/'EDA_REPORT.html').write_text(page)
    return summary, sections
