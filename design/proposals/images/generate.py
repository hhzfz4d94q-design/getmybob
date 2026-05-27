"""Signal Field — five visual specimens.

Generates 5 PNG plates for the OfficeBeat × getmemyjob system:
  01_gmj_bullseye.png       — getmemyjob hero (bullseye / matching metaphor)
  02_gmj_dashboard_grid.png — getmemyjob feature mockup (card grid w/ scores)
  03_ob_signal_field.png    — officebeat hero (signal-extraction lattice)
  04_ob_finance_card.png    — officebeat Finance vertical (deep-navy waveform)
  05_ob_health_card.png     — officebeat Healthcare vertical (emerald braid)

All compositions follow the Signal Field philosophy:
  - White-dominant ground
  - Single intentional accent of color per plate
  - Geometric forms borrowed from scientific observation
  - Tiny clinical typography as reference markers, never voice
"""
import cairo, math, os, random

OUT = os.path.dirname(os.path.abspath(__file__))

# --- Tokens (extracted from the real OfficeBeat logo) ---------------
# The brand spans a gradient: midnight → royal → blue → periwinkle.
# We use the FULL palette here, not just the periwinkle endpoint.
MIDNIGHT      = (11/255, 8/255, 40/255)     # #0B0828 — "Office" wordmark
ROYAL         = (30/255, 20/255, 110/255)   # #1E146E — OB pill body
BLUE          = (24/255, 23/255, 181/255)   # #1817B5 — "Beat" core
PERIWINKLE    = (92/255, 92/255, 224/255)   # #5C5CE0 — end of "Beat"
MIST          = (209/255, 222/255, 255/255) # #D1DEFF — near-end tint

# Legacy aliases — kept so the existing plate code keeps compiling
INDIGO        = BLUE              # was #5C5CD6, now points to brand core
INDIGO_STRONG = ROYAL
INDIGO_DEEP   = MIDNIGHT
INDIGO_SOFT   = PERIWINKLE
INDIGO_50     = (238/255, 238/255, 248/255)
INDIGO_100    = (220/255, 220/255, 241/255)

INK           = MIDNIGHT
MUTED         = (95/255, 90/255, 126/255)   # #5F5A7E — blue-tinted muted
MUTED_SOFT    = (138/255, 134/255, 166/255) # #8A86A6
HAIRLINE      = (229/255, 229/255, 240/255) # #E5E5F0
HAIRLINE_SOFT = (240/255, 240/255, 247/255) # #F0F0F7
FINANCE       = (31/255, 44/255, 111/255)
HEALTH        = (14/255, 140/255, 122/255)
SURFACE       = (1, 1, 1)
SURFACE_TINT  = (246/255, 246/255, 251/255) # #F6F6FB


def setup(filename, w, h, bg=SURFACE, scale=2):
    """Create a high-DPI surface (scale=2 for retina-quality PNG)."""
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w*scale, h*scale)
    ctx = cairo.Context(surf)
    ctx.scale(scale, scale)
    ctx.set_source_rgb(*bg)
    ctx.rectangle(0, 0, w, h)
    ctx.fill()
    return surf, ctx, w, h


def label(ctx, text, x, y, size=10, color=MUTED, bold=False, caps=False, tracking=0):
    """Small clinical label. Inter, tabular, restrained."""
    if caps: text = text.upper()
    weight = cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL
    ctx.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, weight)
    ctx.set_font_size(size)
    ctx.set_source_rgb(*color)
    if tracking:
        for ch in text:
            ctx.move_to(x, y)
            ctx.show_text(ch)
            ext = ctx.text_extents(ch)
            x += ext.x_advance + tracking
    else:
        ctx.move_to(x, y)
        ctx.show_text(text)


