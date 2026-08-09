#!/usr/bin/env python3
"""
AELION — Discovery Call & Consultoría Prep PDF Generator

Generates styled HTML cheat sheets and converts to PDF via Chrome headless.
stdlib-only (no external packages).

Usage:
    python3 generate-call-prep.py discovery <data.json> [--output /path/to/output.pdf]
    python3 generate-call-prep.py consultoria <data.json> [--output /path/to/output.pdf]

Data JSON format: see TEMPLATE_DATA examples at bottom of file.
"""

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# ─── Brand constants ───────────────────────────────────────────────
NAVY = "#0a0e1a"
BLUE = "#4da6ff"
DARK_BLUE = "#1a3a5c"
LIGHT_BG = "#f8f9fa"
GREEN_BG = "#e8f5e9"
BORDER = "#dee2e6"
TEXT = "#212529"
MUTED = "#6c757d"


def html_escape(text):
    """Escape HTML special characters."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def build_discovery_html(data):
    """Build Discovery Call prep HTML from data dict."""
    d = data
    prospect_name = d.get("prospect_name", "—")
    business_name = d.get("business_name", "—")
    date_time = d.get("date_time", "—")
    duration = d.get("duration", "30 min")
    objective = d.get("objective", "Entender, NO vender")

    # Prospect info rows
    info_rows = ""
    for key, val in d.get("prospect_info", {}).items():
        info_rows += f"<tr><td class='label'>{html_escape(key)}:</td><td>{html_escape(str(val))}</td></tr>\n"

    # Context block
    context_html = ""
    if d.get("context"):
        context_html = f"""
        <div class="section">
            <h2>CONTEXTO</h2>
            <p>{html_escape(d['context'])}</p>
            {f'<p class="role-instruction">&rarr; {html_escape(d.get("role_instruction", ""))}</p>' if d.get("role_instruction") else ''}
        </div>"""

    # What they said
    said_html = ""
    if d.get("what_they_said"):
        said_html = f"""
        <div class="section">
            <h2>LO QUE DIJO (TEXTUAL)</h2>
            <blockquote>{html_escape(d['what_they_said'])}</blockquote>
        </div>"""

    # Pain translation table
    pain_html = ""
    if d.get("pain_translation"):
        rows = ""
        for p in d["pain_translation"]:
            rows += f"""<tr>
                <td>"{html_escape(p['said'])}"</td>
                <td>{html_escape(p['means'])}</td>
                <td>{html_escape(p['question'])}</td>
            </tr>"""
        pain_html = f"""
        <div class="section">
            <h2>TRADUCCIÓN DEL DOLOR</h2>
            <table class="pain-table">
                <tr class="header-row"><th>Lo que dijo</th><th>Lo que significa</th><th>Pregunta para profundizar</th></tr>
                {rows}
            </table>
        </div>"""

    # Call structure phases
    phases_html = ""
    for phase in d.get("phases", []):
        script = ""
        if phase.get("script"):
            script = f'<div class="script-block">{html_escape(phase["script"])}</div>'

        bullets = ""
        if phase.get("bullets"):
            items = "".join(f"<li>{html_escape(b)}</li>" for b in phase["bullets"])
            bullets = f"<ul>{items}</ul>"

        sub_sections = ""
        if phase.get("sub_sections"):
            for sub in phase["sub_sections"]:
                sub_items = "".join(f"<li>{html_escape(q)}</li>" for q in sub.get("questions", []))
                sub_sections += f"""
                <div class="sub-section">
                    <h4>{html_escape(sub['title'])}</h4>
                    <ul>{sub_items}</ul>
                </div>"""

        note = ""
        if phase.get("note"):
            note = f'<p class="phase-note">{html_escape(phase["note"])}</p>'

        phases_html += f"""
        <div class="phase">
            <h3>{html_escape(phase['title'])}</h3>
            {note}
            {script}
            {bullets}
            {sub_sections}
        </div>"""

    # Shooting bullets
    bullets_html = ""
    if d.get("shooting_bullets"):
        items = "".join(f"<li>{html_escape(b)}</li>" for b in d["shooting_bullets"])
        bullets_html = f"""
        <div class="section">
            <h2>SHOOTING BULLETS — Soluciones para su vertical</h2>
            <p class="muted">Mencionar naturalmente durante la conversación, NO como pitch.</p>
            <ul class="bullets-list">{items}</ul>
        </div>"""

    # Solutions table (only if asked)
    solutions_html = ""
    if d.get("solutions"):
        rows = ""
        for s in d["solutions"]:
            rows += f"<tr><td>{html_escape(s['problem'])}</td><td>{html_escape(s['solution'])}</td></tr>"
        solutions_html = f"""
        <div class="section">
            <h2>SOLUCIONES POSIBLES (SOLO SI PREGUNTA)</h2>
            <table class="solutions-table">
                <tr class="header-row"><th>Problema</th><th>Solución IA/Automatización</th></tr>
                {rows}
            </table>
        </div>"""

    # Objection handling
    objections_html = ""
    if d.get("objections"):
        items = ""
        for obj in d["objections"]:
            items += f"""
            <div class="objection">
                <h4>"{html_escape(obj['trigger'])}"</h4>
                <div class="script-block">{html_escape(obj['response'])}</div>
            </div>"""
        objections_html = f"""
        <div class="section">
            <h2>SI TE PREGUNTA O DICE...</h2>
            {items}
        </div>"""

    # Active listening prompts
    listening_html = ""
    if d.get("listening_prompts"):
        items = "".join(f"<li>{html_escape(p)}</li>" for p in d["listening_prompts"])
        listening_html = f"""
        <div class="section highlight-section">
            <h2>PROMPTS DE ESCUCHA ACTIVA</h2>
            <ul>{items}</ul>
        </div>"""

    # Post-call checklist
    postcall_html = ""
    if d.get("post_call"):
        items = "".join(f"<li>{html_escape(p)}</li>" for p in d["post_call"])
        postcall_html = f"""
        <div class="section">
            <h2>POST-LLAMADA (hacer inmediatamente después)</h2>
            <ul class="checklist">{items}</ul>
        </div>"""

    # Do / Don't
    dos_donts_html = ""
    if d.get("do_list") or d.get("dont_list"):
        donts = ""
        if d.get("dont_list"):
            items = "".join(f"<li>{html_escape(x)}</li>" for x in d["dont_list"])
            donts = f"<div class='half'><h3 class='dont'>Lo que NO hacer:</h3><ul>{items}</ul></div>"
        dos = ""
        if d.get("do_list"):
            items = "".join(f"<li>{html_escape(x)}</li>" for x in d["do_list"])
            dos = f"<div class='half'><h3 class='do'>Lo que SÍ hacer:</h3><ul>{items}</ul></div>"
        dos_donts_html = f"""
        <div class="section dos-donts">
            {donts}{dos}
        </div>"""

    # Remember section
    remember_html = ""
    if d.get("remember"):
        remember_html = f"""
        <div class="section remember-section">
            <h2>RECUERDA</h2>
            <p>{html_escape(d['remember'])}</p>
        </div>"""

    # Objective
    goal_html = ""
    if d.get("goal"):
        goal_html = f"""
        <div class="section goal-section">
            <h2>TU OBJETIVO</h2>
            <p>Que al colgar {html_escape(prospect_name)} piense:</p>
            <div class="script-block">{html_escape(d['goal'])}</div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Discovery Call: {html_escape(prospect_name)}</title>
