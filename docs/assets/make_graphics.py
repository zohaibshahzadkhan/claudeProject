"""Generate README graphics (SVG) for the Spendly / Claude Code repo."""
import os, sys
from xml.sax.saxutils import escape as esc

OUT = sys.argv[1] if len(sys.argv) > 1 else "docs/assets"
os.makedirs(OUT, exist_ok=True)

FONT = "Inter, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', 'SF Mono', Menlo, Consolas, 'DejaVu Sans Mono', monospace"
C = dict(
    bg0="#0B1020", bg1="#121A33", card="#151E36", card2="#1B2644", line="#2A3658",
    text="#E8EDF7", muted="#8D9AB8", dim="#5A678A",
    orange="#E8825F", blue="#5B9BFF", green="#3FCB7E", purple="#A98BFF",
    teal="#2ED3C0", amber="#F2C14E", pink="#F178B6",
)


def svg(w, h, body, title):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}">
<title>{esc(title)}</title>
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{C['bg0']}"/><stop offset="1" stop-color="{C['bg1']}"/>
  </linearGradient>
  <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
    <path d="M32 0H0V32" fill="none" stroke="#FFFFFF" stroke-opacity="0.035"/>
  </pattern>
  <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M0 0L10 5L0 10z" fill="{C['muted']}"/>
  </marker>
  <marker id="arrA" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M0 0L10 5L0 10z" fill="{C['amber']}"/>
  </marker>
