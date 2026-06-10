from pathlib import Path

import yaml
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch

from read import read_2e_ctp_instance
from utils import prepare_data


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "run_examples.yaml"


def _var_value(var):
    try:
        return var.X
    except AttributeError:
        return var.x


def _draw_base(ax, inst):
    legend_handles = []

    if inst.DEPOT is not None:
        dx, dy = inst.DEPOT
        depot_artist = ax.scatter([dx], [dy], s=180, c="#111111", marker="*", label="Depot", zorder=5)
        ax.annotate("Depot", (dx, dy), textcoords="offset points", xytext=(8, 8), fontsize=10, fontweight="bold", color="#111111")
        legend_handles.append(depot_artist)

    node_x = [n.x for n in inst.demands.values()]
    node_y = [n.y for n in inst.demands.values()]
    node_artist = ax.scatter(node_x, node_y, s=70, c="#1f77b4", marker="o", label="Nodes", zorder=3)
    legend_handles.append(node_artist)

    for node in inst.demands.values():
        ax.annotate(str(node.id), (node.x, node.y), textcoords="offset points", xytext=(6, 6), fontsize=9, color="#1f77b4")

    cover_x = [c.x for c in inst.covers.values()]
    cover_y = [c.y for c in inst.covers.values()]
    cover_artist = ax.scatter(cover_x, cover_y, s=120, c="#ff7f0e", marker="D", label="Covering Nodes", zorder=4)
    legend_handles.append(cover_artist)

    for cover in inst.covers.values():
        ax.annotate(f"C{cover.id - 1000}", (cover.x, cover.y), textcoords="offset points", xytext=(8, 8), fontsize=10, fontweight="bold", color="#ff7f0e")

    hub_x = [h.x for h in inst.hubs.values()]
    hub_y = [h.y for h in inst.hubs.values()]
    hub_artist = ax.scatter(hub_x, hub_y, s=180, c="#d62728", marker="s", label="Hubs", zorder=4)
    legend_handles.append(hub_artist)

    for hub in inst.hubs.values():
        ax.annotate(f"H{hub.id - 2000}", (hub.x, hub.y), textcoords="offset points", xytext=(8, 8), fontsize=10, fontweight="bold", color="#d62728")

    return legend_handles


def _draw_arrow(ax, start, end, color, linestyle="-", linewidth=1.8, mutation_scale=12, offset=0.0):
    if start == end:
        return None

    # compute perpendicular unit vector for offset
    dx_line = end[0] - start[0]
    dy_line = end[1] - start[1]
    perp_x = dy_line
    perp_y = -dx_line
    norm = (perp_x * perp_x + perp_y * perp_y) ** 0.5

    if norm > 0 and offset != 0.0:
        perp_x /= norm
        perp_y /= norm
        shifted_start = (start[0] + perp_x * offset, start[1] + perp_y * offset)
        shifted_end = (end[0] + perp_x * offset, end[1] + perp_y * offset)
    else:
        shifted_start = start
        shifted_end = end

    arrow = FancyArrowPatch(
        shifted_start,
        shifted_end,
        arrowstyle="-|>",
        mutation_scale=mutation_scale,
        linewidth=linewidth,
        color=color,
        linestyle=linestyle,
        shrinkA=8,
        shrinkB=8,
        zorder=6,
    )
    ax.add_patch(arrow)
    return arrow


def _draw_arc_label(ax, start, end, text, color, y_offset=0.0, perp=None):
    mid_x = (start[0] + end[0]) / 2
    mid_y = (start[1] + end[1]) / 2

    if perp is None:
        dx = end[1] - start[1]
        dy = start[0] - end[0]
        norm = (dx * dx + dy * dy) ** 0.5

        if norm > 0:
            dx /= norm
            dy /= norm
        else:
            dx = dy = 0.0
    else:
        dx, dy = perp

    ax.annotate(
        text,
        (mid_x + dx * y_offset, mid_y + dy * y_offset),
        textcoords="offset points",
        xytext=(0, 0),
        ha="center",
        va="center",
        fontsize=8,
        color=color,
        bbox={"boxstyle": "round,pad=0.2", "fc": "white", "ec": color, "alpha": 0.85},
        zorder=7,
    )


