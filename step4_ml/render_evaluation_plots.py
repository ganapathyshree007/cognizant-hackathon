"""Render calibration and confusion-matrix figures from benchmark CSV outputs."""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

source=Path("step4_ml_output/evaluation"); plot_dir=source/"plots"; plot_dir.mkdir(exist_ok=True)
cal=pd.read_csv(source/"calibration_test.csv")
fig,ax=plt.subplots(figsize=(6,5))
for name,group in cal.groupby("model"):
    ax.plot(group.mean_predicted_probability,group.observed_positive_rate,marker="o",label=name)
ax.plot([0,1],[0,1],"--",color="gray",label="perfect calibration"); ax.set(xlabel="Mean predicted probability",ylabel="Observed repeat-ED rate",title="Test-set calibration (8 quantile bins)"); ax.legend(); fig.tight_layout(); fig.savefig(plot_dir/"calibration_test.png",dpi=160); plt.close(fig)
metrics=pd.read_csv(source/"full_metrics_by_split.csv").query("split == 'test'")
fig,axes=plt.subplots(1,len(metrics),figsize=(10,3.2))
for ax,(_,row) in zip(axes,metrics.iterrows()):
    matrix=[[row.tn,row.fp],[row.fn,row.tp]]; im=ax.imshow(matrix,cmap="Blues")
    for i in range(2):
        for j in range(2): ax.text(j,i,int(matrix[i][j]),ha="center",va="center")
    ax.set(title=row.model,xticks=[0,1],xticklabels=["Pred no","Pred yes"],yticks=[0,1],yticklabels=["Actual no","Actual yes"])
fig.suptitle("Test-set confusion matrices at threshold 0.50"); fig.tight_layout(); fig.savefig(plot_dir/"confusion_matrices_test.png",dpi=160); plt.close(fig)
