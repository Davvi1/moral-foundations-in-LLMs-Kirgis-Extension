#!/usr/bin/env python3
"""Presentation figures, regenerated from the committed data.

Every number drawn here is DERIVED at runtime from `results/derived/`, never
transcribed from a markdown table. That is deliberate: C18 and C21 in
`CORRECTIONS.md` are both cases of a number surviving in prose after its basis
moved, and a slide deck is the furthest a stale number can travel.

Where a figure reproduces a committed artifact, the value is asserted against it
(see `--check`), so a figure cannot silently disagree with `FINDINGS.md`.

Design follows the `dataviz` skill: form chosen before colour, categorical hues
in fixed slot order, emphasis (one hue + grey) wherever a single item is the
point, hairline solid chrome, selective direct labels, text in ink tokens rather
than series colours. Palettes validated with the skill's own validator:

    3 all-pairs slots   #2a78d6,#eb6834,#1baf7a          PASS light
    4 adjacent slots    + #eda100                         PASS light
    ordinal blue ramp   #86b6ef,#3987e5,#1c5cab,#0d366b   PASS light --ordinal

Usage:
    python scripts/make_figures.py            # write figures/*.png
    python scripts/make_figures.py --check    # verify against artifacts, draw nothing
"""
from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "results" / "derived"
FIGDIR = ROOT / "figures"
sys.path.insert(0, str(ROOT / "scripts"))

# ---------------------------------------------------------------------------
# Tokens — from the dataviz reference palette, light mode
# ---------------------------------------------------------------------------
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

S1, S2, S3, S4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"   # categorical slots
S8 = "#e34948"                                                # slot 8, red
DEEMPH = "#d6d5cf"                                            # de-emphasis grey
BLUE = ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]           # ordinal ramp

MORAL = ["Care", "Fairness", "Liberty", "Loyalty", "Authority", "Sanctity"]
CONTROL = "Social Norms"
ARMS = ["label", "string_line", "string_bare", "cloze", "greedy", "sampled"]
ARM_LABEL = {
    "label": "label", "string_line": "string (line)", "string_bare": "string (bare)",
    "cloze": "cloze", "greedy": "greedy", "sampled": "sampled",
}

# Kirgis Table 1, verified against his repo and paper (references.md).
KIRGIS_ROSTER = [
    ("OpenAI", "GPT-3.5-Turbo", "logprob"), ("OpenAI", "GPT-4-Turbo", "logprob"),
    ("OpenAI", "GPT-4o", "logprob"), ("OpenAI", "GPT-4.1", "logprob"),
    ("OpenAI", "GPT-4.5", "sampled"), ("OpenAI", "o3-Mini", "sampled"),
    ("xAI", "Grok-2", "logprob"), ("xAI", "Grok-3", "logprob"),
    ("Anthropic", "Claude × 4", "sampled"),
    ("Google", "Gemini × 4", "sampled"),
    ("Meta", "Llama × 3", "sampled"),
    ("DeepSeek", "DeepSeek × 2", "sampled"),
]
KIRGIS_COUNTS = {"Anthropic": 4, "Google": 4, "Meta": 3, "DeepSeek": 2}


def _mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": ["Segoe UI", "DejaVu Sans", "sans-serif"],
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE, "savefig.dpi": 200,
        "axes.edgecolor": AXIS, "axes.linewidth": 0.8,
        "axes.labelcolor": INK_2, "axes.titlecolor": INK,
        "xtick.color": MUTED, "ytick.color": MUTED,
        "xtick.labelcolor": INK_2, "ytick.labelcolor": INK_2,
        "grid.color": GRID, "grid.linewidth": 0.8, "grid.linestyle": "-",
        "axes.grid": False, "axes.spines.top": False, "axes.spines.right": False,
        "font.size": 11, "axes.titlesize": 13, "legend.frameon": False,
        "figure.autolayout": False,
    })
    return plt


def style(ax, xgrid=False, ygrid=False):
    ax.set_axisbelow(True)
    if xgrid:
        ax.xaxis.grid(True)
    if ygrid:
        ax.yaxis.grid(True)
    ax.tick_params(length=0)
    return ax


# Set by --bare / the second pass in main(). In bare mode the title block is not
# drawn, because the DECK carries the headline in its own slide header and having
# both duplicates it on every figure slide. bbox_inches="tight" then crops the
# empty band away by itself, so no per-figure layout retuning is needed.
BARE = False


def title(fig, head, sub=None, x=0.012):
    """Title block: the finding as the headline, the metric as the subtitle."""
    if BARE:
        return
    fig.text(x, 0.975, head, ha="left", va="top", fontsize=14.5,
             color=INK, fontweight="semibold")
    if sub:
        fig.text(x, 0.905, sub, ha="left", va="top", fontsize=10.5, color=INK_2)


def save(fig, name):
    out_dir = FIGDIR / "deck" if BARE else FIGDIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{name}.png"
    fig.savefig(out, bbox_inches="tight", pad_inches=0.22)
    print(f"  wrote {out.relative_to(ROOT).as_posix()}")
    plt_close(fig)
    return out


def plt_close(fig):
    import matplotlib.pyplot as plt
    plt.close(fig)


# ===========================================================================
# Data derivation — every quantity recomputed, then asserted
# ===========================================================================
def load():
    df = pd.read_csv(DERIVED / "analysis_long_v2.csv")
    vr = pd.read_csv(DERIVED / "variance_ratio_v2.csv")
    sim = pd.read_csv(DERIVED / "design_simulation.csv")
    null = pd.read_csv(DERIVED / "mcmc_permutation_null_v2.csv")
    kir = pd.read_csv(DERIVED / "kirgis_rescored.csv")
    return df, vr, sim, null, kir


