"""Gera SVGs dos diagramas do ToDo prontos para importar no Figma.

Tudo com atributos inline (sem CSS, sem <marker>, sem variáveis), porque o
importador de SVG do Figma ignora essas coisas. Cada <g id="..."> vira uma
camada nomeada no Figma.
"""

import math
import sys
from html import escape
from pathlib import Path

OUT_DIR = Path(sys.argv[1])

THEMES = {
    "escuro": dict(
        bg="#161d25", ink="#e4e9ef", muted="#98a3b0", line="#3a4552", card="#1b232d",
        adapters="#12302b", adapters_ink="#6fd0bd", app="#1c2142", app_ink="#9ea9f5",
        domain="#33270f", domain_ink="#f0b85a", infra="#20272f", infra_ink="#a7b2bf", forbid="#f2695c",
    ),
    "claro": dict(
        bg="#ffffff", ink="#18212b", muted="#5b6673", line="#c9d1da", card="#ffffff",
        adapters="#e3f1ee", adapters_ink="#1f6f62", app="#e8ebfb", app_ink="#3c4bb0",
        domain="#fbf0dc", domain_ink="#9a5b00", infra="#eceff2", infra_ink="#4d5866", forbid="#c2362b",
    ),
}

SANS = "IBM Plex Sans"
MONO = "IBM Plex Mono"
LINE = 17
PAD = 10


def text(x, y, s, T, *, size=12, font=MONO, weight=400, color="ink", anchor="start", italic=False, underline=False):
    extra = ' font-style="italic"' if italic else ""
    extra += ' text-decoration="underline"' if underline else ""
    return (
        f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{weight}" '
        f'fill="{T[color]}" text-anchor="{anchor}"{extra}>{escape(s)}</text>'
    )


def layer_id(name):
    return escape(name.replace(" ", "_").replace("·", "").replace("|", "ou"))