def _arc_load_value(y_vars, i, j, demands):
    load = 0.0
    for demand_id, demand in demands.items():
        var = y_vars.get((i, j, demand_id))
        if var is None:
            continue
        load += demand.demand * _var_value(var)
    return load


def _draw_cover_assignments(ax, inst, model=None, z=None, min_value=1e-6):
    has_assignment = False

    if z is None and model is not None and hasattr(model, "_vars"):
        z = model._vars.get("z", {})

    if not z:
        return has_assignment

    for demand_id, demand in inst.demands.items():
        for cover_id, cover in inst.covers.items():
            var = z.get((demand_id, cover_id))
            if var is None:
                continue

            value = _var_value(var)
            if value <= min_value:
                continue

            ax.plot(
                [demand.x, cover.x],
                [demand.y, cover.y],
                color="#7f7f7f",
                linestyle=":",
                linewidth=1.1,
                alpha=0.45,
                zorder=2,
            )
            has_assignment = True

    return has_assignment


def _draw_solution(ax, inst, model=None, x1=None, x2=None, min_value=1e-6):
    coord = inst.COORD
    # use instance x-range (max_x - min_x) as stable offset scale (same for all arcs)
    xs = [p[0] for p in coord.values()] if coord else [0.0]
    x_range = max(xs) - min(xs) if xs else 1.0
    if x_range == 0:
        x_range = 1.0
    base_scale = 0.005 * x_range
    y1 = None
    y2 = None
    has_x1 = False
    has_x2 = False

    if x1 is None and model is not None and hasattr(model, "_vars"):
        x1 = model._vars.get("x1", {})
    if x2 is None and model is not None and hasattr(model, "_vars"):
        x2 = model._vars.get("x2", {})
    if model is not None and hasattr(model, "_vars"):
        y1 = model._vars.get("y1", {})
        y2 = model._vars.get("y2", {})

    if x1:
        for (i, j), var in x1.items():
            value = _var_value(var)
            if abs(value) <= min_value:
                continue
            start = coord[i]
            end = coord[j]
            # compute offset magnitude proportional to distance (reduced)
            ddx = end[0] - start[0]
            ddy = end[1] - start[1]
            dist = (ddx * ddx + ddy * ddy) ** 0.5
            base_offset = base_scale
            # compute canonical perpendicular based on ordered pair so both directions share same perp
            a, b = (i, j) if i < j else (j, i)
            can_start = coord[a]
            can_end = coord[b]
            pdx = can_end[0] - can_start[0]
            pdy = can_end[1] - can_start[1]
            perp_x = pdy
            perp_y = -pdx
            pnorm = (perp_x * perp_x + perp_y * perp_y) ** 0.5
            if pnorm > 0:
                perp_x /= pnorm
                perp_y /= pnorm
            else:
                perp_x = perp_y = 0.0

            # decide sign: +1 if arc goes from smaller->larger id, -1 otherwise
            if (j, i) in x1:
                sign = 1 if i < j else -1
            else:
                sign = 0

            arrow_offset = sign * base_offset
            # apply canonical perp for consistent opposite displacement
            shifted_start = (start[0] + perp_x * arrow_offset, start[1] + perp_y * arrow_offset) if arrow_offset != 0 else start
            shifted_end = (end[0] + perp_x * arrow_offset, end[1] + perp_y * arrow_offset) if arrow_offset != 0 else end
            _draw_arrow(ax, shifted_start, shifted_end, color="#1f4e79", linestyle="-", linewidth=2.0, offset=0.0)
            if y1 and value > min_value:
                load_value = _arc_load_value(y1, i, j, inst.demands)
                if sign != 0:
                    label_offset = sign * base_offset * 2
                else:
                    label_offset = 0.0
                _draw_arc_label(ax, start, end, f"{load_value:g}", color="#1f4e79", y_offset=label_offset, perp=(perp_x, perp_y))
            has_x1 = True

    if x2:
        for (i, j), var in x2.items():
            value = _var_value(var)
            if abs(value) <= min_value:
                continue
            start = coord[i]
            end = coord[j]
            # compute offset magnitude proportional to distance (reduced)
            ddx = end[0] - start[0]
            ddy = end[1] - start[1]
            dist = (ddx * ddx + ddy * ddy) ** 0.5
            base_offset = base_scale
            # compute canonical perpendicular based on ordered pair so both directions share same perp
            a, b = (i, j) if i < j else (j, i)
            can_start = coord[a]
            can_end = coord[b]
            pdx = can_end[0] - can_start[0]
            pdy = can_end[1] - can_start[1]
            perp_x = pdy
            perp_y = -pdx
            pnorm = (perp_x * perp_x + perp_y * perp_y) ** 0.5
            if pnorm > 0:
                perp_x /= pnorm
                perp_y /= pnorm
            else:
                perp_x = perp_y = 0.0

            # decide sign for x2 on same hub
            if (j, i) in x2:
                sign = 1 if i < j else -1
            else:
                sign = 0

            arrow_offset = sign * base_offset
            shifted_start = (start[0] + perp_x * arrow_offset, start[1] + perp_y * arrow_offset) if arrow_offset != 0 else start
            shifted_end = (end[0] + perp_x * arrow_offset, end[1] + perp_y * arrow_offset) if arrow_offset != 0 else end
            _draw_arrow(ax, shifted_start, shifted_end, color="#c44e52", linestyle="--", linewidth=2.0, offset=0.0)
            if y2 and value > min_value:
                load_value = _arc_load_value(y2, i, j, inst.demands)
                if sign != 0:
                    label_offset = sign * base_offset * 2
                else:
                    label_offset = 0.0
                _draw_arc_label(ax, start, end, f"{load_value:g}", color="#c44e52", y_offset=label_offset, perp=(perp_x, perp_y))
            has_x2 = True

    return has_x1, has_x2