def thinline(ctx, x1, y1, x2, y2, color=HAIRLINE, width=0.5):
    if len(color) == 4:
        ctx.set_source_rgba(*color)
    else:
        ctx.set_source_rgb(*color)
    ctx.set_line_width(width)
    ctx.move_to(x1, y1)
    ctx.line_to(x2, y2)
    ctx.stroke()


def tick(ctx, cx, cy, angle, inner, outer, color=MUTED_SOFT, width=0.5):
    x1 = cx + inner * math.cos(angle); y1 = cy + inner * math.sin(angle)
    x2 = cx + outer * math.cos(angle); y2 = cy + outer * math.sin(angle)
    thinline(ctx, x1, y1, x2, y2, color, width)


def brand_gradient(ctx, x0, y0, x1, y1, stops=None):
    """The signature OfficeBeat gradient — from the wordmark itself.
    Returns a Cairo LinearGradient configured midnight→royal→blue→periwinkle.
    Defaults: BLUE → PERIWINKLE (matches "B-e-a-t" of the wordmark)."""
    grad = cairo.LinearGradient(x0, y0, x1, y1)
    if stops is None:
        grad.add_color_stop_rgb(0.0, *BLUE)
        grad.add_color_stop_rgb(1.0, *PERIWINKLE)
    else:
        for offset, color in stops:
            grad.add_color_stop_rgb(offset, *color)
    return grad


def hero_gradient(ctx, x0, y0, x1, y1):
    """The deep-hero gradient: midnight → royal → blue (135deg in CSS)."""
    grad = cairo.LinearGradient(x0, y0, x1, y1)
    grad.add_color_stop_rgb(0.0, *MIDNIGHT)
    grad.add_color_stop_rgb(0.4, *ROYAL)
    grad.add_color_stop_rgb(1.0, *BLUE)
    return grad


def label_rgba(ctx, text, x, y, size, color, bold=False, caps=False, tracking=0):
    """Variant of label() that accepts RGBA color."""
    if caps: text = text.upper()
    weight = cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL
    ctx.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, weight)
    ctx.set_font_size(size)
    if len(color) == 4:
        ctx.set_source_rgba(*color)
    else:
        ctx.set_source_rgb(*color)
    if tracking:
        for ch in text:
            ctx.move_to(x, y)
            ctx.show_text(ch)
            ext = ctx.text_extents(ch)
            x += ext.x_advance + tracking
    else:
        ctx.move_to(x, y)
        ctx.show_text(text)