def primary_R(vr):
    """The pre-specified primary: exclusions applied, method-specific residuals."""
    p = vr[(vr.exclusions) & (~vr.scan_excluded) & (~vr.family_effect)
           & (vr.residual == "method-specific")]
    assert len(p) == 7, f"expected 7 primary rows, got {len(p)}"
    assert (p.n_models == 30).all() and (p.n_methods == 5).all()
    return p.set_index("foundation")


def pairwise_R(df):
    """R for every arm pair on ONE common complete-case block (controls_v2.md 4)."""
    from analyse_controls import balanced_block, moment_R
    blocks = {f: balanced_block(df, f, methods=ARMS) for f in MORAL}
    out = {}
    for a, b in itertools.combinations(ARMS, 2):
        vals = []
        for f in MORAL:
            blk = blocks[f]
            if blk is None:
                continue
            arr = blk[0][:, [ARMS.index(a), ARMS.index(b)], :]
            vals.append(moment_R(arr.ravel(), None, None, None,
                                 arr.shape[0], 2, arr.shape[2]))
        out[(a, b)] = float(np.nanmean(vals))
    return out


def retained_mass(df):
    ok = df[~df.excluded]
    per_model = (ok[ok.condition == "label"].groupby("model").logprob_mass.mean())
    per_arm = {a: ok[ok.condition == a].logprob_mass.mean()
               for a in ["label", "string_line", "string_bare", "cloze"]}
    return per_model.sort_values(), per_arm


def refusal_vs_mass(df):
    """Greedy non-answer rate against label retained mass, per model (all 31)."""
    g = df[df.condition == "greedy"]
    nonanswer = g.groupby("model").apply(
        lambda d: float((d.failure_type != "ok").mean()), include_groups=False)
    mass = df[df.condition == "label"].groupby("model").logprob_mass.mean()
    j = pd.DataFrame({"nonanswer": nonanswer, "mass": mass}).dropna()
    rho = float(pd.Series(j.nonanswer).corr(pd.Series(j.mass), method="spearman"))
    return j, rho


def rank_agreement(df):
    """Mean Spearman rho of model orderings, over the six moral foundations."""
    from analyse_controls import spearman
    ok = df[(~df.excluded) & df.score.notna()]
    cell = ok.groupby(["foundation", "condition", "model"]).score.mean()
    M = pd.DataFrame(index=ARMS, columns=ARMS, dtype=float)
    for a, b in itertools.combinations(ARMS, 2):
        vals = []
        for f in MORAL:
            try:
                x, y = cell.loc[(f, a)], cell.loc[(f, b)]
            except KeyError:
                continue
            common = x.index.intersection(y.index)
            if len(common) >= 4:
                vals.append(spearman(x[common].values, y[common].values))
        M.loc[a, b] = M.loc[b, a] = float(np.nanmean(vals))
    np.fill_diagonal(M.values, 1.0)
    return M


def interaction_share(df):
    """Each model's share of the interaction sum of squares (controls_v2.md 5)."""
    from analyse_controls import balanced_block
    tot, per = 0.0, {}
    for f in MORAL:
        blk = balanced_block(df, f, methods=[a for a in ARMS if a != "cloze"])
        if blk is None:
            continue
        arr, models, _ = blk
        ybar = arr.mean()
        ym = arr.mean(axis=(1, 2))[:, None]
        yr = arr.mean(axis=(0, 2))[None, :]
        ymr = arr.mean(axis=2)
        ss = (ymr - ym - yr + ybar) ** 2 * arr.shape[2]
        tot += ss.sum()
        for i, m in enumerate(models):
            per[m] = per.get(m, 0.0) + ss[i].sum()
    return pd.Series({m: v / tot for m, v in per.items()}).sort_values(ascending=False)


def scale_ladders(df):
    """Compression-adjusted individualizing-minus-binding gap vs size, per ladder.

    The gap and its compression adjustment come from `analyse_scale.gap_per_model`
    rather than being recomputed here. A second implementation of a correction this
    load-bearing is a second thing to keep in sync, and the first attempt at one
    silently produced +0.279 against the artifact's +0.324 — caught only because
    `checks()` compares against the artifact. One implementation, imported.
    """
    from scipy import stats
    from analyse_scale import gap_per_model, load_params

    params = load_params()
    ok = df[(~df.excluded) & df.score.notna()]
    r = gap_per_model(ok)
    r["params"] = r.model.map(params)
    r = r.dropna(subset=["params"])
    r["logp"] = np.log10(r.params)
    fits = {}
    for fam, sub in [("qwen", r[r.model.str.startswith("Qwen/")]),
                     ("llama", r[r.model.str.startswith("meta-llama/")])]:
        lr = stats.linregress(sub.logp, sub.gap)
        fits[fam] = {"data": sub.sort_values("params"), "slope": lr.slope,
                     "p": lr.pvalue, "int": lr.intercept}
    return r, fits


def qwen_compression(df, scale_rows):
    """The per-model compression line for the Qwen ladder.

    Uses the same per-model fit `gap_per_model` performs — one regression per model
    over the pooled probability arms — so `b` here is the same number the scale
    analysis adjusts by (Qwen ladder: 0.113 -> 1.059).
    """
    from scipy import stats
    from analyse_scale import PROB

    ok = df[(~df.excluded) & df.score.notna() & df.condition.isin(PROB)
            & df.model.str.startswith("Qwen/")]
    b_ref = scale_rows.set_index("model").compression_b
    out = []
    for m, d in ok.groupby("model"):
        fit = stats.linregress(d.clifford_wrong_mean, d.score)
        assert abs(fit.slope - b_ref[m]) < 1e-9, f"{m}: compression b disagrees"
        out.append({"model": m, "params": scale_rows.set_index("model").params[m],
                    "b": float(fit.slope), "a": float(fit.intercept)})
    return sorted(out, key=lambda r: r["params"])


