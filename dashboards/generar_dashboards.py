import pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib.gridspec import GridSpec
from pathlib import Path

df = pd.read_csv("Base_energetica_limpia.csv")
det = df[~df.fuente_energia.str.startswith("TOTAL") & (df.tipo_energia != "TOTAL GENERAL")]
AÑOS = sorted(df.año.unique())

def serie(sub, tipo=None, fuentes=None, por_fuente=False):
    d = det[det.subcategoria == sub]
    if tipo: d = d[d.tipo_energia == tipo]
    if fuentes: d = d[d.fuente_energia.isin(fuentes)]
    if por_fuente:
        return d.pivot_table(index="fuente_energia", columns="año", values="valor_miles_TEP", aggfunc="sum").fillna(0)
    return d.groupby("año").valor_miles_TEP.sum().reindex(AÑOS, fill_value=0)

pf = serie("PRODUCCIÓN", "PRIMARIA", por_fuente=True)
prod = pd.DataFrame({"Petróleo": pf.loc["Petróleo"], "Gas natural": pf.loc["Gas Natural de Pozo"]})
prod["Resto"] = pf.sum() - prod.sum(axis=1)
prod_tot = pf.sum()
expo = serie("EXPORTACIÓN Y BUNKER").abs(); impo = serie("IMPORTACIÓN")
saldo = expo - impo
ef = serie("EXPORTACIÓN Y BUNKER", por_fuente=True).abs(); imf = serie("IMPORTACIÓN", por_fuente=True)
idx = ef.index.union(imf.index)
saldo_f = ef.reindex(idx, fill_value=0) - imf.reindex(idx, fill_value=0)
cambio = (saldo_f[2024] - saldo_f[2019])
autoab = prod_tot / serie("OFERTA INTERNA", "PRIMARIA") * 100
transf = det[det.categoria == "CENTROS DE TRANSFORMACIÓN"]
def efic(d):
    return d[d.valor_miles_TEP > 0].valor_miles_TEP.sum() / d[d.valor_miles_TEP < 0].valor_miles_TEP.abs().sum() * 100
ef_c = {n: transf[transf.subcategoria == s].groupby("año").apply(efic) for s, n in
        [("REFINERÍAS", "Refinerías"), ("CENTRALES ELÉCTRICAS - SERVICIO PÚBLICO", "Centrales eléctricas")]}
ef_c["Todos los centros"] = transf.groupby("año").apply(efic)
cg = df[df.tipo_energia == "TOTAL GENERAL"].pivot_table(index="subcategoria", columns="año", values="valor_miles_TEP")
cons = cg.loc["CONSUMO FINAL - TOTAL"]
sect = cg.loc[[s for s in cg.index if s.startswith("CONSUMO FINAL -") and s != "CONSUMO FINAL - TOTAL"]]
sect.index = sect.index.str.replace("CONSUMO FINAL - ", "").str.capitalize()

# ---------- estilo ----------
BG, INK, INK2, GRID = "#fbfaf7", "#1d1d1b", "#5e5d58", "#e6e5e0"
AZ, NA, AQ, GR = "#2a78d6", "#eb6834", "#1baf7a", "#9a9994"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.facecolor": BG, "figure.facecolor": BG,
    "axes.edgecolor": "#c9c8c2", "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "axes.axisbelow": True, "xtick.color": INK2, "ytick.color": INK2,
    "axes.titlesize": 12.5, "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.titlecolor": INK,
    "axes.titlepad": 10})
fmt = lambda v: f"{v:,.0f}".replace(",", ".")

def kpi(ax, valor, titulo, sub):
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor="white", edgecolor=GRID, lw=1.2))
    ax.text(0.06, 0.74, titulo, fontsize=10.5, color=INK2, transform=ax.transAxes)
    ax.text(0.06, 0.36, valor, fontsize=24, fontweight="bold", color=INK, transform=ax.transAxes)
    ax.text(0.06, 0.12, sub, fontsize=9.5, color=INK2, transform=ax.transAxes)

def header(fig, titulo, sub):
    fig.text(0.035, 0.955, titulo, fontsize=21, fontweight="bold", color=INK)
    fig.text(0.035, 0.918, sub, fontsize=12, color=INK2)
    fig.text(0.035, 0.018, "Fuente: Secretaría de Energía – Balance Energético Nacional 2019–2024 · Unidad: miles de TEP · "
             "Análisis: Nahuel Mansilla", fontsize=9, color=INK2)

def end_label(ax, x, y, txt):
    ax.annotate(txt, (x, y), xytext=(7, 0), textcoords="offset points", va="center", fontsize=9.5, color=INK2)

out = Path("dashboards"); out.mkdir(exist_ok=True)

# ===== Dashboard 1: Oferta y comercio =====
fig = plt.figure(figsize=(16, 10))
header(fig, "Argentina pasó de importar a exportar energía",
       "Dashboard 1 · Oferta y comercio exterior · 2019–2024")
gs = GridSpec(3, 4, figure=fig, left=0.05, right=0.975, top=0.885, bottom=0.07, hspace=0.42, wspace=0.28,
              height_ratios=[0.42, 1, 1])