# --------------------------------------------------------------------
# 01 — getmemyjob bullseye hero (1600×900, social/hero)
# Concentric rings, candidate-job points scattered, ONE point hit dead center.
# --------------------------------------------------------------------
def plate_01_bullseye():
    surf, ctx, W, H = setup("01_gmj_bullseye.png", 1600, 900)
    cx, cy = W*0.66, H/2
    rs = [50, 110, 180, 260, 350, 450]

    # outer faint ring lattice
    for r in rs:
        ctx.set_source_rgb(*HAIRLINE)
        ctx.set_line_width(0.6)
        ctx.arc(cx, cy, r, 0, 2*math.pi)
        ctx.stroke()

    # tick marks every 30°
    for deg in range(0, 360, 30):
        a = math.radians(deg)
        tick(ctx, cx, cy, a, rs[-1]+6, rs[-1]+18, MUTED_SOFT, 0.5)

    # major axes — faint cross
    thinline(ctx, cx - rs[-1] - 20, cy, cx + rs[-1] + 20, cy, HAIRLINE_SOFT, 0.5)
    thinline(ctx, cx, cy - rs[-1] - 20, cx, cy + rs[-1] + 20, HAIRLINE_SOFT, 0.5)

    # scattered "candidate jobs" — small dots, fainter as they move outward
    random.seed(42)
    for _ in range(60):
        a = random.uniform(0, 2*math.pi)
        d = random.uniform(rs[1], rs[-1])
        x = cx + d*math.cos(a); y = cy + d*math.sin(a)
        # opacity decreases with distance
        alpha = 1.0 - (d - rs[1])/(rs[-1] - rs[1])*0.7
        ctx.set_source_rgba(*MUTED_SOFT, alpha*0.5)
        ctx.arc(x, y, 1.6, 0, 2*math.pi)
        ctx.fill()

    # the inner ring — indigo, the matched candidates
    ctx.set_source_rgb(*INDIGO)
    ctx.set_line_width(1.8)
    ctx.arc(cx, cy, rs[0], 0, 2*math.pi)
    ctx.stroke()

    # second ring — softer indigo
    ctx.set_source_rgba(*INDIGO, 0.4)
    ctx.set_line_width(0.9)
    ctx.arc(cx, cy, rs[1], 0, 2*math.pi)
    ctx.stroke()

    # five matched dots clustered inside the inner ring — each dot uses
    # a different stop on the brand gradient (subtle wordmark callback)
    matched = [
        ((cx-22, cy-8),   ROYAL),
        ((cx+10, cy-26),  BLUE),
        ((cx+24, cy+4),   BLUE),
        ((cx-6,  cy+22),  PERIWINKLE),
        ((cx-30, cy+18),  PERIWINKLE),
    ]
    for (x, y), color in matched:
        ctx.set_source_rgb(*color)
        ctx.arc(x, y, 4, 0, 2*math.pi)
        ctx.fill()
        # subtle glow
        ctx.set_source_rgba(*color, 0.18)
        ctx.arc(x, y, 11, 0, 2*math.pi)
        ctx.fill()

    # THE focal point — center, brand ROYAL (the deep OB-pill blue) ringed in white
    ctx.set_source_rgb(1,1,1)
    ctx.arc(cx, cy, 9, 0, 2*math.pi); ctx.fill()
    ctx.set_source_rgb(*ROYAL)
    ctx.arc(cx, cy, 6, 0, 2*math.pi); ctx.fill()

    # crosshair through center, slightly extended
    ctx.set_source_rgb(*INDIGO)
    ctx.set_line_width(1.0)
    ctx.move_to(cx - 18, cy); ctx.line_to(cx - 10, cy); ctx.stroke()
    ctx.move_to(cx + 10, cy); ctx.line_to(cx + 18, cy); ctx.stroke()
    ctx.move_to(cx, cy - 18); ctx.line_to(cx, cy - 10); ctx.stroke()
    ctx.move_to(cx, cy + 10); ctx.line_to(cx, cy + 18); ctx.stroke()

    # --- Left text column (the only words on the plate) -----------
    left_x = 90
    label(ctx, "SIGNAL FIELD · PL. 01", left_x, 90, 10, MUTED, bold=True, caps=True, tracking=1.4)
    thinline(ctx, left_x, 110, left_x + 60, 110, INDIGO, 1.2)

    ctx.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(64); ctx.set_source_rgb(*INK)
    ctx.move_to(left_x, 240); ctx.show_text("Find the")
    ctx.move_to(left_x, 320); ctx.show_text("signal in")
    # "the noise." rendered with the brand gradient — same trick the logo
    # uses on the word "Beat". Mirrors the wordmark's signature.
    text = "the noise."
    ctx.set_font_size(64)
    ext = ctx.text_extents(text)
    grad = brand_gradient(ctx, left_x, 0, left_x + ext.width, 0)
    ctx.set_source(grad)
    ctx.move_to(left_x, 400); ctx.show_text(text)

    ctx.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(16); ctx.set_source_rgb(*MUTED)
    ctx.move_to(left_x, 490); ctx.show_text("Every day, 20,000+ open roles flow past your")
    ctx.move_to(left_x, 512); ctx.show_text("inbox. We tune the matcher around the five")
    ctx.move_to(left_x, 534); ctx.show_text("titles, industries, and skills you actually want —")
    ctx.move_to(left_x, 556); ctx.show_text("and surface twenty that are worth your attention.")

    # tiny coordinate labels around the rings (clinical reference markers)
    label(ctx, "r₀ · 50", cx + rs[0] + 6, cy - 4, 9, MUTED_SOFT)
    label(ctx, "r₁ · 110", cx + rs[1] + 6, cy - 4, 9, MUTED_SOFT)
    label(ctx, "r₅ · 450", cx + rs[-1] + 22, cy + 4, 9, MUTED_SOFT)

    # bottom footer line
    label(ctx, "GETMEMYJOB · OFFICEBEAT LLC · MMXXVI", left_x, H-50, 9, MUTED_SOFT, caps=True, tracking=1.2)

    out = os.path.join(OUT, "01_gmj_bullseye.png")
    surf.write_to_png(out); print(f"wrote {out}")