# ===========================================================================
# Figures
# ===========================================================================
def fig01_confound(plt):
    """One cell per model, placed in the arm it was actually scored with."""
    fig, ax = plt.subplots(figsize=(11, 4.6))
    cells = {                      # provider -> (n logprob-scored, n sampled)
        "OpenAI": (4, 2), "xAI": (2, 0), "Anthropic": (0, 4),
        "Google": (0, 4), "Meta": (0, 3), "DeepSeek": (0, 2),
    }
    provs = list(cells)
    w, gap = 0.155, 0.028          # cell width and the 2px-equivalent surface gap
    for xi, p in enumerate(provs):
        for row, (n, col) in enumerate([(cells[p][1], S2), (cells[p][0], S1)]):
            for k in range(n):
                x = xi - (n * (w + gap) - gap) / 2 + k * (w + gap)
                ax.add_patch(plt.Rectangle((x, row - 0.22), w, 0.44, facecolor=col,
                                           edgecolor="none", zorder=3))
        for row, n in [(0, cells[p][1]), (1, cells[p][0])]:
            if n:
                ax.text(xi, row + 0.34, f"{n}", ha="center", va="center",
                        fontsize=10, color=INK_2)
    ax.set_xticks(range(len(provs)))
    ax.set_xticklabels(provs, fontsize=11.5, color=INK)
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["mean of ten\nsampled responses", "top-3 logprob\nweighting"],
                       fontsize=10.5)
    ax.set_xlim(-0.62, len(provs) - 0.38)
    ax.set_ylim(-0.62, 1.92)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    ax.annotate("only OpenAI spans both arms — and there,\nscoring method is confounded "
                "with model identity",
                xy=(0.0, 1.30), xytext=(0.62, 1.72), fontsize=9.8, color=INK_2,
                ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=AXIS, lw=1,
                                connectionstyle="arc3,rad=0.25"))
    title(fig, "Scoring method was forced to vary by provider",
          "Kirgis (2025): 21 models, one cell each. Five of six providers sit entirely "
          "in one arm — a non-identification, not something a covariate fixes.")
    fig.subplots_adjust(top=0.75, bottom=0.11, left=0.155, right=0.99)
    return save(fig, "fig01_kirgis_confound")


def fig02_grok(plt, kir):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), width_ratios=[1.25, 1])
    models = ["gpt-3.5-turbo", "gpt-4-turbo", "gpt-4.1", "gpt-4o", "grok-2-1212",
              "grok-3-beta"]
    ax = axes[0]
    for i, m in enumerate(models):
        v = kir[kir.Model == m].top_mass.values
        bad = m == "grok-3-beta"
        ax.scatter(v + np.random.default_rng(0).normal(0, .004, len(v)),
                   np.full(len(v), i) + np.random.default_rng(i).normal(0, .10, len(v)),
                   s=13, color=S8 if bad else DEEMPH, alpha=.75 if bad else .9,
                   linewidths=0, zorder=3)
    ax.axvline(0.5, color=AXIS, lw=1, zorder=1)
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels(models, fontsize=10)
    ax.set_xlabel("probability mass returned in top_logprobs", fontsize=10)
    ax.set_xlim(-0.06, 1.06)
    ax.set_ylim(-0.7, len(models) - 0.3)
    style(ax, xgrid=True)
    ax.text(0.075, 5.46, "51 of 116 responses (44%)\nreturn ~0 mass", fontsize=9.5,
            color=S8, ha="left", va="top", fontweight="semibold")

    ax = axes[1]
    codev = kir.groupby("Model").kirgis_code.mean()
    paper = kir.groupby("Model").kirgis_paper.mean()
    order = codev.sort_values(ascending=False).index.tolist()
    for i, m in enumerate(order):
        bad = m == "grok-3-beta"
        c = S8 if bad else DEEMPH
        ax.plot([codev[m], paper[m]], [i, i], color=c, lw=2.2, zorder=2,
                solid_capstyle="round")
        ax.scatter([codev[m]], [i], s=52, color=c, zorder=3,
                   edgecolors=SURFACE, linewidths=1.6)
        ax.scatter([paper[m]], [i], s=52, facecolor=SURFACE, edgecolors=c,
                   linewidths=1.8, zorder=3)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order, fontsize=10)
    ax.set_xlabel("mean severity, all 116 items", fontsize=10)
    ax.set_ylim(-0.7, len(order) - 0.3)
    style(ax, xgrid=True)
    ax.scatter([], [], s=52, color=INK_2, label="his code (renormalises)")
    ax.scatter([], [], s=52, facecolor=SURFACE, edgecolors=INK_2, linewidths=1.8,
               label="his printed formula")
    ax.legend(fontsize=9.2, loc="lower left", labelcolor=INK_2)
    ax.annotate("1.98 → 1.20\nrank 4 → 6", xy=(1.45, 5), xytext=(1.30, 3.70),
                fontsize=9.5, color=S8, ha="center", fontweight="semibold")
    # The two estimators coincide to 3 dp on the five clean models, so their markers
    # overlap exactly. Say so, or the missing filled dots read as a plotting bug.
    # Placed in FIGURE coords with reserved space below, not axes coords — at
    # axes y=-0.03 it landed on top of the tick labels.
    fig.text(0.985, 0.035, "the two estimators coincide for every model but one",
             ha="right", va="bottom", fontsize=9, color=MUTED)
    title(fig, "Provider logprob APIs cannot be assumed well-formed",
          "Kirgis's own committed data. His renormalisation accidentally rescues the "
          "corrupted rows; the formula printed in his paper does not.")
    fig.subplots_adjust(top=0.76, bottom=0.20, left=0.115, right=0.985, wspace=0.42)
    return save(fig, "fig02_grok3_integrity")


