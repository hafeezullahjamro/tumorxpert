from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

from jinja2 import Environment, select_autoescape
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

try:
    from weasyprint import HTML as WeasyHTML
except Exception:  # pragma: no cover - depends on optional OS libraries
    WeasyHTML = None

logger = logging.getLogger(__name__)

TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>{{ app_name }} Study Report</title>
    <style>
      @page { size: A4; margin: 24px; }
      body { font-family: "Segoe UI", sans-serif; color: #16313c; font-size: 12px; }
      .page { display: block; }
      .hero { background: linear-gradient(135deg, #103847 0%, #1b5366 100%); color: white; border-radius: 18px; padding: 24px; }
      .hero h1 { margin: 0 0 8px 0; font-size: 28px; }
      .hero-grid { width: 100%; margin-top: 18px; }
      .hero-grid td { vertical-align: top; padding-right: 16px; }
      h2 { color: #103847; margin-top: 26px; margin-bottom: 10px; font-size: 18px; }
      table { width: 100%; border-collapse: collapse; }
      th, td { padding: 10px 12px; text-align: left; }
      .metric-table { border: 1px solid #d7e3e8; border-radius: 14px; overflow: hidden; }
      .metric-table th { background: #eef5f8; color: #355766; width: 45%; }
      .metric-table td { border-top: 1px solid #e7eef1; }
      .chips { margin-top: 10px; }
      .chip { display: inline-block; background: #e7f4ef; color: #1f6d52; padding: 6px 10px; border-radius: 999px; margin: 0 6px 6px 0; font-size: 11px; font-weight: 600; }
      .chip.missing { background: #fdecec; color: #a83e3e; }
      .card-grid { width: 100%; margin-top: 8px; }
      .card-grid td { width: 33.3%; padding-right: 10px; vertical-align: top; }
      .stat-card { border: 1px solid #d7e3e8; border-radius: 14px; padding: 14px; background: #fbfdfe; }
      .stat-label { color: #5d7a86; font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; }
      .stat-value { font-size: 24px; color: #103847; font-weight: 700; margin-top: 6px; }
      .chart-row { margin-top: 10px; }
      .chart-label { margin-bottom: 4px; color: #355766; font-weight: 600; }
      .chart-track { width: 100%; height: 12px; border-radius: 999px; background: #e7eef1; overflow: hidden; }
      .chart-bar { height: 100%; border-radius: 999px; }
      .notes { border: 1px solid #fde0b2; background: #fff8ec; border-radius: 14px; padding: 14px 18px; }
      .thumb-grid { width: 100%; border-spacing: 10px; border-collapse: separate; }
      .thumb-grid td { width: 50%; vertical-align: top; }
      .thumb { border: 1px solid #d7e3e8; border-radius: 14px; padding: 10px; background: #fbfdfe; }
      .thumb img { width: 100%; border-radius: 10px; }
      .thumb figcaption { margin-top: 8px; color: #48636f; font-size: 11px; }
      footer { margin-top: 28px; color: #5d7a86; font-size: 10px; border-top: 1px solid #d7e3e8; padding-top: 10px; }
    </style>
  </head>
  <body>
    <div class="page">
      <section class="hero">
        <h1>{{ app_name }} MRI Report</h1>
        <div>Automated brain tumor MRI segmentation summary</div>
        <table class="hero-grid">
          <tr>
            <td>
              <div><strong>Study</strong></div>
              <div>{{ study_name }}</div>
            </td>
            <td>
              <div><strong>Study ID</strong></div>
              <div>{{ study_id }}</div>
            </td>
            <td>
              <div><strong>Generated</strong></div>
              <div>{{ generated_at }}</div>
            </td>
          </tr>
        </table>
      </section>

      <section>
        <h2>Detected Sequences</h2>
        <div class="chips">
          {% for name, present in sequences.items() %}
            <span class="chip {{ '' if present else 'missing' }}">{{ name.upper() }} {{ "YES" if present else "NO" }}</span>
          {% endfor %}
        </div>
      </section>

      <section>
        <h2>Key Findings</h2>
        <table class="card-grid">
          <tr>
            <td><div class="stat-card"><div class="stat-label">Whole Tumor</div><div class="stat-value">{{ metrics.wt_ml }}</div><div>mL</div></div></td>
            <td><div class="stat-card"><div class="stat-label">Tumor Core</div><div class="stat-value">{{ metrics.tc_ml }}</div><div>mL</div></div></td>
            <td><div class="stat-card"><div class="stat-label">Enhancing Tumor</div><div class="stat-value">{{ metrics.et_ml }}</div><div>mL</div></div></td>
          </tr>
        </table>
      </section>

      <section>
        <h2>Volume Profile</h2>
        {% for chart in charts %}
          <div class="chart-row">
            <div class="chart-label">{{ chart.label }} ({{ chart.value }} mL)</div>
            <div class="chart-track">
              <div class="chart-bar" style="width: {{ chart.width }}%; background: {{ chart.color }};"></div>
            </div>
          </div>
        {% endfor %}
      </section>

      <section>
        <h2>Segmentation Pipeline</h2>
        <table class="metric-table">
          <tr><th>Primary output</th><td>{{ segmentation_backend|upper }}</td></tr>
          <tr><th>Inference stack</th><td>nnU-Net + Swin UNETR + ensemble fusion</td></tr>
        </table>
      </section>

      <section>
        <h2>Quantitative Summary</h2>
        <table class="metric-table">
          <tr><th>Whole tumor (WT)</th><td>{{ metrics.wt_ml }} mL</td></tr>
          <tr><th>Tumor core (TC)</th><td>{{ metrics.tc_ml }} mL</td></tr>
          <tr><th>Enhancing tumor (ET)</th><td>{{ metrics.et_ml }} mL</td></tr>
          <tr><th>Edema/Core ratio</th><td>{{ metrics.edema_core_ratio }}</td></tr>
          <tr><th>Confidence summary</th><td>{{ metrics.confidence_summary }}</td></tr>
          <tr><th>Low-confidence fraction</th><td>{{ metrics.low_confidence_fraction }}</td></tr>
          {% if metrics.model_agreement_wt_dice is defined %}
          <tr><th>Model agreement (WT Dice)</th><td>{{ metrics.model_agreement_wt_dice }}</td></tr>
          {% endif %}
          {% if metrics.label_disagreement_ml is defined %}
          <tr><th>Label disagreement</th><td>{{ metrics.label_disagreement_ml }} mL</td></tr>
          {% endif %}
          <tr><th>Runtime</th><td>{{ metrics.runtime_sec }} s</td></tr>
        </table>
      </section>

      {% if model_metrics %}
      <section>
        <h2>Model Comparison</h2>
        <table class="metric-table">
          <tr>
            <th>Model</th>
            <th>WT</th>
            <th>TC</th>
            <th>ET</th>
            <th>Confidence</th>
          </tr>
          {% for name, model in model_metrics.items() %}
          <tr>
            <td>{{ name|replace('_', ' ')|title }}</td>
            <td>{{ model.wt_ml }}</td>
            <td>{{ model.tc_ml }}</td>
            <td>{{ model.et_ml }}</td>
            <td>{{ model.confidence_summary }}</td>
          </tr>
          {% endfor %}
        </table>
      </section>
      {% endif %}

      {% if qc_flags %}
      <section>
        <h2>QC Notes</h2>
        <div class="notes">
          <ul>
            {% for key, message in qc_flags.items() %}
            <li><strong>{{ key }}</strong>: {{ message }}</li>
            {% endfor %}
          </ul>
        </div>
      </section>
      {% endif %}

      {% if thumbnails %}
      <section>
        <h2>Selected Image Panels</h2>
        <table class="thumb-grid">
          <tr>
            {% for name, path in thumbnails.items() %}
            {% if loop.index <= 4 %}
            <td>
              <figure class="thumb">
                <img src="{{ path }}">
                <figcaption>{{ name|replace('_', ' ')|title }}</figcaption>
              </figure>
            </td>
            {% if loop.index is even %}</tr><tr>{% endif %}
            {% endif %}
            {% endfor %}
          </tr>
        </table>
      </section>
      {% endif %}

      <footer>
        Research use only. TumorXpert outputs are intended for technical validation and workflow review, not for clinical decision making.
      </footer>
    </div>
  </body>
</html>
"""


def _display_metric_name(key: str) -> str:
    mapping = {
        "wt_ml": "Whole Tumor (WT)",
        "tc_ml": "Tumor Core (TC)",
        "et_ml": "Enhancing Tumor (ET)",
        "edema_core_ratio": "Edema/Core Ratio",
        "confidence_summary": "Confidence Summary",
        "low_confidence_fraction": "Low-Confidence Fraction",
        "model_agreement_wt_dice": "Model Agreement (WT Dice)",
        "label_disagreement_ml": "Label Disagreement",
        "runtime_sec": "Runtime",
    }
    return mapping.get(key, key.replace("_", " ").title())


def _build_chart_rows(metrics: Dict[str, float]) -> list[dict[str, float | str]]:
    volumes = [
        ("Whole Tumor", float(metrics.get("wt_ml", 0.0)), "#0f766e"),
        ("Tumor Core", float(metrics.get("tc_ml", 0.0)), "#0284c7"),
        ("Enhancing Tumor", float(metrics.get("et_ml", 0.0)), "#ea580c"),
    ]
    max_value = max((value for _, value, _ in volumes), default=1.0) or 1.0
    return [
        {
            "label": label,
            "value": round(value, 2),
            "width": max(8.0, (value / max_value) * 100.0) if value > 0 else 0.0,
            "color": color,
        }
        for label, value, color in volumes
    ]


def _build_volume_chart(metrics: Dict[str, float]) -> Drawing:
    drawing = Drawing(430, 170)
    drawing.add(String(0, 152, "Tumor Volume Profile", fontName="Helvetica-Bold", fontSize=13, fillColor=colors.HexColor("#103847")))
    values = [
        ("WT", float(metrics.get("wt_ml", 0.0)), colors.HexColor("#0f766e")),
        ("TC", float(metrics.get("tc_ml", 0.0)), colors.HexColor("#0284c7")),
        ("ET", float(metrics.get("et_ml", 0.0)), colors.HexColor("#ea580c")),
    ]
    max_value = max((value for _, value, _ in values), default=1.0) or 1.0
    bar_left = 70
    bar_width = 300
    bar_height = 18
    start_y = 118

    for index, (label, value, color) in enumerate(values):
        y = start_y - index * 38
        drawing.add(String(0, y + 3, label, fontName="Helvetica-Bold", fontSize=11, fillColor=colors.HexColor("#355766")))
        drawing.add(Rect(bar_left, y, bar_width, bar_height, rx=8, ry=8, fillColor=colors.HexColor("#e7eef1"), strokeColor=None))
        filled_width = 0 if value <= 0 else max(12, (value / max_value) * bar_width)
        drawing.add(Rect(bar_left, y, filled_width, bar_height, rx=8, ry=8, fillColor=color, strokeColor=None))
        drawing.add(String(bar_left + bar_width + 10, y + 3, f"{value:.2f} mL", fontName="Helvetica", fontSize=10, fillColor=colors.HexColor("#16313c")))
    return drawing


def _build_quality_chart(metrics: Dict[str, float]) -> Drawing:
    drawing = Drawing(430, 148)
    drawing.add(String(0, 130, "Run Summary", fontName="Helvetica-Bold", fontSize=13, fillColor=colors.HexColor("#103847")))
    confidence = float(metrics.get("confidence_summary", 0.0))
    low_confidence_fraction = float(metrics.get("low_confidence_fraction", 0.0))
    agreement = metrics.get("model_agreement_wt_dice")
    runtime = float(metrics.get("runtime_sec", 0.0))
    items = [
        ("Confidence", confidence, 1.0, colors.HexColor("#16a34a")),
        ("Low-Confidence", low_confidence_fraction, 1.0, colors.HexColor("#dc2626")),
        ("Runtime", runtime, max(runtime, 1.0), colors.HexColor("#64748b")),
    ]
    if agreement is not None:
        items.insert(1, ("Agreement", float(agreement), 1.0, colors.HexColor("#2563eb")))
    bar_left = 95
    bar_width = 250
    bar_height = 14
    start_y = 100
    for index, (label, value, max_value, color) in enumerate(items):
        y = start_y - index * 28
        width = max(10, (value / max_value) * bar_width) if value > 0 else 0
        drawing.add(String(0, y + 2, label, fontName="Helvetica-Bold", fontSize=10, fillColor=colors.HexColor("#355766")))
        drawing.add(Rect(bar_left, y, bar_width, bar_height, rx=7, ry=7, fillColor=colors.HexColor("#e7eef1"), strokeColor=None))
        drawing.add(Rect(bar_left, y, width, bar_height, rx=7, ry=7, fillColor=color, strokeColor=None))
        suffix = " s" if label == "Runtime" else ""
        drawing.add(String(bar_left + bar_width + 10, y + 2, f"{value:.2f}{suffix}", fontName="Helvetica", fontSize=10, fillColor=colors.HexColor("#16313c")))
    return drawing


def _build_reportlab_story(
    *,
    app_name: str,
    study_name: str,
    study_id: str,
    sequences: Dict[str, bool],
    metrics: Dict[str, float],
    model_metrics: Dict[str, Dict[str, float]],
    segmentation_backend: str,
    qc_flags: Dict[str, str],
    thumbnails: Optional[Dict[str, Path]],
    generated_at: str,
):
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#103847"),
        spaceAfter=10,
    )
    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=20,
        textColor=colors.HexColor("#103847"),
        spaceBefore=8,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#16313c"),
    )
    caption_style = ParagraphStyle(
        "Caption",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#48636f"),
        alignment=1,
    )

    story = [
        Paragraph(f"{app_name} MRI Report", title_style),
        Paragraph(
            f"<b>Study:</b> {study_name}<br/><b>Study ID:</b> {study_id}<br/><b>Generated:</b> {generated_at}",
            body_style,
        ),
        Spacer(1, 12),
    ]

    sequence_row = []
    for name, present in sequences.items():
        color = colors.HexColor("#e7f4ef") if present else colors.HexColor("#fdecec")
        text_color = colors.HexColor("#1f6d52") if present else colors.HexColor("#a83e3e")
        cell = Table(
            [[Paragraph(f"<font color='{text_color.hexval()}'><b>{name.upper()}</b> {'YES' if present else 'NO'}</font>", body_style)]],
            colWidths=[1.25 * inch],
        )
        cell.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), color),
                    ("BOX", (0, 0), (-1, -1), 0, color),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        sequence_row.append(cell)

    story.extend(
        [
            Paragraph("Detected Sequences", heading_style),
            Table([sequence_row], colWidths=[1.35 * inch] * len(sequence_row)),
            Spacer(1, 14),
            Paragraph("Segmentation Pipeline", heading_style),
        ]
    )

    pipeline_table = Table(
        [
            ["Primary Output", segmentation_backend.upper()],
            ["Inference Stack", "nnU-Net + Swin UNETR + ensemble fusion"],
        ],
        colWidths=[2.0 * inch, 2.8 * inch],
        hAlign="LEFT",
    )
    pipeline_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef5f8")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d7e3e8")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend(
        [
            pipeline_table,
            Spacer(1, 14),
            Paragraph("Quantitative Summary", heading_style),
        ]
    )

    metric_rows = [[Paragraph("<b>Metric</b>", body_style), Paragraph("<b>Value</b>", body_style)]]
    for key in (
        "wt_ml",
        "tc_ml",
        "et_ml",
        "edema_core_ratio",
        "confidence_summary",
        "low_confidence_fraction",
        "model_agreement_wt_dice",
        "label_disagreement_ml",
        "runtime_sec",
    ):
        value = metrics.get(key)
        if value is None:
            continue
        suffix = " mL" if key.endswith("_ml") else " s" if key == "runtime_sec" else ""
        metric_rows.append([_display_metric_name(key), f"{value}{suffix}"])

    metrics_table = Table(metric_rows, colWidths=[2.6 * inch, 2.2 * inch], hAlign="LEFT")
    metrics_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef5f8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#355766")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d7e3e8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fbfdfe")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend([metrics_table, Spacer(1, 14), _build_volume_chart(metrics), Spacer(1, 10), _build_quality_chart(metrics)])

    if model_metrics:
        comparison_rows = [["Model", "WT", "TC", "ET", "Confidence"]]
        for name, values in model_metrics.items():
            comparison_rows.append(
                [
                    name.replace("_", " ").title(),
                    f"{float(values.get('wt_ml', 0.0)):.2f}",
                    f"{float(values.get('tc_ml', 0.0)):.2f}",
                    f"{float(values.get('et_ml', 0.0)):.2f}",
                    f"{float(values.get('confidence_summary', 0.0)):.3f}",
                ]
            )
        comparison_table = Table(
            comparison_rows,
            colWidths=[1.6 * inch, 0.9 * inch, 0.9 * inch, 0.9 * inch, 1.1 * inch],
            hAlign="LEFT",
        )
        comparison_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef5f8")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d7e3e8")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.extend([Spacer(1, 12), Paragraph("Model Comparison", heading_style), comparison_table])

    if qc_flags:
        note_items = "<br/>".join(f"&bull; <b>{key}</b>: {message}" for key, message in qc_flags.items())
        story.extend([Spacer(1, 12), Paragraph("QC Notes", heading_style), Paragraph(note_items, body_style)])

    if thumbnails:
        selected_items = list(thumbnails.items())[:4]
        if selected_items:
            story.extend([Spacer(1, 12), Paragraph("Selected Image Panels", heading_style)])
            image_rows = []
            current_row = []
            for name, path in selected_items:
                current_row.append(
                    Table(
                        [
                            [Image(str(path), width=2.45 * inch, height=1.85 * inch)],
                            [Paragraph(name.replace("_", " ").title(), caption_style)],
                        ],
                        colWidths=[2.55 * inch],
                    )
                )
                if len(current_row) == 2:
                    image_rows.append(current_row)
                    current_row = []
            if current_row:
                while len(current_row) < 2:
                    current_row.append("")
                image_rows.append(current_row)
            story.append(Table(image_rows, colWidths=[2.7 * inch, 2.7 * inch], hAlign="LEFT", spaceBefore=6))

    story.extend(
        [
            Spacer(1, 16),
            Paragraph(
                "Research use only. TumorXpert outputs are intended for technical validation and workflow review, not for clinical decision making.",
                ParagraphStyle(
                    "Footer",
                    parent=body_style,
                    fontSize=8.5,
                    textColor=colors.HexColor("#5d7a86"),
                ),
            ),
        ]
    )
    return story


def generate_pdf_report(
    *,
    app_name: str,
    study_name: str,
    study_id: str,
    sequences: Dict[str, bool],
    metrics: Dict[str, float],
    model_metrics: Dict[str, Dict[str, float]],
    segmentation_backend: str,
    qc_flags: Dict[str, str],
    thumbnails: Optional[Dict[str, Path]],
    output_path: Path,
    generated_at: str,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if WeasyHTML is not None:
        env = Environment(autoescape=select_autoescape(["html"]))
        template = env.from_string(TEMPLATE)
        rendered = template.render(
            app_name=app_name,
            study_name=study_name,
            study_id=study_id,
            sequences=sequences,
            metrics=metrics,
            model_metrics=model_metrics,
            segmentation_backend=segmentation_backend,
            qc_flags=qc_flags,
            thumbnails={k: str(v) for k, v in (thumbnails or {}).items()},
            charts=_build_chart_rows(metrics),
            generated_at=generated_at,
        )
        try:
            WeasyHTML(string=rendered, base_url=str(output_path.parent)).write_pdf(
                str(output_path)
            )
        except Exception as exc:
            logger.warning("WeasyPrint rendering failed; using ReportLab fallback: %s", exc)
        else:
            logger.info("Generated PDF report with WeasyPrint at %s", output_path)
            return output_path

    logger.info("Generating report with ReportLab fallback PDF.")
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=24,
        rightMargin=24,
        topMargin=24,
        bottomMargin=24,
    )
    story = _build_reportlab_story(
        app_name=app_name,
        study_name=study_name,
        study_id=study_id,
        sequences=sequences,
        metrics=metrics,
        model_metrics=model_metrics,
        segmentation_backend=segmentation_backend,
        qc_flags=qc_flags,
        thumbnails=thumbnails,
        generated_at=generated_at,
    )
    doc.build(story)
    logger.info("Generated PDF report with ReportLab fallback at %s", output_path)
    return output_path