# --------------------------------------------------------------------
# 02 — getmemyjob dashboard mockup (1600×900)
# Stylized card grid suggesting scored job listings.
# --------------------------------------------------------------------
def plate_02_dashboard():
    surf, ctx, W, H = setup("02_gmj_dashboard_grid.png", 1600, 900, bg=SURFACE_TINT)
    # header bar
    ctx.set_source_rgb(1,1,1)
    ctx.rectangle(0, 0, W, 72); ctx.fill()
    thinline(ctx, 0, 72, W, 72, HAIRLINE, 1)

    label(ctx, "GETMEMYJOB", 50, 44, 13, INDIGO, bold=True, caps=True, tracking=1.6)
    label(ctx, "TODAY'S TOP 20 · TUE 27 MAY", W-330, 44, 11, MUTED, caps=True, tracking=1.2)

    # eyebrow + h1
    label(ctx, "JOBS FOR YOU", 50, 130, 11, MUTED, bold=True, caps=True, tracking=1.6)
    ctx.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(34); ctx.set_source_rgb(*INK)
    ctx.move_to(50, 168); ctx.show_text("20 matches · avg score 88")

    # build a 5×3 card grid suggesting cards w/ scores
    grid_x0, grid_y0 = 50, 220
    card_w, card_h, gap = 290, 180, 18
    rows, cols = 3, 5
    scores = [94, 91, 89, 86, 83,
              82, 80, 78, 76, 73,
              72, 70, 68, 65, 62]
    titles = [("VP, Risk Strategy", "Stripe"),
              ("Director, TPRM", "Ramp"),
              ("Head of GRC", "Plaid"),
              ("VP, ERM", "Brex"),
              ("Dir, Reg Compliance", "Mercury"),
              ("Director, Risk", "Modern Treasury"),
              ("VP, Compliance", "Wise"),
              ("Head of Audit", "Affirm"),
              ("Director, Risk Adv", "TreasuryPrime"),
              ("Sr. Dir, Risk Tech", "Galileo"),
              ("Head, Third-Party Risk", "Marqeta"),
              ("VP, GRC Programs", "Lithic"),
              ("Director, Risk Ops", "Unit"),
              ("Head, Risk Ops", "Bond"),
              ("VP, Risk Mgmt", "Highnote")]

    for r in range(rows):
        for c in range(cols):
            i = r*cols + c
            x = grid_x0 + c*(card_w+gap); y = grid_y0 + r*(card_h+gap)
            # card surface
            ctx.set_source_rgb(1,1,1)
            ctx.rectangle(x, y, card_w, card_h); ctx.fill()
            ctx.set_source_rgb(*HAIRLINE)
            ctx.set_line_width(0.6); ctx.rectangle(x, y, card_w, card_h); ctx.stroke()
            # score chip
            s = scores[i]
            chip_w = 56; chip_h = 24
            chip_x = x + card_w - chip_w - 14; chip_y = y + 14
            # color: dark indigo for top scores, fade for lower
            chip_fill = INDIGO if s >= 80 else (INDIGO_50 if s >= 70 else SURFACE_TINT)
            chip_text = (1,1,1) if s >= 80 else (INDIGO if s >= 70 else MUTED)
            ctx.set_source_rgb(*chip_fill)
            # rounded-ish rectangle (approximate via 4 arcs)
            rr = 12
            for cx_, cy_ in [(chip_x+rr, chip_y+rr), (chip_x+chip_w-rr, chip_y+rr),
                              (chip_x+chip_w-rr, chip_y+chip_h-rr), (chip_x+rr, chip_y+chip_h-rr)]:
                ctx.arc(cx_, cy_, rr, 0, 2*math.pi); ctx.fill()
            ctx.rectangle(chip_x, chip_y+rr, chip_w, chip_h-2*rr); ctx.fill()
            ctx.rectangle(chip_x+rr, chip_y, chip_w-2*rr, chip_h); ctx.fill()
            label(ctx, str(s), chip_x + 18, chip_y + 17, 13, chip_text, bold=True)

            # rank
            label(ctx, f"{i+1:02d}", x + 16, y + 30, 10, MUTED_SOFT, bold=True, caps=True, tracking=1)
            # title
            ctx.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            ctx.set_font_size(15); ctx.set_source_rgb(*INK)
            ctx.move_to(x + 16, y + 64); ctx.show_text(titles[i][0])
            # company
            label(ctx, titles[i][1].upper(), x+16, y+86, 10, MUTED, caps=True, tracking=1.2)
            # tiny score bars indicating match breakdown
            bar_y = y + 110
            comps = [("T", 0.4 + (s-60)/40*0.6),
                     ("I", 0.5 + (s-60)/40*0.5),
                     ("S", 0.6 + (s-60)/40*0.4)]
            for bi, (lbl_, frac) in enumerate(comps):
                by = bar_y + bi*16
                label(ctx, lbl_, x+16, by+8, 9, MUTED_SOFT, bold=True)
                # track
                ctx.set_source_rgb(*HAIRLINE_SOFT)
                ctx.rectangle(x+30, by, card_w-46, 4); ctx.fill()
                # fill — color faded by score
                fill_color = INDIGO if s >= 80 else (INDIGO_SOFT if s >= 70 else MUTED_SOFT)
                ctx.set_source_rgb(*fill_color)
                ctx.rectangle(x+30, by, (card_w-46)*max(0.1, min(1, frac)), 4); ctx.fill()

    # footer marker
    label(ctx, "SIGNAL FIELD · PL. 02 — UI SPECIMEN, CARDS-AS-OBSERVATION",
          50, H-30, 9, MUTED_SOFT, caps=True, tracking=1.2)

    out = os.path.join(OUT, "02_gmj_dashboard_grid.png")
    surf.write_to_png(out); print(f"wrote {out}")