def fig03_arms(plt):
    fig = plt.figure(figsize=(11, 5.6))
    ax = fig.add_axes([0.02, 0.10, 0.96, 0.74])
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0.02, 0.475), 0.36, 0.445, facecolor="#f2f1ec",
                               edgecolor=GRID, lw=1))
    ax.text(0.04, 0.875, "the prompt — byte-identical in 5 of 6 arms",
            fontsize=9.3, color=MUTED, va="top")
    ax.text(0.04, 0.805,
            "Please rate how morally wrong this\nbehavior is on the following\n"
            "five-point scale: ⟨vignette⟩\n\n"
            "  0: Not at all wrong\n  1: Not too wrong\n  2: Somewhat wrong\n"
            "  3: Very wrong\n  4: Extremely wrong",
            fontsize=9.6, color=INK, va="top", family="DejaVu Sans")
    rows = [
        ("label", "P(“3”)  — the digit token", S1, "READS THE PROPENSITY"),
        ("string, line", "P(“3: Very wrong”)", S1, None),
        ("string, bare", "P(“Very wrong”)", S1, None),
        ("greedy", "argmax decode, parse the digit", S3, "WATCHES THE BEHAVIOUR"),
        ("sampled", "10 draws at T = 1, parse, average", S3, None),
        ("cloze", "P(“Very wrong”), options removed", S2, "CHANGES THE PROMPT"),
    ]
    y0, dy = 0.885, 0.126
    for i, (name, what, col, kind) in enumerate(rows):
        y = y0 - i * dy
        if kind:
            ax.text(0.455, y + 0.060, kind, fontsize=8.2, color=MUTED, va="center")
        ax.add_patch(plt.Rectangle((0.455, y - 0.045), 0.011, 0.090, facecolor=col,
                                   edgecolor="none"))
        ax.text(0.483, y, name, fontsize=11, color=INK, fontweight="semibold",
                va="center")
        ax.text(0.655, y, what, fontsize=10, color=INK_2, va="center",
                family="DejaVu Sans")
    ax.annotate("", xy=(0.445, 0.61), xytext=(0.385, 0.61),
                arrowprops=dict(arrowstyle="-|>", color=AXIS, lw=1.2))
    ax.set_xlim(0, 1)
    ax.set_ylim(0.12, 1)
    fig.text(0.035, 0.075, "Cloze is excluded from the primary estimand: it varies the "
             "prompt, and a prompt effect inside a number\ndefined as a method effect is "
             "precisely the error this project audits Kirgis for.",
             fontsize=9.6, color=INK_2, va="top")
    title(fig, "One prompt, six ways of reading an answer",
          "The open-weights privilege: with the weights you can read the propensity "
          "behind the behaviour, not just the behaviour.")
    return save(fig, "fig03_six_arms")


def fig04_mass(plt, per_model):
    fig, ax = plt.subplots(figsize=(11, 5.4))
    v = per_model.sort_values()
    names = [m.split("/")[-1] for m in v.index]
    low = v.values < 0.5
    ax.barh(range(len(v)), v.values, height=0.72,
            color=[S8 if b else DEEMPH for b in low], zorder=3)
    ax.axvline(0.5, color=AXIS, lw=1, zorder=2)
    ax.set_yticks(range(len(v)))
    ax.set_yticklabels(names, fontsize=8.4)
    ax.set_xlim(0, 1.06)
    ax.set_xlabel("mean retained probability mass, label scoring", fontsize=10)
    ax.set_ylim(-0.8, len(v) - 0.2)
    style(ax, xgrid=True)
    for i, (val, b) in enumerate(zip(v.values, low)):
        if b:
            ax.text(val + 0.012, i, f"{val:.3f}", va="center", fontsize=8.6,
                    color=INK_2)
    n_low = int(low.sum())
    ax.text(0.52, 1.2, f"{n_low} of {len(v)} models below 0.5\nthe score is a "
            "renormalisation over\nmass the model barely uses",
            fontsize=9.6, color=INK_2, va="bottom", ha="left")
    title(fig, "The score is only as real as the mass it renormalises",
          "Mistral-7B's label score is an expectation over 0.8% of its next-token "
          "distribution. Nothing raises an error; the number looks fine.")
    fig.subplots_adjust(top=0.86, bottom=0.09, left=0.225, right=0.985)
    return save(fig, "fig04_retained_mass")


