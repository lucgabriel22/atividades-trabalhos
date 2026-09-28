"""Gera o relatório técnico diagramado da NexoFrota."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable,
    HRFlowable,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).parents[1]
OUTPUT = ROOT / "relatorio_tecnico_nexofrota.pdf"

NAVY = colors.HexColor("#0F172A")
SLATE = colors.HexColor("#334155")
MUTED = colors.HexColor("#64748B")
LIGHT = colors.HexColor("#F1F5F9")
LINE = colors.HexColor("#CBD5E1")
BLUE = colors.HexColor("#2563EB")
CYAN = colors.HexColor("#0891B2")
GREEN = colors.HexColor("#059669")
AMBER = colors.HexColor("#D97706")
RED = colors.HexColor("#DC2626")
WHITE = colors.white


def register_fonts() -> tuple[str, str]:
    candidates = [
        (
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/arialbd.ttf"),
        ),
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
    ]
    for regular, bold in candidates:
        if regular.exists() and bold.exists():
            pdfmetrics.registerFont(TTFont("NexoRegular", str(regular)))
            pdfmetrics.registerFont(TTFont("NexoBold", str(bold)))
            return "NexoRegular", "NexoBold"
    return "Helvetica", "Helvetica-Bold"


FONT, FONT_BOLD = register_fonts()


def styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "cover_kicker": ParagraphStyle(
            "CoverKicker",
            parent=sample["Normal"],
            fontName=FONT_BOLD,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#67E8F9"),
            spaceAfter=10,
            tracking=1.4,
        ),
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=sample["Title"],
            fontName=FONT_BOLD,
            fontSize=35,
            leading=39,
            textColor=WHITE,
            alignment=TA_LEFT,
            spaceAfter=14,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle",
            parent=sample["Normal"],
            fontName=FONT,
            fontSize=15,
            leading=22,
            textColor=colors.HexColor("#CBD5E1"),
            spaceAfter=24,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=sample["Heading1"],
            fontName=FONT_BOLD,
            fontSize=22,
            leading=27,
            textColor=NAVY,
            spaceBefore=6,
            spaceAfter=12,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=sample["Heading2"],
            fontName=FONT_BOLD,
            fontSize=14,
            leading=18,
            textColor=BLUE,
            spaceBefore=12,
            spaceAfter=7,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=sample["BodyText"],
            fontName=FONT,
            fontSize=9.3,
            leading=14.2,
            textColor=SLATE,
            alignment=TA_LEFT,
            spaceAfter=7,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=sample["BodyText"],
            fontName=FONT,
            fontSize=7.8,
            leading=11,
            textColor=MUTED,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=sample["Normal"],
            fontName=FONT_BOLD,
            fontSize=8,
            leading=10,
            textColor=WHITE,
        ),
        "table_cell": ParagraphStyle(
            "TableCell",
            parent=sample["Normal"],
            fontName=FONT,
            fontSize=7.5,
            leading=10,
            textColor=SLATE,
        ),
        "callout_title": ParagraphStyle(
            "CalloutTitle",
            parent=sample["Normal"],
            fontName=FONT_BOLD,
            fontSize=9,
            leading=12,
            textColor=NAVY,
            spaceAfter=3,
        ),
        "callout_body": ParagraphStyle(
            "CalloutBody",
            parent=sample["Normal"],
            fontName=FONT,
            fontSize=8.2,
            leading=12,
            textColor=SLATE,
        ),
        "code": ParagraphStyle(
            "Code",
            parent=sample["Code"],
            fontName="Courier",
            fontSize=7.2,
            leading=10,
            textColor=colors.HexColor("#E2E8F0"),
        ),
        "toc": ParagraphStyle(
            "Toc",
            parent=sample["BodyText"],
            fontName=FONT,
            fontSize=10,
            leading=18,
            textColor=SLATE,
        ),
    }


STYLES = styles()


class ArchitectureDiagram(Flowable):
    def __init__(self, width: float = 170 * mm, height: float = 80 * mm) -> None:
        super().__init__()
        self.width = width
        self.height = height

    def draw(self) -> None:
        canvas = self.canv
        canvas.saveState()
        canvas.setFillColor(LIGHT)
        canvas.roundRect(0, 0, self.width, self.height, 10, stroke=0, fill=1)

        self._box(57 * mm, 58 * mm, 56 * mm, 13 * mm, "Streamlit", "mapa e dashboard", BLUE)
        self._box(57 * mm, 35 * mm, 56 * mm, 13 * mm, "FleetService", "orquestração", CYAN)
        self._box(8 * mm, 9 * mm, 66 * mm, 15 * mm, "PostgreSQL", "drivers + vehicles", GREEN)
        self._box(96 * mm, 9 * mm, 66 * mm, 15 * mm, "MongoDB", "telemetry + current", AMBER)

        canvas.setStrokeColor(MUTED)
        canvas.setLineWidth(1.4)
        self._arrow(85 * mm, 58 * mm, 85 * mm, 48 * mm)
        self._arrow(72 * mm, 35 * mm, 46 * mm, 24 * mm)
        self._arrow(98 * mm, 35 * mm, 129 * mm, 24 * mm)
        canvas.restoreState()

    def _box(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        title: str,
        subtitle: str,
        color: colors.Color,
    ) -> None:
        canvas = self.canv
        canvas.setFillColor(color)
        canvas.roundRect(x, y, width, height, 6, stroke=0, fill=1)
        canvas.setFillColor(WHITE)
        canvas.setFont(FONT_BOLD, 10)
        canvas.drawCentredString(x + width / 2, y + height - 6 * mm, title)
        canvas.setFont(FONT, 7.5)
        canvas.drawCentredString(x + width / 2, y + 3.2 * mm, subtitle)

    def _arrow(self, start_x: float, start_y: float, end_x: float, end_y: float) -> None:
        canvas = self.canv
        canvas.line(start_x, start_y, end_x, end_y)
        angle = 0.45
        size = 4
        direction = -1 if end_y < start_y else 1
        canvas.line(end_x, end_y, end_x - size, end_y - direction * size * angle)
        canvas.line(end_x, end_y, end_x + size, end_y - direction * size * angle)


class FlowDiagram(Flowable):
    def __init__(self, labels: list[str], width: float = 170 * mm, height: float = 28 * mm) -> None:
        super().__init__()
        self.labels = labels
        self.width = width
        self.height = height

    def draw(self) -> None:
        canvas = self.canv
        canvas.saveState()
        gap = 5 * mm
        box_width = (self.width - gap * (len(self.labels) - 1)) / len(self.labels)
        for index, label in enumerate(self.labels):
            x = index * (box_width + gap)
            canvas.setFillColor(BLUE if index == 0 else CYAN if index == 1 else NAVY)
            canvas.roundRect(x, 4 * mm, box_width, 17 * mm, 5, stroke=0, fill=1)
            canvas.setFillColor(WHITE)
            canvas.setFont(FONT_BOLD, 7.5)
            canvas.drawCentredString(x + box_width / 2, 12 * mm, label)
            if index < len(self.labels) - 1:
                arrow_x = x + box_width
                canvas.setStrokeColor(MUTED)
                canvas.line(arrow_x + 1 * mm, 12 * mm, arrow_x + gap - 1 * mm, 12 * mm)
                canvas.line(arrow_x + gap - 1 * mm, 12 * mm, arrow_x + gap - 3 * mm, 14 * mm)
                canvas.line(arrow_x + gap - 1 * mm, 12 * mm, arrow_x + gap - 3 * mm, 10 * mm)
        canvas.restoreState()


def paragraph(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, STYLES[style])


def title(number: str, text: str) -> list[Flowable]:
    return [
        paragraph(f"{number}. {text}", "h1"),
        HRFlowable(color=LINE, thickness=0.8),
        Spacer(1, 5),
    ]


def callout(title_text: str, body: str, accent: colors.Color = BLUE) -> Table:
    content = [[paragraph(title_text, "callout_title")], [paragraph(body, "callout_body")]]
    table = Table(content, colWidths=[168 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("LINEBEFORE", (0, 0), (0, -1), 4, accent),
                ("LEFTPADDING", (0, 0), (-1, -1), 11),
                ("RIGHTPADDING", (0, 0), (-1, -1), 11),
                ("TOPPADDING", (0, 0), (-1, 0), 9),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 9),
            ]
        )
    )
    return table


def data_table(headers: list[str], rows: list[list[str]], widths: list[float]) -> Table:
    formatted = [[paragraph(header, "table_header") for header in headers]]
    formatted.extend([[paragraph(cell, "table_cell") for cell in row] for row in rows])
    table = Table(formatted, colWidths=widths, repeatRows=1, hAlign="LEFT")
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.45, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    for row_index in range(1, len(formatted)):
        if row_index % 2 == 0:
            style.append(
                ("BACKGROUND", (0, row_index), (-1, row_index), colors.HexColor("#F8FAFC"))
            )
    table.setStyle(TableStyle(style))
    return table


def code_block(code: str) -> Table:
    content = Preformatted(code.strip(), STYLES["code"])
    table = Table([[content]], colWidths=[168 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#1E293B")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    return table


def hyphen_list(items: list[str]) -> list[Flowable]:
    return [paragraph(f"- {item}") for item in items]


def cover_page(canvas, document) -> None:
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, width, height, stroke=0, fill=1)
    canvas.setFillColor(BLUE)
    canvas.circle(width - 18 * mm, height - 12 * mm, 55 * mm, stroke=0, fill=1)
    canvas.setFillColor(CYAN)
    canvas.circle(width - 7 * mm, 5 * mm, 42 * mm, stroke=0, fill=1)
    canvas.setFillColor(colors.HexColor("#1E293B"))
    canvas.roundRect(20 * mm, 20 * mm, 170 * mm, 18 * mm, 5, stroke=0, fill=1)
    canvas.setFillColor(colors.HexColor("#94A3B8"))
    canvas.setFont(FONT, 8)
    canvas.drawString(27 * mm, 30 * mm, "RELATÓRIO TÉCNICO  |  VERSÃO 1.0  |  SETEMBRO 2026")
    canvas.restoreState()


def regular_page(canvas, document) -> None:
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(20 * mm, height - 16 * mm, width - 20 * mm, height - 16 * mm)
    canvas.setFont(FONT_BOLD, 7.5)
    canvas.setFillColor(NAVY)
    canvas.drawString(20 * mm, height - 12 * mm, "NEXOFROTA")
    canvas.setFont(FONT, 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(width - 20 * mm, height - 12 * mm, "Persistência poliglota")
    canvas.line(20 * mm, 14 * mm, width - 20 * mm, 14 * mm)
    canvas.drawString(20 * mm, 9 * mm, "Relatório técnico")
    canvas.drawRightString(width - 20 * mm, 9 * mm, f"Página {document.page}")
    canvas.restoreState()


def build_story() -> list[Flowable]:
    story: list[Flowable] = [
        Spacer(1, 52 * mm),
        paragraph("PLATAFORMA DE TELEMETRIA LOGÍSTICA", "cover_kicker"),
        paragraph("NexoFrota", "cover_title"),
        paragraph(
            "Persistência poliglota, geolocalização e análise operacional em uma "
            "arquitetura reproduzível.",
            "cover_subtitle",
        ),
        Spacer(1, 15 * mm),
        paragraph("PostgreSQL  /  MongoDB  /  Streamlit  /  GeoJSON", "cover_kicker"),
        Spacer(1, 76 * mm),
        paragraph("Responsável: Lucas Gabriel", "cover_subtitle"),
        PageBreak(),
    ]

    story += title("1", "Resumo executivo")
    story += [
        paragraph(
            "A NexoFrota é uma plataforma para acompanhamento operacional de veículos de carga. "
            "O sistema mantém cadastros relacionais, recebe eventos de telemetria, materializa a "
            "posição atual, executa consultas geoespaciais e apresenta os resultados em um "
            "painel web."
        ),
        paragraph(
            "A solução demonstra persistência poliglota: PostgreSQL protege relações e restrições "
            "cadastrais; MongoDB armazena eventos em GeoJSON e atende buscas por proximidade. "
            "A camada "
            "de serviços combina as fontes sem acoplar a interface aos detalhes de infraestrutura."
        ),
        Spacer(1, 4 * mm),
        callout(
            "Resultado entregue",
            "Aplicação Streamlit, mapa Folium, gráficos Plotly, ambiente Docker, seed controlado, "
            "simulador de movimento, oito testes unitários e documentação operacional.",
            GREEN,
        ),
        Spacer(1, 8 * mm),
        paragraph("Objetivos", "h2"),
        *hyphen_list(
            [
                "Escolher o banco conforme a natureza de cada dado.",
                "Preservar o histórico sem confundir posições antigas com a posição atual.",
                "Localizar veículos em um raio e ordenar os mais próximos.",
                "Unificar dados de fontes distintas por meio de uma camada de serviços.",
                "Fornecer execução reproduzível para avaliação e desenvolvimento.",
            ]
        ),
        Spacer(1, 7 * mm),
        paragraph("Sumário", "h2"),
        paragraph(
            "1. Resumo executivo<br/>2. Requisitos<br/>3. Arquitetura<br/>"
            "4. Modelagem de dados<br/>"
            "5. Geoespacial<br/>6. Interface e simulação<br/>7. Implantação<br/>8. Segurança e "
            "qualidade<br/>9. Testes<br/>10. Limitações e evolução",
            "toc",
        ),
        PageBreak(),
    ]

    story += title("2", "Requisitos e escopo")
    story += [
        paragraph(
            "O escopo cobre o ciclo completo de uma demonstração de telemetria: preparação dos "
            "bancos, dados iniciais, leitura operacional, simulação de eventos e visualização."
        ),
        data_table(
            ["ID", "Requisito", "Implementação"],
            [
                ["RF-01", "Manter motoristas e veículos", "PostgreSQL com chaves e restrições"],
                ["RF-02", "Registrar telemetria", "Coleção MongoDB telemetry"],
                ["RF-03", "Consultar posição atual", "Coleção current_positions"],
                ["RF-04", "Buscar por raio", "Pipeline $geoNear e índice 2dsphere"],
                ["RF-05", "Unificar dados", "FleetService associa por vehicle_id"],
                ["RF-06", "Exibir mapa", "Folium integrado ao Streamlit"],
                ["RF-07", "Exibir indicadores", "Métricas, tabelas e Plotly"],
                ["RF-08", "Simular movimento", "MovementSimulator validado"],
                ["RF-09", "Consultar histórico", "Filtro por veículo e intervalo"],
            ],
            [16 * mm, 58 * mm, 94 * mm],
        ),
        Spacer(1, 9 * mm),
        callout(
            "Fora do escopo",
            "Autenticação de usuários, ingestão por dispositivos reais, mensageria, alta "
            "disponibilidade e observabilidade distribuída são evoluções para produção.",
            AMBER,
        ),
        Spacer(1, 9 * mm),
        paragraph("Critérios de aceite", "h2"),
        *hyphen_list(
            [
                "Os três serviços iniciam com configuração documentada.",
                "O seed cria três veículos e 36 leituras sem segredos no código.",
                "A consulta geoespacial retorna distância em quilômetros.",
                "Uma simulação acrescenta histórico e atualiza a posição atual.",
                "O dashboard sinaliza velocidade, parada e temperatura crítica.",
                "Lint, compilação e testes unitários terminam sem erros.",
            ]
        ),
        PageBreak(),
    ]

    story += title("3", "Arquitetura da solução")
    story += [
        ArchitectureDiagram(),
        Spacer(1, 5 * mm),
        paragraph(
            "A interface acessa somente a camada de serviços. Os repositórios encapsulam consultas "
            "e comandos específicos de cada banco. Modelos de domínio validam coordenadas, datas e "
            "velocidade antes da persistência."
        ),
        paragraph("Fluxo de leitura", "h2"),
        FlowDiagram(["Streamlit", "FleetService", "Repositórios", "Bancos"]),
        *hyphen_list(
            [
                "O PostgreSQL fornece cadastro e vínculo entre motorista e veículo.",
                "O MongoDB fornece a última leitura de cada veículo.",
                "O serviço une os resultados em memória por vehicle_id.",
                "A interface calcula visualizações sem executar SQL ou pipelines diretamente.",
            ]
        ),
        paragraph("Fluxo de escrita", "h2"),
        FlowDiagram(["Simulador", "Validação", "Histórico", "Posição atual"]),
        paragraph(
            "A mesma leitura é inserida como evento imutável e aplicada à projeção atual. "
            "Em cargas "
            "com várias leituras do mesmo veículo, apenas a mais recente atualiza a projeção."
        ),
        PageBreak(),
    ]

    story += title("4", "Modelagem de dados")
    story += [
        paragraph("Modelo relacional", "h2"),
        data_table(
            ["Tabela", "Campo", "Tipo e regra"],
            [
                ["drivers", "id", "Inteiro, chave primária"],
                ["drivers", "name", "Varchar(120), obrigatório"],
                ["drivers", "license_number", "Varchar(20), único"],
                ["drivers", "status", "active, inactive ou leave"],
                ["vehicles", "id", "Inteiro, chave primária"],
                ["vehicles", "plate", "Varchar(10), único"],
                ["vehicles", "model", "Varchar(100), obrigatório"],
                ["vehicles", "driver_id", "Chave estrangeira única"],
                ["vehicles", "active", "Booleano, padrão true"],
            ],
            [35 * mm, 50 * mm, 83 * mm],
        ),
        Spacer(1, 8 * mm),
        paragraph("Documento de telemetria", "h2"),
        code_block(
            """
{
  "vehicle_id": 101,
  "location": {
    "type": "Point",
    "coordinates": [-46.6333, -23.5505]
  },
  "speed_kmh": 56.0,
  "cargo_temperature_c": 4.0,
  "recorded_at": "2026-09-27T12:00:00Z"
}
"""
        ),
        Spacer(1, 5 * mm),
        callout(
            "Regra GeoJSON",
            "A ordem obrigatória é longitude, latitude. Datas são armazenadas como BSON Date em "
            "UTC para preservar ordenação e comparação cronológica.",
            CYAN,
        ),
        PageBreak(),
    ]

    story += title("5", "Histórico, projeção e geoespacial")
    story += [
        paragraph(
            "A coleção telemetry é um log de eventos: nenhuma leitura anterior é substituída. A "
            "coleção current_positions contém um documento por veículo e representa o estado atual."
        ),
        data_table(
            ["Coleção", "Índice", "Finalidade"],
            [
                ["telemetry", "location 2dsphere", "Consultas espaciais sobre eventos"],
                ["telemetry", "vehicle_id + recorded_at", "Histórico ordenado por veículo"],
                ["current_positions", "location 2dsphere", "Raio e proximidade atuais"],
                ["current_positions", "recorded_at desc", "Recência operacional"],
            ],
            [45 * mm, 55 * mm, 68 * mm],
        ),
        Spacer(1, 8 * mm),
        paragraph("Consulta por raio", "h2"),
        code_block(
            """
{
  "$geoNear": {
    "near": {"type": "Point", "coordinates": [longitude, latitude]},
    "distanceField": "distance_meters",
    "maxDistance": radius_km * 1000,
    "spherical": true
  }
}
"""
        ),
        Spacer(1, 6 * mm),
        callout(
            "Por que não consultar apenas o histórico?",
            "Uma leitura antiga pode estar dentro do raio enquanto a posição atual está fora. "
            "Consultar a projeção evita esse falso positivo e reduz o volume examinado.",
            BLUE,
        ),
        Spacer(1, 8 * mm),
        paragraph("Consistência", "h2"),
        paragraph(
            "A escrita ocorre primeiro no histórico e depois na projeção. O desenho favorece "
            "auditoria: se a segunda etapa falhar, a posição atual pode ser reconstruída a partir "
            "do evento mais recente de cada veículo."
        ),
        PageBreak(),
    ]

    story += title("6", "Interface, indicadores e simulação")
    story += [
        paragraph(
            "O painel organiza a operação em quatro abas. O mapa aplica o ponto e o raio definidos "
            "na barra lateral; as demais abas apresentam estado atual e evolução temporal."
        ),
        data_table(
            ["Área", "Conteúdo"],
            [
                ["Mapa", "Veículos no raio, marcadores, círculo e lista dos mais próximos"],
                ["Visão geral", "Cadastro, leitura atual, coordenadas e alertas"],
                ["Dashboard", "KPIs, velocidade e temperatura por veículo"],
                ["Histórico", "Séries por veículo e janela de tempo"],
            ],
            [45 * mm, 123 * mm],
        ),
        Spacer(1, 8 * mm),
        paragraph("Regras de alerta", "h2"),
        data_table(
            ["Condição", "Regra", "Sinalização"],
            [
                ["Velocidade", "Acima de 80 km/h", "Excesso de velocidade"],
                ["Parada", "Abaixo de 1 km/h", "Veículo parado"],
                ["Temperatura", "Fora de -20 a 8 °C", "Temperatura crítica"],
                ["Ausência", "Sem posição atual", "Sem telemetria"],
            ],
            [50 * mm, 55 * mm, 63 * mm],
        ),
        Spacer(1, 8 * mm),
        paragraph("Simulação", "h2"),
        paragraph(
            "O MovementSimulator recebe a última leitura, escolhe ângulo e distância dentro do "
            "limite configurado, ajusta coordenadas e varia velocidade e temperatura. Latitude, "
            "longitude e velocidade são limitadas a domínios válidos."
        ),
        callout(
            "Testabilidade",
            "A fonte aleatória pode ser injetada. Os testes usam uma semente fixa, tornando o "
            "deslocamento repetível sem alterar o comportamento da aplicação.",
            GREEN,
        ),
        PageBreak(),
    ]

    story += title("7", "Implantação e operação")
    story += [
        paragraph(
            "O Docker Compose define três serviços com verificações de saúde e volumes "
            "persistentes. "
            "A aplicação só inicia após PostgreSQL e MongoDB aceitarem conexões."
        ),
        data_table(
            ["Serviço", "Porta do host", "Persistência"],
            [
                ["app", "8501", "Sem estado local"],
                ["postgres", "5433", "Volume postgres_data"],
                ["mongo", "27018", "Volume mongo_data"],
            ],
            [55 * mm, 50 * mm, 63 * mm],
        ),
        Spacer(1, 8 * mm),
        paragraph("Inicialização", "h2"),
        code_block(
            """