class Diagram:
    def __init__(self, T):
        self.T = T
        self.els = []

    # ---------- blocos
    def band(self, x, y, w, h, title, rule, kind):
        T = self.T
        dashed = kind == "infra"
        stroke = f' stroke="{T["line"]}" stroke-dasharray="5 4"' if dashed else ""
        self.els.append(
            f'<g id="faixa_{layer_id(title.split(" ")[0])}">'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{T[kind]}"{stroke}/>'
            + text(x + 14, y + 22, title, T, size=13, font=SANS, weight=600, color=f"{kind}_ink")
            + text(x + w - 14, y + 22, rule, T, size=11.5, color=f"{kind}_ink", anchor="end")
            + "</g>"
        )

    def package(self, x, y, w, h, name):
        T = self.T
        tw = max(70, len(name) * 8 + 20)
        self.els.append(
            f'<g id="pacote_{layer_id(name)}">'
            f'<path d="M{x} {y} h{tw} v18 h{w - tw} v{h - 18} h{-w} Z" fill="none" stroke="{T["muted"]}"/>'
            f'<line x1="{x}" y1="{y + 18}" x2="{x + tw}" y2="{y + 18}" stroke="{T["muted"]}"/>'
            + text(x + 8, y + 13, name, T, size=11.5, weight=500, color="muted")
            + "</g>"
        )

    def box(self, x, y, w, name, stereo=None, attrs=None, ops=None, accent=False):
        T = self.T
        head = 30 + (16 if stereo else 0)
        sections = [s for s in (attrs, ops) if s is not None]
        h = head + sum(len(s) * LINE + PAD for s in sections)
        stroke, sw = (T["domain_ink"], 2) if accent else (T["ink"], 1.2)
        parts = [f'<g id="{layer_id(name)}">',
                 f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="{T["card"]}" stroke="{stroke}" stroke-width="{sw}"/>']
        cy = y + 19
        if stereo:
            parts.append(text(x + w / 2, cy, f"«{stereo}»", T, size=11, color="muted", anchor="middle", italic=True))
            cy += 16
        parts.append(text(x + w / 2, cy, name, T, size=13.5, font=SANS, weight=600, anchor="middle"))
        sy = y + head
        for s in sections:
            parts.append(f'<line x1="{x}" y1="{sy}" x2="{x + w}" y2="{sy}" stroke="{T["ink"]}" stroke-opacity="0.6" stroke-width="0.8"/>')
            ty = sy + 15
            for t in s:
                static = t.startswith("_static_")
                t = t.removeprefix("_static_")
                parts.append(text(x + 8, ty, t, T, underline=static))
                ty += LINE
            sy += len(s) * LINE + PAD
        parts.append("</g>")
        self.els.append("\n".join(parts))
        return h

    # ---------- setas (pontas desenhadas como paths, sem <marker>)
    def arrow(self, pts, kind="dep", label=None, lx=None, ly=None, anchor="middle", name="seta"):
        T = self.T
        color = T["forbid"] if kind == "forbid" else T["ink"]
        dash = {"dep": ' stroke-dasharray="6 4"', "real": ' stroke-dasharray="6 4"', "line": ' stroke-dasharray="6 4"',
                "forbid": ' stroke-dasharray="3 4"', "assoc": ""}[kind]
        width = 1.6 if kind == "forbid" else 1.3
        d = "M" + " L".join(f"{px} {py}" for px, py in pts)
        parts = [f'<g id="{escape(name)}">',
                 f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"{dash}/>']
        (x1, y1), (x2, y2) = pts[-2], pts[-1]
        L = math.hypot(x2 - x1, y2 - y1)
        ux, uy = (x2 - x1) / L, (y2 - y1) / L
        px, py = -uy, ux
        if kind in ("dep", "assoc"):
            bx, by = x2 - 11 * ux, y2 - 11 * uy
            parts.append(f'<path d="M{bx + 5 * px:.1f} {by + 5 * py:.1f} L{x2} {y2} L{bx - 5 * px:.1f} {by - 5 * py:.1f}" '
                         f'fill="none" stroke="{color}" stroke-width="{width}"/>')
        elif kind == "real":
            bx, by = x2 - 14 * ux, y2 - 14 * uy
            parts.append(f'<path d="M{bx + 7 * px:.1f} {by + 7 * py:.1f} L{x2} {y2} L{bx - 7 * px:.1f} {by - 7 * py:.1f} Z" '
                         f'fill="{T["card"]}" stroke="{color}" stroke-width="{width}"/>')
        if label:
            parts.append(text(lx, ly, label, T, size=11, color="forbid" if kind == "forbid" else "muted", anchor=anchor))
        parts.append("</g>")
        self.els.append("\n".join(parts))

    def node(self, x, y, w, h, title, sub, kind):
        T = self.T
        if kind == "ext":
            fill, stroke, extra = T["bg"], T["line"], ""
        else:
            fill, stroke = T[kind], T[f"{kind}_ink"]
            extra = ' stroke-dasharray="5 4"' if kind == "infra" else ""
        sw = 2.2 if kind == "domain" else 1.4
        parts = [f'<g id="{layer_id(title)}">',
                 f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{extra}/>']
        if sub:
            parts.append(text(x + w / 2, y + 32, title, T, size=16, font=SANS, weight=600, anchor="middle"))
            parts.append(text(x + w / 2, y + 54, sub, T, size=12, color="muted", anchor="middle"))
        else:
            parts.append(text(x + w / 2, y + h / 2 + 5, title, T, size=13, weight=500, color="muted", anchor="middle"))
        parts.append("</g>")
        self.els.append("\n".join(parts))

    def forbid_x(self, cx, cy):
        T = self.T
        self.els.append(
            f'<g id="proibido"><circle cx="{cx}" cy="{cy}" r="11" fill="{T["bg"]}" stroke="{T["forbid"]}" stroke-width="1.6"/>'
            f'<path d="M{cx - 5} {cy - 5} L{cx + 5} {cy + 5} M{cx + 5} {cy - 5} L{cx - 5} {cy + 5}" stroke="{T["forbid"]}" stroke-width="2"/></g>'
        )

    def svg(self, x, y, w, h, title):
        T = self.T
        body = "\n".join(self.els)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="{x} {y} {w} {h}">\n'
            f'<title>{escape(title)}</title>\n'
            f'<rect id="fundo" x="{x}" y="{y}" width="{w}" height="{h}" fill="{T["bg"]}"/>\n{body}\n</svg>\n'
        )


def packages(T):
    D = Diagram(T)
    D.node(60, 40, 400, 74, "api | ui", "FastAPI · CLI · traduz HTTP/terminal", "adapters")
    D.node(60, 180, 400, 74, "application", "TaskService · TaskDTO · casos de uso", "app")
    D.node(60, 320, 400, 74, "domain", "Task · Status · porta TaskRepository", "domain")
    D.node(560, 40, 280, 74, "composition root", "monta tudo na inicialização", "infra")
    D.node(560, 320, 280, 74, "persistence", "SqliteRepository · MemoryRepository", "infra")
    D.node(560, 450, 280, 54, "fastapi · pydantic · sqlite3", None, "ext")
    D.arrow([(260, 114), (260, 180)], name="api_para_application")
    D.arrow([(260, 254), (260, 320)], name="application_para_domain")
    D.arrow([(560, 357), (460, 357)], "real", "implementa", 510, 347, name="persistence_implementa_domain")
    D.arrow([(700, 114), (700, 320)], "dep", "cria", 710, 220, "start", name="composition_cria_persistence")
    D.arrow([(560, 77), (460, 77)], "dep", "injeta", 510, 67, name="composition_injeta")
    D.arrow([(640, 394), (640, 450)], "dep", "usa", 648, 428, "start", name="persistence_usa_sqlite")
    D.arrow([(260, 394), (260, 477), (560, 477)], "forbid", "domain → frameworks: o CI quebra", 270, 440, "start",
            name="proibido_domain_frameworks")
    D.forbid_x(410, 477)
    D.arrow([(460, 217), (600, 217), (600, 320)], "forbid", "application → persistence", 590, 290, "end",
            name="proibido_application_persistence")
    D.forbid_x(600, 255)
    return D.svg(40, 20, 820, 500, "Regra de dependência do ToDo")


def classes(T):
    D = Diagram(T)
    D.band(20, 30, 860, 280, "api | ui · adaptadores de entrada", "independentes entre si · sem persistence", "adapters")
    D.band(20, 330, 860, 260, "application · casos de uso", "não importa persistence, fastapi, pydantic, sqlite3", "app")
    D.band(20, 610, 860, 350, "domain · regras de negócio", "puro: nenhum framework, nenhuma outra camada", "domain")
    D.band(890, 30, 330, 280, "composition root", "o único que conhece tudo", "infra")
    D.band(890, 610, 330, 350, "persistence", "implementa a porta do domain", "infra")

    D.package(40, 62, 420, 230, "api")
    h_api = D.box(55, 95, 230, "api.app", "module", ops=[
        "create_app(service): FastAPI", "GET    /tasks", "POST   /tasks", "GET    /tasks/{id}",
        "PUT    /tasks/{id}", "POST   /tasks/{id}/complete", "DELETE /tasks/{id}"])
    D.box(300, 95, 148, "api.schemas", "pydantic", ops=["TaskInput", "TaskOutput", "ErrorResponse", "to_status(filter)"])
    D.package(475, 62, 390, 230, "ui")
    h_cli = D.box(490, 95, 180, "ui.cli", "module", ops=["build_parser()", "run(service, argv): int"])
    h_formt = D.box(683, 95, 172, "ui.formt", "module", ops=["format_task(dto)", "format_task_list(dtos)"])

    h_svc = D.box(50, 370, 330, "TaskService", attrs=["- repository: TaskRepository"], ops=[
        "+ create_task(title, description): Task", "+ list_tasks(status): list[Task]",
        "+ list_page(status, limit, offset): TaskPage", "+ get_task_by_id(id): Task", "+ complete_task(id): Task",
        "+ edit_task(id, title, description): Task", "+ delete_task(id)"])
    D.box(420, 370, 190, "TaskPage", "dataclass, frozen", attrs=["+ items: list[Task]", "+ total: int"])
    D.box(650, 370, 210, "TaskDTO", "dataclass, frozen", attrs=["+ id: str", "+ title: str", "+ description: str", "+ status: str"],
          ops=["_static_+ from_task(task): TaskDTO"])

    D.box(50, 655, 230, "Task", attrs=["+ id: UUID", "+ title: str", "+ description: str", "+ status: Status"],
          ops=["+ complete()", "+ edit(title, description)", "_static_- _validate_title(title)"], accent=True)
    D.box(320, 655, 150, "Status", "enum", attrs=["PENDING", "COMPLETED"])
    D.box(320, 775, 180, "InvalidTitleError", "exception")
    D.box(320, 840, 180, "TaskNotFoundError", "exception")
    D.box(520, 655, 340, "TaskRepository", "Protocol · porta", ops=[
        "+ add_task(task)", "+ get_all_tasks(): list[Task]", "+ find_tasks(status, limit, offset): list[Task]",
        "+ count_tasks(status): int", "+ get_task_by_id(id): Task | None", "+ update_task(task)", "+ delete_task(id)"],
          accent=True)

    h_entry = D.box(905, 72, 300, "main.py · server.py", "entry point",
                    ops=["main → ui.cli.run(service)", "server → api.create_app(service)"])
    h_comp = D.box(905, 182, 300, "composition", "module", ops=["build_service(connection): TaskService", "database_path(): str"])

    D.box(905, 655, 300, "SqliteRepository", attrs=["- connection: sqlite3.Connection", "- _lock: threading.Lock"],
          ops=["+ os 7 métodos de TaskRepository", "- _read(sql, params)", "- _write(sql, params)"])
    D.box(905, 820, 300, "MemoryRepository", attrs=["- tasks: list[Task]"], ops=["+ os 7 métodos de TaskRepository"])

    svc_b, comp_b = 370 + h_svc, 182 + h_comp
    D.arrow([(170, 95 + h_api), (170, 370)], "dep", "usa", 180, 340, "start", name="api_usa_TaskService")
    D.arrow([(580, 95 + h_cli), (580, 318), (300, 318), (300, 370)], "dep", "usa", 590, 300, "start", name="cli_usa_TaskService")
    D.arrow([(769, 95 + h_formt), (769, 370)], "dep", "formata", 779, 300, "start", name="formt_usa_TaskDTO")
    D.arrow([(380, 400), (420, 400)], "dep", "cria", 400, 392, name="TaskService_cria_TaskPage")
    D.arrow([(150, svc_b), (150, 655)], "dep", "cria / altera", 160, 603, "start", name="TaskService_usa_Task")
    D.arrow([(370, svc_b), (370, 612), (690, 612), (690, 655)], "assoc", "repository  1", 684, 650, "end",
            name="TaskService_repository")
    D.arrow([(280, 700), (320, 700)], name="Task_usa_Status")
    D.arrow([(280, 798), (320, 798)], "dep", "lança", 300, 791, name="Task_lanca_InvalidTitleError")
    D.arrow([(250, svc_b), (250, 640), (510, 640), (510, 862), (500, 862)], "dep", "lança", 470, 634,
            name="TaskService_lanca_TaskNotFoundError")
    D.arrow([(1055, 72 + h_entry), (1055, 182)], name="entry_usa_composition")
    D.arrow([(905, 117), (865, 117)], name="entry_chama_adaptadores")
    D.arrow([(1150, comp_b), (1150, 655)], "dep", "cria", 1160, 470, "start", name="composition_cria_Sqlite")
    D.arrow([(960, comp_b), (960, 575), (380, 575)], "dep", "injeta o repositório e cria", 950, 567, "end",
            name="composition_cria_TaskService")
    D.arrow([(905, 885), (885, 885), (885, 760)], "line", name="Memory_implementa")
    D.arrow([(905, 760), (860, 760)], "real", name="Sqlite_implementa")
    return D.svg(10, 20, 1220, 950, "Diagrama de classes do backend do ToDo")


OUT_DIR.mkdir(parents=True, exist_ok=True)
for theme, T in THEMES.items():
    for name, fn in (("regra-de-dependencia", packages), ("classes-backend", classes)):
        path = OUT_DIR / f"{name}-{theme}.svg"
        path.write_text(fn(T), encoding="utf-8")
        print(path)
