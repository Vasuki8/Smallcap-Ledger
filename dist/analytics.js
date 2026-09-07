/* Identical date and return conventions to tracker/analytics.py. No network or DOM. */
(function(root){
  'use strict';
  const day=s=>Date.parse(s+'T00:00:00Z')/86400000;
  const iso=d=>d.toISOString().slice(0,10);
  function shift(s,months){const d=new Date(s+'T00:00:00Z'),wanted=d.getUTCDate();d.setUTCDate(1);d.setUTCMonth(d.getUTCMonth()-months);const last=new Date(Date.UTC(d.getUTCFullYear(),d.getUTCMonth()+1,0)).getUTCDate();d.setUTCDate(Math.min(wanted,last));return iso(d);}
  function prior(points,target){let lo=0,hi=points.length;while(lo<hi){const m=(lo+hi)>>1;if(points[m][0]<=target)lo=m+1;else hi=m;}return lo-1;}
  function performance(points){
    if(!points.length)return {returns:{},drawdown:[],rolling:[],max_drawdown:null,volatility:null,gaps:[]};
    const end=points.at(-1)[0],last=points.at(-1)[1],returns={},drawdown=[],rolling=[],changes=[],gaps=[];
    for(const [label,months] of Object.entries({'1M':1,'3M':3,'6M':6,'1Y':12,'3Y':36,'5Y':60,'10Y':120})){
      const target=shift(end,months),i=prior(points,target),annualized=label.endsWith('Y');
      if(i<0||day(target)-day(points[i][0])>7){returns[label]=null;continue;}
      const days=day(end)-day(points[i][0]);returns[label]={value:100*(annualized?Math.pow(last/points[i][1],365.25/days)-1:last/points[i][1]-1),start:points[i][0],end,annualized};
    }
    const days=day(end)-day(points[0][0]);returns['Since start']=days>0?{value:100*(days>=365?Math.pow(last/points[0][1],365.25/days)-1:last/points[0][1]-1),start:points[0][0],end,annualized:days>=365}:null;
    let peak=points[0][1];
    points.forEach(([d,v],i)=>{peak=Math.max(peak,v);drawdown.push([d,(v/peak-1)*100]);if(i){const gap=day(d)-day(points[i-1][0]);if(gap<=7)changes.push(Math.log(v/points[i-1][1]));else gaps.push({from:points[i-1][0],to:d,days:gap});}
      if(i%5===0||i===points.length-1){const target=shift(d,36),j=prior(points,target);if(j>=0&&day(target)-day(points[j][0])<=7)rolling.push([d,(Math.pow(v/points[j][1],365.25/(day(d)-day(points[j][0])))-1)*100]);}});
    let volatility=null;if(changes.length>=30){const mean=changes.reduce((a,b)=>a+b,0)/changes.length;volatility=Math.sqrt(changes.reduce((a,b)=>a+(b-mean)**2,0)/(changes.length-1)*252)*100;}
    return {returns,drawdown,rolling,max_drawdown:Math.min(...drawdown.map(p=>p[1])),volatility,gaps};
  }
  function aligned(fund,benchmark){const map=new Map(benchmark),common=fund.filter(p=>map.has(p[0]));if(common.length<2)return [];const f0=common[0][1],b0=map.get(common[0][0]);return common.map(([d,v])=>[d,v/f0*100,map.get(d)/b0*100]);}
  function reinvested(nav,events,start,end){const points=nav.filter(p=>p[0]>=start&&p[0]<=end),sorted=[...events].sort((a,b)=>a.ex_date.localeCompare(b.ex_date));if(!points.length)return [];let i=0,units=1;return points.map(([d,v])=>{while(i<sorted.length&&sorted[i].ex_date<=d){const e=sorted[i++];if(e.ex_date>points[0][0])units*=1+e.amount/e.reinvestment_nav;}return [d,v*units];});}
  function sip(points,monthly){if(points.length<2)return null;const payments=[];let month=null,units=0;for(const [d,v] of points){if(d.slice(0,7)!==month){month=d.slice(0,7);payments.push([d,-monthly]);units+=monthly/v;}}
    const end=points.at(-1)[0],value=units*points.at(-1)[1],first=payments[0][0],flows=[...payments,[end,value]];
    const npv=r=>flows.reduce((a,[d,v])=>a+v*Math.exp(-Math.log1p(r)*(day(d)-day(first))/365.25),0);let low=-.999,high=10,xirr=null;
    if(end>first&&npv(low)*npv(high)<0){for(let i=0;i<100;i++){const mid=(low+high)/2;if(npv(mid)>0)low=mid;else high=mid;}xirr=(low+high)/2*100;}
    return {invested:payments.length*monthly,value,gain:value-payments.length*monthly,xirr,payments:payments.length,start:points[0][0],end,convention:'First available NAV of each month in the selected range; no tax or exit-load adjustment.'};
  }
  function response(fund,nav,benchmark,query={}){
    const {start,end}=query,monthly=Number(query.monthly||10000),coverage=fund.distribution_coverage;
    for(const value of [start,end])if(value&&(!/^\d{4}-\d{2}-\d{2}$/.test(value)||!Number.isFinite(day(value))||new Date(value+'T00:00:00Z').toISOString().slice(0,10)!==value))throw Error('Enter a valid date range.');
    if(!Number.isFinite(monthly)||monthly<100||monthly>100000000)throw Error('Monthly SIP must be between ₹100 and ₹10 crore.');
    if(start&&end&&start>end)throw Error('The start date must be before the end date.');
    let total=fund.option==='Growth'?nav:[],method='Growth NAV; fund expenses already reflected. Tax and exit loads excluded.';
    if(fund.option==='IDCW'){method='NAV-only view. IDCW distributions are missing; total-return comparisons and SIP results require a complete distribution history.';if(coverage){total=reinvested(nav,fund.distributions||[],coverage.start,coverage.end);method='Hypothetical reinvested IDCW total return using user-confirmed complete distributions. Tax and exit loads excluded.';}}
    else if(fund.option!=='Growth')method='NAV-only view. Bonus or other unit adjustments are not mapped; adjusted comparisons and SIP results are unavailable.';
    const selected=total.filter(p=>(!start||p[0]>=start)&&(!end||p[0]<=end)),navSelected=nav.filter(p=>(!start||p[0]>=start)&&(!end||p[0]<=end)),bp=benchmark?.data||[],common=aligned(total.filter(p=>!end||p[0]<=end),bp);
    return {nav:navSelected,total_return_series:selected,method,can_total_return:!!selected.length,benchmark:query.benchmark,comparison:aligned(selected,bp),stats:performance(total),range_stats:performance(selected),comparison_stats:{fund:performance(common.map(p=>[p[0],p[1]] )).returns,benchmark:performance(common.map(p=>[p[0],p[2]])).returns},sip:sip(selected,monthly),latest_nav:nav.at(-1)||null,first_nav:nav[0]?.[0],last_nav:nav.at(-1)?.[0],benchmark_source:benchmark?{...benchmark,data:undefined,points:bp.length}:null,distribution_coverage:coverage};
  }
  const api={shift,performance,aligned,reinvested,sip,response};if(typeof module!=='undefined'&&module.exports)module.exports=api;root.SmallcapAnalytics=api;
})(typeof window!=='undefined'?window:globalThis);
