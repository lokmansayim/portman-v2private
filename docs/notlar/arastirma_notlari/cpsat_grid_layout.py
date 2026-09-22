"""
Small benchmark: CP-SAT room placement on a modular panel grid.
Module = 125.5 cm. Envelope W x H modules. Rooms are axis-aligned rectangles
in module units that must tile the envelope exactly (rectangular dissection).
Constraints: no overlap, full coverage, min area / min narrow side, adjacency
(shared wall segment >= 1 module), exterior-wall requirement for rooms needing
windows, entrance side, wet-room adjacency. Objective: minimise deviation from
target areas. Reports wall-clock solve times.
"""
import time, sys, itertools
from ortools.sat.python import cp_model

MOD = 1.255  # m per module
CELL_M2 = MOD * MOD  # 1.575 m2 per cell

def build(W, H, rooms, adj_pairs, exterior_rooms, hub, entrance_side="S", objective=True, sym_break=True):
    m = cp_model.CpModel()
    X, Y, WW, HH, A = {}, {}, {}, {}, {}
    xi, yi = [], []
    for r, spec in rooms.items():
        X[r] = m.NewIntVar(0, W, f"x_{r}")
        Y[r] = m.NewIntVar(0, H, f"y_{r}")
        WW[r] = m.NewIntVar(spec["min_side"], W, f"w_{r}")
        HH[r] = m.NewIntVar(spec["min_side"], H, f"h_{r}")
        A[r] = m.NewIntVar(spec["min_cells"], W * H, f"a_{r}")
        m.AddMultiplicationEquality(A[r], [WW[r], HH[r]])
        x2 = m.NewIntVar(0, W, f"x2_{r}"); y2 = m.NewIntVar(0, H, f"y2_{r}")
        xi.append(m.NewIntervalVar(X[r], WW[r], x2, f"xi_{r}"))
        yi.append(m.NewIntervalVar(Y[r], HH[r], y2, f"yi_{r}"))
        if "max_cells" in spec:
            m.Add(A[r] <= spec["max_cells"])
        if "max_side" in spec:
            m.Add(WW[r] <= spec["max_side"]); m.Add(HH[r] <= spec["max_side"])
    m.AddNoOverlap2D(xi, yi)
    m.Add(sum(A.values()) == W * H)  # full coverage => exact tiling

    def adjacent(r, s):
        # share a wall segment of length >= 1 module
        b = []
        for (ra, rb) in [(r, s), (s, r)]:
            # rb is immediately right of ra, with vertical overlap >= 1
            lit = m.NewBoolVar(f"adjR_{ra}_{rb}")
            m.Add(X[ra] + WW[ra] == X[rb]).OnlyEnforceIf(lit)
            m.Add(Y[ra] < Y[rb] + HH[rb]).OnlyEnforceIf(lit)
            m.Add(Y[rb] < Y[ra] + HH[ra]).OnlyEnforceIf(lit)
            b.append(lit)
            lit2 = m.NewBoolVar(f"adjU_{ra}_{rb}")
            m.Add(Y[ra] + HH[ra] == Y[rb]).OnlyEnforceIf(lit2)
            m.Add(X[ra] < X[rb] + WW[rb]).OnlyEnforceIf(lit2)
            m.Add(X[rb] < X[ra] + WW[ra]).OnlyEnforceIf(lit2)
            b.append(lit2)
        m.AddBoolOr(b)

    for (r, s) in adj_pairs:
        adjacent(r, s)
    for r in rooms:
        if r != hub:
            adjacent(r, hub)  # every room opens off the hub (hol) -> door feasibility

    for r in exterior_rooms:  # needs a window -> touches envelope
        lits = []
        for cond in [X[r] == 0, X[r] + WW[r] == W, Y[r] == 0, Y[r] + HH[r] == H]:
            l = m.NewBoolVar(""); m.Add(cond).OnlyEnforceIf(l); lits.append(l)
        m.AddBoolOr(lits)
    # entrance: hub touches the entrance side
    if entrance_side == "S":
        m.Add(Y[hub] == 0)
    if sym_break:
        pass  # entrance side already breaks the up/down mirror symmetry

    if objective:
        devs = []
        for r, spec in rooms.items():
            if "target_cells" in spec:
                d = m.NewIntVar(0, W * H, f"dev_{r}")
                m.AddAbsEquality(d, A[r] - spec["target_cells"])
                devs.append(d)
        m.Minimize(sum(devs))
    return m, (X, Y, WW, HH, A)