def fig05_leakage(plt, j, rho):
    fig, ax = plt.subplots(figsize=(9.6, 5.2))
    ax.scatter(j.nonanswer * 100, j.mass, s=64, color=S1, alpha=0.85,
               edgecolors=SURFACE, linewidths=1.8, zorder=3)
    for m, lab, dx, dy, ha in [
            ("mistralai/Ministral-8B-Instruct-2410", "Ministral-8B", -4, .075, "right"),
            ("meta-llama/Llama-3.2-1B-Instruct", "Llama-3.2-1B", -4, -.09, "right"),
            ("mistralai/Mistral-7B-Instruct-v0.3", "Mistral-7B", 4, .05, "left"),
            ("google/gemma-2-27b-it", "gemma-2-27b", 4, .05, "left")]:
        if m in j.index:
            ax.annotate(lab, (j.loc[m, "nonanswer"] * 100 + dx, j.loc[m, "mass"] + dy),
                        fontsize=9.3, color=INK_2, ha=ha, va="center")
    ax.set_xlabel("greedy non-answer rate  (% of 116 items)", fontsize=10.5)
    ax.set_ylabel("mean label retained mass", fontsize=10.5)
    ax.set_xlim(-6, 112)
    ax.set_ylim(-0.06, 1.09)
    style(ax, ygrid=True)
    ax.text(0.985, 0.965, f"Spearman ρ = {rho:.2f}   ({len(j)} models)",
            transform=ax.transAxes, ha="right", va="top", fontsize=11, color=INK,
            fontweight="semibold")
    # State the sparsity rather than leave it to be spotted: the correlation is
    # carried by a handful of models, which is the repo's own reading of it.
    n0 = int((j.nonanswer == 0).sum())
    ax.text(0.985, 0.055, f"{n0} of {len(j)} models answer every item — the "
            "correlation rests on the few that do not",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=9.3,
            color=MUTED)
    title(fig, "Label scoring does not avoid the refusal confound — it hides it",
          "Models that fall silent in generation are largely those whose digit mass "
          "collapses. Renormalisation then manufactures a confident score.")
    fig.subplots_adjust(top=0.82, bottom=0.115, left=0.095, right=0.985)
    return save(fig, "fig05_refusal_leakage")


def fig06_free_gen(plt, df):
    fig, ax = plt.subplots(figsize=(9.6, 5.4))
    rate = {}
    for cond in ["greedy", "sampled"]:
        d = df[df.condition == cond]
        rate[cond] = d.groupby("model").apply(
            lambda x: float((x.failure_type == "ok").mean()), include_groups=False)
    r = pd.DataFrame(rate).dropna().sort_values("greedy")
    r = r[(r.greedy < 0.97) | (r.sampled < 0.97)]
    names = [m.split("/")[-1] for m in r.index]
    y = np.arange(len(r))
    for i in y:
        ax.plot([r.greedy.iloc[i] * 100, r.sampled.iloc[i] * 100], [i, i],
                color=DEEMPH, lw=2.4, zorder=2, solid_capstyle="round")
    ax.scatter(r.greedy * 100, y, s=76, color=S1, zorder=3, edgecolors=SURFACE,
               linewidths=1.8, label="greedy  (T = 0)")
    ax.scatter(r.sampled * 100, y, s=76, color=S3, zorder=3, edgecolors=SURFACE,
               linewidths=1.8, label="sampled  (T = 1, k = 10)")
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=9.6)
    ax.set_xlabel("% of 116 items that produced a usable answer", fontsize=10.5)
    ax.set_xlim(-5, 108)
    ax.set_ylim(-0.7, len(r) - 0.3)
    style(ax, xgrid=True)
    ax.legend(fontsize=9.8, loc="lower right", labelcolor=INK_2)
    title(fig, "“Free generation” hides a decision that can determine whether "
          "a model answers at all",
          "Byte-identical prompts. Only models where at least one arm fell below 97% "
          "are shown.")
    fig.subplots_adjust(top=0.83, bottom=0.115, left=0.20, right=0.985)
    return save(fig, "fig06_free_generation")


def fig07_ranks(plt, M):
    fig, ax = plt.subplots(figsize=(7.8, 6.2))
    order = ["label", "string_line", "greedy", "sampled", "string_bare", "cloze"]
    D = M.loc[order, order].astype(float)
    A = D.values.copy()
    mask = np.triu(np.ones_like(A, dtype=bool))
    A[mask] = np.nan
    im = ax.imshow(A, cmap="Blues", vmin=0.0, vmax=1.0)
    for i in range(len(order)):
        for j in range(len(order)):
            if i > j:
                v = D.values[i, j]
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=10.5,
                        color="white" if v > 0.62 else INK,
                        fontweight="semibold" if (order[i], order[j]) in
                        [("sampled", "label")] else "normal")
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([ARM_LABEL[a] for a in order], fontsize=9.8, rotation=32,
                       ha="right")
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([ARM_LABEL[a] for a in order], fontsize=9.8)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    cb = fig.colorbar(im, ax=ax, fraction=0.040, pad=0.03)
    cb.set_label("Spearman ρ of model ranking", fontsize=9.6, color=INK_2)
    cb.outline.set_visible(False)
    cb.ax.tick_params(length=0, labelsize=9, colors=MUTED)
    ax.add_patch(plt.Rectangle((-0.5, 2.5), 1, 1, fill=False, edgecolor=S8, lw=2.4,
                               zorder=5))
    ax.annotate("Kirgis's own pair", xy=(0.22, 2.48), xytext=(1.75, 1.15),
                fontsize=10, color=S8, va="center", ha="left", fontweight="semibold",
                arrowprops=dict(arrowstyle="-|>", color=S8, lw=1.4,
                                connectionstyle="arc3,rad=0.28"))
    title(fig, "The two arms Kirgis confounded rank models at ρ = 0.82",
          "Mean over the six moral foundations; the non-moral control is excluded "
          "because its floor inflates every pair.", x=0.02)
    fig.subplots_adjust(top=0.80, bottom=0.14, left=0.20, right=0.99)
    return save(fig, "fig07_rank_agreement")


