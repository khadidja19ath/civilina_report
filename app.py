import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path

# ============================================================
# CONFIG & DATA LOADING
# ============================================================
st.set_page_config(page_title="Civilina — Tableau de Bord", layout="wide", initial_sidebar_state="collapsed")

BASE = Path(__file__).parent

NAVY = "#103e66"
NAVY_DARK = "#09124f"
BLUE = "#12239e"
ACCENT = "#2d6e9e"
TEAL = "#1e9e8f"

@st.cache_data
def load_data():
    act = pd.read_csv(BASE / "activites.csv", parse_dates=["Début_prévu", "Fin_prévue"])
    suivi = pd.read_csv(BASE / "suivi_hebdo.csv", parse_dates=["Date_snapshot", "Début_réel", "Fin_réelle"])
    return act, suivi

act, suivi = load_data()
ALL_DATES = sorted(suivi["Date_snapshot"].unique())

# ============================================================
# MEASURES (mirrors the DAX in the .pbix exactly)
# ============================================================

def weighted_avg(df, val_col, act_df):
    m = df.merge(act_df[["Activity_ID", "Poids_KPI"]], on="Activity_ID", how="left")
    w = m["Poids_KPI"].sum()
    return (m[val_col] * m["Poids_KPI"]).sum() / w if w else 0.0

def apply_filters(df_suivi, df_act, lot, zone, st_, statut_budget=None):
    a = df_act.copy()
    if lot and lot != "Tous":
        a = a[a["Lot"] == lot]
    if zone and zone != "Toutes":
        a = a[a["Zone"] == zone]
    if st_ and st_ != "Tous":
        a = a[a["Sous_traitant"] == st_]
    if statut_budget and statut_budget != "Tous":
        a = a[a["Statut_Budget"] == statut_budget]
    s = df_suivi[df_suivi["Activity_ID"].isin(a["Activity_ID"])]
    return s, a

def at_date_ref(s, date_ref):
    return s[s["Date_snapshot"] == date_ref]

def m_avancement_pondere(s_at_ref, a):
    prevu = weighted_avg(s_at_ref, "Avancement_prévu_pct", a)
    reel = weighted_avg(s_at_ref, "Avancement_réel_pct", a)
    return prevu, reel, reel - prevu

def m_nb_activites_retard(s_at_ref, a):
    m = s_at_ref.merge(a[["Activity_ID"]], on="Activity_ID", how="inner")
    ecart = m["Avancement_réel_pct"] - m["Avancement_prévu_pct"]
    mask = (m["Statut"] != "Terminée") & (ecart < -5)
    return m.loc[mask, "Activity_ID"].nunique()

def m_budget_total(a):
    return a["Coût_prévu_DA"].sum()

def m_cout_reel_cumule(s_at_ref, a):
    m = s_at_ref.merge(a[["Activity_ID"]], on="Activity_ID", how="inner")
    return m["Coût_réel_cumulé_DA"].sum()

def m_nb_decroissances(s):
    return int((s["Flag_Cout"] == "Décroissance").sum())

def m_nb_evolutions_apres_fin(s):
    return int((s["Flag_Evolution_Apres_Fin"] == "À vérifier").sum())

def m_nb_incoherences_statut(s):
    return int((s["Flag_Statut_Incohérent"] == "Incohérent").sum())

def m_nb_activites_critiques(s):
    # Nb_Activités Critiques (mesure choisie par Khadidja : historique, sans filtre DateRef)
    return s.loc[s["Score_Risque"] >= 3, "Activity_ID"].nunique()

def m_nb_activites_dep(s_at_ref, a):
    m = a.merge(s_at_ref[["Activity_ID", "Coût_réel_cumulé_DA"]], on="Activity_ID", how="left")
    return int((m["Coût_réel_cumulé_DA"] > m["Coût_prévu_DA"]).sum())

def cout_reel_activite(s, a, date_ref):
    """Coût Réel Activité, Écart Budget Activité, Budget Consommé Activité % — par activité, à DateRef."""
    s_ref = s[s["Date_snapshot"] == date_ref][["Activity_ID", "Coût_réel_cumulé_DA"]]
    m = a.merge(s_ref, on="Activity_ID", how="left")
    m["Coût Réel Activité"] = m["Coût_réel_cumulé_DA"]
    m["Écart Budget Activité"] = m["Coût Réel Activité"] - m["Coût_prévu_DA"]
    m["Budget Consommé Activité %"] = (m["Coût Réel Activité"] / m["Coût_prévu_DA"]) * 100
    return m

def fmt_int(v):
    return f"{v:,.0f}".replace(",", " ")