kpi(fig.add_subplot(gs[0, 0]), f"+{fmt(saldo[2024])}", "Saldo comercial 2024", f"en 2019: {fmt(saldo[2019])}")
kpi(fig.add_subplot(gs[0, 1]), f"{expo[2024]/impo[2024]:.1f}x".replace(".", ","), "Exportaciones / importaciones", "en 2019: 0,8x")
kpi(fig.add_subplot(gs[0, 2]), f"+{(prod.loc[2024,'Petróleo']/prod.loc[2019,'Petróleo']-1)*100:.0f}%", "Producción de petróleo", "2019 → 2024")
kpi(fig.add_subplot(gs[0, 3]), f"{autoab[2024]:.1f}%".replace(".", ","), "Autoabastecimiento 2024", "producción / oferta interna")

ax = fig.add_subplot(gs[1, :2])
x = np.arange(len(AÑOS)); w = 0.38
ax.bar(x - w/2, expo, w, color=AZ, label="Exportaciones")
ax.bar(x + w/2, impo, w, color=NA, label="Importaciones")
for i, a in enumerate(AÑOS):
    ax.text(i, max(expo[a], impo[a]) + 500, f"{saldo[a]:+,.0f}".replace(",", "."), ha="center", fontsize=9.5,
            color=INK, fontweight="bold" if saldo[a] > 0 else "normal")
ax.set_xticks(x, AÑOS); ax.set_ylim(0, 20500)
ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: fmt(v)))
ax.set_title("Exportaciones vs. importaciones (número = saldo)")
ax.legend(frameon=False, loc="upper left", fontsize=9.5)

ax = fig.add_subplot(gs[1:, 2:])
c = cambio.copy(); big = c[c.abs() >= 100]
c = pd.concat([big, pd.Series({"Otros": c[c.abs() < 100].sum()})]).sort_values()
CORTOS = {"Gas Distribuido por Redes": "Gas por redes", "Diesel Oil + Gas Oil": "Gasoil", "Kerosene y Aerokerosene": "Kerosene",
          "Energía Nuclear": "Nuclear", "Carbón Mineral": "Carbón", "Gas Natural de Pozo": "Gas de pozo",
          "Energía Eléctrica": "Electricidad", "Motonafta Total": "Motonafta"}
c.index = [CORTOS.get(i, i) for i in c.index]
ax.barh(c.index, c.values, color=[AZ if v > 0 else NA for v in c], height=0.62)
for i, v in enumerate(c.values):
    ax.text(v + (120 if v >= 0 else -120), i, f"{v:+,.0f}".replace(",", "."), va="center",
            ha="left" if v >= 0 else "right", fontsize=9.5, color=INK2)
ax.axvline(0, color="#8a8984", lw=1); ax.grid(axis="y", visible=False)
ax.set_xlim(-2300, 7600); ax.tick_params(axis="y", labelsize=10)
ax.set_title("¿Qué explica el giro? Cambio del saldo 2019 → 2024 por producto")

ax = fig.add_subplot(gs[2, :2])
ind = prod.div(prod.loc[2019]) * 100
for col, color in [("Petróleo", AZ), ("Gas natural", AQ), ("Resto", GR)]:
    ax.plot(AÑOS, ind[col], marker="o", lw=2.2, color=color)
    end_label(ax, 2024, ind.loc[2024, col], f"{col} {ind.loc[2024, col]-100:+.0f}%")
ax.axhline(100, color="#bdbcb6", lw=1, ls="--")
ax.set_xticks(AÑOS); ax.set_xlim(2018.7, 2025.6)
ax.set_title("Producción primaria por fuente (índice 2019 = 100)")
fig.savefig(out / "dashboard_1_oferta_comercio.png", dpi=110)
plt.close(fig)

# ===== Dashboard 2: Transformación y consumo =====
fig = plt.figure(figsize=(16, 10))
header(fig, "La energía extra no se queda en el país: se exporta",
       "Dashboard 2 · Transformación y consumo · 2019–2024")
gs = GridSpec(3, 4, figure=fig, left=0.05, right=0.975, top=0.885, bottom=0.07, hspace=0.42, wspace=0.28,
              height_ratios=[0.42, 1, 1])
kpi(fig.add_subplot(gs[0, 0]), f"+{(prod_tot[2024]/prod_tot[2019]-1)*100:.0f}%", "Producción primaria", "2019 → 2024")
kpi(fig.add_subplot(gs[0, 1]), f"{(cons[2024]/cons[2019]-1)*100:+.0f}%", "Consumo final interno", "2019 → 2024")
kpi(fig.add_subplot(gs[0, 2]), f"+{(expo[2024]/expo[2019]-1)*100:.0f}%", "Exportaciones de energía", "2019 → 2024")
kpi(fig.add_subplot(gs[0, 3]), f"{ef_c['Todos los centros'][2024]:.0f}%", "Eficiencia de transformación", "estable desde 2019 (85%)")