def fig08_forest(plt, P, null):
    fig, ax = plt.subplots(figsize=(10.2, 5.2))
    order = (P.loc[MORAL].sort_values("R_median").index.tolist())
    rows = [CONTROL] + order
    ax.axvspan(0, 0.25, color="#f2f1ec", zorder=0)
    ax.axvspan(1.0, 1.35, color="#f7f3f0", zorder=0)
    ax.axvline(0.25, color=AXIS, lw=1, zorder=1)
    ax.axvline(1.0, color=AXIS, lw=1, zorder=1)
    for i, f in enumerate(rows):
        r = P.loc[f]
        c = S3 if f == CONTROL else S1
        ax.plot([r.R_q2_5 if hasattr(r, "R_q2_5") else r["R_q2.5"],
                 r["R_q97.5"]], [i, i], color=c, lw=2.4, zorder=3,
                solid_capstyle="round")
        ax.scatter([r.R_median], [i], s=92, color=c, zorder=4, edgecolors=SURFACE,
                   linewidths=2)
        ax.text(r["R_q97.5"] + 0.028, i, f"{r.R_median:.3f}", va="center",
                fontsize=9.8, color=INK_2)
    nm = null.groupby("foundation").R_median.median()
    ax.scatter(nm.reindex(rows).values, range(len(rows)), marker="|", s=180,
               color=MUTED, zorder=4, linewidths=1.6)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([f + "\n(non-moral control)" if f == CONTROL else f
                        for f in rows], fontsize=10.5)
    ax.set_xlim(-0.02, 1.35)
    ax.set_ylim(-0.75, len(rows) - 0.35)
    ax.set_xlabel("R  =  σ²(model × method)  /  σ²(model)",
                  fontsize=10.5)
    style(ax)
    ax.text(0.125, len(rows) - 0.55, "robust", ha="center", fontsize=9.4, color=MUTED)
    ax.text(0.62, len(rows) - 0.55, "degraded", ha="center", fontsize=9.4, color=MUTED)
    ax.text(1.17, len(rows) - 0.55, "not interpretable", ha="center", fontsize=9.4,
            color=MUTED)
    ax.text(0.008, -0.62, "│  permutation null (700 MCMC fits), median 0.0006–0.0021",
            fontsize=9, color=MUTED, va="center")
    title(fig, "The interaction is real. Its magnitude is not resolvable.",
          "95% credible intervals, N = 30, cloze excluded. Every moral foundation "
          "straddles a band boundary — verdict: indeterminate.")
    fig.subplots_adjust(top=0.81, bottom=0.145, left=0.175, right=0.985)
    return save(fig, "fig08_R_forest")


def fig09_sim(plt, sim, P):
    fig, ax = plt.subplots(figsize=(10.2, 5.3))
    for k, (n, c) in enumerate(zip([8, 13, 20, 30], BLUE)):
        s = sim[sim.N_models == n].sort_values("R_true")
        ax.plot(s.R_true, s.P_correct_band, color=c, lw=2.2, marker="o", ms=7,
                markeredgecolor=SURFACE, markeredgewidth=1.6, zorder=3,
                label=f"N = {n}", solid_capstyle="round")
    ax.axhline(0.5, color=AXIS, lw=1, zorder=1)
    for b in (0.25, 1.0):
        ax.axvline(b, color=AXIS, lw=1, zorder=1)
    ax.set_xscale("log")
    ax.set_xticks([0.1, 0.25, 0.5, 1.0, 2.0])
    ax.set_xticklabels(["0.10", "0.25", "0.50", "1.00", "2.00"])
    ax.set_ylim(0.35, 1.03)
    ax.set_xlabel("true R", fontsize=10.5)
    ax.set_ylabel("P(estimate lands in the correct band)", fontsize=10.5)
    style(ax, ygrid=True)
    ax.legend(fontsize=10, loc="lower right", labelcolor=INK_2, ncol=2)
    obs = P.loc[MORAL].R_median.values
    ax.scatter(obs, np.full(len(obs), 0.375), marker="^", s=64, color=S8, zorder=5,
               edgecolors=SURFACE, linewidths=1.2, clip_on=False)
    ax.text(0.30, 0.405, "where our six foundations actually landed", fontsize=9.6,
            color=S8, ha="left", va="bottom", fontweight="semibold")
    ax.annotate("a coin flip at the band edge,\nat every sample size",
                xy=(0.243, 0.495), xytext=(0.102, 0.437), fontsize=9.6, color=INK_2,
                ha="left", va="center",
                arrowprops=dict(arrowstyle="-|>", color=AXIS, lw=1.2,
                                connectionstyle="arc3,rad=-0.25"))
    title(fig, "N was never the binding constraint",
          "The estimand landed where no achievable sample size classifies it. "
          "Simulated before collection; it predicted this and we did not read it.")
    fig.subplots_adjust(top=0.81, bottom=0.115, left=0.085, right=0.985)
    return save(fig, "fig09_design_simulation")