Copy-Item .env.example .env
docker compose up -d --build
docker compose exec app python -m nexofrota.seed --if-empty
"""
        ),
        Spacer(1, 7 * mm),
        paragraph("Operação local", "h2"),
        code_block(
            """
docker compose up -d postgres mongo
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements-dev.txt
$env:PYTHONPATH = "src"
python -m nexofrota.seed --if-empty
streamlit run src/app.py
"""
        ),
        Spacer(1, 7 * mm),
        callout(
            "Operação destrutiva",
            "O modo --reset remove os cadastros e as duas coleções antes de recriar a amostra. "
            "Deve ser usado somente em desenvolvimento.",
            RED,
        ),
        PageBreak(),
    ]

    story += title("8", "Segurança e qualidade")
    story += [
        paragraph("Controles implementados", "h2"),
        *hyphen_list(
            [
                "Segredos lidos de variáveis de ambiente; .env fora do versionamento.",
                "Container da aplicação executado por usuário sem privilégios.",
                "SQL parametrizado e esquema com restrições de integridade.",
                "Coordenadas, velocidade e data validadas no domínio.",
                "Conteúdo textual escapado antes de entrar nos pop-ups do mapa.",
                "Timeout de conexão e verificação explícita dos dois bancos.",
                "Seed destrutivo condicionado a uma opção clara de linha de comando.",
            ]
        ),
        Spacer(1, 7 * mm),
        data_table(
            ["Aspecto", "Prática"],
            [
                ["Separação", "Interface, serviço, repositório, modelo e configuração"],
                ["Idempotência", "Schema, índices, upserts e seed --if-empty"],
                ["Observabilidade", "Logs de inicialização e falhas de seed"],
                ["Manutenção", "Tipos, funções pequenas e decisões registradas em ADRs"],
                ["Portabilidade", "Docker e dependências com faixas de versão"],
            ],
            [48 * mm, 120 * mm],
        ),
        Spacer(1, 8 * mm),
        callout(
            "Credenciais de exemplo",
            "Os valores do arquivo .env.example são exclusivos para desenvolvimento local. "
            "Ambientes compartilhados exigem senhas fortes e um gerenciador de segredos.",
            AMBER,
        ),
        PageBreak(),
    ]

    story += title("9", "Validação e testes")
    story += [
        paragraph(
            "A validação automatizada cobre comportamento de domínio e qualidade estática. A "
            "execução registrada durante a entrega concluiu oito testes unitários com sucesso."
        ),
        data_table(
            ["Grupo", "Verificação"],
            [
                ["GeoJSON", "Conversão do modelo para documento e retorno ao domínio"],
                ["Validação", "Rejeição de latitude fora do intervalo"],
                ["Alertas", "Normal, excesso de velocidade, parada e temperatura"],
                ["Simulação", "Limite de deslocamento e preservação da frota"],
                ["Seed", "36 leituras, três veículos e estado final conhecido"],
                ["Estático", "Ruff, formatação e compilação dos módulos"],
            ],
            [48 * mm, 120 * mm],
        ),
        Spacer(1, 9 * mm),
        code_block(
            """