ax = fig.add_subplot(gs[1, :2])
dest = pd.DataFrame({"Exportaciones": expo, "Producción primaria": prod_tot, "Consumo final": cons})
di = dest / dest.loc[2019] * 100
for col, color in [("Exportaciones", AZ), ("Producción primaria", "#3d3d3a"), ("Consumo final", NA)]:
    ax.plot(AÑOS, di[col], marker="o", lw=2.2, color=color)
    end_label(ax, 2024, di.loc[2024, col], f"{col} {di.loc[2024, col]-100:+.0f}%")
ax.axhline(100, color="#bdbcb6", lw=1, ls="--")
ax.set_xticks(AÑOS); ax.set_xlim(2018.7, 2026.0)
ax.set_title("Producción, consumo y exportaciones (índice 2019 = 100)")

ax = fig.add_subplot(gs[1, 2:])
ax.plot(AÑOS, autoab, marker="o", lw=2.2, color=AZ)
ax.axhline(100, color="#8a8984", lw=1, ls="--")
for a, v in autoab.items():
    ax.annotate(f"{v:.1f}%".replace(".", ","), (a, v), xytext=(0, -15 if v < 100 else 9), textcoords="offset points",
                ha="center", fontsize=9.5, color=INK2)
ax.text(2024, 99.0, "100% = produce lo que consume", ha="right", fontsize=9, color=INK2)
ax.set_ylim(97.5, 111); ax.set_xticks(AÑOS)
ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
ax.set_title("Autoabastecimiento: producción primaria / oferta interna")

ax = fig.add_subplot(gs[2, :2])
for col, color, ls in [("Refinerías", AZ, "-"), ("Todos los centros", "#3d3d3a", "--"), ("Centrales eléctricas", NA, "-")]:
    ax.plot(AÑOS, ef_c[col], marker="o", lw=2.2, color=color, ls=ls)
    end_label(ax, 2024, ef_c[col][2024], f"{col} {ef_c[col][2024]:.0f}%")
ax.set_ylim(45, 100); ax.set_xticks(AÑOS); ax.set_xlim(2018.7, 2026.0)
ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
ax.set_title("Eficiencia de transformación (sale / entra)")

ax = fig.add_subplot(gs[2, 2:])
t = pd.DataFrame({"2020": (sect[2020]/sect[2019]-1)*100, "2024": (sect[2024]/sect[2019]-1)*100}).loc[sect[2024].sort_values(ascending=False).index]
y = np.arange(len(t))
ax.barh(y - 0.2, t["2024"], 0.38, color=AZ, label="2019 → 2024")
ax.barh(y + 0.2, t["2020"], 0.38, color=NA, label="2019 → 2020 (pandemia)")
for i, s in enumerate(t.index):
    for dy, col in [(-0.2, "2024"), (0.2, "2020")]:
        v = t.loc[s, col]; lab = f"{v:+.0f}%".replace("-0%", "0%").replace("+0%", "0%")
        ax.text(v + (0.7 if v >= 0 else -0.7), i + dy, lab, va="center", ha="left" if v >= 0 else "right", fontsize=8.5, color=INK2)
ax.set_yticks(y, t.index); ax.invert_yaxis(); ax.axvline(0, color="#8a8984", lw=1)
ax.set_xlim(-32, 22); ax.grid(axis="y", visible=False)
ax.xaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
ax.legend(frameon=False, fontsize=9, loc="upper right")
ax.set_title("Consumo final por sector: variación vs. 2019")
fig.savefig(out / "dashboard_2_transformacion_consumo.png", dpi=110)
plt.close(fig)

# ===== Datos para Tableau =====
with pd.ExcelWriter("datos_tableau_parte2.xlsx") as xw:
    pd.DataFrame({"año": AÑOS, "exportaciones": expo.values, "importaciones": impo.values, "saldo": saldo.values,
                  "tasa_cobertura": (expo/impo).values, "autoabastecimiento_pct": autoab.values,
                  "produccion_primaria": prod_tot.values, "consumo_final": cons.values,
                  "eficiencia_transformacion_pct": ef_c["Todos los centros"].values}).round(2).to_excel(xw, sheet_name="indicadores", index=False)
    com = pd.concat([ef.stack().rename("exportaciones"), imf.stack().rename("importaciones")], axis=1).fillna(0)
    com["saldo"] = com.exportaciones - com.importaciones
    com.reset_index().rename(columns={"fuente_energia": "producto"}).round(2).to_excel(xw, sheet_name="comercio_por_producto", index=False)
    p = prod.copy(); p.index.name = "año"
    p.reset_index().melt("año", var_name="fuente", value_name="produccion").round(2).to_excel(xw, sheet_name="produccion_por_fuente", index=False)
    s = sect.copy(); s.index.name = "sector"
    s.reset_index().melt("sector", var_name="año", value_name="consumo").round(2).to_excel(xw, sheet_name="consumo_por_sector", index=False)
    e = pd.DataFrame(ef_c); e.index.name = "año"
    e.reset_index().melt("año", var_name="centro", value_name="eficiencia_pct").round(2).to_excel(xw, sheet_name="eficiencia", index=False)
print("ok")
