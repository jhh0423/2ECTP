"""Run PuLP solver configurations from YAML."""

from pathlib import Path

import yaml

# Ensure imports work when this file is executed as a script
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / 'scripts'
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from pulp_solver.solver import run
from visualize import plot_solution


DEFAULT_CONFIG = PROJECT_ROOT / 'configs' / 'run_examples.yaml'


def main():
    with open(DEFAULT_CONFIG, 'r', encoding='utf-8') as f:
        examples = yaml.safe_load(f)['examples']

    figure_dir = PROJECT_ROOT / 'tests' / 'figures'
    figure_dir.mkdir(parents=True, exist_ok=True)

    for ex in examples:
        instance_path = (PROJECT_ROOT / ex['instance']).resolve()
        print(f"Running example: {instance_path.name} -> instance={instance_path}")
        model = run(str(instance_path), write_lp=True)
        if model is not None:
            save_path = figure_dir / f"{instance_path.stem}_solution.png"
            plot_solution(instance_path, model=model, show=True, save_path=save_path)


if __name__ == '__main__':
    main()