def solve(m, vars_, workers=8, tlimit=60, enumerate_all=False, log=False):
    s = cp_model.CpSolver()
    s.parameters.num_workers = workers
    s.parameters.max_time_in_seconds = tlimit
    s.parameters.log_search_progress = log
    if enumerate_all:
        s.parameters.enumerate_all_solutions = True
        s.parameters.num_workers = 1
        class Cnt(cp_model.CpSolverSolutionCallback):
            def __init__(self): super().__init__(); self.n = 0
            def on_solution_callback(self): self.n += 1
        cb = Cnt(); t = time.time(); st = s.Solve(m, cb); return st, time.time() - t, cb.n, s
    t = time.time(); st = s.Solve(m); return st, time.time() - t, None, s

def show(s, vars_, W, H):
    X, Y, WW, HH, A = vars_
    grid = [["." for _ in range(W)] for _ in range(H)]
    for r in X:
        x, y, w, h = s.Value(X[r]), s.Value(Y[r]), s.Value(WW[r]), s.Value(HH[r])
        for i in range(x, x + w):
            for j in range(y, y + h):
                grid[H - 1 - j][i] = r[0].upper()
        print(f"  {r:8s} x={x} y={y} w={w} h={h} cells={w*h} ~{w*h*CELL_M2:.1f} m2 ({w*MOD:.2f}x{h*MOD:.2f} m)")
    for row in grid: print("   " + " ".join(row))

if __name__ == "__main__":
    # 2+1, 8 x 6 modules = 10.04 x 7.53 m = 75.6 m2 gross
    W, H = 8, 6
    # min_side/min_cells derived from Planli Alanlar Imar Yon. Madde 31 (net) + module rounding
    rooms = {
        "salon":  dict(min_side=3, min_cells=8,  target_cells=12),  # >=3.00 m narrow side, >=12 m2 -> 8 cells
        "mutfak": dict(min_side=2, min_cells=3,  target_cells=4),   # >=1.50 m / 3.3 m2 -> 2 modules side
        "yatak1": dict(min_side=2, min_cells=6,  target_cells=8),   # >=2.40 m / 8 m2 -> 6 cells (9.4 m2)
        "yatak2": dict(min_side=2, min_cells=6,  target_cells=6),
        "banyo":  dict(min_side=1, min_cells=2,  target_cells=2, max_cells=3),  # >=1.20 m / 3 m2 -> 2 cells (3.15 m2)
        "hol":    dict(min_side=1, min_cells=2,  target_cells=4, max_side=6),
    }
    adj = [("mutfak", "salon"), ("banyo", "mutfak")]  # wet rooms share a wall (plumbing)
    exterior = ["salon", "mutfak", "yatak1", "yatak2", "banyo"]
    for (label, obj) in [("feasibility only", False), ("min area deviation", True)]:
        m, v = build(W, H, rooms, adj, exterior, hub="hol", objective=obj)
        st, dt, _, s = solve(m, v, workers=8, tlimit=60)
        print(f"[{W}x{H}, 6 rooms, {label}] status={s.StatusName(st)} time={dt:.3f}s obj={s.ObjectiveValue() if obj else '-'}")
        if st in (cp_model.OPTIMAL, cp_model.FEASIBLE): show(s, v, W, H)
    # enumerate all feasible tilings (no objective) with 1 worker, 60 s cap
    m, v = build(W, H, rooms, adj, exterior, hub="hol", objective=False)
    st, dt, n, s = solve(m, v, enumerate_all=True, tlimit=60)
    print(f"[{W}x{H} enumerate] status={s.StatusName(st)} solutions={n} time={dt:.2f}s")
    # larger: 3+1 on 10 x 8 modules (12.55 x 10.04 m = 126 m2)
    W, H = 10, 8
    rooms3 = dict(rooms)
    rooms3["yatak3"] = dict(min_side=2, min_cells=6, target_cells=6)
    rooms3["salon"] = dict(min_side=3, min_cells=8, target_cells=16)
    rooms3["wc"] = dict(min_side=1, min_cells=1, target_cells=1, max_cells=2)
    rooms3["hol"] = dict(min_side=1, min_cells=2, target_cells=6, max_side=8)
    adj3 = adj + [("wc", "banyo")]
    ext3 = exterior + ["yatak3"]
    m, v = build(W, H, rooms3, adj3, ext3, hub="hol", objective=True)
    st, dt, _, s = solve(m, v, workers=8, tlimit=120)
    print(f"[{W}x{H}, 8 rooms, min deviation] status={s.StatusName(st)} time={dt:.3f}s obj={s.ObjectiveValue()}")
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE): show(s, v, W, H)
    import ortools; print("ortools", ortools.__version__)
