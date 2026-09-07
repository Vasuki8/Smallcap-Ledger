"""Date-matched returns. Missing distribution or benchmark history is never estimated."""
from __future__ import annotations
import bisect
import calendar
import math
from datetime import date, timedelta


def shift_years(d, years):
    return d.replace(year=d.year-years, day=min(d.day, calendar.monthrange(d.year-years, d.month)[1]))


def shift_months(d, months):
    year,month=divmod(d.year*12+d.month-1-months,12)
    return date(year,month+1,min(d.day,calendar.monthrange(year,month+1)[1]))


def performance(points):
    if not points:
        return {"returns": {}, "drawdown": [], "rolling": [], "max_drawdown": None, "volatility": None}
    points = sorted(points)
    dates = [date.fromisoformat(p[0]) for p in points]
    values = [p[1] for p in points]
    end = dates[-1]
    returns = {}
    targets = {"1M":shift_months(end,1), "3M":shift_months(end,3), "6M":shift_months(end,6),
               "1Y":shift_years(end,1), "3Y":shift_years(end,3), "5Y":shift_years(end,5), "10Y":shift_years(end,10)}
    for label,target in targets.items():
        i=bisect.bisect_right(dates,target)-1
        if i<0 or (target-dates[i]).days>7:
            returns[label]=None
            continue
        days=(end-dates[i]).days
        result=(values[-1]/values[i])**(365.25/days)-1 if label.endswith("Y") else values[-1]/values[i]-1
        returns[label]={"value":result*100,"start":dates[i].isoformat(),"end":end.isoformat(),"annualized":label.endswith("Y")}
    days=(end-dates[0]).days
    returns["Since start"]={"value":((values[-1]/values[0])**(365.25/days)-1 if days>=365 else values[-1]/values[0]-1)*100,
                            "start":points[0][0],"end":end.isoformat(),"annualized":days>=365} if days>0 else None
    peak=values[0]
    draw=[]
    changes=[]
    rolling=[]
    for i,(day,val) in enumerate(points):
        peak=max(peak,val)
        draw.append([day,(val/peak-1)*100])
        if i and (dates[i]-dates[i-1]).days<=7:
            changes.append(math.log(val/values[i-1]))
        if i%5==0 or i==len(points)-1:
            j=bisect.bisect_right(dates,shift_years(dates[i],3))-1
            if j>=0 and (shift_years(dates[i],3)-dates[j]).days<=7:
                rolling.append([day,((val/values[j])**(365.25/(dates[i]-dates[j]).days)-1)*100])
    vol=None
    if len(changes)>=30:
        avg=sum(changes)/len(changes)
        vol=(sum((x-avg)**2 for x in changes)/(len(changes)-1)*252)**0.5*100
    gaps=[{"from":points[i-1][0],"to":points[i][0],"days":(dates[i]-dates[i-1]).days} for i in range(1,len(points)) if (dates[i]-dates[i-1]).days>7]
    return {"returns":returns,"drawdown":draw,"rolling":rolling,"max_drawdown":min(p[1] for p in draw),"volatility":vol,"gaps":gaps}


def aligned(fund, benchmark):
    b=dict(benchmark)
    common=[(d,v,b[d]) for d,v in fund if d in b]
    if len(common)<2:
        return []
    f0,b0=common[0][1:]
    return [[d,v/f0*100,bv/b0*100] for d,v,bv in common]


def reinvested(nav, distributions, start, end):
    """Only use when a user-confirmed complete distribution window covers the series."""
    points=[p for p in nav if start<=p[0]<=end]
    if not points:
        return []
    events=sorted(distributions,key=lambda x:x["ex_date"])
    idx=0
    units=1.0
    output=[]
    for day,value in points:
        while idx<len(events) and events[idx]["ex_date"]<=day:
            event=events[idx]
            if event["ex_date"]>points[0][0]:
                units*=1+event["amount"]/event["reinvestment_nav"]
            idx+=1
        output.append([day,value*units])
    return output


def sip(points, monthly):
    if len(points)<2:
        return None
    payments=[]
    month=None
    units=0
    for day,value in points:
        if day[:7]!=month:
            month=day[:7]
            payments.append((date.fromisoformat(day),-monthly))
            units+=monthly/value
    end=date.fromisoformat(points[-1][0])
    final=units*points[-1][1]
    flows=payments+[(end,final)]
    first=payments[0][0]
    def npv(r):
        return sum(v*math.exp(-math.log1p(r)*((d-first).days/365.25)) for d,v in flows)
    low,high=-0.999,10.0
    annual=None
    if end>first and npv(low)*npv(high)<0:
        for _ in range(100):
            mid=(low+high)/2
            if npv(mid)>0: low=mid
            else: high=mid
        annual=(low+high)/2*100
    return {"invested":len(payments)*monthly,"value":final,"gain":final-len(payments)*monthly,"xirr":annual,
            "payments":len(payments),"start":points[0][0],"end":points[-1][0],"convention":"First available NAV of each month in the selected range; no tax or exit-load adjustment."}
