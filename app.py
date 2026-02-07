import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from db import init_db, get_conn

# --- Exit helpers imports
import os
import time
import threading

# =========================================================
# Config
# =========================================================
st.set_page_config(page_title="Spese Condominiali", layout="wide")
init_db()
TODAY = date.today()

# =========================================================
# Exit helpers
# =========================================================
def shutdown_app(delay_seconds: float = 1.0):
    """
    Spegne il processo Streamlit/Python dopo un breve delay per permettere
    di renderizzare la pagina di uscita.
    """
    def _kill():
        time.sleep(delay_seconds)
        os._exit(0)  # terminazione immediata del processo (chiude l'app)
    threading.Thread(target=_kill, daemon=True).start()


def render_exit_page():
    """Pagina semplice di uscita (senza tentare di chiudere la tab)."""
    st.markdown(
        """
        <div style="display:flex;align-items:center;justify-content:center;height:70vh;">
          <div style="text-align:center;max-width:560px;">
            <h2>✅ Applicazione chiusa</h2>
            <p>Ora puoi chiudere questa scheda del browser.</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# =========================================================
# CSS
# =========================================================
st.markdown(
    """
    <style>
      .block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1250px; }
      h1, h2, h3 { letter-spacing: -0.2px; }

      .stMetric { background: #ffffff; border: 1px solid #edf2f7; padding: 12px 14px; border-radius: 12px; }
      .stTabs [data-baseweb="tab-list"] { gap: 6px; }
      .stTabs [data-baseweb="tab"] { padding: 10px 14px; border-radius: 10px; }

      .card {
        background: #ffffff;
        border: 1px solid #edf2f7;
        border-radius: 14px;
        padding: 14px 14px 8px 14px;
        box-shadow: 0 1px 0 rgba(0,0,0,0.02);
        margin-bottom: 12px;
      }
      .card-title { font-weight: 700; font-size: 1.05rem; margin-bottom: 10px; }
      .muted { color: #6b7280; font-size: 0.92rem; }

      /* Rata "badge" */
      .badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 54px;
        height: 38px;
        border-radius: 999px;
        padding: 0 10px;
        font-weight: 800;
        border: 1px solid #e5e7eb;
        background: #f3f4f6;
      }

      /* Stato pagamento: come badge, colorato */
      .statusbadge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 160px;
        height: 38px;
        border-radius: 999px;
        padding: 0 12px;
        font-weight: 800;
        border: 1px solid #e5e7eb;
      }
      .sb-green { background:#ecfdf3; border-color:#bbf7d0; color:#166534; }
      .sb-yellow{ background:#fffbeb; border-color:#fde68a; color:#92400e; }
      .sb-red   { background:#fef2f2; border-color:#fecaca; color:#991b1b; }

      /* Pulsanti più "pieni" (aiuta allineamento) */
      button[kind="primary"], button[kind="secondary"] { border-radius: 10px !important; }
      div.stButton > button { padding-top: 0.55rem; padding-bottom: 0.55rem; }

      div[data-testid="stVerticalBlock"] > div { gap: 0.55rem; }
      .stDataFrame { border-radius: 12px; overflow: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# Helpers DB
# =========================================================
def df_query(sql: str, params=()):
    with get_conn() as conn:
        return pd.read_sql_query(sql, conn, params=params)

def exec_sql(sql: str, params=()):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()

def exec_many(sql: str, seq_params):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, seq_params)
        conn.commit()

def get_immobili_df():
    return df_query("SELECT id, nome, indirizzo, codice_fiscale, iban FROM immobili ORDER BY nome")

def get_immobile_id(nome: str) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM immobili WHERE nome=%s", (nome,))
            row = cur.fetchone()
            return int(row[0]) if row else None

# =========================================================
# Helpers UI/Logic
# =========================================================
def is_scaduto(scadenza_str: str) -> bool:
    try:
        d = pd.to_datetime(scadenza_str).date()
        return d < TODAY
    except Exception:
        return False

def status_class(stato: str, scadenza_str: str) -> str:
    if stato == "Pagato":
        return "sb-green"
    if stato == "Da pagare" and is_scaduto(scadenza_str):
        return "sb-red"
    return "sb-yellow"

def status_text_lower(stato: str, scadenza_str: str) -> str:
    if stato == "Pagato":
        return "pagato"
    if stato == "Da pagare" and is_scaduto(scadenza_str):
        return "da pagare (scaduto)"
    return "da pagare"

def color_for_row(stato: str, scadenza_str: str) -> str:
    if stato == "Pagato":
        return "color: #1a7f37;"
    if stato == "Da pagare" and is_scaduto(scadenza_str):
        return "color: #d1242f;"
    if stato == "Da pagare":
        return "color: #d97706;"
    return ""

def style_font_by_status(df: pd.DataFrame, stato_col="stato", scad_col="scadenza"):
    if df.empty:
        return df
    def _apply_row(row):
        css = color_for_row(str(row[stato_col]), str(row[scad_col]))
        return [css] * len(row)
    return df.style.apply(_apply_row, axis=1)

def safe_note(base_note: str, extra: str) -> str:
    base_note = "" if base_note is None else str(base_note).strip()
    extra = "" if extra is None else str(extra).strip()
    if base_note and extra:
        return base_note + " | " + extra
    return base_note or extra

def last_n_years_available(df: pd.DataFrame, n: int = 3):
    years = sorted(pd.to_numeric(df["esercizio"], errors="coerce").dropna().astype(int).unique().tolist())
    if not years:
        y = TODAY.year
        return [y - 2, y - 1, y]
    return years[-n:] if len(years) >= n else years

def euro(x) -> str:
    try:
        return f"€ {float(x):,.2f}"
    except Exception:
        return "€ 0,00"

def compute_rata_display(df: pd.DataFrame) -> pd.Series:
    """
    Usa SEMPRE numero_rate_totali dal DB (colonna aggiunta),
    fallback a 1 se non valorizzato.
    """
    if df.empty:
        return pd.Series([], dtype="string")
    nr = pd.to_numeric(df.get("numero_rata"), errors="coerce").fillna(1).astype(int)
    tot = pd.to_numeric(df.get("numero_rate_totali"), errors="coerce").fillna(1).astype(int)
    tot = tot.where(tot >= 1, 1)
    return nr.astype(str) + "/" + tot.astype(str)

# =========================================================
# “Form versioning” for clean reset
# =========================================================
if "ns_form_v" not in st.session_state:
    st.session_state.ns_form_v = 0

def ns_key(name: str) -> str:
    return f"{name}__v{st.session_state.ns_form_v}"

def reset_nuova_spesa():
    st.session_state.ns_form_v += 1
    st.session_state["rate_items"] = []
    st.rerun()

if "dash_form_v" not in st.session_state:
    st.session_state.dash_form_v = 0

def dash_key(name: str) -> str:
    return f"{name}__v{st.session_state.dash_form_v}"

def reset_dashboard():
    st.session_state.dash_form_v += 1
    st.rerun()

# =========================================================
# App UI
# =========================================================
st.title("Spese Condominiali")

# Exit flow (intercetta subito al rerun)
if st.session_state.get("_exit_requested"):
    render_exit_page()
#    shutdown_app(delay_seconds=1.0)
    st.stop()

tabs = st.tabs(["➕ Nuova spesa", "✅ Pagamenti", "📊 Dashboard", "🏠 Immobili", "⚙️ Impostazioni"])

# =========================================================
# IMMOBILI
# =========================================================
with tabs[3]:
    st.markdown('<div class="card"><div class="card-title">Immobili</div>', unsafe_allow_html=True)
    imm = get_immobili_df()
    if imm.empty:
        st.info("Nessun immobile presente.")
    else:
        st.dataframe(
            imm[["nome","indirizzo","codice_fiscale","iban"]].rename(columns={
                "nome": "Immobile",
                "indirizzo": "Indirizzo",
                "codice_fiscale": "Codice fiscale",
                "iban": "IBAN"
            }),
            use_container_width=True,
            hide_index=True
        )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="card-title">➕ Aggiungi immobile</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    with c1:
        nome_new = st.text_input("Nome", placeholder="Es. Jesolo", label_visibility="collapsed", key="imm_add_name")
    with c2:
        if st.button("Aggiungi", key="imm_add_btn", use_container_width=True):
            nome_new = (nome_new or "").strip()
            if not nome_new:
                st.warning("Inserisci un nome valido.")
            else:
                exec_sql("INSERT INTO immobili(nome) VALUES (%s) ON CONFLICT (nome) DO NOTHING", (nome_new,))
                st.success("Immobile aggiunto (o già presente).")
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="card-title">Gestisci immobile</div>', unsafe_allow_html=True)
    imm = get_immobili_df()
    if imm.empty:
        st.info("Aggiungi un immobile per gestirlo.")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        top = st.columns([3, 1, 1])
        with top[0]:
            scelta_nome = st.selectbox("Immobile", imm["nome"].tolist(), key="imm_sel", label_visibility="collapsed")

        imm_id = get_immobile_id(scelta_nome)
        n_spese = int(df_query("SELECT COUNT(*) AS n FROM spese WHERE immobile_id=%s", (imm_id,)).iloc[0]["n"])

        if "imm_edit_mode" not in st.session_state:
            st.session_state.imm_edit_mode = False
            st.session_state.imm_edit_id = None

        with top[1]:
            if st.button("✏️ Modifica", key="imm_edit_btn", use_container_width=True):
                st.session_state.imm_edit_mode = True
                st.session_state.imm_edit_id = imm_id

        with top[2]:
            del_disabled = n_spese > 0
            if st.button("🗑️ Elimina", key="imm_del_btn", disabled=del_disabled, use_container_width=True):
                st.session_state.imm_confirm_delete = True
                st.session_state.imm_delete_id = imm_id

        if n_spese > 0:
            st.caption(f"Elimina disattivato: esistono {n_spese} spese/pagamenti associati.")

        if st.session_state.imm_edit_mode and st.session_state.imm_edit_id == imm_id:
            # Valori correnti
            row = imm[imm["id"] == imm_id].iloc[0]
            cur_nome = row["nome"]
            cur_indirizzo = row.get("indirizzo", "")
            cur_cf = row.get("codice_fiscale", "")
            cur_iban = row.get("iban", "")

            st.markdown("**Modifica immobile**")
            f1, f2 = st.columns(2)
            with f1:
                new_name = st.text_input("Nome", value=cur_nome or "", key="imm_edit_nome")
                new_indirizzo = st.text_input("Indirizzo", value=cur_indirizzo or "", key="imm_edit_indirizzo")
            with f2:
                new_cf = st.text_input("Codice fiscale", value=cur_cf or "", key="imm_edit_cf")
                new_iban = st.text_input("IBAN", value=cur_iban or "", key="imm_edit_iban")

            a, b = st.columns([1, 1])
            with a:
                if st.button("Salva", key="imm_save_edit", use_container_width=True):
                    new_name = (new_name or "").strip()
                    new_indirizzo = (new_indirizzo or "").strip() or None
                    new_cf = (new_cf or "").strip() or None
                    new_iban = (new_iban or "").strip() or None

                    if not new_name:
                        st.warning("Il nome non può essere vuoto.")
                    else:
                        try:
                            exec_sql(
                                "UPDATE immobili SET nome=%s, indirizzo=%s, codice_fiscale=%s, iban=%s WHERE id=%s",
                                (new_name, new_indirizzo, new_cf, new_iban, imm_id),
                            )
                            st.session_state.imm_edit_mode = False
                            st.session_state.imm_edit_id = None
                            st.success("Immobile aggiornato.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Errore aggiornamento immobile: {e}")
            with b:
                if st.button("Annulla", key="imm_cancel_edit", use_container_width=True):
                    st.session_state.imm_edit_mode = False
                    st.session_state.imm_edit_id = None
                    st.rerun()
        if "imm_confirm_delete" not in st.session_state:
            st.session_state.imm_confirm_delete = False
            st.session_state.imm_delete_id = None

        if st.session_state.imm_confirm_delete and st.session_state.imm_delete_id == imm_id:
            st.error("Confermi l’eliminazione dell’immobile? Operazione irreversibile.")
            a, b = st.columns(2)
            with a:
                if st.button("Sì, elimina definitivamente", key="imm_del_yes"):
                    exec_sql("DELETE FROM immobili WHERE id=%s", (imm_id,))
                    st.session_state.imm_confirm_delete = False
                    st.session_state.imm_delete_id = None
                    st.success("Immobile eliminato.")
                    st.rerun()
            with b:
                if st.button("No, annulla", key="imm_del_no"):
                    st.session_state.imm_confirm_delete = False
                    st.session_state.imm_delete_id = None
                    st.info("Operazione annullata.")
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# NUOVA SPESA
# =========================================================
with tabs[0]:
    st.markdown('<div class="card"><div class="card-title">Nuova spesa</div>', unsafe_allow_html=True)
    imm = get_immobili_df()
    if imm.empty:
        st.info("Inserisci prima almeno un immobile nella scheda 🏠 Immobili.")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        r1 = st.columns([2, 1, 1, 1])
        with r1[0]:
            nome_immobile = st.selectbox("Immobile", imm["nome"].tolist(), key=ns_key("ns_immobile"))
        with r1[1]:
            esercizio = st.number_input("Esercizio", min_value=2000, max_value=2100, value=TODAY.year, step=1, key=ns_key("ns_esercizio"))
        with r1[2]:
            tipo_spesa = st.selectbox("Tipo", ["Ordinario", "Straordinario"], index=0, key=ns_key("ns_tipo"))
        with r1[3]:
            tot_rates = st.number_input("N° rate", min_value=1, value=1, step=1, key=ns_key("ns_tot_rates"))

        if st.session_state.get(ns_key("ns_stato"), "Da pagare") == "Pagato":
            r2 = st.columns([1.1, 1.2, 3.7])
        else:
            r2 = st.columns([1.2, 0.001, 3.8])
        with r2[0]:
            stato = st.selectbox("Stato", ["Da pagare", "Pagato"], index=0, key=ns_key("ns_stato"))
        data_pagamento_all = None
        with r2[1]:
            if stato == "Pagato":
                data_pagamento_all = st.date_input("Data pag.", value=TODAY, key=ns_key("ns_data_pag"))
            else:
                st.write("")
        with r2[2]:
            note_base = st.text_input("Note", placeholder="Es. gestione ordinaria 2026...", key=ns_key("ns_note"))

        st.divider()
        st.markdown('<div class="muted">Dettaglio rate</div>', unsafe_allow_html=True)

        if "rate_items" not in st.session_state:
            st.session_state.rate_items = []

        while len(st.session_state.rate_items) < tot_rates:
            st.session_state.rate_items.append({"scadenza": TODAY, "importo": 0.0})
        while len(st.session_state.rate_items) > tot_rates:
            st.session_state.rate_items.pop()

        left, right = st.columns([3.7, 2.3], gap="small")
        with left:
            hdr = st.columns([0.68, 1.45, 1.45], gap="small")
            hdr[0].caption("Rata")
            hdr[1].caption("Scadenza")
            hdr[2].caption("Importo (€)")

            total_importo = 0.0
            for i in range(tot_rates):
                rr = st.columns([0.68, 1.45, 1.45], gap="small")
                with rr[0]:
                    st.markdown(f'<span class="badge">{i+1}/{tot_rates}</span>', unsafe_allow_html=True)
                with rr[1]:
                    scad_i = st.date_input("Scadenza", value=st.session_state.rate_items[i]["scadenza"], key=f"{ns_key('ns_scad')}_{i}", label_visibility="collapsed")
                with rr[2]:
                    imp_i = st.number_input("Importo (€)", min_value=0.0, value=float(st.session_state.rate_items[i]["importo"]), step=10.0, key=f"{ns_key('ns_imp')}_{i}", label_visibility="collapsed")
                st.session_state.rate_items[i]["scadenza"] = scad_i
                st.session_state.rate_items[i]["importo"] = float(imp_i)
                total_importo += float(imp_i)

        st.success(f"**Totale rate (somma importi): € {total_importo:,.2f}**")

        st.divider()
        btns = st.columns([1, 1, 3])
        with btns[0]:
            if st.button("✅ Registra", key=ns_key("ns_registra"), use_container_width=True):
                if total_importo <= 0:
                    st.warning("Inserisci almeno un importo maggiore di 0.")
                else:
                    immobile_id = get_immobile_id(nome_immobile)
                    rows = []
                    for i, item in enumerate(st.session_state.rate_items):
                        importo_i = float(item["importo"])
                        if importo_i <= 0:
                            continue
                        nr = i + 1
                        extra_desc = f"{tipo_spesa} | Esercizio {int(esercizio)} | Rata {nr}/{int(tot_rates)}"
                        note_final = safe_note(note_base, extra_desc)

                        rows.append((
                            immobile_id,
                            int(esercizio),
                            item["scadenza"].isoformat(),
                            importo_i,
                            note_final if note_final else None,
                            stato,
                            (data_pagamento_all.isoformat() if (stato == "Pagato" and data_pagamento_all) else None),
                            nr,
                            int(tot_rates),
                            tipo_spesa
                        ))

                    if not rows:
                        st.warning("Non ci sono rate con importo > 0 da registrare.")
                    else:
                        exec_many("""
                            INSERT INTO spese
                            (immobile_id, esercizio, scadenza, importo, note, stato, data_pagamento, numero_rata, numero_rate_totali, tipo_spesa)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """, rows)
                        st.success(f"✅ Registrate {len(rows)} rate nel database.")
                        reset_nuova_spesa()
        with btns[1]:
            if st.button("↩️ Reset", key=ns_key("ns_reset"), use_container_width=True):
                reset_nuova_spesa()

    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# PAGAMENTI
# =========================================================
with tabs[1]:
    st.markdown('<div class="card"><div class="card-title">Pagamenti</div>', unsafe_allow_html=True)

    imm = get_immobili_df()
    if imm.empty:
        st.info("Inserisci prima almeno un immobile nella scheda 🏠 Immobili.")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        if "pay_mark_mode" not in st.session_state:
            st.session_state.pay_mark_mode = False
            st.session_state.pay_mark_id = None

        df_all_years = df_query("SELECT DISTINCT esercizio FROM spese ORDER BY esercizio DESC")
        anni = [int(x) for x in pd.to_numeric(df_all_years["esercizio"], errors="coerce").dropna().tolist()] if not df_all_years.empty else []
        anni_opt = ["Tutti"] + anni

        f = st.columns([2, 1.2, 1.2])
        with f[0]:
            filtro_immobile = st.selectbox("Immobile", ["Tutti"] + imm["nome"].tolist(), index=0, key="pay_f_imm")
        with f[1]:
            filtro_stato = st.selectbox("Stato", ["Tutti", "Da pagare", "Pagato"], index=1, key="pay_f_stato")
        with f[2]:
            filtro_esercizio = st.selectbox("Esercizio", anni_opt, index=0, key="pay_f_esercizio")

        sql = """
            SELECT s.id, i.nome AS immobile, s.esercizio, s.numero_rata, s.numero_rate_totali, s.tipo_spesa,
                   s.scadenza, s.importo, s.note, s.stato, s.data_pagamento
            FROM spese s
            JOIN immobili i ON i.id = s.immobile_id
            WHERE 1=1
        """
        params = []
        if filtro_immobile != "Tutti":
            sql += " AND i.nome=%s"
            params.append(filtro_immobile)
        if filtro_stato != "Tutti":
            sql += " AND s.stato=%s"
            params.append(filtro_stato)
        if filtro_esercizio != "Tutti":
            sql += " AND s.esercizio=%s"
            params.append(int(filtro_esercizio))

        sql += " ORDER BY s.scadenza ASC, i.nome ASC, s.esercizio ASC, s.numero_rata ASC"
        df = df_query(sql, tuple(params))

        if df.empty:
            st.info("Nessuna riga soddisfa i criteri selezionati.")
        else:
            df["rata_disp"] = compute_rata_display(df)
            df["label"] = df.apply(
                lambda r: f"{r['immobile']} — {r['tipo_spesa']} — {int(r['esercizio']) if pd.notna(r['esercizio']) else ''} — Rata {r['rata_disp']} — Scad. {r['scadenza']} — {euro(r['importo'])}",
                axis=1
            )

            srow = st.columns([3, 2], gap="small")
            with srow[0]:
                sel = st.selectbox("Seleziona rata", df["label"].tolist(), key="pay_sel", label_visibility="collapsed")

            row = df[df["label"] == sel].iloc[0]
            spesa_id = int(row["id"])
            stato_attuale = str(row["stato"])
            scad_sel = str(row["scadenza"])

            cls = status_class(stato_attuale, scad_sel)
            text = status_text_lower(stato_attuale, scad_sel)

            with srow[1]:
                st.markdown(f'<span class="statusbadge {cls}">{text}</span>', unsafe_allow_html=True)

            in_mark_mode = st.session_state.pay_mark_mode and st.session_state.pay_mark_id == spesa_id

            action_row = st.columns([1, 1, 1, 2], gap="small")
            with action_row[0]:
                if st.button("✅ Pagata", key="btn_pay", use_container_width=True):
                    st.session_state.pay_mark_mode = True
                    st.session_state.pay_mark_id = spesa_id
                    st.rerun()

            if not in_mark_mode:
                with action_row[1]:
                    if st.button("↩️ Da pagare", key="btn_unpay", use_container_width=True):
                        with get_conn() as c:
                            nota_extra = st.session_state.get("pay_note", "")
                            with c.cursor() as cur:
                                if (nota_extra or "").strip():
                                    cur.execute("""
                                        UPDATE spese
                                        SET note = CASE
                                            WHEN note IS NULL OR trim(note) = '' THEN %s
                                            ELSE note || ' | ' || %s
                                        END
                                        WHERE id = %s
                                    """, (nota_extra.strip(), nota_extra.strip(), spesa_id))
                                cur.execute("UPDATE spese SET stato='Da pagare', data_pagamento=NULL WHERE id=%s", (spesa_id,))
                            c.commit()
                        st.success("Impostata come Da pagare.")
                        st.rerun()

                with action_row[2]:
                    if st.button("🗑️ Elimina", key="btn_delete", use_container_width=True):
                        st.session_state.confirm_delete_spesa = True
                        st.session_state.pending_delete_spesa_id = spesa_id

                if "confirm_delete_spesa" not in st.session_state:
                    st.session_state.confirm_delete_spesa = False
                    st.session_state.pending_delete_spesa_id = None

                if st.session_state.confirm_delete_spesa and st.session_state.pending_delete_spesa_id == spesa_id:
                    st.error("Confermi l’eliminazione di questa rata? Operazione irreversibile.")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Sì, elimina", key="confirm_del_yes", use_container_width=True):
                            exec_sql("DELETE FROM spese WHERE id=%s", (spesa_id,))
                            st.session_state.confirm_delete_spesa = False
                            st.session_state.pending_delete_spesa_id = None
                            st.success("Rata eliminata.")
                            st.rerun()
                    with c2:
                        if st.button("No, annulla", key="confirm_del_no", use_container_width=True):
                            st.session_state.confirm_delete_spesa = False
                            st.session_state.pending_delete_spesa_id = None
                            st.info("Operazione annullata.")
                            st.rerun()

            if in_mark_mode:
                st.markdown("")
                dp_row = st.columns([2, 3], gap="small")
                with dp_row[0]:
                    dp = st.date_input("Data pagamento", value=TODAY, key="pay_date_pick")
                with dp_row[1]:
                    st.write("")

                ra = st.columns([1, 1, 3], gap="small")
                with ra[0]:
                    if st.button("💾 Registra", key="pay_registra", use_container_width=True):
                        nota_extra = st.session_state.get("pay_note", "")
                        with get_conn() as c:
                            with c.cursor() as cur:
                                if (nota_extra or "").strip():
                                    cur.execute("""
                                        UPDATE spese
                                        SET note = CASE
                                            WHEN note IS NULL OR trim(note) = '' THEN %s
                                            ELSE note || ' | ' || %s
                                        END
                                        WHERE id = %s
                                    """, (nota_extra.strip(), nota_extra.strip(), spesa_id))
                                cur.execute("UPDATE spese SET stato='Pagato', data_pagamento=%s WHERE id=%s", (dp.isoformat(), spesa_id))
                            c.commit()
                        st.session_state.pay_mark_mode = False
                        st.session_state.pay_mark_id = None
                        st.success("Pagamento registrato.")
                        st.rerun()
                with ra[1]:
                    if st.button("❌ Annulla", key="pay_annulla", use_container_width=True):
                        st.session_state.pay_mark_mode = False
                        st.session_state.pay_mark_id = None
                        st.rerun()

            st.text_input("Nota extra", placeholder="Es. pagato con bonifico...", key="pay_note")

            st.divider()
            st.markdown('<div class="muted">Righe (ordinate per scadenza crescente)</div>', unsafe_allow_html=True)

            view = df.drop(columns=["label"]).copy()
            view["numero rata"] = compute_rata_display(view)
            view["importo"] = view["importo"].apply(euro)
            view = view[[
                "immobile",
                "esercizio",
                "tipo_spesa",
                "numero rata",
                "importo",
                "scadenza",
                "stato",
                "data_pagamento",
                "note"
            ]]
            st.dataframe(style_font_by_status(view, stato_col="stato", scad_col="scadenza"), use_container_width=True)

            total_pay = float(pd.to_numeric(df["importo"], errors="coerce").fillna(0).sum())
            st.success(f"**Totale righe (somma importi): € {total_pay:,.2f}**")

    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# DASHBOARD
# =========================================================
with tabs[2]:
    st.markdown('<div class="card"><div class="card-title">Dashboard</div>', unsafe_allow_html=True)

    df = df_query("""
        SELECT i.nome AS immobile, s.id, s.esercizio, s.numero_rata, s.numero_rate_totali, s.tipo_spesa,
               s.scadenza, s.importo, s.note, s.stato, s.data_pagamento
        FROM spese s
        JOIN immobili i ON i.id = s.immobile_id
    """)

    if df.empty:
        st.info("Nessun dato nel database.")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        df["scadenza_dt"] = pd.to_datetime(df["scadenza"], errors="coerce")
        df["esercizio"] = pd.to_numeric(df["esercizio"], errors="coerce").astype("Int64")

        anni_last3 = last_n_years_available(df, 3)
        immobili = sorted(df["immobile"].unique().tolist())

        filters = st.columns([1.2, 2, 2], gap="small")
        with filters[0]:
            anno_mode = st.selectbox("Periodo", ["Ultimi 3 anni", "Tutto"], index=0, key=dash_key("dash_periodo"))
        with filters[1]:
            imm_sel = st.selectbox("Immobile", ["Tutti"] + immobili, index=0, key=dash_key("dash_imm"))
        with filters[2]:
            stato_sel = st.selectbox("Stato", ["Tutti", "Pagato", "Da pagare"], index=0, key=dash_key("dash_stato"))

        dff = df.copy()
        if anno_mode == "Ultimi 3 anni":
            dff = dff[dff["esercizio"].isin(anni_last3)]
        if imm_sel != "Tutti":
            dff = dff[dff["immobile"] == imm_sel]
        if stato_sel != "Tutti":
            dff = dff[dff["stato"] == stato_sel]

        pagato = float(pd.to_numeric(dff.loc[dff["stato"] == "Pagato", "importo"], errors="coerce").fillna(0).sum())
        da_pagare = float(pd.to_numeric(dff.loc[dff["stato"] == "Da pagare", "importo"], errors="coerce").fillna(0).sum())
        totale = float(pd.to_numeric(dff["importo"], errors="coerce").fillna(0).sum())

        k1, k2, k3 = st.columns(3)
        k1.metric("Totale Pagato (€)", f"{pagato:,.2f}")
        k2.metric("Totale Da pagare (€)", f"{da_pagare:,.2f}")
        k3.metric("Totale Generale (€)", f"{totale:,.2f}")

        rb = st.columns([1, 4])
        with rb[0]:
            if st.button("↩️ Reset", key=dash_key("dash_reset"), use_container_width=True):
                reset_dashboard()

        st.divider()

        if dff.empty:
            st.info("Non ci sono pagamenti/spese che soddisfano i criteri selezionati.")
        else:
            grp = (dff.groupby("esercizio", as_index=False)["importo"].sum().sort_values("esercizio"))
            grp["label"] = grp["importo"].map(lambda x: f"€ {float(x):,.0f}")

            fig = px.bar(grp, x="esercizio", y="importo", text="label")
            fig.update_traces(textposition="outside", textfont_size=18, cliponaxis=False)
            fig.update_layout(
                xaxis_title="Anno (Esercizio)",
                yaxis_title="Importo",
                xaxis=dict(
                    type="category",
                    tickmode="array",
                    tickvals=grp["esercizio"].tolist(),
                    ticktext=[str(int(y)) for y in grp["esercizio"].tolist()],
                ),
                uniformtext_minsize=16,
                uniformtext_mode="show",
            )
            st.plotly_chart(fig, use_container_width=True)

        st.divider()
        st.markdown('<div class="muted">Dettaglio righe (ordinate per scadenza crescente)</div>', unsafe_allow_html=True)

        if dff.empty:
            st.write("Nessuna riga da mostrare.")
        else:
            det = dff.sort_values(["scadenza_dt", "immobile", "esercizio", "numero_rata"], ascending=True).copy()
            det["numero rata"] = compute_rata_display(det)
            det["importo"] = det["importo"].apply(euro)

            det = det[[
                "immobile",
                "esercizio",
                "tipo_spesa",
                "numero rata",
                "importo",
                "scadenza",
                "stato",
                "data_pagamento",
                "note"
            ]]
            st.dataframe(style_font_by_status(det, stato_col="stato", scad_col="scadenza"), use_container_width=True)

            total_det = float(pd.to_numeric(dff["importo"], errors="coerce").fillna(0).sum())
            st.success(f"**Totale righe (somma importi): € {total_det:,.2f}**")

    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# IMPOSTAZIONI (NEW TAB)
# =========================================================
with tabs[4]:
    st.markdown('<div class="card"><div class="card-title">Impostazioni</div>', unsafe_allow_html=True)
    st.markdown('<div class="muted">Da qui puoi chiudere l’applicazione in modo sicuro.</div>', unsafe_allow_html=True)
    st.divider()

    st.warning("Chiudendo l’app, tutte le sessioni verranno interrotte e la pagina non sarà più raggiungibile.")

    cols = st.columns([1.2, 3.8])
    with cols[0]:
        # Bottone "normale" (stile in linea con gli altri), non primary
        if st.button("🚪 Exit", use_container_width=True, key="exit_btn"):
            st.session_state["_exit_requested"] = True
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