</defs>
<rect width="{w}" height="{h}" rx="18" fill="url(#bg)"/>
<rect width="{w}" height="{h}" rx="18" fill="url(#grid)"/>
<rect x="0.5" y="0.5" width="{w-1}" height="{h-1}" rx="18" fill="none" stroke="{C['line']}"/>
{body}
</svg>'''


def t(x, y, s, size=14, fill=None, weight=400, anchor="start", mono=False, ls=0, op=1):
    fam = MONO if mono else FONT
    return (f'<text x="{x}" y="{y}" font-family="{fam}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill or C["text"]}" text-anchor="{anchor}" letter-spacing="{ls}" opacity="{op}">{esc(s)}</text>')


def rect(x, y, w, h, fill=None, stroke=None, rx=12, op=1, sw=1, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill or C["card"]}" '
            f'fill-opacity="{op}" stroke="{stroke or C["line"]}" stroke-width="{sw}"{d}/>')


def chip(x, y, label, color, mono=True, size=12, h=24, pad=10):
    w = int(len(label) * size * (0.62 if mono else 0.56)) + pad * 2
    return (rect(x, y, w, h, fill=color, stroke=color, rx=h // 2, op=0.14) +
            t(x + w / 2, y + h / 2 + size * 0.36, label, size, color, 600, "middle", mono)), w


def header(title, sub, x=40, y=56):
    return t(x, y, title, 26, weight=700, ls=-0.3) + t(x, y + 26, sub, 14, C["muted"])


# ---------------------------------------------------------------- 1. banner
def banner():
    W, H = 1200, 320
    b = []
    b.append(f'<circle cx="1050" cy="-40" r="260" fill="{C["orange"]}" opacity="0.07"/>')
    b.append(f'<circle cx="980" cy="380" r="200" fill="{C["blue"]}" opacity="0.06"/>')
    c, _ = chip(56, 58, "AI-ASSISTED ENGINEERING", C["orange"], mono=False, size=11, h=24)
    b.append(c)
    b.append(t(56, 136, "Spendly", 58, weight=800, ls=-1.5))
    b.append(t(56, 176, "Spec-driven development with Claude Code:", 19, C["muted"]))
    b.append(t(56, 202, "rules, guardrails, subagents and a repeatable delivery pipeline.", 19, C["muted"]))
    x = 56
    for lbl, col in [("Flask", C["blue"]), ("SQLite", C["teal"]), ("pytest", C["green"]), ("Claude Code", C["orange"])]:
        c, w = chip(x, 238, lbl, col, mono=True, size=12)
        b.append(c); x += w + 10

    stats = [("9", "feature specs", C["blue"]), ("6", "slash commands", C["orange"]),
             ("4", "subagents", C["purple"]), ("2", "hooks", C["amber"]),
             ("166", "passing tests", C["green"]), ("13", "merged PRs", C["teal"])]
    gx, gy, cw, ch, gap = 640, 52, 162, 100, 14
    for i, (n, lbl, col) in enumerate(stats):
        cx, cy = gx + (i % 3) * (cw + gap), gy + (i // 3) * (ch + gap)
        b.append(rect(cx, cy, cw, ch, fill=C["card"], rx=14, op=0.85))
        b.append(f'<rect x="{cx}" y="{cy + 18}" width="3" height="{ch - 36}" rx="1.5" fill="{col}"/>')
        b.append(t(cx + 22, cy + 56, n, 36, col, 800, ls=-1))
        b.append(t(cx + 22, cy + 80, lbl, 13, C["muted"]))
    return svg(W, H, "\n".join(b), "Spendly: spec-driven development with Claude Code")


# ---------------------------------------------------------------- 2. workflow
def workflow():
    W, H = 1200, 660
    b = [header("Feature delivery pipeline",
                "Every feature follows the same six stages. Review findings wait for my approval before any fix is applied.")]
    stages = [
        ("01", "SPEC", "/create-spec", C["blue"], ["Clean-tree check", "Feature branch", "Definition of done"]),
        ("02", "PLAN", "Plan Mode", C["teal"], ["Explore subagent", "Plan reviewed first", "No code written yet"]),
        ("03", "BUILD", "CLAUDE.md", C["orange"], ["Routes → app.py", "SQL → db.py only", "Auto-formatted"]),
        ("04", "TEST", "/test-feature", C["green"], ["Tests from the spec", "not from the code", "Failures triaged"]),
        ("05", "REVIEW", "/code-review-feature", C["purple"], ["Security + quality", "Read-only, diff-only", "Waits for approval"]),
        ("06", "SHIP", "/ship-feature", C["pink"], ["Conventional commit", "PR → squash merge", "Branch cleanup"]),
    ]
    y0, cw, chh, gap, x0 = 140, 160, 168, 32, 40
    # loop-back arrow (review -> build)
    rx, bx = x0 + 4 * (cw + gap) + cw / 2, x0 + 2 * (cw + gap) + cw / 2
    b.append(f'<path d="M{rx} {y0} V{y0-22} H{bx} V{y0-4}" fill="none" stroke="{C["amber"]}" '
             f'stroke-width="1.6" stroke-dasharray="5 4" marker-end="url(#arrA)"/>')
    mid = (rx + bx) / 2
    b.append(rect(mid - 118, y0 - 34, 236, 24, fill=C["bg1"], stroke=C["amber"], rx=12, op=1))
    b.append(t(mid, y0 - 18, "changes requested → back to build", 12, C["amber"], 600, "middle"))

    for i, (num, name, cmd, col, lines) in enumerate(stages):
        x = x0 + i * (cw + gap)
        b.append(rect(x, y0, cw, chh, rx=14))
        b.append(f'<rect x="{x+16}" y="{y0-1}" width="{cw-32}" height="3" rx="1.5" fill="{col}"/>')
        b.append(t(x + 16, y0 + 32, num, 12, col, 700, mono=True))
        b.append(t(x + 44, y0 + 32, name, 15, weight=800, ls=1))
        sz = 11 if len(cmd) > 14 else 12
        c, _ = chip(x + 12, y0 + 46, cmd, col, size=sz, h=24, pad=8)
        b.append(c)
        for j, ln in enumerate(lines):
            b.append(f'<circle cx="{x+19}" cy="{y0+100+j*22}" r="2.5" fill="{col}"/>')
            b.append(t(x + 29, y0 + 104 + j * 22, ln, 12.5, C["muted"]))
        if i < 5:
            ax = x + cw + 4
            if i == 4:
                b.append(f'<line x1="{ax}" y1="{y0+chh/2}" x2="{ax+gap-8}" y2="{y0+chh/2}" stroke="{C["amber"]}" stroke-width="2" marker-end="url(#arrA)"/>')
                b.append(f'<circle cx="{ax+gap/2-4}" cy="{y0+chh/2+26}" r="11" fill="{C["amber"]}"/>')
                b.append(t(ax + gap / 2 - 4, y0 + chh / 2 + 30.5, "✓", 13, C["bg0"], 800, "middle"))
            else:
                b.append(f'<line x1="{ax}" y1="{y0+chh/2}" x2="{ax+gap-8}" y2="{y0+chh/2}" stroke="{C["muted"]}" stroke-width="1.6" marker-end="url(#arr)"/>')

    # agents lane
    ly = 360
    b.append(t(40, ly, "SUBAGENTS", 12, C["purple"], 700, ls=2))
    b.append(t(40, ly + 26, "Each runs in its own context", 13, C["muted"]))
    b.append(t(40, ly + 46, "with only the tools it needs.", 13, C["muted"]))
    b.append(t(40, ly + 78, "No agent grades its own work:", 13, C["text"], 600))
    b.append(t(40, ly + 98, "writing, running and reviewing", 13, C["muted"]))
    b.append(t(40, ly + 118, "are separate jobs.", 13, C["muted"]))

    def agent(x, y, w, name, tools, col, note):
        s = rect(x, y, w, 70, fill=C["card2"], stroke=col, rx=10, op=1)
        s += t(x + 14, y + 25, name, 13, weight=700, mono=True)
        s += t(x + 14, y + 44, tools, 11.5, col, 600)
        s += t(x + 14, y + 61, note, 11, C["dim"])
        return s

    # test group
    gx, gy, gw, gh = 330, 340, 400, 150
    b.append(rect(gx, gy, gw, gh, fill=C["green"], stroke=C["green"], op=0.05, rx=14, dash="4 4"))
    b.append(t(gx + 16, gy + 26, "/test-feature", 13, C["green"], 700, mono=True))
    b.append(t(gx + gw - 16, gy + 26, "sequential", 11, C["muted"], 600, "end"))
    b.append(agent(gx + 16, gy + 52, 172, "test-writer", "Read · Write · Edit", C["green"], "no Bash: can't run"))
    b.append(f'<line x1="{gx+192}" y1="{gy+87}" x2="{gx+206}" y2="{gy+87}" stroke="{C["muted"]}" stroke-width="1.6" marker-end="url(#arr)"/>')
    b.append(agent(gx + 212, gy + 52, 172, "test-runner", "Read · Bash · Grep", C["green"], "no Write: can't edit"))
    # review group
    rgx = 750
    b.append(rect(rgx, gy, 410, gh, fill=C["purple"], stroke=C["purple"], op=0.05, rx=14, dash="4 4"))
    b.append(t(rgx + 16, gy + 26, "/code-review-feature", 13, C["purple"], 700, mono=True))
    b.append(t(rgx + 394, gy + 26, "parallel", 11, C["muted"], 600, "end"))
    b.append(agent(rgx + 16, gy + 52, 180, "security-reviewer", "Read-only · git diff", C["purple"], "SQLi, auth, ownership"))
    b.append(t(rgx + 205, gy + 93, "∥", 18, C["muted"], 700, "middle"))
    b.append(agent(rgx + 214, gy + 52, 180, "quality-reviewer", "Read-only · git diff", C["purple"], "Flask practice, rules"))
    # connectors
    tx = x0 + 3 * (cw + gap) + cw / 2
    vx = x0 + 4 * (cw + gap) + cw / 2
    b.append(f'<path d="M{tx} {y0+chh} V{gy-8}" stroke="{C["green"]}" stroke-width="1.4" stroke-dasharray="3 4" fill="none"/>')
    b.append(f'<path d="M{vx} {y0+chh} V{gy-8}" stroke="{C["purple"]}" stroke-width="1.4" stroke-dasharray="3 4" fill="none"/>')

    # guardrails
    gy2 = 528
    b.append(t(40, gy2, "ALWAYS-ON GUARDRAILS", 12, C["amber"], 700, ls=2))
    b.append(t(1160, gy2, "active in every session and on every tool call", 12, C["dim"], 400, "end"))
    rails = [("CLAUDE.md", "Architecture, style & warnings", "loaded into every session", C["orange"]),
             ("Permissions", "Edit / Write → ask first", ".claude/settings.json", C["blue"]),
             ("PostToolUse hook", "black on every edited .py", "consistent formatting", C["teal"]),
             ("PreToolUse hook", "Blocks rm on db / .env", "exit 2 = call denied", C["amber"])]
    cw2 = (1120 - 3 * 16) / 4
    for i, (a, bb, cc, col) in enumerate(rails):
        x = 40 + i * (cw2 + 16)
        b.append(rect(x, gy2 + 16, cw2, 92, rx=12))
        b.append(f'<rect x="{x}" y="{gy2+34}" width="3" height="56" rx="1.5" fill="{col}"/>')
        b.append(t(x + 20, gy2 + 46, a, 14, col, 700, mono=True))
        b.append(t(x + 20, gy2 + 70, bb, 13, C["text"]))
        b.append(t(x + 20, gy2 + 90, cc, 12, C["dim"]))
    return svg(W, H, "\n".join(b), "Feature delivery pipeline with Claude Code")


# ---------------------------------------------------------------- 3. setup layers
def layers():
    W = 1200
    rows = [
        ("CONTEXT", "What Claude knows", "CLAUDE.md · .claude/specs/", C["blue"],
         [("CLAUDE.md", "architecture · style · warnings"), ("9 specs", "one contract per feature"),
          ("Subagent policy", "explore before build")]),
        ("CONTROL", "What Claude may do", ".claude/settings.json", C["amber"],
         [("ask: Edit, Write", "human approves changes"), ("PreToolUse", "destructive-cmd guard"),
          ("PostToolUse", "black auto-format"), ("allowed-tools", "scoped per command")]),
        ("AUTOMATION", "Repeatable procedures", ".claude/commands/", C["orange"],
         [("/create-spec", "branch + spec"), ("/test-feature", "write + run"),
          ("/code-review-feature", "2 reviewers"), ("/ship-feature", "commit → merge"),
          ("/seed-*", "user + expense data")]),
        ("DELEGATION", "Who does the work", ".claude/agents/ · skills/", C["purple"],
         [("test-writer", "Read/Write"), ("test-runner", "Read/Bash"),
          ("security-reviewer", "read-only"), ("quality-reviewer", "read-only"),
          ("ui-designer skill", "manual only")]),
    ]
    rh, gap, y0 = 104, 16, 118
    H = y0 + len(rows) * (rh + gap) + 24
    b = [header("Claude Code configuration: 4 layers",
                "Everything lives in versioned files under .claude/ and is reviewed like application code.")]
    for i, (name, sub, path, col, items) in enumerate(rows):
        y = y0 + i * (rh + gap)
        b.append(rect(40, y, 1120, rh, rx=14))
        b.append(f'<rect x="40" y="{y}" width="250" height="{rh}" rx="14" fill="{col}" fill-opacity="0.10"/>')
        b.append(f'<rect x="40" y="{y+20}" width="4" height="{rh-40}" rx="2" fill="{col}"/>')
        b.append(t(62, y + 36, f"L{i+1}  {name}", 15, col, 800, ls=1.5))
        b.append(t(62, y + 60, sub, 14, C["text"], 600))
        b.append(t(62, y + 82, path, 11.5, C["muted"], mono=True))
        n = len(items)
        avail = 1160 - 306 - 16
        iw = (avail - (n - 1) * 10) / n
        for j, (a, d) in enumerate(items):
            x = 306 + j * (iw + 10)
            b.append(rect(x, y + 18, iw, rh - 36, fill=C["card2"], rx=10))
            size = 12.5 if len(a) * 7.8 < iw - 24 else 11
            b.append(t(x + 14, y + 46, a, size, C["text"], 700, mono=True))
            b.append(t(x + 14, y + 68, d, 12, C["muted"]))
        if i < len(rows) - 1:
            b.append(f'<line x1="165" y1="{y+rh+2}" x2="165" y2="{y+rh+gap-2}" stroke="{C["dim"]}" stroke-width="1.5"/>')
    return svg(W, H, "\n".join(b), "Claude Code configuration layers")


# ---------------------------------------------------------------- 4. matrix
def matrix():
    cols = [("CLAUDE.md", "rules", C["orange"]), ("Spec", "first", C["blue"]), ("Branch", "+ PR", C["teal"]),
            ("UI", "skill", C["pink"]), ("pytest", "suite", C["green"]), ("Test", "agents", C["green"]),
            ("Hooks", "", C["amber"]), ("/ship-", "feature", C["pink"]), ("Claude", "co-author", C["purple"])]
    F, I, N = 2, 1, 0  # full evidence / consistent with history / not used
    rows = [
        ("Landing · Terms · Privacy", "pre-spec", "Nov 3", [N, N, N, N, N, N, N, N, F]),
        ("01  Database setup", "PR #1", "Nov 9", [F, F, F, N, N, N, N, N, N]),
        ("02  Registration", "PR #2", "Nov 10", [F, F, F, N, N, N, N, N, N]),
        ("03  Login & logout", "PR #3", "Nov 17", [F, F, F, N, N, N, N, N, F]),
        ("04  Profile page (UI)", "PR #4", "Nov 17", [F, F, F, I, N, N, N, N, F]),
        ("05  Profile ← database", "PR #5", "Nov 18", [F, F, F, N, F, N, N, N, F]),
        ("06  Date filter", "PR #6", "Nov 18", [F, F, F, N, F, I, N, N, F]),
        ("07  Add expense", "PR #7", "Nov 20", [F, F, F, N, F, I, N, N, F]),
        ("08  Edit expense", "PR #9", "Nov 23", [F, F, F, N, F, I, N, N, F]),
        ("09  Delete expense", "PR #12", "Nov 23", [F, F, F, N, F, I, F, I, F]),
        ("Technical README / docs", "PR #8, #13", "Nov 20–23", [F, N, F, N, N, N, N, N, F]),
    ]
    W, x0, fw, cwid = 1200, 40, 300, 91
    hy, ry0, rh = 132, 182, 42
    H = ry0 + len(rows) * rh + 86
    b = [header("Which Claude Code approach was used for which feature",
                "Built from git history and the files in .claude/. Each row adds tooling as the workflow matured.")]
    cx0 = x0 + fw
    b.append(rect(x0, hy - 18, 1120, H - hy - 50, rx=14, op=0.6))
    for j, (a, bb, col) in enumerate(cols):
        cx = cx0 + j * cwid + cwid / 2
        b.append(f'<rect x="{cx-cwid/2+6}" y="{hy-6}" width="{cwid-12}" height="3" rx="1.5" fill="{col}"/>')
        b.append(t(cx, hy + 18, a, 12.5, C["text"], 700, "middle"))
        b.append(t(cx, hy + 34, bb, 12, C["muted"], 500, "middle"))
    b.append(t(x0 + 20, hy + 18, "FEATURE", 12, C["muted"], 700, ls=1.5))
    b.append(t(x0 + fw - 20, hy + 18, "SHIPPED", 12, C["muted"], 700, "end", ls=1.5))
    for i, (name, pr, date, vals) in enumerate(rows):
        y = ry0 + i * rh
        if i % 2 == 0:
            b.append(f'<rect x="{x0+1}" y="{y}" width="1118" height="{rh}" fill="#FFFFFF" fill-opacity="0.025"/>')
        b.append(t(x0 + 20, y + 26, name, 14, C["text"], 600))
        b.append(t(x0 + fw - 20, y + 20, pr, 11.5, C["muted"], 600, "end", mono=True))
        b.append(t(x0 + fw - 20, y + 35, date, 11, C["dim"], 400, "end"))
        for j, v in enumerate(vals):
            cx, cy, col = cx0 + j * cwid + cwid / 2, y + rh / 2, cols[j][2]
            if v == F:
                b.append(f'<circle cx="{cx}" cy="{cy}" r="8" fill="{col}"/>')
                b.append(f'<path d="M{cx-3.5} {cy} l2.5 2.6 l4.6 -5" stroke="{C["bg0"]}" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
            elif v == I:
                b.append(f'<circle cx="{cx}" cy="{cy}" r="7" fill="none" stroke="{col}" stroke-width="2"/>')
                b.append(f'<path d="M{cx} {cy-7} a7 7 0 0 0 0 14 z" fill="{col}"/>')
            else:
                b.append(f'<line x1="{cx-5}" y1="{cy}" x2="{cx+5}" y2="{cy}" stroke="{C["dim"]}" stroke-width="2" stroke-linecap="round" opacity="0.6"/>')
    ly = H - 30
    b.append(f'<circle cx="52" cy="{ly-4}" r="7" fill="{C["green"]}"/>')
    b.append(t(66, ly, "Confirmed by a file or commit in the repo", 12.5, C["muted"]))
    lx = 360
    b.append(f'<circle cx="{lx}" cy="{ly-4}" r="6" fill="none" stroke="{C["green"]}" stroke-width="2"/>')
    b.append(f'<path d="M{lx} {ly-10} a6 6 0 0 0 0 12 z" fill="{C["green"]}"/>')
    b.append(t(lx + 14, ly, "Consistent with history (tool available, matching naming/format)", 12.5, C["muted"]))
    b.append(f'<line x1="840" y1="{ly-4}" x2="850" y2="{ly-4}" stroke="{C["dim"]}" stroke-width="2" stroke-linecap="round"/>')
    b.append(t(860, ly, "Not used / not yet introduced", 12.5, C["muted"]))
    return svg(W, H, "\n".join(b), "Feature by Claude Code approach matrix")


# ---------------------------------------------------------------- 5. timeline
def timeline():
    W, H = 1200, 520
    b = [header("How the workflow evolved in 3 weeks",
                "I iterated on the process like a product, adding each capability when a real need appeared.")]
    ev = [
        ("Nov 3", ["Claude Code", "first commits"], ["Landing, Terms,", "Privacy pages"]),
        ("Nov 9", ["CLAUDE.md", "+ first spec"], ["#1 Database", "setup"]),
        ("Nov 10", ["Slash", "commands"], ["#2 Registration"]),
        ("Nov 17", ["UI designer", "skill"], ["#3 Login/logout", "#4 Profile page"]),
        ("Nov 18", ["4 subagents"], ["#5 Profile ← DB", "#6 Date filter"]),
        ("Nov 20", ["Tech README"], ["#7 Add expense"]),
        ("Nov 23", ["Hooks +", "/ship-feature"], ["#9 Edit expense", "#12 Delete expense"]),
    ]
    cols = [C["orange"], C["orange"], C["orange"], C["pink"], C["purple"], C["teal"], C["amber"]]
    ly = 250
    x0, x1 = 110, 1090
    b.append(f'<line x1="70" y1="{ly}" x2="1130" y2="{ly}" stroke="{C["line"]}" stroke-width="3" stroke-linecap="round"/>')
    b.append(t(1160, 52, "ABOVE THE LINE: TOOLING ADDED", 11, C["orange"], 700, "end", ls=1.2))
    b.append(t(1160, 72, "BELOW THE LINE: FEATURES SHIPPED", 11, C["blue"], 700, "end", ls=1.2))
    step = (x1 - x0) / (len(ev) - 1)
    for i, (d, top, bot) in enumerate(ev):
        x, col = x0 + i * step, cols[i]
        b.append(f'<line x1="{x}" y1="{ly-50}" x2="{x}" y2="{ly-12}" stroke="{col}" stroke-width="1.5" opacity="0.6"/>')
        b.append(f'<line x1="{x}" y1="{ly+12}" x2="{x}" y2="{ly+34}" stroke="{C["blue"]}" stroke-width="1.5" opacity="0.5"/>')
        b.append(f'<circle cx="{x}" cy="{ly}" r="10" fill="{C["bg0"]}" stroke="{col}" stroke-width="3"/>')
        b.append(f'<circle cx="{x}" cy="{ly}" r="4" fill="{col}"/>')
        bw, bh = 140, 22 + 18 * len(top)
        b.append(rect(x - bw / 2, ly - 52 - bh, bw, bh, fill=col, stroke=col, op=0.12, rx=10))
        for k, s in enumerate(top):
            b.append(t(x, ly - 52 - bh + 24 + k * 18, s, 13, col, 700, "middle"))
        b.append(t(x, ly + 54, d, 12, C["text"], 700, "middle", mono=True))
        for k, s in enumerate(bot):
            b.append(t(x, ly + 78 + k * 19, s, 12.5, C["muted"], 500, "middle"))
    # maturity band
    by = 430
    stages = [("Ad-hoc prompting", C["dim"]), ("Rules + specs", C["blue"]),
              ("Automated commands", C["orange"]), ("Agents + guardrails", C["purple"])]
    sw = 1120 / 4
    for i, (s, col) in enumerate(stages):
        x = 40 + i * sw
        pts = f"{x},{by} {x+sw-14},{by} {x+sw},{by+24} {x+sw-14},{by+48} {x},{by+48} {x+14 if i else x},{by+24}"
        b.append(f'<polygon points="{pts}" fill="{col}" fill-opacity="{0.10+0.07*i}" stroke="{col}" stroke-opacity="0.5"/>')
        b.append(t(x + sw / 2, by + 29, s, 13.5, C["text"] if i else C["muted"], 700, "middle"))
    b.append(t(40, by - 12, "WORKFLOW MATURITY", 11, C["muted"], 700, ls=1.5))
    return svg(W, H, "\n".join(b), "Workflow evolution timeline")


for name, fn in [("banner", banner), ("workflow", workflow), ("claude-code-layers", layers),
                 ("feature-approach-matrix", matrix), ("workflow-evolution", timeline)]:
    with open(os.path.join(OUT, f"{name}.svg"), "w") as f:
        f.write(fn())
    print("wrote", name)
