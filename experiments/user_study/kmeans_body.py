"""Scalar Lloyd implementation embedded in the prepared WAFFLE body."""
def cluster_score(points,k):
    centers=[list(p) for p in points[:k]]
    for _ in range(50):
        totals=[[0.0,0.0,0] for _ in centers]
        for x,y in points:
            selected=min(range(k),key=lambda i:(x-centers[i][0])**2+(y-centers[i][1])**2)
            totals[selected][0]+=x;totals[selected][1]+=y;totals[selected][2]+=1
        movement=0.0
        for i,(x,y,n) in enumerate(totals):
            if n:
                a,b=x/n,y/n;movement=max(movement,abs(a-centers[i][0]),abs(b-centers[i][1]));centers[i]=[a,b]
        if movement<1e-10:break
    return -sum(min((x-a)**2+(y-b)**2 for a,b in centers) for x,y in points)