# --------------------------------------------------------------------
# 03 — officebeat signal-extraction lattice hero (1600×900)
# Vertical bars in a row — most are short-grey "noise", a few are tall-indigo "signal"
# representing the consulting "what matters" thesis.
# --------------------------------------------------------------------
def plate_03_signal_field():
    surf, ctx, W, H = setup("03_ob_signal_field.png", 1600, 900)
    bars_x0 = 700; bars_y_base = 700; bar_w = 6; bar_gap = 4
    n_bars = 130

    # deterministic "spectrum" with a few standout peaks
    random.seed(7)
    heights = []
    for i in range(n_bars):
        if i in (32, 41, 67, 89, 104):
            heights.append(random.uniform(280, 400))  # signal peaks
        else:
            heights.append(random.uniform(18, 80))     # noise floor
    peaks = {32, 41, 67, 89, 104}

    for i, h in enumerate(heights):
        x = bars_x0 + i*(bar_w + bar_gap)
        if x + bar_w > W - 80: break
        if i in peaks:
            # Signal peaks — vertical brand gradient (royal at base → periwinkle at top)
            grad = cairo.LinearGradient(0, bars_y_base, 0, bars_y_base - h)
            grad.add_color_stop_rgb(0.0, *ROYAL)
            grad.add_color_stop_rgb(0.5, *BLUE)
            grad.add_color_stop_rgb(1.0, *PERIWINKLE)
            ctx.set_source(grad)
        else:
            ctx.set_source_rgb(215/255, 217/255, 232/255)  # noise floor
        ctx.rectangle(x, bars_y_base - h, bar_w, h)
        ctx.fill()
        # tiny baseline tick
        ctx.set_source_rgb(*HAIRLINE)
        ctx.rectangle(x, bars_y_base, bar_w, 2); ctx.fill()

    # baseline axis
    thinline(ctx, bars_x0 - 20, bars_y_base + 2, W - 80, bars_y_base + 2, MUTED_SOFT, 0.8)
    # tick labels under axis
    for i, lbl_ in [(8, "10"), (30, "100"), (58, "1k"), (86, "10k"), (114, "100k")]:
        x = bars_x0 + i*(bar_w + bar_gap)
        if x < W - 80:
            tick(ctx, x, bars_y_base + 6, math.pi/2, 0, 4, MUTED_SOFT, 0.6)
            label(ctx, lbl_, x - 8, bars_y_base + 22, 9, MUTED_SOFT, caps=True, tracking=1)

    label(ctx, "FREQ. ↑", bars_x0 - 60, bars_y_base + 24, 9, MUTED_SOFT, caps=True, tracking=1.2)

    # callout for tallest peak
    peak_idx = 41
    peak_x = bars_x0 + peak_idx*(bar_w + bar_gap)
    peak_y = bars_y_base - heights[peak_idx]
    thinline(ctx, peak_x + bar_w/2, peak_y - 8, peak_x + bar_w/2, peak_y - 50, INDIGO, 0.6)
    thinline(ctx, peak_x + bar_w/2, peak_y - 50, peak_x + 90, peak_y - 50, INDIGO, 0.6)
    label(ctx, "TPRM · 2026 PEAK", peak_x + 95, peak_y - 46, 10, INDIGO, bold=True, caps=True, tracking=1.2)

    # --- Left text ---------------------------------------------
    lx = 90
    label(ctx, "SIGNAL FIELD · PL. 03", lx, 90, 10, MUTED, bold=True, caps=True, tracking=1.4)
    thinline(ctx, lx, 110, lx + 60, 110, INDIGO, 1.2)

    ctx.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(60); ctx.set_source_rgb(*INK)
    ctx.move_to(lx, 260); ctx.show_text("Where it")
    ctx.move_to(lx, 332); ctx.show_text("matters,")
    # "with rigour." with the signature brand gradient
    text = "with rigour."
    ctx.set_font_size(60)
    ext = ctx.text_extents(text)
    grad = brand_gradient(ctx, lx, 0, lx + ext.width, 0)
    ctx.set_source(grad)
    ctx.move_to(lx, 404); ctx.show_text(text)

    ctx.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(17); ctx.set_source_rgb(*MUTED)
    ctx.move_to(lx, 490); ctx.show_text("Practitioner-led advisory in financial services")
    ctx.move_to(lx, 512); ctx.show_text("and healthcare — risk, regulation, and operating")
    ctx.move_to(lx, 534); ctx.show_text("models, delivered by people who built them.")

    # bottom row of clinical labels — verticals indexed like specimens
    label(ctx, "F · FINANCE & BANKING", lx, H-100, 10, FINANCE, bold=True, caps=True, tracking=1.4)
    label(ctx, "H · HEALTHCARE & LIFE SCIENCES", lx, H-78, 10, HEALTH, bold=True, caps=True, tracking=1.4)
    label(ctx, "OFFICEBEAT LLC · ESTD MMXIX · NYC", lx, H-50, 9, MUTED_SOFT, caps=True, tracking=1.2)

    out = os.path.join(OUT, "03_ob_signal_field.png")
    surf.write_to_png(out); print(f"wrote {out}")