def plot_instance(file_path, show=True, save_path=None):
    inst = prepare_data(read_2e_ctp_instance(file_path))

    fig, ax = plt.subplots(figsize=(10, 8))
    legend_handles = _draw_base(ax, inst)

    title = getattr(inst, "NAME", Path(file_path).stem)
    ax.set_title(f"2D Visualization - {title}")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.grid(True, linestyle="--", alpha=0.3)
    ax.set_aspect("equal", adjustable="datalim")
    ax.legend(handles=legend_handles)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches="tight")

    if show:
        plt.show()

    return fig, ax, inst


def plot_solution(file_path, model=None, x1=None, x2=None, show=True, save_path=None, min_value=1e-6):
    inst = prepare_data(read_2e_ctp_instance(file_path))

    fig, ax = plt.subplots(figsize=(10, 8))
    legend_handles = _draw_base(ax, inst)
    has_assignment = _draw_cover_assignments(ax, inst, model=model, min_value=min_value)
    has_x1, has_x2 = _draw_solution(ax, inst, model=model, x1=x1, x2=x2, min_value=min_value)

    if has_assignment:
        legend_handles.append(Line2D([0], [0], color="#7f7f7f", lw=1.1, linestyle=":", label="Demand to covering node"))
    if has_x1:
        legend_handles.append(Line2D([0], [0], color="#1f4e79", lw=2.0, label="Route of the large trucks"))
    if has_x2:
        legend_handles.append(Line2D([0], [0], color="#c44e52", lw=2.0, linestyle="--", label="Route of the small trucks"))

    title = getattr(inst, "NAME", Path(file_path).stem)
    ax.set_title(f"2D Visualization - {title} (Gurobi solution)")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.grid(True, linestyle="--", alpha=0.3)
    ax.set_aspect("equal", adjustable="datalim")
    ax.legend(handles=legend_handles)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=300, bbox_inches="tight")

    if show:
        plt.show()

    return fig, ax, inst


def _load_first_instance_path(config_path=DEFAULT_CONFIG_PATH):
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    examples = config.get("examples", [])
    if not examples:
        raise ValueError(f"No examples found in {config_path}")

    instance_value = examples[0]["instance"]
    instance_path = Path(instance_value)
    if not instance_path.is_absolute():
        instance_path = (PROJECT_ROOT / instance_path).resolve()
    return instance_path


if __name__ == "__main__":
    instance_path = _load_first_instance_path()
    plot_instance(instance_path)