def fmt_pct(v, dec=1):
    return f"{v:,.{dec}f} %".replace(".", ",")

def fmt_pts(v):
    s = f"{v:+.2f}".replace(".", ",")
    return f"{s} pts"

def fmt_da(v):
    return f"{v:,.0f} DA".replace(",", " ")

def fmt_m(v):
    return f"{v/1e6:.0f}M"

# ============================================================
# STYLE
# ============================================================
st.markdown(f"""
<style>
    .block-container {{ padding-top: 1rem; max-width: 1500px; }}
    div[data-testid="stMetric"] {{
        background: #F5F9FC; border: 1px solid #E1E9F0; border-radius: 10px;
        padding: 14px 16px 10px;
    }}
    div[data-testid="stMetric"] label {{ color: {NAVY}; font-weight: 600; }}
    .insight-box {{
        background: #F5F9FC; border-radius: 10px; padding: 18px 22px;
        font-size: 16px; line-height: 1.6; margin-top: 8px;
    }}
    .filter-label {{ font-size: 12px; color: #6B7785; font-weight: 600; margin-bottom: -6px; }}
</style>
""", unsafe_allow_html=True)

st.image(str(BASE / "banner.png"), use_container_width=True)

def kpi_card(label, value, color=NAVY):
    st.markdown(f"""
    <div style="background:#F5F9FC;border:1px solid #E1E9F0;border-radius:10px;
                padding:12px 14px 10px;min-height:78px;">
        <div style="font-size:11.5px;color:{color};font-weight:600;line-height:1.25;
                    white-space:normal;margin-bottom:6px;">{label}</div>
        <div style="font-size:22px;font-weight:700;color:{color};">{value}</div>
    </div>
    """, unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📊  Tableau de Bord - Suivi du Projet", "🎯  Performance & Priorités", "💰  Coût & Performance"])

# ============================================================
# PAGE 1 — Tableau de Bord - Suivi du Projet
# ============================================================
with tab1:
    st.markdown(f"<span style='color:{ACCENT};font-size:13px'>Performance&nbsp;&nbsp;|&nbsp;&nbsp;Coûts&nbsp;&nbsp;|&nbsp;&nbsp;Risques&nbsp;&nbsp;|&nbsp;&nbsp;Décisions</span>", unsafe_allow_html=True)

    fcol, ccol = st.columns([1, 4])
    with fcol:
        st.markdown("**🔽 Filtres**")
        date_sel_1 = st.selectbox("Période de référence", ["Tout"] + [d.strftime("%d/%m/%Y") for d in ALL_DATES], key="d1")
        lot_1 = st.selectbox("Lot", ["Tous"] + sorted(act["Lot"].unique()), key="l1")
        zone_1 = st.selectbox("Zone", ["Toutes"] + sorted(act["Zone"].unique()), key="z1")
        st_1 = st.selectbox("Sous-traitant", ["Tous"] + sorted(act["Sous_traitant"].unique()), key="s1")
        if st.button("↺ Réinitialiser les filtres", key="reset1"):
            for k in ["d1", "l1", "z1", "s1"]:
                st.session_state.pop(k, None)
            st.rerun()

    date_ref_1 = max(ALL_DATES) if date_sel_1 == "Tout" else pd.Timestamp(pd.to_datetime(date_sel_1, format="%d/%m/%Y"))
    s_f, a_f = apply_filters(suivi, act, lot_1, zone_1, st_1)
    s_ref = at_date_ref(s_f, date_ref_1)
    prevu, reel, ecart = m_avancement_pondere(s_ref, a_f)
    nb_retard = m_nb_activites_retard(s_ref, a_f)
    pct_retard = nb_retard / a_f["Activity_ID"].nunique() * 100 if len(a_f) else 0
    budget_total = m_budget_total(a_f)
    cout_reel = m_cout_reel_cumule(s_ref, a_f)
    pct_budget = cout_reel / budget_total * 100 if budget_total else 0

    with ccol:
        k1, k2, k3, k4, k5, k6 = st.columns(6)
        with k1: kpi_card("Avancement Réel Pondéré %", fmt_pct(reel, 2))
        with k2: kpi_card("Avancement Prévu Pondéré %", fmt_pct(prevu, 2))
        with k3: kpi_card("Écart Avancement (pts)", fmt_pts(ecart))
        with k4: kpi_card("Nb Activités en Retard", str(nb_retard))
        with k5: kpi_card("% Activités en Retard", fmt_pct(pct_retard, 0))
        with k6: kpi_card("% Budget Consommé", fmt_pct(pct_budget, 1))

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📈 Avancement Prévu VS Réel**")
            evo = s_f.merge(act[["Activity_ID", "Poids_KPI"]], on="Activity_ID", how="left")
            evo_g = evo.groupby("Date_snapshot").apply(
                lambda g: pd.Series({
                    "Prévu": (g["Avancement_prévu_pct"] * g["Poids_KPI"]).sum() / g["Poids_KPI"].sum(),
                    "Réel": (g["Avancement_réel_pct"] * g["Poids_KPI"]).sum() / g["Poids_KPI"].sum(),
                })
            ).reset_index()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=evo_g["Date_snapshot"], y=evo_g["Prévu"], name="Avancement Prévu Pondéré %", line=dict(color="#8FD3D3", width=3)))
            fig.add_trace(go.Scatter(x=evo_g["Date_snapshot"], y=evo_g["Réel"], name="Avancement Réel Pondéré %", line=dict(color=NAVY, width=3)))
            fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown("**📊 Performance par Lot %**")
            rows = []
            for lot_name, grp_a in a_f.groupby("Lot"):
                grp_s = at_date_ref(s_f[s_f["Activity_ID"].isin(grp_a["Activity_ID"])], date_ref_1)
                p, r, _ = m_avancement_pondere(grp_s, grp_a)
                rows.append({"Lot": lot_name, "Avancement Prévu Pondéré %": p, "Avancement Réel Pondéré %": r})
            lot_df = pd.DataFrame(rows)
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(x=lot_df["Lot"], y=lot_df["Avancement Prévu Pondéré %"], name="Prévu", marker_color="#8FD3D3", text=lot_df["Avancement Prévu Pondéré %"].round(0), textposition="outside"))
            fig2.add_trace(go.Bar(x=lot_df["Lot"], y=lot_df["Avancement Réel Pondéré %"], name="Réel", marker_color=NAVY, text=lot_df["Avancement Réel Pondéré %"].round(0), textposition="outside"))
            fig2.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown(f"""
    <div class="insight-box">
    💡 <b>Insight</b> — À date du 24/08/2026, le projet affiche un avancement réel de <b style="color:{NAVY}">96,99 %</b> contre <b style="color:{NAVY}">99,16 %</b> prévu, soit un écart de <b style="color:{NAVY}">-2,17 pts</b>.
    <b style="color:{NAVY}">15 activités (25 %)</b> sont actuellement en retard. Le budget consommé (<b style="color:{NAVY}">93,59 %</b>) reste maîtrisé et cohérent avec l'avancement — <b style="color:{NAVY}">pas de dérive de coût globale</b>, malgré un volume élevé de retards ponctuels à traiter en Page 2/3.
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# PAGE 2 — Performance & Priorités
# ============================================================
with tab2:
    st.markdown("**Suivi détaillé des activités par zone, sous-traitant et priorités**")
    f1, f2, f3, f4, f5 = st.columns([1, 1, 1, 1, 0.6])
    with f1:
        date_sel_2 = st.selectbox("Période de référence", ["Tout"] + [d.strftime("%d/%m/%Y") for d in ALL_DATES], key="d2")
    with f2:
        lot_2 = st.selectbox("Lot", ["Tous"] + sorted(act["Lot"].unique()), key="l2")
    with f3:
        zone_2 = st.selectbox("Zone", ["Toutes"] + sorted(act["Zone"].unique()), key="z2")
    with f4:
        st_2 = st.selectbox("Sous-traitant", ["Tous"] + sorted(act["Sous_traitant"].unique()), key="s2")
    with f5:
        st.write("")
        if st.button("↺ Effacer", key="reset2"):
            for k in ["d2", "l2", "z2", "s2"]:
                st.session_state.pop(k, None)
            st.rerun()

    date_ref_2 = max(ALL_DATES) if date_sel_2 == "Tout" else pd.Timestamp(pd.to_datetime(date_sel_2, format="%d/%m/%Y"))
    s_f2, a_f2 = apply_filters(suivi, act, lot_2, zone_2, st_2)
    s_ref2 = at_date_ref(s_f2, date_ref_2)
    _, _, ecart2 = m_avancement_pondere(s_ref2, a_f2)
    nb_retard2 = m_nb_activites_retard(s_ref2, a_f2)
    nb_evo = m_nb_evolutions_apres_fin(s_f2)
    nb_crit = m_nb_activites_critiques(s_f2)
    nb_incoh = m_nb_incoherences_statut(s_f2)

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: kpi_card("Écart Avancement (pts)", fmt_pts(ecart2))
    with k2: kpi_card("Activités en Retard", str(nb_retard2))
    with k3: kpi_card("Évolutions Après Fin", str(nb_evo))
    with k4: kpi_card("Activités Critiques", str(nb_crit))
    with k5: kpi_card("Nb Incohérences Statut", str(nb_incoh))

    t1, t2 = st.columns([1.4, 1.6])
    with t1:
        st.markdown("**📋 Top activités en retard (prioritaires)**")
        m = s_ref2.merge(a_f2, on="Activity_ID", how="inner")
        m["Écart"] = m.apply(lambda r: (r["Avancement_réel_pct"] - r["Avancement_prévu_pct"]) if r["Statut"] != "Terminée" else None, axis=1)
        top = m.dropna(subset=["Écart"]).sort_values("Écart").head(10)
        st.dataframe(
            top[["Activity_ID", "Sous_traitant", "Activité", "Écart", "Statut", "Niveau_Risque"]]
              .rename(columns={"Niveau_Risque": "Niveau Risque"})
              .style.format({"Écart": "{:+.2f}"}),
            hide_index=True, use_container_width=True, height=380
        )
    with t2:
        cc1, cc2 = st.columns(2)
        with cc1:
            st.markdown("**Performance par sous-traitant**")
            rows = []
            for name, grp_a in a_f2.groupby("Sous_traitant"):
                grp_s = at_date_ref(s_f2[s_f2["Activity_ID"].isin(grp_a["Activity_ID"])], date_ref_2)
                _, _, e = m_avancement_pondere(grp_s, grp_a)
                rows.append({"Sous_traitant": name, "Écart": e})
            df_st = pd.DataFrame(rows).sort_values("Écart")
            fig3 = px.bar(df_st, x="Écart", y="Sous_traitant", orientation="h",
                          color=df_st["Écart"] > 0, color_discrete_map={True: "#2ecc71", False: "#e15241"}, text="Écart")
            fig3.update_traces(texttemplate="%{text:.1f}", textposition="outside", cliponaxis=False)
            pad3 = max(abs(df_st["Écart"].min()), abs(df_st["Écart"].max())) * 0.45 + 0.5
            fig3.update_xaxes(range=[df_st["Écart"].min() - pad3, df_st["Écart"].max() + pad3])
            fig3.update_layout(height=330, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig3, use_container_width=True)
        with cc2:
            st.markdown("**Écart Avancement (pts) par Zone**")
            rows = []
            for name, grp_a in a_f2.groupby("Zone"):
                grp_s = at_date_ref(s_f2[s_f2["Activity_ID"].isin(grp_a["Activity_ID"])], date_ref_2)
                _, _, e = m_avancement_pondere(grp_s, grp_a)
                rows.append({"Zone": name, "Écart": e})
            df_z = pd.DataFrame(rows).sort_values("Écart")
            fig4 = px.bar(df_z, x="Écart", y="Zone", orientation="h",
                          color=df_z["Écart"] > 0, color_discrete_map={True: "#2ecc71", False: "#e15241"}, text="Écart")
            fig4.update_traces(texttemplate="%{text:.1f}", textposition="outside", cliponaxis=False)
            pad4 = max(abs(df_z["Écart"].min()), abs(df_z["Écart"].max())) * 0.45 + 0.5
            fig4.update_xaxes(range=[df_z["Écart"].min() - pad4, df_z["Écart"].max() + pad4])
            fig4.update_layout(height=330, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig4, use_container_width=True)

    st.markdown(f"""
    <div class="insight-box" style="color:{NAVY_DARK}">
    💡 <b>Insight</b> — Le retard est <b>concentré sur deux sous-traitants</b> : <b>ST Alpha</b> (écart pondéré <b>-5,8 pts</b>, 9 activités à risque sur 13) et <b>ST Gamma</b> (<b>-4,7 pts</b>, 5/11 à risque) — à l'inverse, <b>ST Delta</b> est en avance (<b>+1,2 pt</b>) et <b>ST Beta</b> est quasiment dans les temps (-0,1 pt).
    Par lot, <b>Charpente métallique</b> (<b>-4,2 pts</b>) est le plus en retard, devant CVC/Plomberie (-2,3 pts). Par zone, <b>Administration et Zone B</b> sont les plus touchées (-2,5 pts chacune). L'activité la plus critique reste <b>ACT-021</b> (Équipements sanitaires, ST Alpha, -9,8 pts).
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# PAGE 3 — Coût & Performance
# ============================================================
with tab3:
    st.markdown("**Suivi budgétaire et performance des activités**")
    f1, f2, f3, f4, f5, f6 = st.columns([1, 1, 1, 1, 1, 0.6])
    with f1:
        date_sel_3 = st.selectbox("Période de référence", ["Tout"] + [d.strftime("%d/%m/%Y") for d in ALL_DATES], key="d3")
    with f2:
        statut_b_3 = st.selectbox("Statut Budget", ["Tous"] + sorted(act["Statut_Budget"].dropna().unique()), key="sb3")
    with f3:
        lot_3 = st.selectbox("Lot", ["Tous"] + sorted(act["Lot"].unique()), key="l3")
    with f4:
        zone_3 = st.selectbox("Zone", ["Toutes"] + sorted(act["Zone"].unique()), key="z3")
    with f5:
        st_3 = st.selectbox("Sous-traitant", ["Tous"] + sorted(act["Sous_traitant"].unique()), key="s3")
    with f6:
        st.write("")
        if st.button("↺ Effacer", key="reset3"):
            for k in ["d3", "sb3", "l3", "z3", "s3"]:
                st.session_state.pop(k, None)
            st.rerun()

    date_ref_3 = max(ALL_DATES) if date_sel_3 == "Tout" else pd.Timestamp(pd.to_datetime(date_sel_3, format="%d/%m/%Y"))
    s_f3, a_f3 = apply_filters(suivi, act, lot_3, zone_3, st_3, statut_b_3)
    s_ref3 = at_date_ref(s_f3, date_ref_3)
    budget_total3 = m_budget_total(a_f3)
    cout_reel3 = m_cout_reel_cumule(s_ref3, a_f3)
    pct_budget3 = cout_reel3 / budget_total3 * 100 if budget_total3 else 0
    nb_dep = m_nb_activites_dep(s_ref3, a_f3)
    nb_decr = m_nb_decroissances(s_f3)

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: kpi_card("💰 Budget Total", fmt_m(budget_total3) + " DA")
    with k2: kpi_card("💼 Coût Réel Cumulé (à date réf)", fmt_m(cout_reel3) + " DA")
    with k3: kpi_card("% Budget Consommé", fmt_pct(pct_budget3, 1))
    with k4: kpi_card("⚠️ Nb Activités en Dépassement", str(nb_dep))
    with k5: kpi_card("Nb Décroissances Coût", str(nb_decr))

    cra = cout_reel_activite(s_f3, a_f3, date_ref_3)

    c1, c2 = st.columns([1.1, 1])
    with c1:
        st.markdown("**Avancement vs Budget consommé**")
        merged_ref = s_ref3.merge(cra, on="Activity_ID", how="inner")
        fig5 = px.scatter(
            merged_ref, x="Avancement_réel_pct", y="Budget Consommé Activité %",
            size="Poids_KPI", color="Statut_Budget",
            color_discrete_map={"Dans le budget": "#6EC5C0", "Dépassement": "#12239e"},
            hover_data=["Activity_ID", "Activité"], size_max=28,
        )
        fig5.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10),
                            xaxis_title="Avancement Réel Pondéré %", yaxis_title="Budget Consommé Activité %")
        st.plotly_chart(fig5, use_container_width=True)
    with c2:
        st.markdown("**Écart Budget Activité**")
        tbl = cra.sort_values("Écart Budget Activité", ascending=False)[
            ["Activity_ID", "Coût Réel Activité", "Coût_prévu_DA", "Écart Budget Activité"]
        ].rename(columns={"Coût_prévu_DA": "Coût_prévu_DA"})
        st.dataframe(
            tbl.style.format({"Coût Réel Activité": "{:,.0f}", "Coût_prévu_DA": "{:,.0f}", "Écart Budget Activité": "{:+,.0f}"}),
            hide_index=True, use_container_width=True, height=380
        )

    st.markdown(f"""
    <div class="insight-box" style="color:{BLUE}">
    💡 <b>Insight</b> — <b>18 activités sur 60</b> dépassent leur budget individuel malgré un taux de consommation global maîtrisé (93,6 %) — le total masque des situations locales. Le dépassement le plus important est <b>ACT-048</b> (Réseau EF/EC, ST Delta, +8,1 %). Par ailleurs, <b>105 décroissances</b> du coût cumulé ont été détectées sur 51/60 activités — ceci suggère une <b>anomalie de saisie récurrente côté suivi terrain</b>, à corriger en priorité, plutôt qu'un vrai signal de performance.
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br><center style='color:#9AA5B1;font-size:12px'>Civilina — Construction & Infrastructures · Béjaïa, Algérie · Ensemble pour bâtir demain</center>", unsafe_allow_html=True)