# --------------------------------------------------------------------
# 04 — officebeat Finance vertical card (900×1100) — deep navy waveform
# --------------------------------------------------------------------
def plate_04_finance():
    surf, ctx, W, H = setup("04_ob_finance_card.png", 900, 1100)

    # Top half — navy field with a sine-derivative waveform (capital markets pulse)
    top_h = 620
    ctx.set_source_rgb(*FINANCE)
    ctx.rectangle(0, 0, W, top_h); ctx.fill()

    # waveform — composed of three sin waves at different frequencies
    ctx.set_source_rgba(1, 1, 1, 0.20)
    ctx.set_line_width(1.0)
    step = 4
    cx = W/2; cy = top_h * 0.62
    for off in (-1, 0, 1):
        ctx.new_path()
        for x in range(0, W+step, step):
            phase = x/W * 4 * math.pi + off * 0.7
            y = cy + (math.sin(phase)*30 + math.sin(phase*2.1)*18 + math.sin(phase*0.4)*40) * 0.7
            if x == 0: ctx.move_to(x, y)
            else: ctx.line_to(x, y)
        ctx.stroke()

    # main waveform — bright
    ctx.set_source_rgba(1, 1, 1, 0.95)
    ctx.set_line_width(1.6)
    ctx.new_path()
    for x in range(0, W+step, step):
        phase = x/W * 4 * math.pi
        y = cy + (math.sin(phase)*30 + math.sin(phase*2.1)*18 + math.sin(phase*0.4)*40) * 0.85
        if x == 0: ctx.move_to(x, y)
        else: ctx.line_to(x, y)
    ctx.stroke()

    # five "tick marks" along baseline — quarters
    base_y = cy + 100
    thinline(ctx, 80, base_y, W-80, base_y, (1,1,1,0.4), 0.5)
    for i, q in enumerate(['Q1','Q2','Q3','Q4','FY']):
        x = 80 + i * (W-160)/4
        tick(ctx, x, base_y, -math.pi/2, 0, 6, (1,1,1,0.6), 0.5)
        label_rgba(ctx, q, x-8, base_y+22, 10, (1,1,1,0.65), bold=True, caps=True, tracking=1.4)

    # title (white)
    label_rgba(ctx, "VERTICAL · F", 60, 80, 10, (1,1,1,0.7), bold=True, caps=True, tracking=1.6)
    thinline(ctx, 60, 96, 110, 96, (1,1,1,0.9), 1.2)

    ctx.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(56); ctx.set_source_rgb(1, 1, 1)
    ctx.move_to(60, 200); ctx.show_text("Finance &")
    ctx.move_to(60, 268); ctx.show_text("Banking")

    # Bottom half — white, practice listing as a typeset stratum
    practices = [
        ("ERM", "Enterprise Risk · Frameworks · Maturity"),
        ("CR",  "Credit Risk · Modelling · Validation"),
        ("OR",  "Operational Risk · KRI Programs · Loss"),
        ("TR",  "Treasury · Liquidity · Capital · IRR"),
        ("M&A", "Programs · Integration · Carve-Outs"),
        ("RT",  "Real-Time Payments · Operational Risk"),
    ]
    y0 = top_h + 60
    for i, (code, desc) in enumerate(practices):
        y = y0 + i*54
        label(ctx, code, 60, y, 18, FINANCE, bold=True, caps=True, tracking=1.6)
        ctx.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(14); ctx.set_source_rgb(*MUTED)
        ctx.move_to(170, y); ctx.show_text(desc)
        thinline(ctx, 60, y + 16, W - 60, y + 16, HAIRLINE_SOFT, 0.5)

    label(ctx, "OFFICEBEAT · PL. 04", 60, H-30, 9, MUTED_SOFT, caps=True, tracking=1.4)

    out = os.path.join(OUT, "04_ob_finance_card.png")
    surf.write_to_png(out); print(f"wrote {out}")


