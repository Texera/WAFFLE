"""Independent NumPy reference and small, deterministic study fixtures."""
import csv
import math
from pathlib import Path
import numpy as np

def read_points(path):
    with Path(path).open(newline='',encoding='utf-8') as f:
        return np.array([[float(r['x']),float(r['y'])] for r in csv.DictReader(f)])

def scores(path):
    points=read_points(path); out=[]
    for k in (2,3,4):
        centers=points[:k].copy()
        for _ in range(50):
            labels=((points[:,None,:]-centers[None,:,:])**2).sum(axis=2).argmin(axis=1)
            updated=np.array([points[labels==i].mean(axis=0) if np.any(labels==i) else centers[i] for i in range(k)])
            change=np.max(np.abs(updated-centers)); centers=updated
            if change<1e-10:break
        score=-float(((points[:,None,:]-centers[None,:,:])**2).sum(axis=2).min(axis=1).sum())
        out.append(dict(K=k,score=score))
    return out

def make_data(root,pack):
    root=Path(root); root.mkdir(parents=True,exist_ok=False)
    shift=0 if pack=='A' else 3
    centers=[(0,0),(8,8),(0,8),(8,0)] if pack=='A' else [(2,1),(11,10),(2,10),(11,1)]
    pts=[(x+dx,y+dy) for dx,dy in [(0,0),(.4,-.2),(-.3,.5),(0.2,.3)] for x,y in centers]
    for variant,scale in [('visible',1),('first',.1),('cap',10),('extra',1)]:
        d=root/variant; (d/'sales').mkdir(parents=True)
        with (d/'points.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.writer(f);w.writerow(['x','y']);w.writerows((x*scale,y*scale) for x,y in pts)
        files={'01-jan.csv':[10+shift,30+shift], '02-feb.csv':[40+shift], '03-mar.csv':[5+shift,15+shift,25+shift]}
        if variant=='extra':files['04-apr.csv']=[8+shift,18+shift]
        for name,prices in files.items():
            with (d/'sales'/name).open('w',newline='',encoding='utf-8') as f:
                w=csv.writer(f);w.writerow(['price']);w.writerows([x] for x in prices)
    values=scores(root/'visible/points.csv')
    return dict(pack=pack,target=(values[0]['score']+values[1]['score'])/2,best_K=max(values,key=lambda r:r['score'])['K'])

def expected(data,task,target):
    data=Path(data)
    if task.startswith('files'):
        rows=[]
        for p in sorted((data/'sales').glob('*.csv')):
            with p.open(newline='',encoding='utf-8') as f:values=[float(r['price']) for r in csv.DictReader(f)]
            rows.append(dict(filename=p.name,mean=sum(values)/len(values)))
        return rows[:1] if task=='files-starter' else rows
    rows=scores(data/'points.csv')
    if task=='sweep-starter':return rows[:1]
    if task=='adapt':
        for i,r in enumerate(rows):
            if r['score']>=target:return rows[:i+1]
    return rows

def compare(expected,actual):
    if not isinstance(actual,list) or len(expected)!=len(actual):return False
    for a,b in zip(expected,actual):
        if a.keys()!=b.keys():return False
        for key,value in a.items():
            if isinstance(value,(int,float)):
                if not isinstance(b[key],(int,float)) or not math.isfinite(b[key]) or not math.isclose(value,b[key],rel_tol=1e-9,abs_tol=1e-9):return False
            elif value!=b[key]:return False
    return True

def check_evidence(want,visits,results,exit_code):
    return exit_code==0 and compare(want,visits) and compare(want,results)