pytest -q
........                                            [100%]
8 passed

ruff check .
All checks passed!
"""
        ),
        Spacer(1, 8 * mm),
        paragraph("Testes de integração recomendados", "h2"),
        *hyphen_list(
            [
                "Aplicar o schema em um PostgreSQL limpo e verificar restrições.",
                "Confirmar índices 2dsphere e composto após o seed.",
                "Comparar distâncias do pipeline geoespacial com valores conhecidos.",
                "Executar simulações concorrentes e validar histórico e projeção.",
            ]
        ),
        PageBreak(),
    ]

    story += title("10", "Limitações e evolução")
    story += [
        paragraph(
            "A implementação atende demonstração e avaliação acadêmica. Para produção, o volume, "
            "a frequência dos eventos e os requisitos de disponibilidade exigem componentes "
            "adicionais."
        ),
        data_table(
            ["Horizonte", "Evolução"],
            [
                [
                    "Curto prazo",
                    "Autenticação, perfis, filtros configuráveis e testes de integração",
                ],
                ["Médio prazo", "Fila de eventos, API de ingestão, métricas e alertas externos"],
                ["Longo prazo", "Particionamento, retenção, replicação e reconstrução por eventos"],
            ],
            [45 * mm, 123 * mm],
        ),
        Spacer(1, 8 * mm),
        paragraph("Recomendações", "h2"),
        *hyphen_list(
            [
                "Parametrizar limites por carga, contrato e rota.",
                "Manter current_positions por consumidor de eventos ou change stream.",
                "Adicionar trilha de auditoria de acesso e alterações cadastrais.",
                "Definir retenção, backups testados e objetivos de recuperação.",
                "Instrumentar latência de ingestão, atraso de posição e falhas de banco.",
            ]
        ),
        Spacer(1, 9 * mm),
        callout(
            "Conclusão",
            "A NexoFrota usa cada banco por sua vantagem real: integridade relacional para "
            "cadastros e documentos geoespaciais para telemetria. A projeção de posição atual, a "
            "camada de serviços e a automação de qualidade formam uma base organizada para "
            "evolução.",
            GREEN,
        ),
        Spacer(1, 10 * mm),
        paragraph("Artefatos", "h2"),
        paragraph(
            "Código-fonte: desafio mongodb aula4/src<br/>"
            "Testes: desafio mongodb aula4/tests<br/>"
            "Decisões: desafio mongodb aula4/docs/DECISOES_ARQUITETURA.md<br/>"
            "Relatório editável: desafio mongodb aula4/docs/RELATORIO_TECNICO.md"
        ),
    ]
    return story


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=23 * mm,
        bottomMargin=19 * mm,
        title="NexoFrota - Relatório Técnico",
        author="Lucas Gabriel",
        subject="Persistência poliglota e telemetria logística",
    )
    document.build(build_story(), onFirstPage=cover_page, onLaterPages=regular_page)
    print(OUTPUT)


if __name__ == "__main__":
    main()