# --------------------------------------------------------------------
# 05 — officebeat Healthcare vertical card (900×1100) — emerald braid
# --------------------------------------------------------------------
def plate_05_health():
    surf, ctx, W, H = setup("05_ob_health_card.png", 900, 1100)

    # Top half — emerald field with a braided lattice (care / connection)
    top_h = 620
    ctx.set_source_rgb(*HEALTH)
    ctx.rectangle(0, 0, W, top_h); ctx.fill()

    # braided lattice — two phase-shifted sin curves at low alpha
    cx = W/2; cy = top_h * 0.62
    step = 3
    for off, alpha in [(-1, 0.25), (1, 0.25)]:
        ctx.set_source_rgba(1, 1, 1, alpha)
        ctx.set_line_width(1.0)
        ctx.new_path()
        for x in range(0, W+step, step):
            phase = x/W * 6 * math.pi
            y = cy + math.sin(phase + off) * 70
            if x == 0: ctx.move_to(x, y)
            else: ctx.line_to(x, y)
        ctx.stroke()

    # bright primary curve
    ctx.set_source_rgba(1, 1, 1, 0.95)
    ctx.set_line_width(1.8)
    ctx.new_path()
    for x in range(0, W+step, step):
        phase = x/W * 6 * math.pi
        y = cy + math.sin(phase) * 70
        if x == 0: ctx.move_to(x, y)
        else: ctx.line_to(x, y)
    ctx.stroke()

    # five marked nodes along the curve — practice anchors
    for i in range(5):
        x = 100 + i * (W-200)/4
        phase = x/W * 6 * math.pi
        y = cy + math.sin(phase) * 70
        ctx.set_source_rgb(1, 1, 1)
        ctx.arc(x, y, 8, 0, 2*math.pi); ctx.fill()
        ctx.set_source_rgb(*HEALTH)
        ctx.arc(x, y, 4, 0, 2*math.pi); ctx.fill()

    label_rgba(ctx, "VERTICAL · H", 60, 80, 10, (1,1,1,0.7), bold=True, caps=True, tracking=1.6)
    thinline(ctx, 60, 96, 110, 96, (1,1,1,0.9), 1.2)

    ctx.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(56); ctx.set_source_rgb(1, 1, 1)
    ctx.move_to(60, 200); ctx.show_text("Healthcare")
    ctx.move_to(60, 268); ctx.show_text("& Life Sci.")

    # Bottom — practice listing in emerald
    practices = [
        ("DT",  "Digital Transformation · Care Models"),
        ("AIG", "AI Program Governance · Clinical Models"),
        ("EHR", "EHR Strategy · Implementation · Optim."),
        ("REG", "HIPAA / HITRUST · Regulatory Programs"),
        ("OPS", "Operating Models · Network Strategy"),
        ("M&A", "Programs · Integration · Provider Deals"),
    ]
    y0 = top_h + 60
    for i, (code, desc) in enumerate(practices):
        y = y0 + i*54
        label(ctx, code, 60, y, 18, HEALTH, bold=True, caps=True, tracking=1.6)
        ctx.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(14); ctx.set_source_rgb(*MUTED)
        ctx.move_to(170, y); ctx.show_text(desc)
        thinline(ctx, 60, y + 16, W - 60, y + 16, HAIRLINE_SOFT, 0.5)

    label(ctx, "OFFICEBEAT · PL. 05", 60, H-30, 9, MUTED_SOFT, caps=True, tracking=1.4)

    out = os.path.join(OUT, "05_ob_health_card.png")
    surf.write_to_png(out); print(f"wrote {out}")


if __name__ == "__main__":
    plate_01_bullseye()
    plate_02_dashboard()
    plate_03_signal_field()
    plate_04_finance()
    plate_05_health()
    print("\ndone — 5 plates in", OUT)