<style>
@page {{ size: letter; margin: 1.5cm 2cm; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    color: {TEXT};
    line-height: 1.5;
    font-size: 11px;
    padding: 20px 30px;
}}
.header {{
    text-align: center;
    margin-bottom: 20px;
    padding-bottom: 15px;
    border-bottom: 3px solid {DARK_BLUE};
}}
.header h1 {{
    font-size: 22px;
    color: {DARK_BLUE};
    margin-bottom: 4px;
    text-transform: uppercase;
    letter-spacing: 1px;
}}
.header .subtitle {{
    font-size: 14px;
    color: {MUTED};
}}
.header .meta {{
    font-size: 11px;
    color: {MUTED};
    margin-top: 4px;
}}
.section {{
    margin-bottom: 18px;
    page-break-inside: avoid;
}}
h2 {{
    font-size: 14px;
    color: {DARK_BLUE};
    border-bottom: 2px solid {BLUE};
    padding-bottom: 4px;
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
h3 {{
    font-size: 12px;
    color: {DARK_BLUE};
    margin-bottom: 4px;
}}
h4 {{
    font-size: 11px;
    color: {DARK_BLUE};
    margin-bottom: 3px;
}}
.info-table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 8px;
}}
.info-table td {{
    padding: 3px 8px;
    border-bottom: 1px solid #eee;
    font-size: 11px;
}}
.info-table .label {{
    font-weight: 700;
    width: 140px;
    color: {DARK_BLUE};
}}
.pain-table, .solutions-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 10.5px;
}}
.pain-table th, .solutions-table th {{
    background: {DARK_BLUE};
    color: white;
    padding: 6px 8px;
    text-align: left;
    font-size: 10.5px;
}}
.pain-table td, .solutions-table td {{
    padding: 6px 8px;
    border-bottom: 1px solid {BORDER};
    vertical-align: top;
}}
.pain-table tr:nth-child(even), .solutions-table tr:nth-child(even) {{
    background: {LIGHT_BG};
}}
blockquote {{
    background: {LIGHT_BG};
    border-left: 4px solid {BLUE};
    padding: 10px 14px;
    font-style: italic;
    margin: 8px 0;
    font-size: 11px;
}}
.script-block {{
    background: {GREEN_BG};
    border-left: 4px solid #4caf50;
    padding: 10px 14px;
    font-style: italic;
    margin: 6px 0;
    font-size: 10.5px;
}}
.role-instruction {{
    color: #e65100;
    font-style: italic;
    font-weight: 600;
}}
.phase {{
    margin-bottom: 14px;
    padding-left: 8px;
    border-left: 2px solid #e0e0e0;
}}
.phase h3 {{
    background: {DARK_BLUE};
    color: white;
    padding: 4px 10px;
    margin-left: -10px;
    font-size: 11.5px;
}}
.phase-note {{
    font-size: 10px;
    color: {MUTED};
    font-style: italic;
    margin: 4px 0;
}}
.sub-section {{
    margin: 6px 0 6px 10px;
}}
.sub-section h4 {{
    font-weight: 700;
}}
ul {{
    padding-left: 18px;
    margin: 4px 0;
}}
li {{
    margin-bottom: 3px;
    font-size: 10.5px;
}}
.bullets-list li {{
    background: {LIGHT_BG};
    padding: 4px 8px;
    margin-bottom: 4px;
    list-style: none;
    border-left: 3px solid {BLUE};
}}
.bullets-list {{
    padding-left: 0;
}}
.checklist li {{
    list-style: none;
    padding-left: 5px;
}}
.checklist li::before {{
    content: "\\25A2  ";
    font-size: 13px;
}}
.highlight-section {{
    background: #fff8e1;
    padding: 10px 14px;
    border-radius: 4px;
}}
.objection h4 {{
    color: #c62828;
    margin-top: 8px;
}}
.dos-donts {{
    display: flex;
    gap: 16px;
}}
.dos-donts .half {{
    flex: 1;
}}
.dont {{ color: #c62828; }}
.do {{ color: #2e7d32; }}
.remember-section {{
    background: #fce4ec;
    padding: 12px 16px;
    border-radius: 4px;
    border-left: 4px solid #c62828;
}}
.remember-section h2 {{
    color: #c62828;
    border-bottom-color: #c62828;
}}
.goal-section {{
    background: {GREEN_BG};
    padding: 12px 16px;
    border-radius: 4px;
}}
.goal-section h2 {{
    color: #2e7d32;
    border-bottom-color: #2e7d32;
}}
.muted {{
    color: {MUTED};
    font-size: 10px;
    font-style: italic;
}}
.page-break {{
    page-break-before: always;
}}
</style>
</head>
<body>

<div class="header">
    <h1>Discovery Call: {html_escape(prospect_name)} — {html_escape(business_name)}</h1>
    <div class="subtitle">{html_escape(date_time)} | Duración: {html_escape(duration)} | Objetivo: {html_escape(objective)}</div>
</div>

<div class="section">
    <h2>INFORMACIÓN DEL PROSPECTO</h2>
    <table class="info-table">{info_rows}</table>
</div>

{context_html}
{said_html}
{pain_html}

<div class="section">
    <h2>ESTRUCTURA DE LA LLAMADA</h2>
    {phases_html}
</div>

{bullets_html}
{listening_html}
{solutions_html}
{objections_html}
{dos_donts_html}
{postcall_html}
{remember_html}
{goal_html}

</body>
</html>"""


def build_consultoria_html(data):
    """Build Consultoría de IA (AI Audit) prep HTML from data dict."""
    d = data
    prospect_name = d.get("prospect_name", "—")
    business_name = d.get("business_name", "—")
    date_time = d.get("date_time", "—")
    duration = d.get("duration", "60-90 min")
    objective = d.get("objective", "Diagnóstico profundo")
    investment = d.get("investment", "$15,000 MXN")

    # Prospect info rows
    info_rows = ""
    for key, val in d.get("prospect_info", {}).items():
        info_rows += f"<tr><td class='label'>{html_escape(key)}:</td><td>{html_escape(str(val))}</td></tr>\n"

    # Pre-diagnostic checklist
    checklist_html = ""
    if d.get("pre_diagnostic_checklist"):
        items = "".join(f"<li>{html_escape(c)}</li>" for c in d["pre_diagnostic_checklist"])
        checklist_html = f"""
        <div class="section">
            <h2>PRE-REQUISITOS</h2>
            <ul class="checklist">{items}</ul>
        </div>"""

    # Discovery findings
    findings_html = ""
    if d.get("discovery_findings"):
        findings_html = f"""
        <div class="section">
            <h2>HALLAZGOS DE LA DISCOVERY CALL</h2>
            <div class="script-block">{html_escape(d['discovery_findings'])}</div>
        </div>"""

    # Growth Scanner 8 variables
    scanner_html = ""
    if d.get("growth_scanner_variables"):
        vars_content = ""
        for var in d["growth_scanner_variables"]:
            deep_items = "".join(f"<li>{html_escape(q)}</li>" for q in var.get("deep_dive", []))
            hyp = ""
            if var.get("hypothesis_alan"):
                hyp = f'<div class="hypothesis"><strong>Hipótesis:</strong> {html_escape(var["hypothesis_alan"])}</div>'
            vars_content += f"""
            <div class="scanner-variable">
                <div class="var-header">
                    <span class="var-number">{var['number']}</span>
                    <span class="var-name">{html_escape(var['name'])}</span>
                    <span class="var-desc">{html_escape(var['description'])}</span>
                </div>
                <div class="var-entry">
                    <strong>Pregunta de entrada:</strong> {html_escape(var.get('entry_question', ''))}
                </div>
                {hyp}
                <div class="var-deep">
                    <strong>Profundización (Monk 5 Whys):</strong>
                    <ul>{deep_items}</ul>
                </div>
            </div>"""
        scanner_html = f"""
        <div class="section">
            <h2>GROWTH SCANNER — 8 VARIABLES</h2>
            <p class="muted">Recorrer las 8 variables. Para cada una: pregunta de entrada → profundizar con Monk → anotar datos reales + citas textuales.</p>
            {vars_content}
        </div>"""

    # Ops Canvas
    canvas_html = ""
    if d.get("ops_canvas_prep"):
        oc = d["ops_canvas_prep"]
        def canvas_col(title, items):
            li = "".join(f"<li>{html_escape(i)}</li>" for i in items)
            return f"<div class='canvas-col'><h4>{html_escape(title)}</h4><ul>{li}</ul></div>"
        canvas_html = f"""
        <div class="section">
            <h2>OPS CANVAS — MAPEAR EN VIVO</h2>
            <p class="muted">Dibujar con Alan. 3 columnas. Para cada paso: quién lo hace, qué herramienta usa, dónde se atasca.</p>
            <div class="canvas-grid">
                {canvas_col("Acquisition Engine", oc.get("acquisition_engine", []))}
                {canvas_col("Delivery Engine", oc.get("delivery_engine", []))}
                {canvas_col("Support Engine", oc.get("support_engine", []))}
            </div>
        </div>"""

    # Opportunity Matrix
    matrix_html = ""
    if d.get("opportunity_matrix_hypotheses"):
        om = d["opportunity_matrix_hypotheses"]
        def matrix_quadrant(title, items, css_class):
            li = "".join(f"<li>{html_escape(i)}</li>" for i in items)
            return f"<div class='matrix-quad {css_class}'><h4>{html_escape(title)}</h4><ul>{li}</ul></div>"
        matrix_html = f"""
        <div class="section">
            <h2>OPPORTUNITY MATRIX (HIPÓTESIS — VALIDAR CON DATOS)</h2>
            <div class="matrix-grid">
                {matrix_quadrant("Quick Wins (Alto Impacto, Bajo Esfuerzo)", om.get("quick_wins", []), "qw")}
                {matrix_quadrant("Big Swings (Alto Impacto, Alto Esfuerzo)", om.get("big_swings", []), "bs")}
                {matrix_quadrant("Nice-to-Haves (Bajo Impacto, Bajo Esfuerzo)", om.get("nice_to_haves", []), "nth")}
                {matrix_quadrant("Deprioritize (Bajo Impacto, Alto Esfuerzo)", om.get("deprioritize", []), "dp")}
            </div>
        </div>"""

    # ROI Calculator prep
    roi_html = ""
    if d.get("roi_calculator_prep"):
        rc = d["roi_calculator_prep"]
        savings_rows = ""
        for s in rc.get("direct_savings", []):
            savings_rows += f"<tr><td>{html_escape(s['task'])}</td><td>{html_escape(s['hours_saved_per_week'])}</td><td>{html_escape(s['employees_affected'])}</td><td>{html_escape(s['hourly_rate'])}</td><td class='muted'>{html_escape(s.get('note', ''))}</td></tr>"
        uplift_rows = ""
        for u in rc.get("revenue_uplift", []):
            uplift_rows += f"<tr><td>{html_escape(u['opportunity'])}</td><td>{html_escape(u['estimated_value'])}</td><td class='muted'>{html_escape(u.get('note', ''))}</td></tr>"
        roi_html = f"""
        <div class="section">
            <h2>ROI CALCULATOR — DATOS POR RECOPILAR</h2>
            <p class="muted">Estos campos se llenan CON los números reales de Alan durante la entrevista. Sin datos reales, no hay Money Slide.</p>
            <h3>Ahorros Directos</h3>
            <table class="solutions-table">
                <tr class="header-row"><th>Tarea</th><th>Hrs/sem ahorradas</th><th>Empleados</th><th>$/hora</th><th>Nota</th></tr>
                {savings_rows}
            </table>
            <h3 style="margin-top:10px">Revenue Uplift</h3>
            <table class="solutions-table">
                <tr class="header-row"><th>Oportunidad</th><th>Valor estimado</th><th>Nota</th></tr>
                {uplift_rows}
            </table>
        </div>"""

    # Metrics to collect
    metrics_html = ""
    if d.get("metrics_to_collect"):
        items = "".join(f"<li>{html_escape(m)}</li>" for m in d["metrics_to_collect"])
        metrics_html = f"""
        <div class="section highlight-section">
            <h2>MÉTRICAS OBLIGATORIAS — NO SALIR SIN ESTOS DATOS</h2>
            <ul class="checklist">{items}</ul>
        </div>"""

    # Presentation structure
    pres_html = ""
    if d.get("presentation_structure"):
        ps = d["presentation_structure"]
        pres_html = f"""
        <div class="section">
            <h2>ESTRUCTURA DE LA PRESENTACIÓN (DÍAS 2-5)</h2>
            <div class="phase"><h3>Parte I: Identificación del Problema</h3><p>{html_escape(ps.get('part_1_problem', ''))}</p></div>
            <div class="phase"><h3>Parte II: Análisis</h3><p>{html_escape(ps.get('part_2_analysis', ''))}</p></div>
            <div class="phase"><h3>Parte III: Solución (Tiers)</h3><p>{html_escape(ps.get('part_3_solution', ''))}</p></div>
            <div class="phase"><h3>Parte IV: Próximos Pasos + ROI</h3><p>{html_escape(ps.get('part_4_next_steps', ''))}</p></div>
        </div>"""

    # Deliverables timeline
    timeline_html = ""
    if d.get("deliverables_timeline"):
        dt = d["deliverables_timeline"]
        rows = ""
        for key, val in dt.items():
            label = key.replace("_", " ").title()
            rows += f"<tr><td class='label'>{html_escape(label)}</td><td>{html_escape(val)}</td></tr>"
        timeline_html = f"""
        <div class="section">
            <h2>TIMELINE DE ENTREGA</h2>
            <table class="info-table">{rows}</table>
        </div>"""

    # Do / Don't
    dos_donts_html = ""
    if d.get("do_list") or d.get("dont_list"):
        donts = ""
        if d.get("dont_list"):
            items = "".join(f"<li>{html_escape(x)}</li>" for x in d["dont_list"])
            donts = f"<div class='half'><h3 class='dont'>Lo que NO hacer:</h3><ul>{items}</ul></div>"
        dos = ""
        if d.get("do_list"):
            items = "".join(f"<li>{html_escape(x)}</li>" for x in d["do_list"])
            dos = f"<div class='half'><h3 class='do'>Lo que SÍ hacer:</h3><ul>{items}</ul></div>"
        dos_donts_html = f"""
        <div class="section dos-donts">
            {donts}{dos}
        </div>"""

    # Remember
    remember_html = ""
    if d.get("remember"):
        remember_html = f"""
        <div class="section remember-section">
            <h2>RECUERDA</h2>
            <p>{html_escape(d['remember'])}</p>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Consultoría de IA: {html_escape(prospect_name)}</title>
<style>
@page {{ size: letter; margin: 1.5cm 2cm; }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    color: {TEXT};
    line-height: 1.5;
    font-size: 11px;
    padding: 20px 30px;
}}
.header {{
    text-align: center;
    margin-bottom: 20px;
    padding-bottom: 15px;
    border-bottom: 3px solid #0d47a1;
}}
.header h1 {{
    font-size: 22px;
    color: #0d47a1;
    margin-bottom: 4px;
    text-transform: uppercase;
    letter-spacing: 1px;
}}
.header .subtitle {{
    font-size: 13px;
    color: {MUTED};
}}
.header .investment {{
    font-size: 14px;
    color: #0d47a1;
    font-weight: 700;
    margin-top: 4px;
}}
.section {{
    margin-bottom: 18px;
    page-break-inside: avoid;
}}
h2 {{
    font-size: 14px;
    color: #0d47a1;
    border-bottom: 2px solid #1565c0;
    padding-bottom: 4px;
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
h3 {{
    font-size: 12px;
    color: #0d47a1;
    margin-bottom: 4px;
    margin-top: 8px;
}}
h4 {{
    font-size: 11px;
    color: #0d47a1;
    margin-bottom: 3px;
}}
.info-table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 8px;
}}
.info-table td {{
    padding: 3px 8px;
    border-bottom: 1px solid #eee;
    font-size: 11px;
}}
.info-table .label {{
    font-weight: 700;
    width: 140px;
    color: #0d47a1;
}}
.solutions-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 10px;
}}
.solutions-table th {{
    background: #0d47a1;
    color: white;
    padding: 5px 6px;
    text-align: left;
    font-size: 10px;
}}
.solutions-table td {{
    padding: 5px 6px;
    border-bottom: 1px solid {BORDER};
    vertical-align: top;
    font-size: 10px;
}}
.solutions-table tr:nth-child(even) {{
    background: {LIGHT_BG};
}}
.script-block {{
    background: #e3f2fd;
    border-left: 4px solid #1565c0;
    padding: 10px 14px;
    font-style: italic;
    margin: 6px 0;
    font-size: 10.5px;
}}
ul {{
    padding-left: 18px;
    margin: 4px 0;
}}
li {{
    margin-bottom: 3px;
    font-size: 10.5px;
}}
.checklist li {{
    list-style: none;
    padding-left: 5px;
}}
.checklist li::before {{
    content: "\\25A2  ";
    font-size: 13px;
}}
.highlight-section {{
    background: #fff8e1;
    padding: 10px 14px;
    border-radius: 4px;
}}
.scanner-variable {{
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 8px 10px;
    margin-bottom: 10px;
    page-break-inside: avoid;
}}
.var-header {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
}}
.var-number {{
    background: #0d47a1;
    color: white;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 11px;
    flex-shrink: 0;
}}
.var-name {{
    font-weight: 700;
    color: #0d47a1;
    font-size: 12px;
}}
.var-desc {{
    color: {MUTED};
    font-size: 10px;
}}
.var-entry {{
    background: #e8f5e9;
    padding: 6px 10px;
    border-radius: 3px;
    margin: 4px 0;
    font-size: 10.5px;
}}
.var-deep {{
    font-size: 10.5px;
    margin-top: 4px;
}}
.hypothesis {{
    background: #fff3e0;
    padding: 6px 10px;
    border-radius: 3px;
    margin: 4px 0;
    font-size: 10px;
    border-left: 3px solid #ff9800;
}}
.canvas-grid {{
    display: flex;
    gap: 10px;
}}
.canvas-col {{
    flex: 1;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 8px;
}}
.canvas-col h4 {{
    background: #0d47a1;
    color: white;
    padding: 4px 8px;
    border-radius: 3px;
    margin-bottom: 6px;
    text-align: center;
    font-size: 10px;
}}
.matrix-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
}}
.matrix-quad {{
    border-radius: 4px;
    padding: 8px;
    font-size: 10px;
}}
.matrix-quad h4 {{
    font-size: 10px;
    margin-bottom: 4px;
}}
.matrix-quad ul {{
    padding-left: 14px;
}}
.matrix-quad li {{
    font-size: 10px;
}}
.qw {{ background: #e8f5e9; border: 1px solid #4caf50; }}
.qw h4 {{ color: #2e7d32; }}
.bs {{ background: #e3f2fd; border: 1px solid #1565c0; }}
.bs h4 {{ color: #0d47a1; }}
.nth {{ background: #f3e5f5; border: 1px solid #7b1fa2; }}
.nth h4 {{ color: #7b1fa2; }}
.dp {{ background: #fafafa; border: 1px solid #bdbdbd; }}
.dp h4 {{ color: #757575; }}
.phase {{
    margin-bottom: 10px;
    padding-left: 8px;
    border-left: 2px solid #e0e0e0;
}}
.phase h3 {{
    background: #0d47a1;
    color: white;
    padding: 4px 10px;
    margin-left: -10px;
    font-size: 11px;
}}
.dos-donts {{
    display: flex;
    gap: 16px;
}}
.dos-donts .half {{
    flex: 1;
}}
.dont {{ color: #c62828; }}
.do {{ color: #2e7d32; }}
.remember-section {{
    background: #fce4ec;
    padding: 12px 16px;
    border-radius: 4px;
    border-left: 4px solid #c62828;
}}
.remember-section h2 {{
    color: #c62828;
    border-bottom-color: #c62828;
}}
.muted {{
    color: {MUTED};
    font-size: 10px;
    font-style: italic;
}}
</style>
</head>
<body>

<div class="header">
    <h1>Consultoría de IA: {html_escape(prospect_name)} — {html_escape(business_name)}</h1>
    <div class="subtitle">{html_escape(date_time)} | Duración: {html_escape(duration)} | {html_escape(objective)}</div>
    <div class="investment">Inversión: {html_escape(investment)}</div>
</div>

<div class="section">
    <h2>INFORMACIÓN DEL PROSPECTO</h2>
    <table class="info-table">{info_rows}</table>
</div>

{checklist_html}
{findings_html}
{scanner_html}
{canvas_html}
{matrix_html}
{roi_html}
{metrics_html}
{pres_html}
{timeline_html}
{dos_donts_html}
{remember_html}

</body>
</html>"""


def generate_pdf(html_content, output_path):
    """Convert HTML to PDF using Chrome headless."""
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
        f.write(html_content)
        tmp_html = f.name

    chrome_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    ]

    chrome = None
    for p in chrome_paths:
        if os.path.exists(p):
            chrome = p
            break

    if not chrome:
        print(f"[!] Chrome not found. HTML saved to: {tmp_html}")
        print(f"    Open in browser and Cmd+P to save as PDF.")
        return tmp_html

    result = subprocess.run(
        [chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={output_path}", f"file://{tmp_html}"],
        capture_output=True, text=True, timeout=30
    )

    os.unlink(tmp_html)

    if os.path.exists(output_path):
        print(f"[OK] PDF saved to: {output_path}")
        return output_path
    else:
        print(f"[!] PDF generation failed: {result.stderr}")
        return None


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 generate-call-prep.py discovery <data.json> [--output path.pdf]")
        sys.exit(1)

    doc_type = sys.argv[1]
    data_path = sys.argv[2]
    output = None

    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        output = sys.argv[idx + 1]

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not output:
        name_slug = data.get("prospect_name", "prospect").replace(" ", "-")
        output = os.path.expanduser(f"~/Desktop/Prep-{name_slug}.pdf")

    if doc_type == "discovery":
        html = build_discovery_html(data)
    elif doc_type == "consultoria":
        html = build_consultoria_html(data)
    else:
        print(f"Unknown type: {doc_type}. Use 'discovery' or 'consultoria'.")
        sys.exit(1)

    generate_pdf(html, output)
    subprocess.run(["open", output])


if __name__ == "__main__":
    main()