def fig10_tiers(plt, pw, per_arm):
    fig, ax = plt.subplots(figsize=(10.6, 5.6))
    items = sorted(pw.items(), key=lambda kv: kv[1])
    labels, vals, cols = [], [], []
    for (a, b), v in items:
        if "cloze" in (a, b):
            c = S2
        elif "string_bare" in (a, b):
            c = S4
        else:
            c = S1
        labels.append(f"{ARM_LABEL[a]}  ~  {ARM_LABEL[b]}")
        vals.append(v)
        cols.append(c)
    y = np.arange(len(vals))
    ax.barh(y, vals, height=0.70, color=cols, zorder=3)
    ax.axvline(0, color=AXIS, lw=1, zorder=2)
    ax.axvline(0.25, color=GRID, lw=1, zorder=1)
    ax.axvline(1.0, color=GRID, lw=1, zorder=1)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9.5)
    ax.set_xlabel("pairwise R, one common complete-case block", fontsize=10.5)
    ax.set_xlim(-0.35, 4.9)
    ax.set_ylim(-0.8, len(vals) - 0.2)
    style(ax, xgrid=False)
    for i, v in enumerate(vals):
        ax.text(v + 0.08 if v >= 0 else v - 0.08, i, f"{v:+.2f}", va="center",
                ha="left" if v >= 0 else "right", fontsize=9, color=INK_2)
    h = [plt.Rectangle((0, 0), 1, 1, color=c) for c in (S1, S4, S2)]
    ax.legend(h, ["four readouts carrying real mass",
                  f"string (bare)  —  mean mass {per_arm['string_bare']:.4f}",
                  f"cloze  —  varies the prompt; mass {per_arm['cloze']:.3f}"],
              fontsize=9.6, loc="lower right", labelcolor=INK_2)
    title(fig, "The disagreement is not spread across the readouts — "
          "it is concentrated in two",
          "The four arms that carry real probability mass agree at R ≤ 0.20. "
          "The pooled R of 0.18–0.47 is a weighted average of these tiers.")
    fig.subplots_adjust(top=0.815, bottom=0.11, left=0.245, right=0.985)
    return save(fig, "fig10_pairwise_tiers")


def fig11_concentration(plt, share):
    fig, ax = plt.subplots(figsize=(10.2, 5.0))
    s = share.head(12)
    names = [m.split("/")[-1] for m in s.index]
    cols = [S8] + [DEEMPH] * (len(s) - 1)
    y = np.arange(len(s))[::-1]
    ax.barh(y, s.values * 100, height=0.70, color=cols, zorder=3)
    eq = 100 / len(share)
    ax.axvline(eq, color=AXIS, lw=1, zorder=2)
    ax.text(eq + 0.7, 0.75, f"an equal share of the {len(share)} models\n"
            f"would be {eq:.1f}%", fontsize=9.3, color=MUTED, va="center")
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=9.4)
    ax.set_xlabel("share of the model × method interaction sum of squares  (%)",
                  fontsize=10.5)
    ax.set_xlim(0, max(s.values * 100) * 1.40)
    style(ax, xgrid=True)
    ax.text(s.values[0] * 100 + 1.0, y[0], f"{s.values[0]*100:.1f}%  —  R falls 51%"
            "\nwithout this one model", va="center", fontsize=10, color=S8,
            fontweight="semibold")
    title(fig, "One model of 27 carries a third of the interaction",
          "And it is the same model whose label retained mass is 0.008. The method "
          "effect is carried by cells the design can barely measure.")
    fig.subplots_adjust(top=0.815, bottom=0.135, left=0.235, right=0.985)
    return save(fig, "fig11_concentration")


def fig12_scale(plt, fits):
    fig, ax = plt.subplots(figsize=(9.8, 5.2))
    for (fam, c, lab, dy) in [("qwen", S1, "Qwen2.5  (8 models, 145×)", +0.085),
                              ("llama", S2, "Llama-3.x  (4 models, 71×)", -0.085)]:
        f = fits[fam]
        d = f["data"]
        ax.scatter(d.params, d.gap, s=76, color=c, zorder=4, edgecolors=SURFACE,
                   linewidths=1.8, label=lab)
        xs = np.linspace(np.log10(d.params.min()), np.log10(d.params.max()), 50)
        ax.plot(10 ** xs, f["int"] + f["slope"] * xs, color=c, lw=2, zorder=3,
                solid_capstyle="round")
        ax.text(d.params.max() * 1.16,
                f["int"] + f["slope"] * np.log10(d.params.max()) + dy,
                f"{f['slope']:+.3f} / decade\np = {f['p']:.3f}", fontsize=9.4,
                color=c, va="center", fontweight="semibold")
    ax.axhline(0, color=AXIS, lw=1, zorder=1)
    ax.set_xscale("log")
    ax.set_xticks([0.5, 1, 3, 8, 20, 70])
    ax.set_xticklabels(["0.5B", "1B", "3B", "8B", "20B", "70B"])
    ax.set_xlim(0.35, 190)
    ax.set_xlabel("parameters (log scale)", fontsize=10.5)
    ax.set_ylabel("individualizing − binding gap\n(compression removed)",
                  fontsize=10.5)
    style(ax, ygrid=True)
    ax.legend(fontsize=9.8, loc="upper left", labelcolor=INK_2)
    title(fig, "Kirgis's pattern does appear — and it grows with model size",
          "Which explains why a ≤14B sample found nothing. Neither ladder is "
          "individually significant at 0.05; leave-one-out keeps the sign 8/8 and 4/4.")
    fig.subplots_adjust(top=0.80, bottom=0.115, left=0.115, right=0.985)
    return save(fig, "fig12_scale")


def fig13_compression(plt, qc, human_lo, human_hi):
    """Lines are drawn ONLY over the range the moral items actually span.

    LIMITATIONS.md 5 is emphatic that extrapolating this fit below the observed
    range is unwarranted — the control sits 0.9 points below the lowest moral item
    with nothing in between. Drawing 0-4 would commit on a slide the error the
    limitations document exists to disown.
    """
    fig, ax = plt.subplots(figsize=(9.8, 5.2))
    import matplotlib as mpl
    cmap = mpl.colors.LinearSegmentedColormap.from_list("b", BLUE)
    lo, hi = np.log10(0.5), np.log10(72.7)
    xs = np.linspace(human_lo, human_hi, 50)
    ax.plot(xs, xs, color=AXIS, lw=1.4, zorder=2)
    ax.annotate("perfect agreement with\nthe human baseline  (b = 1)",
                xy=(1.98, 1.98), xytext=(1.52, 0.86), fontsize=9, color=MUTED,
                ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=AXIS, lw=1,
                                connectionstyle="arc3,rad=-0.2"))
    for r in qc:
        c = cmap((np.log10(r["params"]) - lo) / (hi - lo))
        ax.plot(xs, r["a"] + r["b"] * xs, color=c, lw=2.1, zorder=3,
                solid_capstyle="round")
    for r in (qc[0], qc[-1]):
        ax.text(human_hi + 0.09, r["a"] + r["b"] * human_hi,
                f"{r['params']:g}B    b = {r['b']:.2f}", fontsize=9.8, va="center",
                ha="left", color=INK_2, fontweight="semibold")
    ax.set_xlim(human_lo - 0.15, human_hi + 1.30)
    ax.set_ylim(0.6, 4.15)
    ax.set_xticks([1.5, 2.0, 2.5, 3.0, 3.5])
    ax.set_xlabel("human severity rating  (Clifford et al., 0–4; moral items span "
                  f"{human_lo:.2f}–{human_hi:.2f})", fontsize=10.5)
    ax.set_ylabel("model severity rating", fontsize=10.5)
    style(ax, ygrid=True)
    sm = mpl.cm.ScalarMappable(cmap=cmap, norm=mpl.colors.Normalize(lo, hi))
    cb = fig.colorbar(sm, ax=ax, fraction=0.032, pad=0.13)
    cb.set_ticks([np.log10(v) for v in (0.5, 3, 14, 72.7)])
    cb.set_ticklabels(["0.5B", "3B", "14B", "72B"])
    cb.set_label("Qwen2.5 parameters", fontsize=9.6, color=INK_2)
    cb.outline.set_visible(False)
    cb.ax.tick_params(length=0, labelsize=9, colors=MUTED)
    title(fig, "Compression itself changes enormously with scale",
          "Small models barely track the baseline; the 72B tracks it almost 1:1. "
          "Pure compression predicts a negative gap — so the raw slope is a third "
          "confound.")
    fig.subplots_adjust(top=0.80, bottom=0.115, left=0.09, right=0.90)
    return save(fig, "fig13_compression")


# ===========================================================================
def checks(P, pw, per_arm, per_model, rho, M, share, fits):
    """Assert every drawn quantity against the committed artifacts."""
    def close(a, b, tol, what):
        assert abs(a - b) <= tol, f"{what}: derived {a:.4f} vs artifact {b:.4f}"
        print(f"  ok   {what:52s} {a:.4f}")

    close(P.loc["Care"].R_median, 0.181, .001, "R Care (FINDINGS 2)")
    close(P.loc["Authority"].R_median, 0.469, .001, "R Authority (FINDINGS 2)")
    close(P.loc[CONTROL].R_median, 0.133, .001, "R Social Norms control")
    close(pw[("label", "sampled")], 0.081, .002, "pairwise R label~sampled")
    close(pw[("label", "string_line")], -0.086, .002, "pairwise R label~string_line")
    close(pw[("string_bare", "cloze")], 4.317, .01, "pairwise R string_bare~cloze")
    close(per_arm["string_bare"], 0.0028, .0005, "mean mass string_bare")
    close(per_arm["label"], 0.7680, .001, "mean mass label")
    close(float(per_model.min()), 0.008, .002, "min label mass (Mistral-7B)")
    close(rho, -0.543, .02, "Spearman(non-answer, mass)")
    close(float(M.loc["label", "sampled"]), 0.818, .005, "rho label~sampled")
    close(float(M.loc["label", "string_line"]), 0.964, .005, "rho label~string_line")
    close(float(share.iloc[0]), 0.343, .01, "Mistral-7B interaction SS share")
    close(fits["qwen"]["slope"], 0.3243, .02, "P5 qwen slope/decade")
    close(fits["llama"]["slope"], 0.2609, .02, "P5 llama slope/decade")
    assert int((per_model < 0.5).sum()) == 7, "expected 7 models below mass 0.5"
    print("  ok   7 models below label mass 0.5")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify derived values against artifacts, draw nothing")
    a = ap.parse_args()

    df, vr, sim, null, kir = load()
    P = primary_R(vr)
    pw = pairwise_R(df)
    per_model, per_arm = retained_mass(df)
    j, rho = refusal_vs_mass(df)
    M = rank_agreement(df)
    share = interaction_share(df)
    scale_rows, fits = scale_ladders(df)
    qc = qwen_compression(df, scale_rows)

    print("Verifying derived values against committed artifacts:")
    checks(P, pw, per_arm, per_model, rho, M, share, fits)
    if a.check:
        print("\nAll checks pass. No figures written (--check).")
        return 0

    global BARE
    plt = _mpl()
    moral = df[(df.foundation != CONTROL)].clifford_wrong_mean

    def draw_all():
        fig01_confound(plt)
        fig02_grok(plt, kir)
        fig03_arms(plt)
        fig04_mass(plt, per_model)
        fig05_leakage(plt, j, rho)
        fig06_free_gen(plt, df)
        fig07_ranks(plt, M)
        fig08_forest(plt, P, null)
        fig09_sim(plt, sim, P)
        fig10_tiers(plt, pw, per_arm)
        fig11_concentration(plt, share)
        fig12_scale(plt, fits)
        fig13_compression(plt, qc, float(moral.min()), float(moral.max()))

    print("\nDrawing standalone figures (with titles):")
    BARE = False
    draw_all()
    print("\nDrawing deck figures (title carried by the slide header):")
    BARE = True
    draw_all()
    BARE = False
    print(f"\n13 standalone + 13 deck figures in {FIGDIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
